"""Normalize archived Tistory HTML and build one-paste AdFit copies."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from .export_tistory import TISTORY_ADFIT_MARKER


ROOT = Path(__file__).resolve().parents[2]
TISTORY_DIR = ROOT / "docs" / "tistory"

ARCHIVED_POSTS = {
    "2026-07-03": {"file": "2026-07-03.html"},
    "2026-07-04": {"file": "2026-07-04.html"},
    "2026-07-05": {"file": "2026-07-05.html"},
    "2026-07-06": {"file": "2026-07-06.html"},
    "2026-07-07": {"file": "2026-07-07.html"},
    "2026-07-08": {
        "file": "2026-07-08.html",
        "second_story_heading": "PR 이미지 첨부 한 번이 자동화를 막고 있었다",
    },
    "2026-07-09": {"file": "2026-07-09.html"},
    "2026-07-10": {"file": "2026-07-10.html"},
    "2026-07-10-codex-gpt-5.6": {
        "file": "2026-07-10-codex-gpt-5.6.html",
        "direct_heading": "무엇이 바뀐 걸까?",
    },
    "2026-07-11": {"file": "2026-07-11.html"},
    "2026-07-12": {"file": "2026-07-12.html"},
    "2026-07-13": {
        "file": "2026-07-13.html",
        "direct_heading": "사람을 다시 뛰게 만드는 세 가지 장치",
    },
    "2026-07-14": {"file": "2026-07-14.html"},
}

ADFIT_RE = re.compile(
    r'\s*<figure class="ad-wp"[^>]*data-ad-vendor="adfit"[^>]*></figure>'
    r'(?:\s*<p[^>]*>\s*(?:&nbsp;)?\s*</p>)?',
    re.IGNORECASE,
)
NEWS_CARD_RE = re.compile(
    r'<section(?:\s+id="digest-news-\d+")?\s+class="digest-news-card"'
    r'(?:\s+style="[^"]*")?>',
    re.IGNORECASE,
)


def _replace_first_article(html_text):
    def replacement(match):
        tag = match.group(0)
        class_match = re.search(r'class="([^"]+)"', tag)
        classes = class_match.group(1).split() if class_match else []
        if "daily-digest-post" not in classes:
            classes.append("daily-digest-post")
        return (
            f'<article class="{" ".join(classes)}" '
            'data-digest-version="2">'
        )

    return re.sub(r"<article\b[^>]*>", replacement, html_text, count=1)


def _strip_class_style(html_text, class_name):
    pattern = re.compile(
        rf'<section\s+class="{re.escape(class_name)}"(?:\s+style="[^"]*")?>',
        re.IGNORECASE,
    )
    return pattern.sub(f'<section class="{class_name}">', html_text)


def normalize_archived_html(html_text):
    """Move archived posts to the class-only v2 design contract."""
    cleaned = ADFIT_RE.sub("", str(html_text))
    # The skin is the only design owner. Historical inline declarations,
    # especially !important width and padding, caused every post to render
    # differently and overrode the canonical skin layer.
    cleaned = re.sub(r"\s+style=(?:\"[^\"]*\"|'[^']*')", "", cleaned)
    cleaned = _replace_first_article(cleaned)
    counter = 0

    def news_card(match):
        nonlocal counter
        counter += 1
        return f'<section id="digest-news-{counter}" class="digest-news-card">'

    cleaned = NEWS_CARD_RE.sub(news_card, cleaned)
    cleaned = _strip_class_style(cleaned, "digest-quiz")
    cleaned = _strip_class_style(cleaned, "digest-terms")
    cleaned = cleaned.replace("오늘의 메모", "이번 글에서 남는 것")
    cleaned = re.sub(r"[ \t]+$", "", cleaned, flags=re.MULTILINE)
    return cleaned


def _ad_insertion_index(html_text, second_story_heading=None, direct_heading=None):
    standard = html_text.find('<section id="digest-news-2"')
    if standard >= 0:
        return standard
    if second_story_heading:
        heading_at = html_text.find(second_story_heading)
        if heading_at >= 0:
            section_at = html_text.rfind("<section", 0, heading_at)
            if section_at >= 0:
                return section_at
    if direct_heading:
        heading_at = html_text.find(direct_heading)
        if heading_at >= 0:
            heading_tag = html_text.rfind("<h2", 0, heading_at)
            if heading_tag >= 0:
                return heading_tag
    return -1


def add_adfit_after_first_section(
    html_text, *, second_story_heading=None, direct_heading=None
):
    """Insert exactly one AdFit marker before the second main content block."""
    cleaned = ADFIT_RE.sub("", str(html_text))
    split_at = _ad_insertion_index(
        cleaned,
        second_story_heading=second_story_heading,
        direct_heading=direct_heading,
    )
    if split_at < 0:
        raise ValueError("두 번째 본문 시작 위치를 찾지 못했습니다.")
    return (
        cleaned[:split_at].rstrip()
        + "\n"
        + TISTORY_ADFIT_MARKER
        + '\n<p data-ke-size="size16">&nbsp;</p>\n'
        + cleaned[split_at:].lstrip()
    )


def repair_archived_posts(output_dir=TISTORY_DIR):
    output = Path(output_dir)
    written = []
    for slug, config in ARCHIVED_POSTS.items():
        source = output / config["file"]
        normalized = normalize_archived_html(source.read_text(encoding="utf-8"))
        source.write_text(normalized, encoding="utf-8")
        ready = add_adfit_after_first_section(
            normalized,
            second_story_heading=config.get("second_story_heading"),
            direct_heading=config.get("direct_heading"),
        )
        target = output / f"{slug}-adfit.html"
        target.write_text(ready, encoding="utf-8")
        written.append(target)
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description="과거 티스토리 HTML을 현재 양식으로 복구합니다.")
    parser.add_argument("--output-dir", default=str(TISTORY_DIR))
    args = parser.parse_args(argv)
    for path in repair_archived_posts(args.output_dir):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
