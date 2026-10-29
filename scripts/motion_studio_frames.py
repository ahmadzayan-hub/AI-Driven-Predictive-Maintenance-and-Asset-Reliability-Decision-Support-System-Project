"""Render evidence-linked motion frames using local Pillow with Arabic RAQM support.

Optional dependency: Pillow. Use a locally approved font; never download one.
The renderer accepts only a pre-validated motion-evidence-v1 manifest.
"""
from __future__ import annotations

import math
from pathlib import Path

from motion_studio_render import MotionInputError, validate


def render_frames(manifest: dict, folder: Path, font_path: Path, *,
                  duration: float | None = None, fps: int = 30) -> int:
    validate(manifest)
    if fps != 30:
        raise MotionInputError("Only 30fps is supported")
    try:
        from PIL import Image, ImageDraw, ImageFont, features
    except ImportError as exc:
        raise MotionInputError("Install Pillow in the isolated motion worker") from exc
    if not font_path.is_file():
        raise MotionInputError("Provide an approved local TTF/OTF font")
    if manifest["language"] == "ar" and not features.check("raqm"):
        raise MotionInputError("Arabic RTL requires a Pillow build with libraqm")
    duration = float(duration if duration is not None else manifest["duration"])
    if not 3 <= duration <= 180:
        raise MotionInputError("Duration outside limits")
    total = int(round(duration * fps))
    w, h = (1280, 720) if manifest["format"] == "wide" else (720, 1280)
    folder.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(str(font_path), int(w * .046))
    tag_font = ImageFont.truetype(str(font_path), int(w * .017))
    rtl = manifest["language"] == "ar"
    direction = "rtl" if rtl else "ltr"
    scenes = manifest["scenes"]
    bg = Image.new("RGB", (w, h), "#0b2540")
    g = ImageDraw.Draw(bg)
    g.rectangle((0, int(h*.16), w, int(h*.17)), fill="#197f9b")
    g.line((int(w*.08), int(h*.84), int(w*.92), int(h*.84)), fill="#55c3ca", width=4)
    safe_width = int(w*.82)
    for i in range(total):
        t = i / max(1,total)
        scene_index = 0 if t < .25 else (1 if t < .75 else 2)
        text = scenes[scene_index]["text"].strip()
        canvas = bg.copy()
        draw = ImageDraw.Draw(canvas)
        words = text.split()
        lines, current = [], ""
        for word in words:
            proposal = (current+" "+word).strip()
            if current and draw.textbbox((0,0),proposal,font=font)[2] > safe_width:
                lines.append(current)
                current = word
            else:
                current = proposal
        if current: lines.append(current)
        if len(lines) > 5:
            raise MotionInputError("Scene exceeds 5 readable text lines")
        line_height = int(w*.075)
        y = int(h*.44 - len(lines)*line_height/2)
        anchor_x = int(w*.91 if rtl else w*.09)
        for line in lines:
            if rtl:
                draw.text((anchor_x,y),line,font=font,fill="#ffffff",
                          direction=direction,anchor="ra")
            else:
                draw.text((anchor_x,y),line,font=font,fill="#ffffff",anchor="la")
            y += line_height
        status="DRAFT / FOR HUMAN REVIEW" if not rtl else "مسودة / للمراجعة البشرية"
        if rtl:
            draw.text((anchor_x,int(h*.12)),status,font=tag_font,
                      fill="#a6dfeb",direction=direction,anchor="ra")
        else:
            draw.text((anchor_x,int(h*.12)),status,font=tag_font,
                      fill="#a6dfeb",anchor="la")
        progress=int(w*.84*t)
        draw.rectangle((int(w*.08),int(h*.84)-3,int(w*.08)+progress,int(h*.84)+3),
                       fill="#e8b966")
        canvas.save(folder/f"frame-{i:06d}.png", optimize=False)
    return total
