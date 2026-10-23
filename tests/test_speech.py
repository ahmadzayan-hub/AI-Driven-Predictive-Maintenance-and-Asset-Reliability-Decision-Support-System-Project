"""The optional voice service never needs a model download or live microphone.

Adapters make load, failure and contention reproducible. Real decoder checks
run only when the optional voice package is installed, using generated audio.
"""

import io
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import wave

from server.speech import LocalSpeech, MODEL_FILES, MAX_BYTES, SpeechError, _decode

try:
    from fastapi.testclient import TestClient
    from server.app import create_app
    from tests.support import scoped_token as issue_local_test_token
    from tests.support import closing
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False


def complete_model(root):
    path = Path(root) / "model"
    path.mkdir()
    for name in MODEL_FILES:
        (path / name).write_bytes(b"test fixture, not model weights")
    return path


def service_for(path, *, factory=None, decoder=None):
    factory = factory or Mock(return_value=SimpleNamespace(
        transcribe=Mock(return_value=([SimpleNamespace(text="  Hello  world ")], None))))
    return LocalSpeech({"AGENTIC_OS_WHISPER_ENABLED": "1",
                        "AGENTIC_OS_WHISPER_MODEL_DIR": str(path)},
                       model_factory=factory, decoder=decoder or Mock(return_value="audio"),
                       package_check=lambda: True)


class LocalSpeechTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = complete_model(self.temp.name)

    def assert_code(self, code, callback):
        with self.assertRaises(SpeechError) as raised:
            callback()
        self.assertEqual(raised.exception.code, code)

    def test_disabled_never_imports_or_loads_a_model(self):
        check, factory = Mock(), Mock()
        service = LocalSpeech({}, package_check=check, model_factory=factory)
        self.assertEqual(service.status(), {
            "enabled": False, "available": False, "provider": "faster-whisper",
            "model": None, "max_seconds": 30, "max_bytes": 2_000_000})
        self.assert_code("unavailable", lambda: service.transcribe(b"x", "audio/webm", "en"))
        check.assert_not_called()
        factory.assert_not_called()

    def test_relative_missing_or_incomplete_model_never_reaches_a_loader(self):
        for path in ("small", str(self.path / "absent")):
            factory = Mock()
            service = LocalSpeech({"AGENTIC_OS_WHISPER_ENABLED": "1",
                                   "AGENTIC_OS_WHISPER_MODEL_DIR": path},
                                  model_factory=factory, package_check=lambda: True)
            self.assertFalse(service.status()["available"])
            factory.assert_not_called()
        (self.path / "tokenizer.json").unlink()
        self.assertFalse(service_for(self.path).status()["available"])

    def test_package_absence_is_unavailable_and_status_never_discloses_path(self):
        service = service_for(self.path)
        service._package_check = lambda: False
        self.assertFalse(service.status()["available"])
        service._package_check = lambda: True
        self.assertEqual(service.status()["model"], "local-whisper")
        self.assertNotIn(str(self.path), json.dumps(service.status()))

    def test_lazy_local_only_cpu_load_is_reused_and_preserves_requested_language(self):
        model = SimpleNamespace(transcribe=Mock(return_value=(
            [SimpleNamespace(text="  أهلاً   بك ")], None)))
        factory = Mock(return_value=model)
        decoder = Mock(return_value="waveform")
        service = service_for(self.path, factory=factory, decoder=decoder)
        self.assertTrue(service.status()["available"])
        factory.assert_not_called()
        result = service.transcribe(b"webm", "audio/webm;codecs=opus", "ar")
        self.assertEqual(result, {"text": "أهلاً بك", "language": "ar", "provider": "faster-whisper"})
        service.transcribe(b"ogg", "audio/ogg", "en")
        factory.assert_called_once_with(str(self.path), device="cpu", compute_type="int8",
                                        cpu_threads=4, num_workers=1, local_files_only=True)
        self.assertEqual(decoder.call_args_list[0].args, (b"webm", "matroska"))
        self.assertEqual(model.transcribe.call_args_list[0].kwargs["language"], "ar")
        self.assertTrue(model.transcribe.call_args.kwargs["vad_filter"])

    def test_invalid_type_size_empty_and_language_are_rejected_before_model_load(self):
        factory, decoder = Mock(), Mock()
        service = service_for(self.path, factory=factory, decoder=decoder)
        for code, payload, mime, language in [
            ("unsupported", b"x", "text/plain", "en"),
            ("too_large", b"x" * (MAX_BYTES + 1), "audio/webm", "en"),
            ("no_speech", b"", "audio/webm", "en"),
            ("language", b"x", "audio/webm", "fr"),
        ]:
            self.assert_code(code, lambda: service.transcribe(payload, mime, language))
        factory.assert_not_called()
        decoder.assert_not_called()

    def test_failed_model_load_does_not_leak_details_or_retry_every_request(self):
        factory = Mock(side_effect=RuntimeError("secret-local-path-or-network-error"))
        service = service_for(self.path, factory=factory)
        self.assert_code("unavailable", lambda: service.transcribe(b"x", "audio/wav", "en"))
        self.assertFalse(service.status()["available"])
        self.assert_code("unavailable", lambda: service.transcribe(b"x", "audio/wav", "en"))
        factory.assert_called_once()

    def test_english_only_model_is_unavailable_for_the_bilingual_service(self):
        service = service_for(self.path, factory=Mock(return_value=SimpleNamespace(
            model=SimpleNamespace(is_multilingual=False))))
        self.assert_code("unavailable", lambda: service.transcribe(b"x", "audio/wav", "ar"))

    def test_empty_or_oversized_transcript_is_not_a_success(self):
        for text, code in (("  ", "no_speech"), ("x" * 4001, "invalid")):
            model = SimpleNamespace(transcribe=Mock(return_value=([SimpleNamespace(text=text)], None)))
            service = service_for(self.path, factory=Mock(return_value=model))
            self.assert_code(code, lambda: service.transcribe(b"x", "audio/wav", "en"))

    def test_contention_is_rejected_and_decoder_failure_releases_the_gate(self):
        entered, finish = threading.Event(), threading.Event()
        def decode(*args):
            entered.set()
            finish.wait(3)
            raise SpeechError("invalid")
        service = service_for(self.path, decoder=decode)
        failures = []
        def run():
            try:
                service.transcribe(b"x", "audio/wav", "en")
            except SpeechError as error:
                failures.append(error.code)
        thread = threading.Thread(target=run)
        thread.start()
        try:
            self.assertTrue(entered.wait(2))
            self.assert_code("busy", lambda: service.transcribe(b"x", "audio/wav", "en"))
        finally:
            finish.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(failures, ["invalid"])
        service._decoder = Mock(return_value="audio")
        self.assertEqual(service.transcribe(b"x", "audio/wav", "en")["text"], "Hello world")


@unittest.skipUnless(API_AVAILABLE, "FastAPI is not installed")
class SpeechApiTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.path = complete_model(root)
        config = root / "config.json"
        config.write_text(json.dumps({"memory_file": str(root / "memory.json"),
                                      "database_file": str(root / "db.sqlite"),
                                      "vault_dir": str(root / "vault")}), encoding="utf-8")
        self.secret = "speech-tests-only-not-a-credential"
        self.app = closing(self, create_app(config, env={
            "AGENTIC_OS_JWT_SECRET": self.secret, "SUPABASE_URL": "https://test.supabase.invalid",
            "AGENTIC_OS_DEFAULT_ROLE": "viewer"}))
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.owner = self.headers("alice", "analyst")
        response = self.client.post("/api/sessions", headers=self.owner)
        self.assertEqual(response.status_code, 201)
        self.sid = response.json()["session_id"]
        self.url = f"/api/sessions/{self.sid}/transcriptions"

    def headers(self, subject, role):
        return {"Authorization": "Bearer " + issue_local_test_token(self.secret, subject, role)}

    def post(self, content=b"fixture", *, headers=None, language="en"):
        return self.client.post(self.url + "?language=" + language, content=content,
                                headers={**(headers or self.owner), "Content-Type": "audio/webm"})

    def test_status_and_transcription_require_identity_and_the_existing_permissions(self):
        self.assertEqual(self.client.get("/api/voice/status").status_code, 401)
        self.assertEqual(self.client.post(self.url, content=b"x").status_code, 401)
        viewer = self.headers("alice", "viewer")
        self.assertEqual(self.client.get("/api/voice/status", headers=viewer).status_code, 200)
        self.assertEqual(self.post(headers=viewer).status_code, 403)

    def test_default_is_explicitly_disabled(self):
        status = self.client.get("/api/voice/status", headers=self.owner).json()
        self.assertFalse(status["enabled"])
        response = self.post(language="ar")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], SpeechError("unavailable").message("ar"))

    def test_another_owner_gets_404_before_the_recording_is_used(self):
        service = service_for(self.path)
        service.transcribe = Mock()
        self.app.state.speech = service
        response = self.post(headers=self.headers("bob", "analyst"))
        self.assertEqual(response.status_code, 404)
        service.transcribe.assert_not_called()

    def test_success_does_not_send_a_message_or_persist_a_transcript(self):
        self.app.state.speech = service_for(self.path)
        response = self.post(language="ar")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"text": "Hello world", "language": "ar",
                                           "provider": "faster-whisper"})
        state = self.client.get(f"/api/sessions/{self.sid}", headers=self.owner).json()
        self.assertEqual(state["transcript"], [])
        self.assertIn("microphone=(self)", response.headers["Permissions-Policy"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_ended_session_is_not_transcribed(self):
        self.app.state.speech = service_for(self.path)
        self.client.delete(f"/api/sessions/{self.sid}", headers=self.owner)
        self.assertEqual(self.post().status_code, 409)
        self.app.state.speech._decoder.assert_not_called()

    def test_invalid_format_and_language_are_rejected(self):
        self.app.state.speech = service_for(self.path)
        response = self.client.post(self.url, content=b"x", headers={
            **self.owner, "Content-Type": "application/json"})
        self.assertEqual(response.status_code, 415)
        self.assertEqual(self.post(language="fr").status_code, 422)

    def test_both_declared_and_streamed_oversize_are_rejected_before_decode(self):
        self.app.state.speech = service_for(self.path)
        self.assertEqual(self.post(b"x" * (MAX_BYTES + 1)).status_code, 413)
        response = self.client.post(self.url, content=iter([b"x" * MAX_BYTES, b"x"]),
                                    headers={**self.owner, "Content-Type": "audio/webm"})
        self.assertEqual(response.status_code, 413)
        self.app.state.speech._decoder.assert_not_called()

    def test_invalid_audio_silence_and_busy_are_safe_localized_responses(self):
        for code, status in (("invalid", 422), ("no_speech", 422), ("busy", 429),
                             ("too_long", 422), ("unavailable", 503)):
            self.app.state.speech = service_for(self.path, decoder=Mock(side_effect=SpeechError(code)))
            response = self.post(language="ar")
            self.assertEqual(response.status_code, status)
            self.assertEqual(response.json()["detail"], SpeechError(code).message("ar"))
            if code == "busy":
                self.assertEqual(response.headers["Retry-After"], "2")


try:
    import av  # noqa: F401
    import numpy  # noqa: F401
    DECODER_AVAILABLE = True
except ImportError:
    DECODER_AVAILABLE = False


@unittest.skipUnless(DECODER_AVAILABLE, "optional PyAV/numpy voice decoder is not installed")
class AudioDecodeTest(unittest.TestCase):
    @staticmethod
    def wav(seconds, sample=b"\x00\x10"):
        data = io.BytesIO()
        with wave.open(data, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16_000)
            audio.writeframes(sample * int(seconds * 16_000))
        return data.getvalue()

    def test_real_in_memory_decoder_returns_a_bounded_mono_waveform(self):
        audio = _decode(self.wav(1), "wav")
        self.assertEqual(len(audio), 16_000)
        self.assertAlmostEqual(float(audio[100]), 0.125)

    def test_decode_rejects_duration_silence_and_wrong_container(self):
        for payload, fmt, code in ((self.wav(31), "wav", "too_long"),
                                   (self.wav(1, b"\x00\x00"), "wav", "no_speech"),
                                   (b"not an audio file", "matroska", "invalid")):
            with self.assertRaises(SpeechError) as caught:
                _decode(payload, fmt)
            self.assertEqual(caught.exception.code, code)


if __name__ == "__main__":
    unittest.main()
