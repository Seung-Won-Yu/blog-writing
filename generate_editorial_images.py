"""Generate deterministic editorial images for a daily Tistory draft.

The images are intentionally rendered from the selected stories instead of
calling an image-generation API.  This keeps the daily workflow free of an
extra API key and gives every post a consistent visual identity.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from news_pipeline import validate_day_id


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
CREAM = "#F7F4EC"
PAPER = "#FCFBF7"
MUTED = "#66716B"
LINE = "#D8DEDB"
WHITE = "#FFFFFF"


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
    for character in normalized:
        candidate = current + character
        if current and _text_width(draw, candidate, font) > max_width:
            lines.append(current.rstrip())
            current = character.lstrip()
        else:
            current = candidate
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


def _editorial(day):
    value = day.get("editorial")
    return value if isinstance(value, dict) else {}


def _news(day):
    value = day.get("news")
    return value if isinstance(value, list) else []


def _cover(day, font_path, bold_font_path):
    image = Image.new("RGB", (1200, 630), GREEN_DARK)
    draw = ImageDraw.Draw(image)

    # Fixed geometry gives the image texture without making it look generated.
    for x in range(720, 1260, 72):
        draw.line((x, 0, x - 320, 630), fill="#235342", width=1)
    draw.rectangle((0, 0, 18, 630), fill=GOLD)
    draw.rounded_rectangle((76, 72, 282, 112), radius=20, fill=GREEN)

    label_font = _font(bold_font_path, 22)
    date_font = _font(font_path, 22)
    title_font = _font(bold_font_path, 52)
    lead_font = _font(font_path, 25)
    source_font = _font(bold_font_path, 19)

    draw.text((99, 79), "DAILY DEV NOTE", font=label_font, fill=WHITE)
    date_label = str(day.get("date_label") or "오늘")
    weekday = str(day.get("weekday") or "").strip()
    date_text = f"{date_label} {weekday}요일" if weekday else date_label
    draw.text((76, 139), date_text, font=date_font, fill="#BFD2C9")

    stories = _news(day)
    title = (
        _editorial(day).get("opening")
        or (stories[0].get("title_kr") if stories else None)
        or "오늘의 AI · 개발 흐름"
    )
    title_lines = wrap_text_by_pixels(draw, title, title_font, 890, 3)
    bottom = _draw_multiline(
        draw, title_lines, (76, 202), title_font, WHITE, line_gap=15
    )

    lead = "뉴스를 모으고, 내 일에 필요한 변화만 짚어봅니다."
    if bottom < 475:
        draw.text((78, min(bottom + 20, 472)), lead, font=lead_font, fill="#DCE8E2")

    sources = []
    for item in stories[:3]:
        source = " ".join(str(item.get("source") or "").split())
        if source and source not in sources:
            sources.append(source)
    source_text = "  ·  ".join(sources) or "AI · DEVELOPMENT · PRODUCT"
    draw.line((76, 548, 1124, 548), fill="#4D7465", width=1)
    draw.text((76, 572), source_text, font=source_font, fill="#BFD2C9")
    draw.text((1074, 572), "01", font=source_font, fill=GOLD)
    return image


def _flow(day, font_path, bold_font_path):
    image = Image.new("RGB", (1200, 675), PAPER)
    draw = ImageDraw.Draw(image)

    kicker_font = _font(bold_font_path, 20)
    heading_font = _font(bold_font_path, 38)
    number_font = _font(bold_font_path, 22)
    source_font = _font(bold_font_path, 18)
    title_font = _font(bold_font_path, 26)
    action_label_font = _font(bold_font_path, 18)
    action_font = _font(font_path, 22)

    draw.rectangle((0, 0, 1200, 11), fill=GREEN)
    draw.text((72, 55), "TODAY'S FLOW", font=kicker_font, fill=GREEN)
    draw.text((72, 92), "오늘의 흐름", font=heading_font, fill=INK)
    draw.line((72, 156, 1128, 156), fill=LINE, width=2)

    stories = _news(day)[:3]
    row_top = 178
    row_height = 116
    for index in range(3):
        item = stories[index] if index < len(stories) else {}
        center_y = row_top + index * row_height + 38
        draw.ellipse((72, center_y - 25, 122, center_y + 25), fill=GREEN)
        number = f"{index + 1:02d}"
        number_width = _text_width(draw, number, number_font)
        draw.text(
            (97 - number_width / 2, center_y - 17),
            number,
            font=number_font,
            fill=WHITE,
        )
        if index < 2:
            draw.line((97, center_y + 25, 97, center_y + 91), fill="#AFC4BA", width=3)

        source = " ".join(str(item.get("source") or "읽을거리").split())
        title = " ".join(str(item.get("title_kr") or "새 소식을 정리하고 있습니다.").split())
        draw.text((154, center_y - 33), source.upper(), font=source_font, fill=GOLD)
        lines = wrap_text_by_pixels(draw, title, title_font, 925, 2)
        _draw_multiline(draw, lines, (154, center_y - 2), title_font, INK, line_gap=6)

    action_top = 532
    draw.rounded_rectangle((72, action_top, 1128, 630), radius=8, fill=CREAM)
    draw.rectangle((72, action_top, 78, 630), fill=GOLD)
    draw.text((102, action_top + 17), "오늘 해볼 것", font=action_label_font, fill=GREEN)
    action = _editorial(day).get("action") or "기사 하나를 골라 내 작업에 적용할 점을 한 줄로 적어보세요."
    action_lines = wrap_text_by_pixels(draw, action, action_font, 970, 2)
    _draw_multiline(
        draw, action_lines, (102, action_top + 48), action_font, MUTED, line_gap=5
    )
    return image


def generate_editorial_images(
    day_id,
    day,
    output_dir=DEFAULT_OUTPUT_DIR,
    public_base_url=DEFAULT_PUBLIC_BASE_URL,
    *,
    font_path=None,
):
    """Write a cover and reading-flow image, attach their metadata, and return it."""
    day_id = validate_day_id(day_id)
    regular_font = font_path or find_font()
    bold_font = font_path or find_font(bold=True)
    target = Path(output_dir) / day_id
    target.mkdir(parents=True, exist_ok=True)

    cover_path = target / "cover.png"
    flow_path = target / "flow.png"
    _cover(day, regular_font, bold_font).save(cover_path, "PNG", optimize=True)
    _flow(day, regular_font, bold_font).save(flow_path, "PNG", optimize=True)

    base_url = str(public_base_url).rstrip("/")
    logical_dir = f"docs/tistory/assets/{day_id}"
    assets = {
        "cover": {
            "url": f"{base_url}/{day_id}/cover.png",
            "path": f"{logical_dir}/cover.png",
            "alt": f"{day.get('date_label') or day_id} 오늘의 AI 개발 뉴스 대표 이미지",
            "width": 1200,
            "height": 630,
        },
        "flow": {
            "url": f"{base_url}/{day_id}/flow.png",
            "path": f"{logical_dir}/flow.png",
            "alt": f"{day.get('date_label') or day_id} 오늘의 뉴스 흐름 요약",
            "width": 1200,
            "height": 675,
        },
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
