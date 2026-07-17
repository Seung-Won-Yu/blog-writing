"""Generate deterministic fallback images for a Tistory draft.

The cover and story images are rendered from the selected stories instead of
calling an image-generation API. This keeps the workflow free of an extra API
key and gives every post a consistent visual identity.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from blog_pipeline.collection.news_pipeline import validate_day_id
from .draft_identity import resolve_draft_identity
from .editorial_format import is_lead_story
from .visual_direction import (
    VISUAL_LABELS,
    motif_for_text,
    scene_for_text,
    scene_label,
    scene_steps,
    validate_visual,
)


HERE = Path(__file__).resolve().parents[2]
DEFAULT_DAYS_DIR = HERE / "data" / "days"
DEFAULT_OUTPUT_DIR = HERE / "docs" / "tistory" / "assets"
DEFAULT_PUBLIC_BASE_URL = (
    "https://seung-won-yu.github.io/blog-writing/tistory/assets/"
)

INK = "#17211C"
GREEN = "#28745A"
GREEN_DARK = "#183F32"
GOLD = "#C99B43"
PAPER = "#FCFBF7"
MUTED = "#66716B"
LINE = "#D8DEDB"
WHITE = "#FFFFFF"
ORANGE = "#E57B43"
MINT = "#A9D8C1"
MOTIF_ACCENTS = {
    "network": "#57D3E3",
    "agent": "#B77CFF",
    "memory": "#F3B85B",
    "security": "#FF7A68",
    "data": "#55D29A",
    "code": "#6FA8FF",
    "cloud": "#8BC7FF",
    "hardware": "#FFB45E",
    "research": "#D49BFF",
    "signal": "#6FE6D0",
}


def find_font(bold=False):
    """Return an installed Korean-capable font path."""
    configured = os.environ.get("BLOG_FONT_PATH")
    regular_candidates = [
        configured,
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "C:/Windows/Fonts/malgun.ttf",
    ]
    bold_candidates = [
        configured,
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "C:/Windows/Fonts/malgunbd.ttf",
    ]
    for candidate in bold_candidates if bold else regular_candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate))
    raise FileNotFoundError(
        "한글 폰트를 찾지 못했습니다. fonts-noto-cjk를 설치하거나 "
        "BLOG_FONT_PATH를 지정해 주세요."
    )


def _font(path, size):
    return ImageFont.truetype(str(path), size=size)


def _text_width(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def wrap_text_by_pixels(draw, text, font, max_width, max_lines):
    """Wrap Korean/English text by rendered width with an ellipsis on overflow."""
    normalized = " ".join(str(text or "").split())
    if not normalized:
        return []

    lines = []
    current = ""
    for word in normalized.split(" "):
        candidate = f"{current} {word}".strip()
        if current and _text_width(draw, candidate, font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
        while current and _text_width(draw, current, font) > max_width:
            split_at = len(current) - 1
            while split_at > 1 and _text_width(draw, current[:split_at], font) > max_width:
                split_at -= 1
            lines.append(current[:split_at].rstrip())
            current = current[split_at:].lstrip()
    if current:
        lines.append(current.rstrip())

    if len(lines) <= max_lines:
        return lines

    visible = lines[:max_lines]
    last = visible[-1].rstrip()
    while last and _text_width(draw, last + "…", font) > max_width:
        last = last[:-1].rstrip()
    visible[-1] = (last or visible[-1][:1]) + "…"
    return visible


def _draw_multiline(draw, lines, xy, font, fill, line_gap):
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        box = draw.textbbox((x, y), line, font=font)
        y += box[3] - box[1] + line_gap
    return y


def _news(day):
    value = day.get("news")
    return value if isinstance(value, list) else []


def _brief_text(value, limit, fallback):
    if isinstance(value, (list, tuple)):
        value = " · ".join(
            str(item or "").strip()
            for item in value
            if str(item or "").strip()
        )
    text = " ".join(str(value or "").replace("\x00", " ").split())
    lowered = text.casefold()
    if not text or any(
        marker in lowered for marker in ("http://", "https://", "<", ">", "```")
    ):
        return fallback
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def _filename_part(value, fallback):
    text = re.sub(r"[^0-9A-Za-z가-힣]+", "-", str(value or "").strip())
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return (text or fallback)[:36].rstrip("-")


def resolve_visual(day):
    """Resolve safe visual copy and per-story motifs for old and new day JSON."""
    stories = _news(day)[:3]
    first = stories[0] if stories else {}
    reference = "{} {}".format(first.get("title_kr", ""), first.get("blurb_kr", ""))
    raw_visual = day.get("visual") if isinstance(day.get("visual"), dict) else {}
    lead_story = is_lead_story(day)
    brief_key = "assets" if lead_story else "stories"
    raw_story_briefs = (
        raw_visual.get(brief_key)
        if isinstance(raw_visual.get(brief_key), list)
        else []
    )
    if lead_story:
        visual_count = min(6, max(2, len(raw_story_briefs)))
        stories = [first for _ in range(visual_count)]
    visual = validate_visual(raw_visual, reference)
    visual["stories"] = []
    for index, item in enumerate(stories):
        brief = (
            raw_story_briefs[index]
            if index < len(raw_story_briefs)
            and isinstance(raw_story_briefs[index], dict)
            else {}
        )
        brief_reference = "{} {} {}".format(
            brief.get("label", ""), brief.get("scene_label", ""), brief.get("steps", "")
        )
        motif = str(brief.get("motif") or "").strip().lower()
        if motif not in MOTIF_ACCENTS:
            motif = motif_for_text(
                "{} {}".format(item.get("title_kr", ""), brief_reference)
            )
        if motif == "signal":
            motif = motif_for_text(
                "{} {}".format(item.get("blurb_kr", ""), brief_reference)
            )
        reference = "{} {}".format(
            "{} {}".format(item.get("title_kr", ""), item.get("blurb_kr", "")),
            brief_reference,
        )
        scene = scene_for_text(reference)
        fallback_label = VISUAL_LABELS[motif]
        fallback_scene_label = scene_label(scene, motif)
        fallback_steps = scene_steps(scene, motif)
        visual["stories"].append(
            {
                "motif": motif,
                "label": _brief_text(brief.get("label"), 12, fallback_label),
                "scene": scene,
                "scene_label": _brief_text(
                    brief.get("scene_label"), 48, fallback_scene_label
                ),
                "steps": _brief_text(brief.get("steps"), 96, fallback_steps),
                "title": " ".join(str(item.get("title_kr") or "").split()),
                "source": " ".join(str(item.get("source") or "").split()),
            }
        )
    while not lead_story and len(visual["stories"]) < 3:
        visual["stories"].append(
            {
                "motif": "signal",
                "label": VISUAL_LABELS["signal"],
                "scene": "signal",
                "scene_label": scene_label("signal"),
                "steps": scene_steps("signal"),
                "title": "",
                "source": "",
            }
        )
    return visual


def _save_png_atomic(image, path):
    temporary = path.with_suffix(path.suffix + ".tmp")
    image.save(temporary, "PNG", optimize=True)
    temporary.replace(path)


def _scaled_box(box, left, top, right, bottom):
    x0, y0, x1, y1 = box
    width = x1 - x0
    height = y1 - y0
    return (
        int(x0 + width * left),
        int(y0 + height * top),
        int(x0 + width * right),
        int(y0 + height * bottom),
    )


def _point(box, x, y):
    x0, y0, x1, y1 = box
    return int(x0 + (x1 - x0) * x), int(y0 + (y1 - y0) * y)


def draw_motif(draw, motif, box, foreground=INK, accent=ORANGE, muted=GREEN):
    """Draw one fixed tech-news visual metaphor using only Pillow primitives."""
    x0, y0, x1, y1 = box
    width = max(1, x1 - x0)
    stroke = max(3, width // 45)

    if motif == "network":
        nodes = [(0.18, 0.72), (0.38, 0.32), (0.62, 0.58), (0.82, 0.22), (0.84, 0.78)]
        for start, end in ((0, 1), (1, 2), (2, 3), (2, 4), (1, 3)):
            draw.line((_point(box, *nodes[start]), _point(box, *nodes[end])), fill=muted, width=stroke)
        for index, (nx, ny) in enumerate(nodes):
            cx, cy = _point(box, nx, ny)
            radius = width // (17 if index == 2 else 24)
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=accent if index == 2 else foreground)
        draw.arc(_scaled_box(box, 0.64, 0.02, 0.98, 0.38), 205, 325, fill=accent, width=stroke)
        draw.arc(_scaled_box(box, 0.69, 0.08, 0.93, 0.32), 205, 325, fill=accent, width=stroke)
    elif motif == "agent":
        for offset in (0.12, 0.0):
            panel = _scaled_box(box, 0.16 + offset, 0.18 - offset / 2, 0.86 + offset, 0.70 - offset / 2)
            draw.rounded_rectangle(panel, radius=width // 28, outline=foreground, width=stroke, fill=None)
            draw.line((_point(panel, 0.08, 0.2), _point(panel, 0.92, 0.2)), fill=muted, width=stroke)
        path = [_point(box, 0.24, 0.79), _point(box, 0.5, 0.79), _point(box, 0.5, 0.62), _point(box, 0.78, 0.62)]
        draw.line(path, fill=accent, width=stroke * 2, joint="curve")
        for cx, cy in (path[0], path[-1]):
            r = width // 26
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=accent)
    elif motif == "memory":
        for index in range(3):
            top = 0.18 + index * 0.19
            card = _scaled_box(box, 0.16 + index * 0.05, top, 0.82 + index * 0.05, top + 0.26)
            draw.rounded_rectangle(card, radius=width // 30, fill=foreground if index == 2 else None, outline=foreground, width=stroke)
            cx, cy = _point(card, 0.16, 0.5)
            r = width // 35
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=accent)
            draw.line((_point(card, 0.29, 0.5), _point(card, 0.76, 0.5)), fill=accent if index == 2 else muted, width=stroke)
    elif motif == "security":
        points = [_point(box, 0.5, 0.1), _point(box, 0.82, 0.24), _point(box, 0.76, 0.68), _point(box, 0.5, 0.9), _point(box, 0.24, 0.68), _point(box, 0.18, 0.24)]
        draw.polygon(points, fill=foreground)
        cx, cy = _point(box, 0.5, 0.48)
        r = width // 12
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=accent)
        draw.rounded_rectangle((cx - r // 3, cy, cx + r // 3, cy + r), radius=r // 5, fill=accent)
    elif motif == "data":
        for index, scale in enumerate((0.58, 0.72, 0.88)):
            left = 0.12 + index * 0.23
            cylinder = _scaled_box(box, left, 0.74 - scale * 0.58, left + 0.22, 0.78)
            cx0, cy0, cx1, cy1 = cylinder
            cap = max(10, (cy1 - cy0) // 7)
            draw.rectangle((cx0, cy0 + cap // 2, cx1, cy1 - cap // 2), fill=foreground)
            draw.ellipse((cx0, cy0, cx1, cy0 + cap), fill=accent)
            draw.ellipse((cx0, cy1 - cap, cx1, cy1), fill=foreground)
    elif motif == "code":
        left = [_point(box, 0.38, 0.18), _point(box, 0.18, 0.5), _point(box, 0.38, 0.82)]
        right = [_point(box, 0.62, 0.18), _point(box, 0.82, 0.5), _point(box, 0.62, 0.82)]
        draw.line(left, fill=foreground, width=stroke * 2, joint="curve")
        draw.line(right, fill=foreground, width=stroke * 2, joint="curve")
        draw.line((_point(box, 0.46, 0.7), _point(box, 0.58, 0.3)), fill=accent, width=stroke * 2)
    elif motif == "cloud":
        cloud = _scaled_box(box, 0.16, 0.24, 0.84, 0.67)
        cx0, cy0, cx1, cy1 = cloud
        draw.rounded_rectangle((cx0, int(cy0 + (cy1 - cy0) * 0.4), cx1, cy1), radius=width // 12, fill=foreground)
        for px, py, radius in ((0.36, 0.43, 0.18), (0.52, 0.32, 0.23), (0.68, 0.46, 0.16)):
            cx, cy = _point(box, px, py)
            r = int(width * radius)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=foreground)
        draw.line((_point(box, 0.5, 0.63), _point(box, 0.5, 0.88)), fill=accent, width=stroke * 2)
        draw.polygon([_point(box, 0.43, 0.79), _point(box, 0.5, 0.91), _point(box, 0.57, 0.79)], fill=accent)
    elif motif == "hardware":
        chip = _scaled_box(box, 0.24, 0.2, 0.76, 0.8)
        draw.rounded_rectangle(chip, radius=width // 25, fill=foreground)
        inner = _scaled_box(chip, 0.22, 0.22, 0.78, 0.78)
        draw.rounded_rectangle(inner, radius=width // 32, outline=accent, width=stroke)
        for position in (0.3, 0.5, 0.7):
            draw.line((_point(box, position, 0.08), _point(box, position, 0.2)), fill=muted, width=stroke)
            draw.line((_point(box, position, 0.8), _point(box, position, 0.92)), fill=muted, width=stroke)
            draw.line((_point(box, 0.12, position), _point(box, 0.24, position)), fill=muted, width=stroke)
            draw.line((_point(box, 0.76, position), _point(box, 0.88, position)), fill=muted, width=stroke)
    elif motif == "research":
        paper = _scaled_box(box, 0.18, 0.12, 0.7, 0.82)
        draw.rounded_rectangle(paper, radius=width // 28, fill=foreground)
        for y in (0.3, 0.44, 0.58):
            draw.line((_point(paper, 0.18, y), _point(paper, 0.78, y)), fill=accent, width=stroke)
        cx, cy = _point(box, 0.67, 0.67)
        r = width // 7
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=accent, width=stroke * 2)
        draw.line((cx + int(r * 0.7), cy + int(r * 0.7), *_point(box, 0.88, 0.9)), fill=accent, width=stroke * 2)
    else:
        cx, cy = _point(box, 0.5, 0.5)
        for radius in (0.36, 0.25, 0.14):
            r = int(width * radius)
            draw.arc((cx - r, cy - r, cx + r, cy + r), 205, 515, fill=muted if radius != 0.14 else accent, width=stroke)
        r = width // 18
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=foreground)


def _hex_rgb(value):
    value = str(value).lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def _blend(left, right, amount):
    left_rgb = _hex_rgb(left)
    right_rgb = _hex_rgb(right)
    return tuple(
        int(a + (b - a) * amount) for a, b in zip(left_rgb, right_rgb)
    )


def _gradient(image, start, end):
    draw = ImageDraw.Draw(image)
    height = image.height
    for y in range(height):
        draw.line((0, y, image.width, y), fill=_blend(start, end, y / max(1, height - 1)))


def _arrow(draw, start, end, color, width=8):
    """Draw a quiet connector node instead of a presentation-style arrow."""
    draw.line((start, end), fill=color, width=width)
    ex, ey = end
    radius = max(2, width // 2)
    draw.ellipse(
        (ex - radius, ey - radius, ex + radius, ey + radius),
        fill=color,
    )


MOTIF_FLOW_GLYPHS = {
    "network": ("request", "connection"),
    "agent": ("goal", "review"),
    "memory": ("conversation", "answer"),
    "security": ("access", "decision"),
    "data": ("records", "insight"),
    "code": ("intent", "tests"),
    "cloud": ("traffic", "delivery"),
    "hardware": ("workload", "speed"),
    "research": ("question", "evidence"),
    "signal": ("events", "action"),
}


def _draw_stage_glyph(draw, kind, box, foreground, accent, muted):
    """Draw a small semantic start or outcome glyph for a motif flow."""
    width = max(1, box[2] - box[0])
    stroke = max(3, width // 35)

    if kind == "request":
        screen = _scaled_box(box, 0.08, 0.18, 0.78, 0.82)
        draw.rounded_rectangle(
            screen, radius=width // 18, outline=foreground, width=stroke
        )
        draw.line(
            (_point(screen, 0.0, 0.22), _point(screen, 1.0, 0.22)),
            fill=muted,
            width=stroke,
        )
        for y, length in ((0.43, 0.56), (0.62, 0.38)):
            draw.line(
                (_point(screen, 0.14, y), _point(screen, 0.14 + length, y)),
                fill=accent,
                width=stroke,
            )
        cx, cy = _point(box, 0.86, 0.5)
        radius = max(3, width // 22)
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius), fill=accent
        )
    elif kind == "goal":
        cx, cy = _point(box, 0.48, 0.5)
        for scale, color in ((0.38, muted), (0.25, foreground), (0.1, accent)):
            radius = int(width * scale)
            draw.ellipse(
                (cx - radius, cy - radius, cx + radius, cy + radius),
                outline=color,
                width=stroke,
            )
        _arrow(
            draw,
            _point(box, 0.78, 0.18),
            _point(box, 0.58, 0.4),
            accent,
            stroke,
        )
    elif kind == "conversation":
        bubble = _scaled_box(box, 0.08, 0.19, 0.87, 0.73)
        draw.rounded_rectangle(
            bubble, radius=width // 14, outline=foreground, width=stroke
        )
        draw.polygon(
            [
                _point(box, 0.25, 0.72),
                _point(box, 0.2, 0.88),
                _point(box, 0.43, 0.72),
            ],
            fill=foreground,
        )
        for y, length in ((0.38, 0.58), (0.56, 0.4)):
            draw.line(
                (_point(bubble, 0.17, y), _point(bubble, 0.17 + length, y)),
                fill=accent if y > 0.5 else muted,
                width=stroke,
            )
    elif kind == "access":
        cx, cy = _point(box, 0.34, 0.5)
        radius = width // 6
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            outline=foreground,
            width=stroke,
        )
        draw.line(
            (cx + radius, cy, *_point(box, 0.84, 0.5)),
            fill=accent,
            width=stroke * 2,
        )
        for x in (0.68, 0.8):
            draw.line(
                (_point(box, x, 0.5), _point(box, x, 0.68)),
                fill=accent,
                width=stroke,
            )
    elif kind == "records":
        dots = ((0.16, 0.25), (0.35, 0.2), (0.18, 0.52), (0.4, 0.46), (0.22, 0.78))
        target = _point(box, 0.82, 0.5)
        for index, position in enumerate(dots):
            point = _point(box, *position)
            draw.line((point, target), fill=muted, width=max(2, stroke // 2))
            radius = width // 26
            draw.ellipse(
                (
                    point[0] - radius,
                    point[1] - radius,
                    point[0] + radius,
                    point[1] + radius,
                ),
                fill=accent if index == 3 else foreground,
            )
        radius = width // 12
        draw.ellipse(
            (
                target[0] - radius,
                target[1] - radius,
                target[0] + radius,
                target[1] + radius,
            ),
            fill=accent,
        )
    elif kind == "intent":
        draw.line(
            [
                _point(box, 0.18, 0.28),
                _point(box, 0.42, 0.5),
                _point(box, 0.18, 0.72),
            ],
            fill=accent,
            width=stroke * 2,
            joint="curve",
        )
        draw.line(
            (_point(box, 0.5, 0.72), _point(box, 0.84, 0.72)),
            fill=foreground,
            width=stroke * 2,
        )
        draw.line(
            (_point(box, 0.55, 0.34), _point(box, 0.78, 0.34)),
            fill=muted,
            width=stroke,
        )
    elif kind == "traffic":
        target = _point(box, 0.83, 0.5)
        for index, y in enumerate((0.25, 0.5, 0.75)):
            start = _point(box, 0.17, y)
            draw.line((start, target), fill=muted, width=stroke)
            radius = width // 19
            draw.ellipse(
                (
                    start[0] - radius,
                    start[1] - radius,
                    start[0] + radius,
                    start[1] + radius,
                ),
                fill=accent if index == 1 else foreground,
            )
        radius = width // 13
        draw.ellipse(
            (
                target[0] - radius,
                target[1] - radius,
                target[0] + radius,
                target[1] + radius,
            ),
            outline=accent,
            width=stroke,
        )
    elif kind == "workload":
        for row in range(3):
            for column in range(3):
                tile = _scaled_box(
                    box,
                    0.1 + column * 0.27,
                    0.16 + row * 0.25,
                    0.29 + column * 0.27,
                    0.34 + row * 0.25,
                )
                draw.rounded_rectangle(
                    tile,
                    radius=max(2, width // 45),
                    fill=accent if (row, column) == (1, 1) else muted,
                    outline=foreground,
                    width=max(1, stroke // 2),
                )
    elif kind == "question":
        cx, cy = _point(box, 0.43, 0.43)
        radius = width // 4
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            outline=foreground,
            width=stroke * 2,
        )
        draw.line(
            (cx + radius * 2 // 3, cy + radius * 2 // 3, *_point(box, 0.84, 0.84)),
            fill=accent,
            width=stroke * 2,
        )
        dot = _point(box, 0.42, 0.52)
        dot_radius = max(3, width // 30)
        draw.ellipse(
            (
                dot[0] - dot_radius,
                dot[1] - dot_radius,
                dot[0] + dot_radius,
                dot[1] + dot_radius,
            ),
            fill=accent,
        )
    elif kind == "events":
        origin = _point(box, 0.15, 0.5)
        radius = width // 25
        draw.ellipse(
            (
                origin[0] - radius,
                origin[1] - radius,
                origin[0] + radius,
                origin[1] + radius,
            ),
            fill=accent,
        )
        for scale in (0.28, 0.5, 0.72):
            reach = int(width * scale)
            draw.arc(
                (
                    origin[0] - reach // 2,
                    origin[1] - reach,
                    origin[0] + reach,
                    origin[1] + reach,
                ),
                285,
                75,
                fill=foreground if scale == 0.72 else muted,
                width=stroke,
            )
    elif kind == "connection":
        nodes = ((0.2, 0.3), (0.38, 0.7), (0.66, 0.28), (0.82, 0.65))
        for left, right in ((0, 1), (0, 2), (1, 3), (2, 3)):
            draw.line(
                (_point(box, *nodes[left]), _point(box, *nodes[right])),
                fill=muted,
                width=stroke,
            )
        for index, node in enumerate(nodes):
            cx, cy = _point(box, *node)
            radius = width // 17
            draw.ellipse(
                (cx - radius, cy - radius, cx + radius, cy + radius),
                fill=accent if index == 3 else foreground,
            )
    elif kind == "review":
        cx, cy = _point(box, 0.5, 0.5)
        radius = width // 3
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            outline=foreground,
            width=stroke * 2,
        )
        draw.line(
            (
                *_point(box, 0.29, 0.52),
                *_point(box, 0.43, 0.68),
                *_point(box, 0.75, 0.32),
            ),
            fill=accent,
            width=stroke * 2,
            joint="curve",
        )
    elif kind == "answer":
        bubble = _scaled_box(box, 0.08, 0.18, 0.87, 0.75)
        draw.rounded_rectangle(
            bubble, radius=width // 14, outline=foreground, width=stroke
        )
        draw.polygon(
            [
                _point(box, 0.64, 0.74),
                _point(box, 0.82, 0.88),
                _point(box, 0.76, 0.71),
            ],
            fill=foreground,
        )
        for y, length in ((0.38, 0.55), (0.57, 0.36)):
            draw.line(
                (_point(bubble, 0.16, y), _point(bubble, 0.16 + length, y)),
                fill=accent if y < 0.5 else muted,
                width=stroke,
            )
    elif kind == "decision":
        root = _point(box, 0.18, 0.5)
        allow = _point(box, 0.76, 0.28)
        block = _point(box, 0.76, 0.72)
        draw.line((root, allow), fill=muted, width=stroke)
        draw.line((root, block), fill=muted, width=stroke)
        radius = width // 8
        for point in (allow, block):
            draw.ellipse(
                (
                    point[0] - radius,
                    point[1] - radius,
                    point[0] + radius,
                    point[1] + radius,
                ),
                outline=foreground,
                width=stroke,
            )
        draw.line(
            (
                allow[0] - radius // 2,
                allow[1],
                allow[0] - radius // 8,
                allow[1] + radius // 3,
                allow[0] + radius // 2,
                allow[1] - radius // 3,
            ),
            fill=accent,
            width=stroke,
            joint="curve",
        )
        draw.line(
            (
                block[0] - radius // 2,
                block[1] - radius // 2,
                block[0] + radius // 2,
                block[1] + radius // 2,
            ),
            fill=accent,
            width=stroke,
        )
        draw.line(
            (
                block[0] + radius // 2,
                block[1] - radius // 2,
                block[0] - radius // 2,
                block[1] + radius // 2,
            ),
            fill=accent,
            width=stroke,
        )
    elif kind == "insight":
        for index, height in enumerate((0.28, 0.46, 0.7)):
            bar = _scaled_box(
                box,
                0.16 + index * 0.24,
                0.82 - height,
                0.32 + index * 0.24,
                0.82,
            )
            draw.rounded_rectangle(
                bar, radius=max(2, width // 40), fill=accent if index == 2 else muted
            )
        draw.line(
            (_point(box, 0.1, 0.82), _point(box, 0.9, 0.82)),
            fill=foreground,
            width=stroke,
        )
        _arrow(
            draw,
            _point(box, 0.2, 0.68),
            _point(box, 0.83, 0.22),
            foreground,
            stroke,
        )
    elif kind == "tests":
        for index, y in enumerate((0.25, 0.5, 0.75)):
            start = _point(box, 0.12, y)
            size = width // 10
            draw.rounded_rectangle(
                (
                    start[0],
                    start[1] - size // 2,
                    start[0] + size,
                    start[1] + size // 2,
                ),
                radius=max(2, width // 50),
                outline=accent,
                width=stroke,
            )
            draw.line(
                (
                    start[0] + size // 5,
                    start[1],
                    start[0] + size // 2,
                    start[1] + size // 4,
                    start[0] + size,
                    start[1] - size // 3,
                ),
                fill=foreground,
                width=stroke,
                joint="curve",
            )
            draw.line(
                (_point(box, 0.42, y), _point(box, 0.87 - index * 0.08, y)),
                fill=muted,
                width=stroke,
            )
    elif kind == "delivery":
        device = _scaled_box(box, 0.2, 0.12, 0.8, 0.88)
        draw.rounded_rectangle(
            device, radius=width // 13, outline=foreground, width=stroke
        )
        draw.line(
            (_point(device, 0.18, 0.2), _point(device, 0.82, 0.2)),
            fill=muted,
            width=stroke,
        )
        _arrow(
            draw,
            _point(device, 0.5, 0.34),
            _point(device, 0.5, 0.7),
            accent,
            stroke,
        )
    elif kind == "speed":
        gauge = _scaled_box(box, 0.12, 0.2, 0.88, 0.9)
        draw.arc(gauge, 180, 360, fill=foreground, width=stroke * 2)
        cx, cy = _point(box, 0.5, 0.63)
        draw.line(
            (cx, cy, *_point(box, 0.76, 0.32)),
            fill=accent,
            width=stroke * 2,
        )
        radius = width // 18
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius), fill=accent
        )
        for x in (0.22, 0.5, 0.78):
            draw.line(
                (_point(box, x, 0.62), _point(box, x, 0.54)),
                fill=muted,
                width=stroke,
            )
    elif kind == "evidence":
        paper = _scaled_box(box, 0.14, 0.09, 0.76, 0.88)
        draw.rounded_rectangle(
            paper, radius=width // 20, outline=foreground, width=stroke
        )
        for y, length in ((0.27, 0.5), (0.43, 0.42), (0.59, 0.3)):
            draw.line(
                (_point(paper, 0.16, y), _point(paper, 0.16 + length, y)),
                fill=muted,
                width=stroke,
            )
        cx, cy = _point(box, 0.72, 0.7)
        radius = width // 7
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius), fill=accent
        )
        draw.line(
            (
                cx - radius // 2,
                cy,
                cx - radius // 8,
                cy + radius // 3,
                cx + radius // 2,
                cy - radius // 3,
            ),
            fill=foreground,
            width=stroke,
            joint="curve",
        )
    else:  # action
        points = [
            _point(box, 0.12, 0.78),
            _point(box, 0.38, 0.78),
            _point(box, 0.38, 0.58),
            _point(box, 0.62, 0.58),
            _point(box, 0.62, 0.36),
            _point(box, 0.84, 0.36),
        ]
        draw.line(points, fill=foreground, width=stroke * 2, joint="curve")
        _arrow(draw, points[-2], _point(box, 0.88, 0.18), accent, stroke)


def _draw_motif_flow(draw, motif, box, foreground, accent, muted):
    """Draw a motif as a semantic start → process → outcome scene."""
    motif = motif if motif in MOTIF_FLOW_GLYPHS else "signal"
    start_kind, outcome_kind = MOTIF_FLOW_GLYPHS[motif]
    _draw_stage_glyph(
        draw,
        start_kind,
        _scaled_box(box, 0.02, 0.12, 0.25, 0.88),
        foreground,
        accent,
        muted,
    )
    _arrow(
        draw,
        _point(box, 0.27, 0.5),
        _point(box, 0.36, 0.5),
        muted,
        max(3, (box[2] - box[0]) // 100),
    )
    draw_motif(
        draw,
        motif,
        _scaled_box(box, 0.37, 0.12, 0.63, 0.88),
        foreground=foreground,
        accent=accent,
        muted=muted,
    )
    _arrow(
        draw,
        _point(box, 0.64, 0.5),
        _point(box, 0.73, 0.5),
        muted,
        max(3, (box[2] - box[0]) // 100),
    )
    _draw_stage_glyph(
        draw,
        outcome_kind,
        _scaled_box(box, 0.75, 0.12, 0.98, 0.88),
        foreground,
        accent,
        muted,
    )


def draw_scene(draw, scene, motif, box, foreground=WHITE, accent=ORANGE, muted=MINT):
    """Draw a concrete article scene with a left-to-right visual explanation."""
    width = max(1, box[2] - box[0])
    stroke = max(3, width // 85)

    if scene == "privacy_photo":
        phone = _scaled_box(box, 0.04, 0.15, 0.31, 0.86)
        draw.rounded_rectangle(phone, radius=width // 28, outline=foreground, width=stroke, fill="#112E3A")
        for row in range(2):
            for column in range(2):
                left = 0.13 + column * 0.36
                top = 0.2 + row * 0.36
                tile = _scaled_box(phone, left, top, left + 0.25, top + 0.25)
                draw.rounded_rectangle(tile, radius=width // 100, fill=muted)
                draw.ellipse(_scaled_box(tile, 0.58, 0.12, 0.82, 0.36), fill=accent)
                draw.polygon(
                    [_point(tile, 0.05, 0.88), _point(tile, 0.42, 0.48), _point(tile, 0.92, 0.88)],
                    fill=foreground,
                )
        _arrow(draw, _point(box, 0.34, 0.5), _point(box, 0.47, 0.5), muted, stroke)
        cx, cy = _point(box, 0.58, 0.5)
        radius = width // 10
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=foreground, width=stroke)
        draw.ellipse((cx - radius // 2, cy - radius // 2, cx + radius // 2, cy + radius // 2), fill=accent)
        for angle_point in ((0.58, 0.22), (0.76, 0.5), (0.58, 0.78), (0.4, 0.5)):
            draw.line((cx, cy, *_point(box, *angle_point)), fill=muted, width=max(2, stroke // 2))
        _arrow(draw, _point(box, 0.7, 0.5), _point(box, 0.79, 0.5), muted, stroke)
        barrier_x, barrier_top = _point(box, 0.84, 0.22)
        _, barrier_bottom = _point(box, 0.84, 0.78)
        draw.line((barrier_x, barrier_top, barrier_x, barrier_bottom), fill=accent, width=stroke * 2)
        lock = _scaled_box(box, 0.78, 0.4, 0.94, 0.7)
        draw.rounded_rectangle(_scaled_box(lock, 0.12, 0.35, 0.88, 0.95), radius=width // 60, fill=foreground)
        draw.arc(_scaled_box(lock, 0.28, 0.02, 0.72, 0.58), 180, 360, fill=foreground, width=stroke)
    elif scene == "observability":
        editor = _scaled_box(box, 0.03, 0.18, 0.36, 0.82)
        draw.rounded_rectangle(editor, radius=width // 35, outline=foreground, width=stroke, fill="#102936")
        draw.line((_point(editor, 0.0, 0.18), _point(editor, 1.0, 0.18)), fill=muted, width=stroke)
        for index, length in enumerate((0.65, 0.45, 0.72, 0.38)):
            draw.line(
                (_point(editor, 0.12, 0.34 + index * 0.13), _point(editor, 0.12 + length, 0.34 + index * 0.13)),
                fill=accent if index == 1 else foreground,
                width=stroke,
            )
        points = [_point(box, 0.39 + index * 0.07, 0.5 + (0.09 if index % 2 else -0.09)) for index in range(5)]
        draw.line(points, fill=accent, width=stroke)
        for point in points:
            r = stroke * 2
            draw.ellipse((point[0] - r, point[1] - r, point[0] + r, point[1] + r), fill=muted)
        dashboard = _scaled_box(box, 0.72, 0.16, 0.98, 0.84)
        draw.rounded_rectangle(dashboard, radius=width // 35, outline=foreground, width=stroke, fill="#102936")
        for index, height in enumerate((0.3, 0.62, 0.45)):
            bar = _scaled_box(dashboard, 0.16 + index * 0.25, 0.78 - height, 0.31 + index * 0.25, 0.78)
            draw.rounded_rectangle(bar, radius=stroke, fill=accent if index == 1 else muted)
    elif scene == "datacenter":
        for index, y in enumerate((0.3, 0.5, 0.7)):
            cx, cy = _point(box, 0.12, y)
            radius = width // 24
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=accent if index == 1 else foreground)
        _arrow(draw, _point(box, 0.2, 0.5), _point(box, 0.35, 0.5), muted, stroke)
        nodes = [(0.4, 0.32), (0.5, 0.5), (0.4, 0.68), (0.62, 0.5)]
        for left, right in ((0, 1), (2, 1), (1, 3)):
            draw.line((_point(box, *nodes[left]), _point(box, *nodes[right])), fill=foreground, width=stroke)
        for node in nodes:
            cx, cy = _point(box, *node)
            radius = width // 42
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=accent)
        _arrow(draw, _point(box, 0.65, 0.5), _point(box, 0.73, 0.5), muted, stroke)
        for index in range(3):
            rack = _scaled_box(box, 0.75 + index * 0.08, 0.18, 0.82 + index * 0.08, 0.82)
            draw.rounded_rectangle(rack, radius=width // 80, outline=foreground, width=stroke, fill="#102936")
            for row in range(4):
                light = _point(rack, 0.5, 0.18 + row * 0.2)
                radius = max(2, stroke // 2)
                draw.ellipse((light[0] - radius, light[1] - radius, light[0] + radius, light[1] + radius), fill=accent)
    elif scene == "model_choice":
        # Three celestial personalities above one editor: the choice is about
        # fit, not a generic left-to-right process diagram.
        editor = _scaled_box(box, 0.22, 0.58, 0.78, 0.9)
        draw.rounded_rectangle(
            editor,
            radius=width // 34,
            fill="#102936",
            outline=foreground,
            width=stroke,
        )
        draw.line(
            (_point(editor, 0.0, 0.22), _point(editor, 1.0, 0.22)),
            fill=muted,
            width=stroke,
        )
        for index, color in enumerate((accent, muted, "#D49BFF")):
            cx, cy = _point(editor, 0.08 + index * 0.08, 0.11)
            radius = max(3, width // 110)
            draw.ellipse(
                (cx - radius, cy - radius, cx + radius, cy + radius),
                fill=color,
            )
        for y, line_width, color in (
            (0.42, 0.44, accent),
            (0.62, 0.62, muted),
            (0.8, 0.34, "#D49BFF"),
        ):
            draw.line(
                (_point(editor, 0.12, y), _point(editor, 0.12 + line_width, y)),
                fill=color,
                width=stroke,
            )

        bodies = ((0.27, 0.29), (0.5, 0.24), (0.73, 0.3))
        for body, target, color in zip(
            bodies,
            ((0.36, 0.58), (0.5, 0.58), (0.64, 0.58)),
            (accent, muted, "#D49BFF"),
        ):
            start = _point(box, *body)
            end = _point(box, *target)
            draw.line((start, end), fill=color, width=max(2, stroke // 2))
            node = max(3, stroke)
            draw.ellipse(
                (end[0] - node, end[1] - node, end[0] + node, end[1] + node),
                fill=color,
            )

        sun_x, sun_y = _point(box, *bodies[0])
        sun_r = width // 17
        draw.ellipse(
            (sun_x - sun_r, sun_y - sun_r, sun_x + sun_r, sun_y + sun_r),
            fill=accent,
        )
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0), (1, 1), (-1, -1)):
            draw.line(
                (
                    sun_x + dx * int(sun_r * 1.35),
                    sun_y + dy * int(sun_r * 1.35),
                    sun_x + dx * int(sun_r * 1.85),
                    sun_y + dy * int(sun_r * 1.85),
                ),
                fill=accent,
                width=stroke,
            )

        planet_x, planet_y = _point(box, *bodies[1])
        planet_r = width // 14
        draw.ellipse(
            (
                planet_x - planet_r,
                planet_y - planet_r,
                planet_x + planet_r,
                planet_y + planet_r,
            ),
            fill=muted,
            outline=foreground,
            width=stroke,
        )
        draw.arc(
            (
                planet_x - planet_r,
                planet_y - planet_r // 2,
                planet_x + planet_r,
                planet_y + planet_r // 2,
            ),
            0,
            360,
            fill=foreground,
            width=max(2, stroke // 2),
        )

        moon_x, moon_y = _point(box, *bodies[2])
        moon_r = width // 16
        draw.arc(
            (
                moon_x - moon_r,
                moon_y - moon_r,
                moon_x + moon_r,
                moon_y + moon_r,
            ),
            65,
            295,
            fill="#D49BFF",
            width=stroke * 3,
        )
        for dx, dy in ((0.09, -0.11), (0.13, 0.04), (-0.1, -0.13)):
            star_x, star_y = _point(box, bodies[2][0] + dx, bodies[2][1] + dy)
            radius = max(2, stroke // 2)
            draw.ellipse(
                (
                    star_x - radius,
                    star_y - radius,
                    star_x + radius,
                    star_y + radius,
                ),
                fill=foreground,
            )
    elif scene == "benchmark_gap":
        # A confident score dial confronts messy real-world code under a lens.
        gauge = _scaled_box(box, 0.04, 0.12, 0.5, 0.88)
        draw.arc(gauge, 205, 335, fill=muted, width=stroke * 3)
        draw.arc(gauge, 205, 286, fill=accent, width=stroke * 3)
        gauge_center = _point(box, 0.27, 0.62)
        draw.line(
            (gauge_center, _point(box, 0.41, 0.31)),
            fill=foreground,
            width=stroke * 2,
        )
        hub = width // 34
        draw.ellipse(
            (
                gauge_center[0] - hub,
                gauge_center[1] - hub,
                gauge_center[0] + hub,
                gauge_center[1] + hub,
            ),
            fill=accent,
        )
        for x, y in ((0.12, 0.55), (0.19, 0.34), (0.34, 0.26), (0.43, 0.45)):
            cx, cy = _point(box, x, y)
            radius = max(2, stroke // 2)
            draw.ellipse(
                (cx - radius, cy - radius, cx + radius, cy + radius),
                fill=foreground,
            )

        crack = [
            _point(box, 0.52, 0.16),
            _point(box, 0.48, 0.38),
            _point(box, 0.55, 0.5),
            _point(box, 0.49, 0.67),
            _point(box, 0.54, 0.86),
        ]
        draw.line(crack, fill=accent, width=stroke * 2, joint="curve")

        for offset in (0.05, 0.025, 0.0):
            page = _scaled_box(
                box,
                0.58 + offset,
                0.18 - offset,
                0.91 + offset,
                0.78 - offset,
            )
            draw.rounded_rectangle(
                page,
                radius=width // 42,
                fill="#102936" if offset == 0 else None,
                outline=foreground,
                width=stroke,
            )
        front_page = _scaled_box(box, 0.58, 0.18, 0.91, 0.78)
        for y, line_width in ((0.28, 0.55), (0.44, 0.38), (0.6, 0.64)):
            draw.line(
                (
                    _point(front_page, 0.13, y),
                    _point(front_page, 0.13 + line_width, y),
                ),
                fill=muted if y != 0.44 else accent,
                width=stroke,
            )
        lens_x, lens_y = _point(box, 0.82, 0.69)
        lens_r = width // 11
        draw.ellipse(
            (
                lens_x - lens_r,
                lens_y - lens_r,
                lens_x + lens_r,
                lens_y + lens_r,
            ),
            outline=accent,
            width=stroke * 2,
        )
        draw.line(
            (lens_x + lens_r * 2 // 3, lens_y + lens_r * 2 // 3, *_point(box, 0.96, 0.9)),
            fill=accent,
            width=stroke * 2,
        )
    elif scene == "code_workflow":
        draw_motif(draw, "code", _scaled_box(box, 0.03, 0.2, 0.34, 0.8), foreground, accent, muted)
        _arrow(draw, _point(box, 0.34, 0.5), _point(box, 0.47, 0.5), muted, stroke)
        branch = [_point(box, 0.5, 0.5), _point(box, 0.63, 0.31), _point(box, 0.63, 0.69)]
        draw.line((branch[0], branch[1]), fill=foreground, width=stroke)
        draw.line((branch[0], branch[2]), fill=foreground, width=stroke)
        for point in branch:
            radius = width // 36
            draw.ellipse((point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius), fill=accent)
        _arrow(draw, _point(box, 0.69, 0.5), _point(box, 0.8, 0.5), muted, stroke)
        cx, cy = _point(box, 0.88, 0.5)
        radius = width // 11
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=foreground, width=stroke)
        draw.line((cx - radius // 2, cy, cx - radius // 8, cy + radius // 3, cx + radius // 2, cy - radius // 3), fill=accent, width=stroke * 2, joint="curve")
    else:
        _draw_motif_flow(draw, motif, box, foreground, accent, muted)


def _cover(day, font_path, bold_font_path):
    image = Image.new("RGB", (1200, 630), "#07131F")
    visual = resolve_visual(day)
    accent = MOTIF_ACCENTS.get(visual["motif"], MOTIF_ACCENTS["signal"])
    _gradient(image, "#06121C", "#12342F")
    draw = ImageDraw.Draw(image)
    story = visual["stories"][0]

    # A single visual scene owns most of the frame; copy supports it instead of
    # turning the thumbnail into a title slide.
    for radius, amount in ((510, 0.08), (400, 0.13), (300, 0.18)):
        draw.ellipse(
            (700 - radius // 2, 315 - radius // 2, 700 + radius, 315 + radius // 2),
            fill=_blend("#0A2025", accent, amount),
        )
    draw_scene(
        draw,
        story["scene"],
        story["motif"],
        (590, 76, 1160, 554),
        foreground=WHITE,
        accent=accent,
        muted="#76C8B5",
    )

    label_font = _font(bold_font_path, 18)
    subject_font = _font(bold_font_path, 58)
    hook_font = _font(font_path, 27)

    draw.text((66, 54), "하루 한 시간 나를 DEVELOP", font=label_font, fill=accent)
    subject_lines = wrap_text_by_pixels(draw, visual["subject"], subject_font, 480, 2)
    subject_bottom = _draw_multiline(
        draw, subject_lines, (66, 190), subject_font, WHITE, line_gap=12
    )
    hook_lines = wrap_text_by_pixels(draw, visual["hook"], hook_font, 460, 2)
    _draw_multiline(
        draw, hook_lines, (66, subject_bottom + 28), hook_font, "#C1D1D6", line_gap=8
    )
    draw.line((66, 536, 126, 536), fill=accent, width=6)
    return image


STORY_PALETTES = (
    {
        "background": "#081018",
        "panel": "#102D3A",
        "foreground": WHITE,
        "muted": "#82A5B2",
        "accent": "#68E0CC",
        "motif_muted": "#367A83",
    },
    {
        "background": "#F3E6C8",
        "panel": "#E8D29F",
        "foreground": "#16211E",
        "muted": "#665F4F",
        "accent": ORANGE,
        "motif_muted": GREEN,
    },
    {
        "background": "#123B31",
        "panel": "#1B5143",
        "foreground": WHITE,
        "muted": "#A8C7BA",
        "accent": GOLD,
        "motif_muted": MINT,
    },
)


def _story_image(day, index, font_path, bold_font_path):
    """Render a visual explanation, not a second title card."""
    visual = resolve_visual(day)
    story = visual["stories"][index]
    palette = STORY_PALETTES[index % len(STORY_PALETTES)]
    image = Image.new("RGB", (1200, 630), palette["background"])
    _gradient(image, palette["background"], palette["panel"])
    draw = ImageDraw.Draw(image)
    accent = MOTIF_ACCENTS.get(story["motif"], palette["accent"])
    draw.ellipse(
        (-220, -260, 420, 380),
        fill=_blend(palette["background"], accent, 0.08),
    )
    draw.ellipse(
        (850, 260, 1430, 840),
        fill=_blend(palette["panel"], accent, 0.07),
    )

    draw_scene(
        draw,
        story["scene"],
        story["motif"],
        (58, 38, 1142, 592),
        foreground=palette["foreground"],
        accent=accent,
        muted=palette["motif_muted"],
    )
    return image


def _flow(day, font_path, bold_font_path):
    image = Image.new("RGB", (1200, 675), PAPER)
    draw = ImageDraw.Draw(image)
    visual = resolve_visual(day)
    kicker_font = _font(bold_font_path, 20)
    heading_font = _font(bold_font_path, 40)
    number_font = _font(bold_font_path, 20)
    label_font = _font(bold_font_path, 27)

    draw.rectangle((0, 0, 1200, 11), fill=GREEN)
    draw.text((72, 48), "THREE SCENES", font=kicker_font, fill=GREEN)
    draw.text((72, 86), "오늘의 세 장면", font=heading_font, fill=INK)

    fills = ("#E7F0EB", "#F4E8CD", "#E7ECE9")
    accents = (GREEN, ORANGE, GOLD)
    card_width = 320
    card_top = 166
    card_bottom = 610
    for index, story in enumerate(visual["stories"][:3]):
        left = 72 + index * 344
        right = left + card_width
        draw.rounded_rectangle((left, card_top, right, card_bottom), radius=20, fill=fills[index], outline=LINE, width=2)
        draw.text((left + 24, card_top + 22), f"0{index + 1}", font=number_font, fill=accents[index])
        icon_box = (left + 44, card_top + 86, right - 44, card_top + 314)
        draw_motif(draw, story["motif"], icon_box, foreground=GREEN_DARK, accent=accents[index], muted=GREEN)
        draw.line((left + 28, card_top + 340, right - 28, card_top + 340), fill="#C9D2CD", width=2)
        label_lines = wrap_text_by_pixels(draw, story["label"], label_font, card_width - 56, 2)
        _draw_multiline(draw, label_lines, (left + 28, card_top + 363), label_font, INK, line_gap=6)
        if index < 2:
            arrow_y = (card_top + card_bottom) // 2
            draw.line((right + 7, arrow_y, right + 25, arrow_y), fill=GREEN, width=4)
            draw.polygon([(right + 25, arrow_y - 7), (right + 35, arrow_y), (right + 25, arrow_y + 7)], fill=GREEN)
    return image


def generate_editorial_images(
    draft_id,
    day,
    output_dir=DEFAULT_OUTPUT_DIR,
    public_base_url=DEFAULT_PUBLIC_BASE_URL,
    *,
    font_path=None,
):
    """Write a cover and format-specific explanatory images."""
    identity = resolve_draft_identity(draft_id, day)
    draft_id = identity.draft_id
    is_automation = identity.content_type == "automation_case"
    regular_font = font_path or find_font()
    bold_font = font_path or find_font(bold=True)
    target = Path(output_dir) / draft_id
    target.mkdir(parents=True, exist_ok=True)

    visual = resolve_visual(day)
    cover_filename = (
        f"{_filename_part(visual.get('subject'), '업무자동화')}-대표.png"
        if is_automation
        else "cover.png"
    )
    cover_path = target / cover_filename
    _save_png_atomic(_cover(day, regular_font, bold_font), cover_path)

    base_url = str(public_base_url).rstrip("/")
    logical_dir = f"docs/tistory/assets/{draft_id}"
    assets = {
        "cover": {
            "url": f"{base_url}/{draft_id}/{cover_filename}",
            "path": f"{logical_dir}/{cover_filename}",
            "alt": f"{day.get('date_label') or identity.publish_date} {visual['subject']} - {visual['hook']} 대표 이미지",
            "width": 1200,
            "height": 630,
        },
    }
    if is_lead_story(day):
        image_rows = [
            (
                index,
                f"visual_{index}",
                (
                    f"{index:02d}-{_filename_part(visual['stories'][index - 1].get('label'), '설명-이미지')}.png"
                    if is_automation
                    else f"visual-{index:02d}.png"
                ),
            )
            for index in range(1, len(visual["stories"]) + 1)
        ]
    else:
        image_rows = [
            (index, f"story_{index}", f"story-{index:02d}.png")
            for index, _ in enumerate(_news(day)[:3], 1)
        ]
    for index, kind, filename in image_rows:
        path = target / filename
        _save_png_atomic(
            _story_image(day, index - 1, regular_font, bold_font), path
        )
        assets[kind] = {
            "url": f"{base_url}/{draft_id}/{filename}",
            "path": f"{logical_dir}/{filename}",
            "alt": "{} · {}: {} 흐름을 표현한 {}".format(
                visual["stories"][index - 1]["label"],
                visual["stories"][index - 1]["scene_label"],
                visual["stories"][index - 1]["steps"],
                "실험 이해 이미지"
                if identity.content_type == "automation_case"
                else "기사 이해 이미지",
            ),
            "width": 1200,
            "height": 630,
            "style": "text-free-editorial-scene",
        }
    day["images"] = assets
    return assets


def _atomic_write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _generate_stored_draft(
    draft_id,
    day_path,
    *,
    output_dir,
    public_base_url,
):
    identity = resolve_draft_identity(draft_id)
    day_path = Path(day_path)
    if not day_path.exists():
        raise SystemExit(f"draft not found: {day_path}")
    day = json.loads(day_path.read_text(encoding="utf-8"))
    resolve_draft_identity(identity.draft_id, day)
    assets = generate_editorial_images(
        identity.draft_id,
        day,
        output_dir=output_dir,
        public_base_url=public_base_url,
    )
    _atomic_write_json(day_path, day)

    # Imported lazily so the pure image generator remains reusable in tests.
    from .export_tistory import write_post

    write_post(identity.draft_id, day=day)
    return assets


def generate_for_draft(
    draft_id,
    *,
    root=HERE,
    output_dir=DEFAULT_OUTPUT_DIR,
    public_base_url=DEFAULT_PUBLIC_BASE_URL,
):
    """Generate fallback assets for a daily or Saturday stored draft."""
    identity = resolve_draft_identity(draft_id)
    return _generate_stored_draft(
        identity.draft_id,
        Path(root) / identity.source,
        output_dir=output_dir,
        public_base_url=public_base_url,
    )


def generate_for_day(
    day_id,
    *,
    days_dir=DEFAULT_DAYS_DIR,
    output_dir=DEFAULT_OUTPUT_DIR,
    public_base_url=DEFAULT_PUBLIC_BASE_URL,
):
    """Generate assets for a stored day and refresh its Tistory export."""
    day_id = validate_day_id(day_id)
    day_path = Path(days_dir) / f"{day_id}.json"
    return _generate_stored_draft(
        day_id,
        day_path,
        output_dir=output_dir,
        public_base_url=public_base_url,
    )


def main():
    parser = argparse.ArgumentParser(
        description="티스토리 초안용 대표·본문 이미지를 생성합니다."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--today", action="store_true", help="오늘 날짜 이미지 생성")
    group.add_argument("--day", help="YYYY-MM-DD 날짜 이미지 생성")
    group.add_argument(
        "--draft-id",
        help="YYYY-MM-DD 또는 YYYY-MM-DD-automation 초안 이미지 생성",
    )
    args = parser.parse_args()

    draft_id = dt.date.today().isoformat() if args.today else (args.draft_id or args.day)
    assets = generate_for_draft(draft_id)
    print("generated images: " + ", ".join(item["path"] for item in assets.values()))


if __name__ == "__main__":
    main()
