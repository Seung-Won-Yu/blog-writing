# -*- coding: utf-8 -*-
"""
Tistory-ready post exporter.

Official Tistory Open API publishing has been retired, so this script generates
reviewable HTML that can be pasted into the Tistory editor's HTML mode.

usage:
  python pages_to_tistory.py --day 2026-07-01
  python draft_tistory_post.py --day 2026-07-01 --from-pages
  python export_tistory.py --today
  python export_tistory.py --latest
  python export_tistory.py --day 2026-07-01
  python export_tistory.py --all
"""
import argparse
import datetime
import glob
import html
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DAYS_DIR = HERE / "data" / "days"
OUT_DIR = HERE / "docs" / "tistory"

DEFAULT_BLOG_URL = "https://won0322.tistory.com"
DEFAULT_CATEGORY = "데일리IT뉴스"
DEFAULT_TAGS = ["AI", "IT뉴스", "개발뉴스", "정처기", "개발용어", "데일리다이제스트"]

POST_SHELL_STYLE = (
    "max-width:760px;margin:0 auto;padding:8px 0 28px;color:#334155;"
    "font-family:AppleSDGothicNeo,'Malgun Gothic',sans-serif;line-height:1.75;"
)
HERO_STYLE = (
    "margin:0 0 28px;padding:28px 26px;border:1px solid #d9e0ea;border-radius:18px;"
    "background:linear-gradient(135deg,#f8fafc 0%,#eef6f5 52%,#fff7ed 100%);"
    "box-shadow:0 12px 34px rgba(24,33,47,.06);"
)
KICKER_STYLE = (
    "margin:0 0 10px;color:#0f9b8e;font-size:13px;font-weight:700;"
    "letter-spacing:.02em;"
)
TITLE_STYLE = "margin:0 0 14px;color:#18212f;font-size:30px;line-height:1.32;font-weight:800;"
LEAD_STYLE = "margin:0;color:#475569;font-size:16px;line-height:1.75;"
META_INTRO_STYLE = (
    "margin:0 0 14px;color:#334155;font-size:15px;line-height:1.7;font-weight:700;"
)
SECTION_TITLE_STYLE = (
    "margin:34px 0 16px;color:#18212f;font-size:22px;line-height:1.35;font-weight:800;"
)
CARD_STYLE = (
    "margin:18px 0;padding:22px 22px;border:1px solid #d9e0ea;border-radius:16px;"
    "background:#fff;box-shadow:0 10px 28px rgba(24,33,47,.055);"
)
NEWS_IMAGE_STYLE = (
    "display:block;width:100%;max-height:270px;object-fit:cover;margin:0 0 16px;"
    "border-radius:14px;border:1px solid #e2e8f0;background:#f8fafc;"
)
BADGE_STYLE = (
    "display:inline-block;margin:0 0 10px;padding:4px 9px;border-radius:999px;"
    "background:#effaf7;color:#0f9b8e;font-size:12px;font-weight:800;"
)
NEWS_TITLE_STYLE = "margin:0 0 10px;color:#18212f;font-size:20px;line-height:1.45;font-weight:800;"
NEWS_BODY_STYLE = (
    "margin:18px 0 0;padding:18px 0 0;border-top:1px solid #e2e8f0;"
)
NEWS_BODY_HEADING_STYLE = (
    "margin:20px 0 8px;color:#18212f;font-size:17px;line-height:1.45;font-weight:800;"
)
NEWS_BODY_PARAGRAPH_STYLE = "margin:0 0 12px;color:#475569;line-height:1.78;"
BUTTON_STYLE = (
    "display:inline-block;margin-top:8px;padding:8px 12px;border-radius:10px;"
    "background:#18212f;color:#fff;text-decoration:none;font-size:13px;font-weight:800;"
)
QUIZ_STYLE = (
    "margin:30px 0;padding:24px 22px;border:1px solid #bddfd9;border-radius:18px;"
    "background:linear-gradient(135deg,#f8fafc,#effaf7);box-shadow:0 10px 28px rgba(15,155,142,.08);"
)
TERM_ITEM_STYLE = (
    "margin:0 0 10px;padding:16px 0;border-bottom:1px solid #d9e0ea;list-style:none;"
)
NOTE_STYLE = (
    "margin-top:34px;padding:16px 18px;border-left:4px solid #0f9b8e;border-radius:12px;"
    "background:#f8fafc;color:#64748b;font-size:14px;line-height:1.7;"
)
SUMMARY_STYLE = (
    "margin:0 0 28px;padding:20px 22px;border:1px solid #d9e0ea;border-radius:16px;"
    "background:#ffffff;box-shadow:0 10px 26px rgba(24,33,47,.045);"
)
SUMMARY_LIST_STYLE = "margin:0;padding-left:20px;color:#475569;line-height:1.75;"


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


def today_day_id():
    return datetime.date.today().isoformat()


def latest_or_today():
    latest = latest_day_id()
    today = today_day_id()
    if latest != today:
        raise SystemExit(
            f"today's data is missing: expected data/days/{today}.json, latest is {latest}. "
            f"Run pipeline_gemini.py first or pass --day {latest} explicitly."
        )
    return latest


def render_content_blocks(blocks):
    rows = []
    for block in blocks or []:
        text = plain(block.get("text"))
        if not text:
            continue
        if block.get("t") == "h":
            rows.append(f'<h4{style(NEWS_BODY_HEADING_STYLE)}>{esc(text)}</h4>')
        else:
            rows.append(f'<p{style(NEWS_BODY_PARAGRAPH_STYLE)}>{esc(text)}</p>')
    if not rows:
        return ""
    return f'<div class="digest-full-content"{style(NEWS_BODY_STYLE)}>' + "".join(rows) + "</div>"


def style(value):
    return f' style="{esc(value)}"'


def post_title(day):
    label = plain(day.get("date_label"))
    return f"[데일리 IT 뉴스] {label} - 오늘의 개발 뉴스와 정처기 문제"


def news_titles(day, limit=None):
    titles = [plain(item.get("title_kr")) for item in day.get("news", [])]
    titles = [title for title in titles if title]
    return titles[:limit] if limit else titles


def trim_text(text, limit):
    value = plain(text)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def title_keyword(text, limit=28):
    value = plain(text)
    if " - " in value:
        left, right = value.split(" - ", 1)
        if len(left) <= 18:
            value = right

    english_terms = []
    for term in re.findall(r"[A-Za-z][A-Za-z0-9+._/-]*", value):
        normalized = term.strip(".,:;()[]{}")
        if len(normalized) < 2:
            continue
        if normalized.lower() in {"the", "and", "with", "for", "from"}:
            continue
        if normalized not in english_terms:
            english_terms.append(normalized)
    if english_terms:
        return " ".join(english_terms[:3])

    value = re.split(r"[,·:;|()]", value)[0].strip()
    if len(value) > limit:
        return value[:limit].rstrip()
    return value


def build_title_candidates(day):
    label = plain(day.get("date_label"))
    titles = news_titles(day, 3)
    first = titles[0] if titles else "오늘의 개발 뉴스"
    second = titles[1] if len(titles) > 1 else "정처기 문제"
    first_keyword = title_keyword(first)
    second_keyword = title_keyword(second)

    candidates = [
        f"[데일리 IT 뉴스] {label} - {first_keyword}, 정처기 문제 정리",
        f"{label} 개발 뉴스 요약: {first_keyword} 외 오늘의 IT 이슈",
        f"오늘의 AI/개발 뉴스와 정보처리기사 문제 정리 ({label})",
    ]
    if len(titles) > 1:
        candidates.insert(
            1,
            f"[개발 뉴스] {first_keyword} · {second_keyword} 핵심 정리",
        )
    return candidates[:4]


def build_meta_description(day):
    label = plain(day.get("date_label"))
    titles = news_titles(day, 2)
    keywords = [title_keyword(title, 34) for title in titles]
    keywords = [keyword for keyword in keywords if keyword]
    topic_text = ", ".join(keywords[:2]) if keywords else "AI/개발 뉴스"
    quiz = day.get("quiz") or {}
    quiz_category = plain(quiz.get("category")) or "정보처리기사"
    return (
        f"{label} 데일리 IT 뉴스: {topic_text} 핵심과 "
        f"{quiz_category} 문제, 개발 용어를 정리했습니다."
    )


def build_key_summary(day):
    titles = news_titles(day, 3)
    quiz = day.get("quiz") or {}
    terms = [plain(item.get("term")) for item in day.get("terms", []) if item.get("term")]

    rows = []
    if titles:
        rows.append("오늘의 주요 뉴스: " + " / ".join(titles))
    if quiz.get("question"):
        rows.append(f"정처기 포인트: {plain(quiz.get('category')) or '기초상식'} 문제로 개념을 점검합니다.")
    if terms:
        rows.append("함께 익힐 용어: " + ", ".join(terms[:4]))
    rows.append("읽는 순서: 뉴스 흐름을 먼저 보고, 마지막에 문제와 용어로 복습하면 좋습니다.")
    return rows[:4]


def build_publish_checklist(day):
    titles = build_title_candidates(day)
    return [
        "제목 후보 중 검색 키워드가 가장 자연스러운 제목을 선택하기",
        "본문 상단 이미지가 정상 표시되는지 확인하기",
        "태그 입력 후 카테고리를 데일리IT뉴스로 지정하기",
        "관련된 정처기/개발일지 글이 있으면 본문 하단에 내부 링크 1개 추가하기",
        f"추천 제목: {titles[0]}" if titles else "추천 제목 확인하기",
    ]


def build_recommended_tags(day):
    tags = list(DEFAULT_TAGS)
    for item in day.get("news", []):
        source = plain(item.get("source"))
        if source and source not in tags:
            tags.append(source)
    for term in day.get("terms", [])[:3]:
        value = plain(term.get("term"))
        if value and value not in tags:
            tags.append(value)
    return tags[:12]


def build_summary_section(day):
    rows = "".join(f"<li>{esc(item)}</li>" for item in build_key_summary(day))
    return f"""
<section class="digest-summary"{style(SUMMARY_STYLE)}>
  <h2{style(SECTION_TITLE_STYLE + "margin-top:0;")}>오늘의 핵심 요약</h2>
  <ul{style(SUMMARY_LIST_STYLE)}>{rows}</ul>
</section>""".strip()


def build_news_section(news):
    if not news:
        return '<p style="margin:0 0 16px;">오늘 수집된 뉴스가 없습니다.</p>'

    parts = []
    for idx, item in enumerate(news, 1):
        title = plain(item.get("title_kr"))
        source = plain(item.get("source"))
        url = plain(item.get("url"))
        blurb = plain(item.get("blurb_kr"))
        image = plain(item.get("image_url") or item.get("image"))
        full_content = render_content_blocks(item.get("content"))

        image_html = (
            f'<img class="digest-news-image" src="{esc(image)}" alt="" loading="lazy"{style(NEWS_IMAGE_STYLE)}>'
            if image
            else ""
        )
        summary_html = (
            f'<p style="margin:0;color:#475569;">{esc(blurb)}</p>'
            if blurb and not full_content
            else ""
        )

        source_link = (
            f'<p class="digest-source-link" style="margin:14px 0 0;"><a href="{esc(url)}" target="_blank" rel="noopener"{style(BUTTON_STYLE)}>원문 보기</a></p>'
            if url
            else ""
        )

        parts.append(
            f"""
<section class="digest-news-card"{style(CARD_STYLE)}>
  {image_html}
  <p class="digest-source"{style(BADGE_STYLE)}>{idx}. {esc(source)}</p>
  <h3{style(NEWS_TITLE_STYLE)}>{esc(title)}</h3>
  {summary_html}
  {full_content}
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
        (
            f'<li class="digest-option is-answer" style="margin:0 0 8px;color:#0f9b8e;font-weight:800;">정답 · {esc(opt)}</li>'
            if i == answer
            else f'<li class="digest-option" style="margin:0 0 8px;">{esc(opt)}</li>'
        )
        for i, opt in enumerate(options)
    )
    return f"""
<section class="digest-quiz"{style(QUIZ_STYLE)}>
  <p class="digest-source"{style(BADGE_STYLE)}>기초상식 · {esc(quiz.get("category", "정보처리기사"))}</p>
  <h2{style(SECTION_TITLE_STYLE + "margin-top:0;")}>오늘의 정처기 문제</h2>
  <p class="digest-question" style="margin:0 0 12px;color:#18212f;font-weight:700;">{esc(quiz.get("question"))}</p>
  <ol class="digest-options" style="margin:12px 0 14px;padding-left:22px;">{option_html}</ol>
  <p class="digest-explain" style="margin:0;color:#475569;"><b>해설</b> {esc(quiz.get("explain_kr"))}</p>
</section>""".strip()


def build_terms_section(terms):
    if not terms:
        return ""
    rows = "".join(
        f"""
<li{style(TERM_ITEM_STYLE)}>
  <b style="color:#18212f;">{esc(t.get("term"))}</b>
  <span style="display:inline-block;margin-left:8px;color:#b7791f;font-size:12px;font-weight:800;">{esc(t.get("kind"))}</span><br>
  <em style="color:#475569;font-style:normal;">{esc(t.get("meaning_kr"))}</em>
</li>""".strip()
        for t in terms
    )
    return f"""
<section class="digest-terms">
  <h2{style(SECTION_TITLE_STYLE)}>오늘의 IT · 개발 · 기획 용어</h2>
  <ul style="margin:0;padding:0;list-style:none;">{rows}</ul>
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
<article class="daily-digest-post"{style(POST_SHELL_STYLE)}>
  <section class="digest-hero"{style(HERO_STYLE)}>
    <p class="digest-meta-intro"{style(META_INTRO_STYLE)}>{esc(build_meta_description(day))}</p>
    <p class="digest-kicker"{style(KICKER_STYLE)}>{esc(date_text)} · 자동 생성 데일리 다이제스트</p>
    <h2 class="digest-title"{style(TITLE_STYLE)}>오늘의 IT/개발 읽을거리</h2>
    <p class="digest-lead"{style(LEAD_STYLE)}>
      오늘은 {esc(lead)} 흐름을 중심으로 읽어볼 만한 소식을 정리했습니다.
      본문은 핵심 내용 요약과 학습용 문제로 구성했으며, 세부 내용은 각 원문 링크에서 확인하는 것을 권장합니다.
    </p>
  </section>

  {build_summary_section(day)}

  <h2{style(SECTION_TITLE_STYLE)}>오늘의 뉴스 3개</h2>
  {build_news_section(news)}

  {build_quiz_section(day.get("quiz"))}

  {build_terms_section(day.get("terms") or [])}

  <p class="digest-note"{style(NOTE_STYLE)}>
    이 글은 공개 뉴스 페이지를 기반으로 자동 수집·요약한 학습용 다이제스트입니다.
    수치, 정책, 제품 정보처럼 정확성이 중요한 내용은 반드시 원문을 함께 확인해 주세요.
  </p>
</article>
"""


def write_post(day_id, day=None, source_page=None):
    day = day or load_day(day_id)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    image_assets = [
        {
            "title": plain(item.get("title_kr")),
            "url": plain(item.get("image_url")),
            "path": plain(item.get("saved_image_path")),
            "original_url": plain(item.get("original_image_url")),
        }
        for item in day.get("news", [])
        if item.get("saved_image_path")
    ]

    html_path = OUT_DIR / f"{day_id}.html"
    meta_path = OUT_DIR / f"{day_id}.json"

    html_path.write_text(render_post(day_id, day), encoding="utf-8")
    meta_path.write_text(
        json.dumps(
            {
                "title": post_title(day),
                "title_candidates": build_title_candidates(day),
                "category": DEFAULT_CATEGORY,
                "tags": build_recommended_tags(day),
                "meta_description": build_meta_description(day),
                "key_summary": build_key_summary(day),
                "publish_checklist": build_publish_checklist(day),
                "source": f"data/days/{day_id}.json",
                "source_page": source_page,
                "html": f"docs/tistory/{day_id}.html",
                "image_assets": image_assets,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"exported: {html_path}")


def read_export(day_id):
    html_path = OUT_DIR / f"{day_id}.html"
    meta_path = OUT_DIR / f"{day_id}.json"

    if not html_path.exists() or not meta_path.exists():
        write_post(day_id)

    with meta_path.open("r", encoding="utf-8") as f:
        meta = json.load(f)
    body = html_path.read_text(encoding="utf-8")
    return meta, body, html_path, meta_path


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--today", action="store_true", help="export today's day")
    group.add_argument("--latest", action="store_true", help="export the newest day only when it is today")
    group.add_argument("--day", help="export one YYYY-MM-DD day")
    group.add_argument("--all", action="store_true", help="export every day")
    args = parser.parse_args()

    if args.today:
        write_post(today_day_id())
    elif args.latest:
        write_post(latest_or_today())
    elif args.day:
        write_post(args.day)
    else:
        for path in day_files():
            write_post(path.stem)


if __name__ == "__main__":
    main()
