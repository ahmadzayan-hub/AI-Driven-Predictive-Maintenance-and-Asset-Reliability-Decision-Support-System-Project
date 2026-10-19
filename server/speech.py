"""Optional, local-only speech recognition over bounded in-memory audio.

The operator installs the optional extra and a complete converted Whisper
model before enabling this service. Neither an HTTP request nor model loading
may fetch weights or tokenizers. Audio and transcripts are never persisted.
"""

import importlib.util
import io
import os
from pathlib import Path
import threading

MAX_SECONDS = 30
MAX_BYTES = 2_000_000
SAMPLE_RATE = 16_000
MAX_TEXT = 4_000
CONTENT_FORMATS = {
    "audio/webm": "matroska",
    "audio/ogg": "ogg",
    "audio/wav": "wav",
    "audio/mp4": "mov",
}
MODEL_FILES = ("model.bin", "config.json", "tokenizer.json")


class SpeechError(Exception):
    """A public error code, never a decoder/model exception or a local path."""

    STATUS = {"unavailable": 503, "busy": 429, "too_large": 413,
              "unsupported": 415, "invalid": 422, "too_long": 422,
              "no_speech": 422, "language": 422}
    MESSAGES = {
        "unavailable": ("Local transcription is not available. You can type your message.",
                        "التفريغ الصوتي المحلي غير متاح. يمكنك كتابة رسالتك."),
        "busy": ("Local transcription is busy. Please try again shortly.",
                 "التفريغ الصوتي المحلي مشغول. حاول مرة أخرى بعد قليل."),
        "too_large": ("The recording exceeds the 2 MB limit.",
                      "يتجاوز التسجيل الحد الأقصى البالغ 2 ميغابايت."),
        "unsupported": ("This audio format is not supported.", "صيغة الصوت هذه غير مدعومة."),
        "invalid": ("The recording could not be read. Please record again.",
                    "تعذرت قراءة التسجيل. أعد التسجيل."),
        "too_long": ("The recording exceeds the 30-second limit.",
                     "يتجاوز التسجيل الحد الأقصى البالغ 30 ثانية."),
        "no_speech": ("No speech was found. Please record again or type your message.",
                      "لم يُعثر على كلام. أعد التسجيل أو اكتب رسالتك."),
        "language": ("Choose English or Arabic for transcription.",
                     "اختر الإنجليزية أو العربية للتفريغ الصوتي."),
    }

    def __init__(self, code):
        self.code = code
        self.status = self.STATUS[code]
        super().__init__(code)

    def message(self, language):
        return self.MESSAGES[self.code][1 if language == "ar" else 0]


def content_format(content_type):
    """Ignore MediaRecorder's codec parameter; never auto-detect playlists."""
    return CONTENT_FORMATS.get((content_type or "").split(";", 1)[0].strip().lower())


def _decode(payload, container_format):
    """Decode one supported container without a file or unbounded waveform.

    A compressed file may contain far more audio than its byte count suggests.
    The duration is checked while resampling, before retaining each frame;
    metadata alone is not trusted. The explicit demuxer and disabled external
    references prevent a supplied playlist from opening files or URLs.
    """
    import av
    import numpy as np

    frames = []
    samples = 0
    try:
        with av.open(io.BytesIO(payload), mode="r", format=container_format,
                     options={"enable_drefs": "0", "protocol_whitelist": "pipe"}) as container:
            streams = list(container.streams.audio)
            if len(streams) != 1:
                raise SpeechError("invalid")
            stream = streams[0]
            if stream.duration is not None and stream.time_base is not None:
                if float(stream.duration * stream.time_base) > MAX_SECONDS + 0.05:
                    raise SpeechError("too_long")
            resampler = av.audio.resampler.AudioResampler(
                format="s16", layout="mono", rate=SAMPLE_RATE)

            def retain(frame):
                nonlocal samples
                samples += frame.samples
                if samples > MAX_SECONDS * SAMPLE_RATE:
                    raise SpeechError("too_long")
                frames.append(frame.to_ndarray().reshape(-1))

            for frame in container.decode(stream):
                if frame.sample_rate and frame.samples / frame.sample_rate > MAX_SECONDS:
                    raise SpeechError("too_long")
                for output in resampler.resample(frame):
                    retain(output)
            for output in resampler.resample(None):
                retain(output)
        if not frames or samples == 0:
            raise SpeechError("no_speech")
        audio = np.concatenate(frames).astype(np.float32) / 32768.0
        # Whisper can hallucinate on digital silence. VAD handles ordinary
        # pauses; this check prevents an empty waveform reaching the model.
        if not np.isfinite(audio).all() or np.max(np.abs(audio)) < 0.0001:
            raise SpeechError("no_speech")
        return audio
    except SpeechError:
        raise
    except Exception:
        raise SpeechError("invalid") from None


class LocalSpeech:
    """One lazily loaded CPU model and at most one decoding job per process."""

    def __init__(self, env=None, *, model_factory=None, decoder=None, package_check=None):
        env = os.environ if env is None else env
        self.enabled = env.get("AGENTIC_OS_WHISPER_ENABLED") == "1"
        configured = env.get("AGENTIC_OS_WHISPER_MODEL_DIR", "")
        self.model_dir = Path(configured) if configured else None
        self._model_factory = model_factory
        self._decoder = decoder or _decode
        self._package_check = package_check or (
            lambda: importlib.util.find_spec("faster_whisper") is not None)
        self._gate = threading.BoundedSemaphore(1)
        self._model = None
        self._failed = False

    def _configured(self):
        try:
            return bool(self.enabled and self.model_dir and self.model_dir.is_absolute()
                        and self.model_dir.is_dir()
                        and all((self.model_dir / name).is_file() for name in MODEL_FILES)
                        and not self._failed and self._package_check())
        except (OSError, ImportError, ValueError):
            return False

    def status(self):
        available = self._configured()
        return {"enabled": self.enabled, "available": available,
                "provider": "faster-whisper", "model": "local-whisper" if available else None,
                "max_seconds": MAX_SECONDS, "max_bytes": MAX_BYTES}

    def ensure_available(self):
        if not self._configured():
            raise SpeechError("unavailable")

    def _load(self):
        if self._model is None:
            try:
                factory = self._model_factory
                if factory is None:
                    from faster_whisper import WhisperModel
                    factory = WhisperModel
                self._model = factory(str(self.model_dir), device="cpu", compute_type="int8",
                                      cpu_threads=4, num_workers=1, local_files_only=True)
                # An English-only model cannot honor the bilingual contract.
                if getattr(getattr(self._model, "model", None), "is_multilingual", True) is False:
                    self._model = None
                    raise ValueError("A multilingual model is required")
            except Exception:
                self._failed = True
                raise SpeechError("unavailable") from None
        return self._model

    def transcribe(self, payload, content_type, language):
        if language not in ("en", "ar"):
            raise SpeechError("language")
        self.ensure_available()
        if len(payload) > MAX_BYTES:
            raise SpeechError("too_large")
        container_format = content_format(content_type)
        if not container_format:
            raise SpeechError("unsupported")
        if not payload:
            raise SpeechError("no_speech")
        if not self._gate.acquire(blocking=False):
            raise SpeechError("busy")
        try:
            audio = self._decoder(payload, container_format)
            model = self._load()
            try:
                segments, _info = model.transcribe(
                    audio, language=language, task="transcribe", beam_size=1,
                    vad_filter=True, condition_on_previous_text=False,
                    temperature=0, max_new_tokens=384)
                parts, length = [], 0
                for segment in segments:
                    text = " ".join(str(segment.text).split())
                    length += len(text) + 1
                    if length > MAX_TEXT:
                        raise SpeechError("invalid")
                    if text:
                        parts.append(text)
                text = " ".join(parts)
            except SpeechError:
                raise
            except Exception:
                raise SpeechError("unavailable") from None
            if not text:
                raise SpeechError("no_speech")
            return {"text": text, "language": language, "provider": "faster-whisper"}
        finally:
            self._gate.release()
