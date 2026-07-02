# -*- coding: utf-8 -*-
"""
Tistory-ready post exporter.

Official Tistory Open API publishing has been retired, so this script generates
reviewable HTML that can be pasted into the Tistory editor's HTML mode.

usage:
  python export_tistory.py --latest
  python export_tistory.py --day 2026-07-01
  python export_tistory.py --all
"""
import argparse
import glob
import html
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DAYS_DIR = HERE / "data" / "days"
OUT_DIR = HERE / "docs" / "tistory"

DEFAULT_CATEGORY = "데일리IT뉴스"
DEFAULT_TAGS = ["AI", "IT뉴스", "개발뉴스", "정처기", "개발용어", "데일리다이제스트"]


def esc(value):
    return html.escape(html.unescape(str(value or "")), quote=True)


def plain(value):
    return " ".join(str(value or "").split())


def slugify(text):
    text = re.sub(r"[^0-9A-Za-z가-힣._-]+", "-", text.strip())
    return re.sub(r"-{2,}", "-", text).strip("-") or "daily-digest"


def day_files():
    return sorted(DAYS_DIR.glob("*.json"))


def load_day(day_id):
    path = DAYS_DIR / f"{day_id}.json"
    if not path.exists():
        raise SystemExit(f"day not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def latest_day_id():
    files = day_files()
    if not files:
        raise SystemExit(f"no day json files in {DAYS_DIR}")
    return files[-1].stem


def summarize_blocks(blocks, limit=3):
    """Use only a short digest so the Tistory post points readers to sources."""
    rows = []
    for block in blocks or []:
        if block.get("t") != "p":
            continue
        text = plain(block.get("text"))
        if not text:
            continue
        rows.append(text)
        if len(rows) >= limit:
            break
    return rows


def post_title(day):
    label = plain(day.get("date_label"))
    return f"[데일리 IT 뉴스] {label} - 오늘의 개발 뉴스와 정처기 문제"


def build_news_section(news):
    if not news:
        return '<p style="margin:0 0 16px;">오늘 수집된 뉴스가 없습니다.</p>'

    parts = []
    for idx, item in enumerate(news, 1):
        title = plain(item.get("title_kr"))
        source = plain(item.get("source"))
        url = plain(item.get("url"))
        blurb = plain(item.get("blurb_kr"))
        bullets = summarize_blocks(item.get("content"))

        bullet_html = ""
        if bullets:
            bullet_html = '<ul class="digest-points">' + "".join(
                f"<li>{esc(text)}</li>" for text in bullets
            ) + "</ul>"

        source_link = (
            f'<p class="digest-source-link"><a href="{esc(url)}" target="_blank" rel="noopener">원문 보기</a></p>'
            if url
            else ""
        )

        parts.append(
            f"""
<section class="digest-news-card">
  <p class="digest-source">{idx}. {esc(source)}</p>
  <h3>{esc(title)}</h3>
  <p>{esc(blurb)}</p>
  {bullet_html}
  {source_link}
</section>""".strip()
        )
    return "\n".join(parts)


def build_quiz_section(quiz):
    if not quiz:
        return ""
    options = quiz.get("options") or []
    answer = int(quiz.get("answer", 0))
    option_html = "".join(
        f'<li class="is-answer">{esc(opt)}</li>' if i == answer else f"<li>{esc(opt)}</li>"
        for i, opt in enumerate(options)
    )
    return f"""
<section class="digest-quiz">
  <p class="digest-source">기초상식 · {esc(quiz.get("category", "정보처리기사"))}</p>
  <h2>오늘의 정처기 문제</h2>
  <p>{esc(quiz.get("question"))}</p>
  <ol>{option_html}</ol>
  <p class="digest-explain"><b>해설</b> {esc(quiz.get("explain_kr"))}</p>
</section>""".strip()


def build_terms_section(terms):
    if not terms:
        return ""
    rows = "".join(
        f"""
<li>
  <b>{esc(t.get("term"))}</b>
  <span>{esc(t.get("kind"))}</span><br>
  <em>{esc(t.get("meaning_kr"))}</em>
</li>""".strip()
        for t in terms
    )
    return f"""
<section class="digest-terms">
  <h2>오늘의 IT · 개발 · 기획 용어</h2>
  <ul>{rows}</ul>
</section>""".strip()


def render_post(day_id, day):
    label = plain(day.get("date_label"))
    weekday = plain(day.get("weekday"))
    date_text = f"{label} ({weekday})" if weekday else label
    news = day.get("news") or []
    lead = " / ".join(plain(item.get("title_kr")) for item in news[:3])

    return f"""<!--
title: {esc(post_title(day))}
category: {esc(DEFAULT_CATEGORY)}
tags: {", ".join(DEFAULT_TAGS)}
slug: {slugify(day_id + "-daily-digest")}
-->
<article class="daily-digest-post">
  <p class="digest-kicker">{esc(date_text)} · 자동 생성 데일리 다이제스트</p>
  <h2 class="digest-title">오늘의 IT/개발 읽을거리</h2>
  <p class="digest-lead">
    오늘은 {esc(lead)} 흐름을 중심으로 읽어볼 만한 소식을 정리했습니다.
    본문은 짧은 요약과 학습용 문제로 구성했으며, 세부 내용은 각 원문 링크에서 확인하는 것을 권장합니다.
  </p>

  <hr>

  <h2>오늘의 뉴스 3개</h2>
  {build_news_section(news)}

  {build_quiz_section(day.get("quiz"))}

  {build_terms_section(day.get("terms") or [])}

  <p class="digest-note">
    이 글은 공개 뉴스 페이지를 기반으로 자동 수집·요약한 학습용 다이제스트입니다.
    수치, 정책, 제품 정보처럼 정확성이 중요한 내용은 반드시 원문을 함께 확인해 주세요.
  </p>
</article>
"""


def write_post(day_id):
    day = load_day(day_id)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    html_path = OUT_DIR / f"{day_id}.html"
    meta_path = OUT_DIR / f"{day_id}.json"

    html_path.write_text(render_post(day_id, day), encoding="utf-8")
    meta_path.write_text(
        json.dumps(
            {
                "title": post_title(day),
                "category": DEFAULT_CATEGORY,
                "tags": DEFAULT_TAGS,
                "source": f"data/days/{day_id}.json",
                "html": f"docs/tistory/{day_id}.html",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"exported: {html_path}")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--latest", action="store_true", help="export the newest day")
    group.add_argument("--day", help="export one YYYY-MM-DD day")
    group.add_argument("--all", action="store_true", help="export every day")
    args = parser.parse_args()

    if args.latest:
        write_post(latest_day_id())
    elif args.day:
        write_post(args.day)
    else:
        for path in day_files():
            write_post(path.stem)


if __name__ == "__main__":
    main()
