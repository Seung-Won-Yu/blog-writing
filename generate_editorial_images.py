"""Generate deterministic editorial images for a daily Tistory draft.

The cover and story images are rendered from the selected stories instead of
calling an image-generation API. This keeps the workflow free of an extra API
key and gives every post a consistent visual identity.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from news_pipeline import validate_day_id
from visual_direction import VISUAL_LABELS, motif_for_text, validate_visual


HERE = Path(__file__).resolve().parent
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


def resolve_visual(day):
    """Resolve safe visual copy and per-story motifs for old and new day JSON."""
    stories = _news(day)[:3]
    first = stories[0] if stories else {}
    reference = "{} {}".format(first.get("title_kr", ""), first.get("blurb_kr", ""))
    visual = validate_visual(day.get("visual"), reference)
    visual["stories"] = []
    for item in stories:
        motif = motif_for_text(item.get("title_kr", ""))
        if motif == "signal":
            motif = motif_for_text(item.get("blurb_kr", ""))
        visual["stories"].append(
            {
                "motif": motif,
                "label": VISUAL_LABELS[motif],
                "title": " ".join(str(item.get("title_kr") or "").split()),
                "source": " ".join(str(item.get("source") or "").split()),
            }
        )
    while len(visual["stories"]) < 3:
        visual["stories"].append(
            {
                "motif": "signal",
                "label": VISUAL_LABELS["signal"],
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


def _cover(day, font_path, bold_font_path):
    image = Image.new("RGB", (1200, 630), "#07131F")
    draw = ImageDraw.Draw(image)
    visual = resolve_visual(day)

    # A full-bleed editorial scene reads as a thumbnail, not a UI card.
    draw.rectangle((0, 0, 1200, 10), fill="#6FE6D0")
    for x in range(0, 1200, 80):
        draw.line((x, 10, x - 210, 630), fill="#102536", width=1)
    for y in range(90, 630, 90):
        draw.line((0, y, 1200, y), fill="#102536", width=1)
    draw.polygon([(740, 10), (1200, 10), (1200, 630), (1000, 630)], fill="#0B2F35")
    draw.ellipse((760, 72, 1190, 502), outline="#1D5960", width=3)
    draw.ellipse((822, 134, 1128, 440), outline="#6FE6D0", width=7)
    draw.arc((714, 28, 1238, 552), 205, 326, fill=ORANGE, width=9)

    label_font = _font(bold_font_path, 18)
    date_font = _font(font_path, 19)
    title_font = _font(bold_font_path, 61)
    footer_font = _font(bold_font_path, 18)

    date_label = str(day.get("date_label") or "오늘")
    weekday = str(day.get("weekday") or "").strip()
    date_text = f"{date_label} {weekday}요일" if weekday else date_label
    draw.text((72, 58), "DAILY DEV BRIEF", font=label_font, fill="#6FE6D0")
    draw.text((72, 96), date_text, font=date_font, fill="#91AAB8")
    title_lines = wrap_text_by_pixels(draw, visual["hook"], title_font, 590, 3)
    title_bottom = _draw_multiline(
        draw, title_lines, (72, 178), title_font, WHITE, line_gap=14
    )
    draw.rectangle((72, min(470, title_bottom + 25), 144, min(476, title_bottom + 31)), fill=ORANGE)

    draw_motif(
        draw,
        visual["motif"],
        (846, 158, 1104, 416),
        foreground=WHITE,
        accent=ORANGE,
        muted="#6FE6D0",
    )
    draw.text(
        (838, 475),
        VISUAL_LABELS[visual["motif"]],
        font=footer_font,
        fill=WHITE,
    )

    footer = "  ·  ".join(
        "{} / {}".format(item.get("source") or "NEWS", item["label"])
        for item in visual["stories"][1:3]
        if item.get("title")
    )
    if footer:
        footer_lines = wrap_text_by_pixels(draw, footer, footer_font, 630, 1)
        _draw_multiline(draw, footer_lines, (72, 560), footer_font, "#91AAB8", 0)
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
    """Render one source-grounded story break with a large visual metaphor."""
    visual = resolve_visual(day)
    story = visual["stories"][index]
    palette = STORY_PALETTES[index % len(STORY_PALETTES)]
    image = Image.new("RGB", (1200, 630), palette["background"])
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, 1200, 9), fill=palette["accent"])
    draw.polygon([(710, 9), (1200, 9), (1200, 630), (900, 630)], fill=palette["panel"])
    for offset in range(-80, 760, 72):
        draw.line(
            (760 + offset, 10, 1030 + offset, 630),
            fill=palette["motif_muted"],
            width=1,
        )
    draw.ellipse((786, 112, 1146, 472), outline=palette["motif_muted"], width=4)
    draw.ellipse((840, 166, 1092, 418), outline=palette["accent"], width=6)

    kicker_font = _font(bold_font_path, 18)
    source_font = _font(font_path, 20)
    title_font = _font(bold_font_path, 47)
    label_font = _font(bold_font_path, 20)
    draw.text((70, 60), f"NEWS {index + 1:02d}", font=kicker_font, fill=palette["accent"])
    source = story["source"] or "오늘의 개발 뉴스"
    source_lines = wrap_text_by_pixels(draw, source, source_font, 480, 1)
    _draw_multiline(draw, source_lines, (176, 58), source_font, palette["muted"], 0)

    title_lines = wrap_text_by_pixels(draw, story["title"], title_font, 610, 3)
    _draw_multiline(
        draw, title_lines, (70, 164), title_font, palette["foreground"], 14
    )
    draw.rectangle((70, 518, 126, 524), fill=palette["accent"])
    draw.text((70, 550), story["label"], font=label_font, fill=palette["muted"])

    draw_motif(
        draw,
        story["motif"],
        (858, 184, 1074, 400),
        foreground=palette["foreground"],
        accent=palette["accent"],
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
    day_id,
    day,
    output_dir=DEFAULT_OUTPUT_DIR,
    public_base_url=DEFAULT_PUBLIC_BASE_URL,
    *,
    font_path=None,
):
    """Write a cover and up to three story images and attach their metadata."""
    day_id = validate_day_id(day_id)
    regular_font = font_path or find_font()
    bold_font = font_path or find_font(bold=True)
    target = Path(output_dir) / day_id
    target.mkdir(parents=True, exist_ok=True)

    cover_path = target / "cover.png"
    visual = resolve_visual(day)
    _save_png_atomic(_cover(day, regular_font, bold_font), cover_path)

    base_url = str(public_base_url).rstrip("/")
    logical_dir = f"docs/tistory/assets/{day_id}"
    assets = {
        "cover": {
            "url": f"{base_url}/{day_id}/cover.png",
            "path": f"{logical_dir}/cover.png",
            "alt": f"{day.get('date_label') or day_id} {visual['hook']} 대표 이미지",
            "width": 1200,
            "height": 630,
        },
    }
    for index, story in enumerate(_news(day)[:3], 1):
        path = target / f"story-{index:02d}.png"
        _save_png_atomic(
            _story_image(day, index - 1, regular_font, bold_font), path
        )
        title = " ".join(str(story.get("title_kr") or "").split())
        assets[f"story_{index}"] = {
            "url": f"{base_url}/{day_id}/story-{index:02d}.png",
            "path": f"{logical_dir}/story-{index:02d}.png",
            "alt": f"{title} 관련 편집 이미지",
            "width": 1200,
            "height": 630,
        }
    day["images"] = assets
    return assets


def _atomic_write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


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
    if not day_path.exists():
        raise SystemExit(f"day not found: {day_path}")
    day = json.loads(day_path.read_text(encoding="utf-8"))
    assets = generate_editorial_images(
        day_id, day, output_dir=output_dir, public_base_url=public_base_url
    )
    _atomic_write_json(day_path, day)

    # Imported lazily so the pure image generator remains reusable in tests.
    from export_tistory import write_post

    write_post(day_id, day=day)
    return assets


def main():
    parser = argparse.ArgumentParser(
        description="티스토리 초안용 대표·본문 이미지를 생성합니다."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--today", action="store_true", help="오늘 날짜 이미지 생성")
    group.add_argument("--day", help="YYYY-MM-DD 날짜 이미지 생성")
    args = parser.parse_args()

    day_id = dt.date.today().isoformat() if args.today else args.day
    assets = generate_for_day(day_id)
    print("generated images: " + ", ".join(item["path"] for item in assets.values()))


if __name__ == "__main__":
    main()
