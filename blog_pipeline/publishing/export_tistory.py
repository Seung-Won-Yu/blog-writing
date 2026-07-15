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

HERE = Path(__file__).resolve().parents[2]
DAYS_DIR = HERE / "data" / "days"
OUT_DIR = HERE / "docs" / "tistory"

DEFAULT_BLOG_URL = "https://won0322.tistory.com"
DEFAULT_CATEGORY = "데일리IT뉴스"
DEFAULT_TAGS = ["AI", "IT뉴스", "개발뉴스", "정처기", "개발용어", "데일리다이제스트"]
MIN_PUBLISH_REVISION = 7
TISTORY_ADFIT_MARKER = (
    '<figure class="ad-wp" contenteditable="false" data-ke-type="revenue" '
    'data-ad-vendor="adfit" data-ad-id-pc="713977" '
    'data-ad-id-mobile="713980"></figure>'
)

def esc(value):
    return html.escape(html.unescape(str(value or "")), quote=True)


def plain(value):
    return " ".join(str(value or "").split())


def source_date_label(value):
    text = plain(value)
    if not text:
        return ""
    try:
        published = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if published.tzinfo is not None:
        published = published.astimezone(
            datetime.timezone(datetime.timedelta(hours=9))
        )
    return f"{published.year}. {published.month}. {published.day}"


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
            rows.append(f'<h4 class="digest-subheading">{esc(text)}</h4>')
        else:
            rows.append(f'<p>{esc(text)}</p>')
    if not rows:
        return ""
    return '<div class="digest-full-content">' + "".join(rows) + "</div>"


def post_title(day):
    editorial = day.get("editorial") or {}
    headline = plain(editorial.get("headline"))
    if headline:
        return trim_text(headline, 70)
    titles = news_titles(day, 1)
    if titles:
        return trim_text(titles[0], 70)
    return "오늘 확인할 AI·개발 소식"


def news_titles(day, limit=None):
    titles = [plain(item.get("title_kr")) for item in day.get("news", [])]
    titles = [title for title in titles if title]
    return titles[:limit] if limit else titles


def estimate_read_minutes(day):
    pieces = []
    editorial = day.get("editorial") or {}
    pieces.extend(editorial.values())
    for item in day.get("news", []):
        pieces.extend([item.get("title_kr"), item.get("blurb_kr")])
        pieces.extend(block.get("text") for block in item.get("content", []) if isinstance(block, dict))
    quiz = day.get("quiz") or {}
    pieces.append(quiz.get("question"))
    pieces.extend(quiz.get("options") or [])
    for term in day.get("terms", []):
        pieces.extend([term.get("term"), term.get("meaning_kr")])
    length = sum(len(plain(piece)) for piece in pieces)
    return max(2, (length + 449) // 450)


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

    korean_terms = re.findall(r"[가-힣][가-힣0-9]*", value)
    if korean_terms:
        korean = " ".join(korean_terms[:5])
        return trim_text(korean, limit)

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
    headline = post_title(day)
    visual = day.get("visual") or {}
    subject = plain(visual.get("subject"))
    hook = plain(visual.get("hook"))
    candidates = [headline]
    if titles:
        count_suffix = f" 외 {len(titles) - 1}건" if len(titles) > 1 else ""
        candidates.append(trim_text(f"{titles[0]}{count_suffix}", 68))
    if subject and hook:
        candidates.append(trim_text(f"{subject}: {hook}", 68))
    elif hook:
        candidates.append(trim_text(hook, 68))
    if label:
        candidates.append(trim_text(f"{headline} ({label})", 70))

    unique = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)
    return unique[:4]


def build_meta_description(day):
    editorial = day.get("editorial") or {}
    opening = plain(editorial.get("opening"))
    first_blurb = ""
    if day.get("news"):
        first_blurb = plain(day["news"][0].get("blurb_kr"))
    parts = [trim_text(opening or first_blurb or post_title(day), 112)]
    quiz = day.get("quiz") or {}
    if quiz:
        quiz_category = plain(quiz.get("category")) or "정보처리기사"
        parts.append(f"{quiz_category} 문제로 개념도 확인합니다.")
    elif first_blurb and first_blurb not in parts[0]:
        parts.append(trim_text(first_blurb, 62))
    return trim_text(" ".join(parts), 160)


def build_key_summary(day):
    titles = news_titles(day, 3)
    quiz = day.get("quiz") or {}
    terms = [plain(item.get("term")) for item in day.get("terms", []) if item.get("term")]

    rows = [f"{index}. {trim_text(title, 72)}" for index, title in enumerate(titles, 1)]
    if quiz.get("question"):
        rows.append(f"정처기 포인트: {plain(quiz.get('category')) or '기초상식'} 문제로 개념을 점검합니다.")
    elif terms:
        rows.append("함께 익힐 용어: " + ", ".join(terms[:4]))
    elif not rows:
        rows.append("오늘 수집된 뉴스가 없습니다.")
    elif len(rows) < 4:
        rows.append("각 소식의 핵심을 확인한 뒤 궁금한 내용은 원문에서 이어서 살펴보세요.")
    return rows[:4]


def build_publish_checklist(day):
    titles = build_title_candidates(day)
    checklist = [
        "제목 후보 중 검색 키워드가 가장 자연스러운 제목을 선택하기",
        "원문 링크와 핵심 사실을 직접 대조해 확인하기",
        "직접 확인한 내용과 내 판단/경험을 각각 2문장 이상 추가하기",
        "태그 입력 후 카테고리를 데일리IT뉴스로 지정하기",
        "관련된 정처기/개발일지 글이 있으면 본문 하단에 내부 링크 1개 추가하기",
        f"추천 제목: {titles[0]}" if titles else "추천 제목 확인하기",
    ]
    if day.get("images") or any(
        item.get("image_url") or item.get("image") for item in day.get("news", [])
    ):
        checklist.insert(1, "본문 이미지가 정상 표시되는지 확인하기")
    return checklist


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


def build_throughline_section(editorial):
    throughline = plain((editorial or {}).get("throughline"))
    if not throughline:
        return ""
    return f"""
<section class="digest-throughline">
  <p class="digest-section-label">오늘의 관점</p>
  <h2>세 소식을 함께 보면</h2>
  <p>{esc(throughline)}</p>
</section>""".strip()


def build_reading_guide(news):
    if not news:
        return ""
    rows = []
    for index, item in enumerate(news, 1):
        rows.append(
            '<div class="digest-reading-item" role="listitem">'
            f'<a href="#digest-news-{index}">'
            f'<span class="digest-reading-index">{index:02d}</span>'
            f'{esc(item.get("title_kr"))}</a></div>'
        )
    return f"""
<nav class="digest-reading-guide" aria-label="글 순서">
  <p class="digest-reading-title">글 순서</p>
  <div class="digest-reading-list" role="list">{''.join(rows)}</div>
</nav>""".strip()


def build_editorial_image(asset, kind):
    if not isinstance(asset, dict) or not plain(asset.get("url")):
        return ""
    width = int(asset.get("width") or 1200)
    is_story = str(kind).startswith("story")
    class_name = "story" if is_story else kind
    default_height = 630 if kind == "cover" or is_story else 675
    height = int(asset.get("height") or default_height)
    loading = "eager" if kind == "cover" else "lazy"
    return (
        f'<figure class="digest-{class_name}-figure">'
        f'<img class="digest-{class_name}-image" src="{esc(asset.get("url"))}" '
        f'alt="{esc(asset.get("alt"))}" width="{width}" height="{height}" '
        f'loading="{loading}">'
        "</figure>"
    )


def build_news_section(news, flow_image=None, story_images=None):
    if not news:
        return '<p class="digest-empty">오늘 수집된 뉴스가 없습니다.</p>'

    parts = []
    story_images = story_images or []
    has_story_images = any(
        isinstance(asset, dict) and asset.get("url") for asset in story_images
    )
    for idx, item in enumerate(news, 1):
        title = plain(item.get("title_kr"))
        source = plain(item.get("source"))
        published = source_date_label(item.get("published_at"))
        url = plain(item.get("url"))
        blurb = plain(item.get("blurb_kr"))
        image = plain(item.get("image_url") or item.get("image"))
        full_content = render_content_blocks(item.get("content"))

        story_asset = story_images[idx - 1] if idx <= len(story_images) else None
        if isinstance(story_asset, dict) and story_asset.get("url"):
            image_html = build_editorial_image(story_asset, f"story_{idx}")
        else:
            image_html = (
                f'<img class="digest-news-image" src="{esc(image)}" alt="" loading="lazy">'
                if image
                else ""
            )
        summary_html = (
            f'<p class="digest-blurb">{esc(blurb)}</p>'
            if blurb
            else ""
        )

        source_link = (
            f'<p class="digest-source-link"><a href="{esc(url)}" target="_blank" rel="noopener">원문 보기</a></p>'
            if url
            else ""
        )
        source_meta = " · ".join(
            value for value in (source, published) if value
        )
        parts.append(
            f"""
<section id="digest-news-{idx}" class="digest-news-card">
  {image_html}
  <div class="digest-news-copy">
    <p class="digest-source">NEWS {idx:02d}{' · ' + esc(source_meta) if source_meta else ''}</p>
    <h3>{esc(title)}</h3>
    {summary_html}
    {full_content}
    {source_link}
  </div>
</section>""".strip()
        )
        if idx == 1 and flow_image and not has_story_images:
            parts.append(build_editorial_image(flow_image, "flow"))
    return "\n".join(parts)


def build_quiz_section(quiz):
    if not quiz:
        return ""
    options = quiz.get("options") or []
    try:
        answer = int(quiz.get("answer", -1))
    except (TypeError, ValueError):
        answer = -1
    option_html = "".join(
        (
            '<li class="digest-option">'
            f'<span class="digest-option-number">{index}.</span>'
            f'<span>{esc(opt)}</span></li>'
        )
        for index, opt in enumerate(options, 1)
    )
    answer_text = options[answer] if 0 <= answer < len(options) else ""
    answer_html = (
        f"<b>정답</b> {answer + 1}번 · {esc(answer_text)}"
        if answer_text
        else "<b>정답 확인 필요</b> 저장된 정답 번호가 올바르지 않습니다."
    )
    return f"""
<section class="digest-quiz">
  <p class="digest-source">기초상식 · {esc(quiz.get("category", "정보처리기사"))}</p>
  <h2>오늘의 정처기 문제</h2>
  <p class="digest-question">{esc(quiz.get("question"))}</p>
  <ol class="digest-options" role="list">{option_html}</ol>
  <details class="digest-answer">
    <summary>정답과 해설 보기</summary>
    <p class="digest-answer-line">{answer_html}</p>
    <p class="digest-explain"><b>해설</b> {esc(quiz.get("explain_kr"))}</p>
  </details>
</section>""".strip()


def build_terms_section(terms):
    if not terms:
        return ""
    rows = "".join(
        f"""
<li>
  <b>{esc(t.get("term"))}</b>
  <span>{esc(t.get("kind"))}</span>
  <em>{esc(t.get("meaning_kr"))}</em>
</li>""".strip()
        for t in terms
    )
    return f"""
<section class="digest-terms">
  <h2>오늘의 IT · 개발 · 기획 용어</h2>
  <ul>{rows}</ul>
</section>""".strip()


def build_closing_section(editorial):
    editorial = editorial or {}
    closing = plain(editorial.get("closing"))
    action = plain(editorial.get("action"))
    if not closing and not action:
        return ""
    closing_html = (
        '<p class="digest-closing-copy">'
        f"{esc(closing)}</p>"
        if closing
        else ""
    )
    action_html = (
        '<div class="digest-action">'
        f"<b>직접 확인해보려면</b><span>{esc(action)}</span></div>"
        if action
        else ""
    )
    return f"""
<section class="digest-closing">
  {closing_html}
  {action_html}
</section>""".strip()


def render_post(day_id, day):
    label = plain(day.get("date_label"))
    weekday = plain(day.get("weekday"))
    date_text = f"{label} ({weekday})" if weekday else label
    news = day.get("news") or []
    editorial = day.get("editorial") or {}
    images = day.get("images") if isinstance(day.get("images"), dict) else {}
    title_flow = " / ".join(plain(item.get("title_kr")) for item in news[:3])
    lead = plain(editorial.get("opening")) or f"오늘은 {title_flow} 흐름을 중심으로 읽어봅니다."
    return f"""<article class="daily-digest-post" data-digest-version="2">
  <section class="digest-hero" aria-label="글 소개">
    <p class="digest-kicker">{esc(date_text)} · 약 {estimate_read_minutes(day)}분</p>
    <p class="digest-lead">{esc(lead)}</p>
  </section>

  {build_editorial_image(images.get("cover"), "cover")}

  {build_throughline_section(editorial)}

  {build_reading_guide(news)}

  <h2 class="digest-news-heading">오늘 고른 뉴스</h2>
  {build_news_section(
      news,
      images.get("flow"),
      [images.get(f"story_{index}") for index in range(1, 4)],
  )}

  {build_quiz_section(day.get("quiz"))}

  {build_terms_section(day.get("terms") or [])}

  {build_closing_section(editorial)}
</article>
"""


def split_post_around_first_story(post_html):
    """Return valid fragments for Tistory's editor-only mid-article ad flow."""
    marker = '<section id="digest-news-2"'
    split_at = post_html.find(marker)
    if split_at < 0:
        return post_html, ""

    before_ad = post_html[:split_at].rstrip() + "\n</article>\n"
    after_body = post_html[split_at:].strip()
    closing = "</article>"
    if not after_body.endswith(closing):
        raise ValueError("Tistory post fragment is missing the article closing tag")
    after_body = after_body[: -len(closing)].rstrip()
    after_ad = f'<div class="daily-digest-continuation daily-digest-post">\n{after_body}\n</div>\n'
    return before_ad, after_ad


def build_adfit_ready_html(post_html):
    """Return one-paste Tistory HTML with AdFit after NEWS 01."""
    marker = '<section id="digest-news-2"'
    split_at = post_html.find(marker)
    if split_at < 0:
        return post_html
    return (
        post_html[:split_at].rstrip()
        + "\n"
        + TISTORY_ADFIT_MARKER
        + '\n<p data-ke-size="size16">&nbsp;</p>\n'
        + post_html[split_at:].lstrip()
    )


def write_post(day_id, day=None, source_page=None):
    day = day or load_day(day_id)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    images = day.get("images") if isinstance(day.get("images"), dict) else {}
    image_titles = {
        "cover": "대표 이미지",
        "story_1": "본문 1번 이미지",
        "story_2": "본문 2번 이미지",
        "story_3": "본문 3번 이미지",
        "flow": "오늘의 흐름 이미지",
    }
    image_assets = [
        {
            "kind": kind,
            "title": image_titles[kind],
            "url": plain(asset.get("url")),
            "path": plain(asset.get("path")),
            "original_url": "",
            "alt": plain(asset.get("alt")),
            "width": int(asset.get("width") or 0),
            "height": int(asset.get("height") or 0),
        }
        for kind in ("cover", "story_1", "story_2", "story_3", "flow")
        for asset in [images.get(kind)]
        if isinstance(asset, dict) and asset.get("url")
    ]
    image_assets.extend(
        [
            {
                "kind": "source",
                "title": plain(item.get("title_kr")),
                "url": plain(item.get("image_url")),
                "path": plain(item.get("saved_image_path")),
                "original_url": plain(item.get("original_image_url")),
            }
            for item in day.get("news", [])
            if item.get("saved_image_path")
        ]
    )

    html_path = OUT_DIR / f"{day_id}.html"
    meta_path = OUT_DIR / f"{day_id}.json"
    generation = day.get("generation") if isinstance(day.get("generation"), dict) else {}
    generation_provider = plain(generation.get("provider"))
    try:
        generation_revision = int(generation.get("revision") or 0)
    except (TypeError, ValueError):
        generation_revision = 0
    publish_ready = (
        generation_provider in {"codex-agent", "github-models", "gemini"}
        and generation_revision >= MIN_PUBLISH_REVISION
    )

    post_html = render_post(day_id, day)
    before_ad_html, after_ad_html = split_post_around_first_story(post_html)
    before_ad_path = OUT_DIR / f"{day_id}-before-ad.html"
    after_ad_path = OUT_DIR / f"{day_id}-after-ad.html"
    adfit_path = OUT_DIR / f"{day_id}-adfit.html"
    html_path.write_text(post_html, encoding="utf-8")
    before_ad_path.write_text(before_ad_html, encoding="utf-8")
    after_ad_path.write_text(after_ad_html, encoding="utf-8")
    adfit_path.write_text(build_adfit_ready_html(post_html), encoding="utf-8")
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
                "generation_provider": generation_provider,
                "publish_ready": publish_ready,
                "source": f"data/days/{day_id}.json",
                "source_page": source_page,
                "html": f"docs/tistory/{day_id}.html",
                "before_ad_html": f"docs/tistory/{day_id}-before-ad.html",
                "after_ad_html": f"docs/tistory/{day_id}-after-ad.html",
                "adfit_html": f"docs/tistory/{day_id}-adfit.html",
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


def should_preserve_published_export(day_id, output_dir=None):
    """Protect manually reviewed output when a bulk rebuild is requested."""
    output = Path(output_dir) if output_dir is not None else OUT_DIR
    html_path = output / f"{day_id}.html"
    meta_path = output / f"{day_id}.json"
    if not html_path.exists() or not meta_path.exists():
        return False
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(plain(meta.get("source_page")))


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
            if should_preserve_published_export(path.stem):
                print(f"preserved published export: {path.stem}")
                continue
            write_post(path.stem)


if __name__ == "__main__":
    main()
