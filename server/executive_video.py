"""Executive video: an MP4 rendered on this host from one executive brief snapshot.

Every on-screen figure and every spoken sentence comes from the brief that the
dashboard, the report and the slides use; nothing is recalculated, summarised
by a model or added. A value the brief does not hold is shown and spoken as not
measured. Narration is synthesised locally with espeak-ng, frames are drawn with
Pillow (libraqm shapes Arabic) and encoded with ffmpeg: no data leaves the host
and no paid or external service is called. The result is a draft. Release still
needs a recorded human review of this exact file (server/export_reviews.py).
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import tempfile
import wave
from datetime import datetime, timezone
from pathlib import Path

from server.executive_export import _clean, faithful, model_evidence
from server.report_fonts import FONT_PATH, verified_font

SIZE = (1280, 720)
FPS = 25
ANIMATE = 30          # frames of motion at the start of each scene (1.2 s)
MAX_SECONDS = 180
VOICES = {"en": "en-gb", "ar": "ar"}
COLOURS = {"bg": (11, 18, 32), "panel": (20, 31, 52), "text": (230, 237, 247), "muted": (148, 163, 184),
           "cyan": (34, 211, 238), "violet": (139, 92, 246), "amber": (232, 185, 102), "edge": (45, 62, 92)}


class VideoUnavailable(RuntimeError):
    """A tool this host needs is missing; nothing was rendered."""


class VideoFailed(RuntimeError):
    """Rendering started and failed; the caller records it as a failed export."""


def missing_tools():
    """What this host lacks to render, so the interface can say so plainly."""
    missing = [name for name in ("ffmpeg", "ffprobe", "espeak-ng") if not shutil.which(name)]
    try:
        from PIL import features
        if not features.check("raqm"):
            missing.append("libraqm")
    except ImportError:
        missing.append("Pillow")
    if verified_font() is None:
        missing.append("font")
    return missing


def _measured(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


MONTHS = {"en": ("January", "February", "March", "April", "May", "June", "July", "August", "September",
                  "October", "November", "December"),
          "ar": ("يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر",
                 "نوفمبر", "ديسمبر")}


def spoken_date(value, language):
    """An ISO date as a listener hears it ("1 January 2025"), never "2025 dash 01";
    anything else is said as written."""
    import re
    match = re.match(r"^(\d{4})-(\d{2})(?:-(\d{2}))?", str(value))
    if not match or not 1 <= int(match.group(2)) <= 12:
        return str(value)
    year, month, day = match.group(1), MONTHS[language][int(match.group(2)) - 1], match.group(3)
    return f"{int(day)} {month} {year}" if day else f"{month} {year}"


def storyboard(brief):
    """The scenes, each with its on-screen text, figures and their sources, and narration."""
    ar = brief["language"] == "ar"

    def tr(en, arabic):
        return arabic if ar else en

    run, scope, advisory = brief["run"], brief["scope"], brief.get("advisory") or {}
    currency = brief.get("currency")

    def figure(measure):
        value, scale = measure.get("value"), measure.get("scale")
        if not _measured(value):
            reason = measure.get("undefined_reason") or tr("not measured in this scope", "غير مقاس في هذا النطاق")
            return tr("Not measured", "غير مقاس"), tr("not measured", "غير مقاس"), reason
        shown = faithful(value)
        spoken = shown.replace(",", "")
        if scale == "percent":
            return shown + "%", spoken + tr(" percent", " بالمئة"), measure.get("formula", "")
        if scale == "hours":
            return shown + tr(" h", " ساعة"), spoken + tr(" hours", " ساعة"), measure.get("formula", "")
        if scale == "money":
            unit = currency or tr("(currency not stated)", "(العملة غير محددة)")
            return f"{currency} {shown}" if currency else f"{shown} {unit}", f"{spoken} {unit}", measure.get("formula", "")
        return shown, spoken, measure.get("formula", "")

    period = scope.get("period")
    when = tr(f"{period['from']} to {period['to']}", f"من {period['from']} إلى {period['to']}") if period else tr("Period not recorded", "الفترة غير مسجلة")
    lang = brief["language"]
    heard = (tr(f"From {spoken_date(period['from'], lang)} to {spoken_date(period['to'], lang)}",
                f"من {spoken_date(period['from'], lang)} إلى {spoken_date(period['to'], lang)}") if period else when)
    records = tr(f"{scope['records']} of {scope['total_records']} records", f"{scope['records']} من {scope['total_records']} سجلاً")
    name = _clean(run.get("dataset_name", ""))
    scenes = [{"id": "title", "kind": "title", "heading": _clean(advisory.get("title") or tr("Executive decision brief", "موجز القرار التنفيذي")),
               "lines": [name, f"{when} · {records}"], "figures": [
                   {"label": tr("Records in scope", "السجلات ضمن النطاق"), "shown": str(scope["records"]), "value": scope["records"],
                    "source": "executive.scope.records"}],
               "narration": tr(f"Executive brief for {name}. {records}. {heard}. This is a draft for review.",
                               f"الموجز التنفيذي لـ {name}. {records}. {heard}. هذه مسودة للمراجعة.")}]
    decision = (advisory.get("decisions") or [{}])[0]
    lead = _clean(advisory.get("recommendation") or decision.get("title") or "")
    scenes.append({"id": "decision", "kind": "statement", "heading": tr("The decision", "القرار المطلوب"),
                   "lines": [lead or tr("No decision is recorded for this scope.", "لا يوجد قرار مسجل لهذا النطاق.")], "figures": [],
                   "narration": lead or tr("No decision is recorded for this scope.", "لا يوجد قرار مسجل لهذا النطاق.")})
    cards, said = [], []
    for measure in brief["kpis"]["measures"][:4]:
        shown, spoken, source = figure(measure)
        title = _clean(measure.get("title", ""))
        cards.append({"label": title, "shown": shown, "value": measure.get("value") if _measured(measure.get("value")) else None,
                      "scale": measure.get("scale"), "source": f"executive.kpi.{measure.get('key')}: {_clean(source)}"})
        said.append(f"{title}: {spoken}.")
    scenes.append({"id": "kpis", "kind": "kpis", "heading": tr("Key measures", "المؤشرات الرئيسية"), "lines": [], "figures": cards,
                   "narration": " ".join(said) or tr("No measure is calculated for this scope.", "لا يوجد مؤشر محسوب لهذا النطاق.")})
    priorities = brief.get("priorities") or []
    # The title says what to look at; the detail carries the brief's own figures.
    items = [_clean(p.get("title", "")) + (f": {_clean(p['detail'])}" if p.get("detail") else "") for p in priorities[:3]]
    scenes.append({"id": "priorities", "kind": "list", "heading": tr("Biggest risks or opportunities", "أهم المخاطر أو الفرص"),
                   "lines": items or [tr("No calculated priority for this scope.", "لا توجد أولوية محسوبة لهذا النطاق.")], "figures": [],
                   "narration": " ".join(f"{i + 1}. {t.rstrip('.')}." for i, t in enumerate(items)) or tr("No calculated priority for this scope.", "لا توجد أولوية محسوبة لهذا النطاق.")})
    models = [model_evidence(m, brief["language"]) for m in (brief.get("models") or [])[:3]]
    limits = [_clean(x) for x in (brief.get("readiness", {}).get("limitations") or [])[:2]]
    forecast = models or [tr("No model was validated for this report, so no forecast is claimed.", "لم يُتحقق من أي نموذج لهذا التقرير، فلا يُدّعى أي توقع.")]
    scenes.append({"id": "forecast", "kind": "list", "heading": tr("Forecast and limits", "التوقع والحدود"),
                   "lines": forecast + limits, "figures": [], "narration": " ".join(forecast + limits)})
    snapshot = brief["snapshot_id"]
    scenes.append({"id": "sources", "kind": "list", "heading": tr("Sources and review", "المصادر والمراجعة"),
                   "lines": [tr(f"Source: {name}, run {run['id']}", f"المصدر: {name}، التشغيل {run['id']}"),
                             tr(f"Snapshot {snapshot[:12]}; every figure is the brief's own.", f"اللقطة {snapshot[:12]}؛ كل رقم من الموجز نفسه."),
                             tr("Draft for review. Release needs a recorded human approval of this file.",
                                "مسودة للمراجعة. يتطلب النشر اعتماداً بشرياً مسجلاً لهذا الملف.")],
                   "figures": [], "narration": tr("Every figure comes from the recorded brief. This video is a draft and needs a human review before release.",
                                                  "كل رقم مأخوذ من الموجز المسجل. هذا الفيديو مسودة ويحتاج إلى مراجعة بشرية قبل النشر.")})
    return scenes


def _run(args, **kwargs):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300, check=False, **kwargs)
    if result.returncode:
        raise VideoFailed((result.stderr or b"")[-600:].decode("utf-8", "replace") or "tool failed")
    return result


def _speak(text, language, path):
    _run(["espeak-ng", "-v", VOICES[language], "-s", "150", "-w", str(path), "--", text])
    with wave.open(str(path), "rb") as source:
        return source.getnframes() / source.getframerate()


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _stamp(seconds):
    ms = int(round(seconds * 1000))
    return f"{ms // 3_600_000:02d}:{ms // 60_000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


def _cues(scenes):
    """Subtitle cues: each scene's narration split into sentences, timed by length
    within the span the voice actually speaks."""
    cues = []
    for scene in scenes:
        parts = [p.strip() for p in scene["narration"].replace("؛", ".").split(". ") if p.strip()] or [scene["narration"]]
        total = sum(len(p) for p in parts) or 1
        at = scene["start"]
        for part in parts:
            span = scene["speech"] * len(part) / total
            cues.append((at, at + span, part if part.endswith((".", "؟", "?")) else part + "."))
            at += span
    return cues


def _subtitles(cues, folder):
    vtt = ["WEBVTT", ""] + [f"{_stamp(a)} --> {_stamp(b)}\n{text}\n" for a, b, text in cues]
    srt = [f"{i + 1}\n{_stamp(a).replace('.', ',')} --> {_stamp(b).replace('.', ',')}\n{text}\n" for i, (a, b, text) in enumerate(cues)]
    (folder / "subtitles.vtt").write_text("\n".join(vtt), encoding="utf-8")
    (folder / "subtitles.srt").write_text("\n".join(srt), encoding="utf-8")


class _Painter:
    def __init__(self, language):
        from PIL import ImageFont
        self.ar = language == "ar"
        self.font = lambda size: ImageFont.truetype(str(FONT_PATH), size)
        self.direction = "rtl" if self.ar else "ltr"

    def text(self, draw, xy, value, size, fill, width=None):
        """Draw text from the reading edge; wrap to width; return the height used."""
        font = self.font(size)
        lines, current = [], ""
        for word in str(value).split():
            proposal = (current + " " + word).strip()
            if current and width and draw.textlength(proposal, font=font, direction=self.direction) > width:
                lines.append(current)
                current = word
            else:
                current = proposal
        if current:
            lines.append(current)
        x, y = xy
        for line in lines:
            if self.ar:
                draw.text((SIZE[0] - x, y), line, font=font, fill=fill, anchor="ra", direction="rtl", language="ar")
            else:
                draw.text((x, y), line, font=font, fill=fill, anchor="la")
            y += int(size * 1.35)
        return y - xy[1]

    def frame(self, scene, scenes, index, progress, brief):
        """One frame: progress 0..1 over a scene's first 1.2 seconds animates
        counting figures, growing bars and lines appearing; then it holds."""
        from PIL import Image, ImageDraw
        image = Image.new("RGB", SIZE, COLOURS["bg"])
        draw = ImageDraw.Draw(image, "RGBA")
        # A slow glow that drifts across the scene: the only decoration.
        cx = int(SIZE[0] * (0.25 + 0.5 * ((index + progress * 0.3) / max(1, len(scenes)))))
        for radius, alpha in ((420, 18), (300, 22), (180, 26)):
            draw.ellipse((cx - radius, -radius // 2, cx + radius, radius), fill=COLOURS["violet"] + (alpha,))
        ease = 1 - (1 - progress) ** 3
        margin = 72
        badge = "مسودة للمراجعة" if self.ar else "Draft for review"
        self.text(draw, (margin, 40), badge, 20, COLOURS["amber"])
        self.text(draw, (margin, 92), scene["heading"], 46, COLOURS["text"], width=SIZE[0] - 2 * margin)
        y = 190
        if scene["kind"] == "kpis":
            for i, card in enumerate(scene["figures"]):
                col, row = i % 2, i // 2
                x0 = margin + col * 572
                left = SIZE[0] - x0 - 548 if self.ar else x0
                top = y + row * 205
                draw.rounded_rectangle((left, top, left + 548, top + 185), radius=18, fill=COLOURS["panel"], outline=COLOURS["edge"])
                draw.rectangle((left + (544 if self.ar else 0), top + 18, left + (548 if self.ar else 4), top + 167), fill=COLOURS["cyan"])
                self.text(draw, (x0 + 28, top + 22), card["label"], 24, COLOURS["muted"], width=490)
                shown = card["shown"]
                value = card["value"]
                if value is not None and ease < 1:
                    # Count up to the value; the settled frame shows the brief's exact figure.
                    shown = shown.replace(faithful(value), faithful(round(value * ease, 6)))
                self.text(draw, (x0 + 28, top + 78), shown, 50, COLOURS["text"] if value is not None else COLOURS["muted"])
                if value is not None and card.get("scale") == "percent" and 0 <= value <= 100:
                    track = (left + 28, top + 158, left + 520, top + 166)
                    draw.rounded_rectangle(track, radius=4, fill=COLOURS["edge"])
                    span = int((track[2] - track[0]) * value / 100 * ease)
                    if self.ar:
                        draw.rounded_rectangle((track[2] - span, track[1], track[2], track[3]), radius=4, fill=COLOURS["cyan"])
                    else:
                        draw.rounded_rectangle((track[0], track[1], track[0] + span, track[3]), radius=4, fill=COLOURS["cyan"])
        elif scene["kind"] == "title":
            for line in scene["lines"]:
                y += self.text(draw, (margin, y + 40), line, 34, COLOURS["muted"], width=SIZE[0] - 2 * margin) + 8
        else:
            size = 34 if scene["kind"] == "statement" else 28 if sum(len(x) for x in scene["lines"]) < 360 else 24
            for i, line in enumerate(scene["lines"]):
                shown = line if scene["kind"] == "statement" else f"{i + 1}. {line}"
                appear = min(1.0, max(0.0, progress * 2 - i * 0.3))
                colour = tuple(int(c * appear + b * (1 - appear)) for c, b in zip(COLOURS["text"], COLOURS["bg"]))
                y += self.text(draw, (margin, y), shown, size, colour, width=SIZE[0] - 2 * margin) + 14
                if y > SIZE[1] - 120:
                    break
        footer = (f"اللقطة {brief['snapshot_id'][:12]} · {_clean(brief['run'].get('dataset_name', ''))} · للمراجعة فقط" if self.ar
                  else f"Snapshot {brief['snapshot_id'][:12]} · {_clean(brief['run'].get('dataset_name', ''))} · Review only")
        self.text(draw, (margin, SIZE[1] - 58), footer, 18, COLOURS["muted"])
        total = sum(s["duration"] for s in scenes)
        done = (scene["start"] + scene["duration"]) / total
        draw.rectangle((0, SIZE[1] - 6, int(SIZE[0] * done), SIZE[1]), fill=COLOURS["cyan"])
        return image


def render(brief, folder):
    """Render video.mp4, subtitles.vtt, subtitles.srt and manifest.json into folder.

    Raises VideoUnavailable before any work if a tool is missing, and
    VideoFailed if a step fails; the caller records either as a failed export.
    """
    missing = missing_tools()
    if missing:
        raise VideoUnavailable(", ".join(missing))
    language = brief["language"]
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    scenes = storyboard(brief)
    painter = _Painter(language)
    with tempfile.TemporaryDirectory(prefix="exec-video-") as scratch:
        scratch = Path(scratch)
        start, rate, pcm = 0.0, None, []
        for i, scene in enumerate(scenes):
            speech = _speak(scene["narration"], language, scratch / f"{i}.wav")
            frames = math.ceil((speech + 1.0) * FPS)
            scene.update(start=start, speech=speech, frames=frames, duration=frames / FPS)
            with wave.open(str(scratch / f"{i}.wav"), "rb") as source:
                rate = rate or source.getframerate()
                if source.getframerate() != rate or source.getsampwidth() != 2 or source.getnchannels() != 1:
                    raise VideoFailed("unexpected speech format")
                data = source.readframes(source.getnframes())
            # Pad each scene's speech with silence to the scene's exact length, so
            # voice, subtitles and pictures share one timeline.
            pcm.append(data + b"\x00\x00" * (round(scene["duration"] * rate) - len(data) // 2))
            start += scene["duration"]
        if start > MAX_SECONDS:
            raise VideoFailed("longer than the three-minute limit")
        with wave.open(str(scratch / "narration.wav"), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(rate)
            out.writeframes(b"".join(pcm))
        cues = _cues(scenes)
        _subtitles(cues, folder)
        video = folder / "video.mp4"
        encoder = subprocess.Popen(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{SIZE[0]}x{SIZE[1]}", "-r", str(FPS), "-i", "-",
             "-i", str(scratch / "narration.wav"), "-i", str(folder / "subtitles.srt"),
             "-map", "0:v", "-map", "1:a", "-map", "2:s",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-threads", "1",
             "-c:a", "aac", "-ar", "48000", "-b:a", "128k", "-c:s", "mov_text",
             "-metadata:s:s:0", f"language={'ara' if language == 'ar' else 'eng'}",
             "-metadata:s:a:0", f"language={'ara' if language == 'ar' else 'eng'}",
             "-fflags", "+bitexact", "-flags:v", "+bitexact", "-flags:a", "+bitexact",
             "-t", f"{start:.3f}", "-movflags", "+faststart", str(video)],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        previous = None
        try:
            for index, scene in enumerate(scenes):
                settled = None
                for f in range(scene["frames"]):
                    if settled is not None:
                        image = settled
                    else:
                        progress = min(1.0, f / ANIMATE)
                        image = painter.frame(scene, scenes, index, progress, brief)
                        if progress == 1.0:
                            settled = image
                    if previous is not None and f < 10:   # a 0.4-second dissolve from the last scene
                        from PIL import Image
                        image = Image.blend(previous, image, (f + 1) / 11)
                    encoder.stdin.write(image.tobytes())
                previous = settled or image
            encoder.stdin.close()
            error = encoder.stderr.read()
            if encoder.wait(timeout=300):
                raise VideoFailed(error[-600:].decode("utf-8", "replace") or "encoder failed")
        except BrokenPipeError:
            raise VideoFailed((encoder.stderr.read() or b"encoder stopped")[-600:].decode("utf-8", "replace")) from None
        finally:
            if encoder.poll() is None:
                encoder.kill()
                encoder.wait()
            encoder.stderr.close()
    probe = json.loads(_run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name",
                             "-of", "json", str(video)]).stdout)
    streams = sorted(s["codec_type"] for s in probe.get("streams", []))
    if streams != ["audio", "subtitle", "video"] or abs(float(probe["format"]["duration"]) - start) > 0.2:
        raise VideoFailed(f"unexpected output: {streams}, {probe.get('format', {}).get('duration')}")
    manifest = {
        "schema": "executive-video-v1", "status": "DRAFT_REQUIRES_HUMAN_REVIEW",
        "run_id": brief["run"]["id"], "snapshot_id": brief["snapshot_id"], "language": language,
        "filters": brief["scope"]["filters"], "records": brief["scope"]["records"],
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration": round(start, 3), "size": list(SIZE), "fps": FPS,
        "engine": {"frames": "Pillow with libraqm (local)", "speech": f"espeak-ng voice {VOICES[language]} (local, synthetic)",
                   "encoder": "ffmpeg libx264 and AAC (local)"},
        "scenes": [{"id": s["id"], "start": round(s["start"], 3), "end": round(s["start"] + s["duration"], 3),
                    "heading": s["heading"], "lines": s["lines"], "narration": s["narration"], "figures": s["figures"]}
                   for s in scenes],
        "files": {name: {"sha256": _sha(folder / name), "bytes": (folder / name).stat().st_size}
                  for name in ("video.mp4", "subtitles.vtt", "subtitles.srt")},
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifest
