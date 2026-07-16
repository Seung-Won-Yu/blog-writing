"""Collect news candidates from RSS, Atom, and simple HTML source pages."""

import argparse
import datetime as dt
import email.utils
import json
import re
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

from .news_pipeline import (
    canonicalize_url,
    deduplicate_candidates,
    make_candidate,
    score_candidate,
    select_candidates,
    validate_day_id,
)


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a" and self._href is None:
            self._href = dict(attrs).get("href")
            self._parts = []

    def handle_data(self, data):
        if self._href is not None:
            self._parts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.links.append((self._href, " ".join(self._parts)))
            self._href = None
            self._parts = []


def _local_name(tag):
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(element, names):
    for child in element:
        if _local_name(child.tag) in names:
            return "".join(child.itertext()).strip()
    return ""


def _strip_html(value):
    parser = _TextParser()
    parser.feed(str(value or ""))
    parser.close()
    return " ".join(unescape(" ".join(parser.parts)).split())


def _normalise_date(value, default_timezone=dt.timezone.utc):
    text = str(value or "").strip()
    if not text:
        return ""

    try:
        parsed = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError):
        parsed = None

    if parsed is None:
        iso_text = text[:-1] + "+00:00" if text.endswith("Z") else text
        try:
            parsed = dt.datetime.fromisoformat(iso_text)
        except ValueError:
            return ""

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=default_timezone)
    return parsed.astimezone(dt.timezone.utc).isoformat()


def parse_feed(text, base_url, default_timezone=dt.timezone.utc):
    """Parse RSS or Atom XML into the pipeline's raw item shape."""
    root = ET.fromstring(text)
    is_atom = _local_name(root.tag) == "feed"
    entry_name = "entry" if is_atom else "item"
    items = []

    for element in root.iter():
        if _local_name(element.tag) != entry_name:
            continue

        title = _child_text(element, {"title"})
        summary = _child_text(element, {"summary", "description", "content"})
        published = _child_text(element, {"published", "updated", "pubdate", "date"})
        links = []
        for child in element:
            if _local_name(child.tag) != "link":
                continue
            value = child.attrib.get("href") or "".join(child.itertext()).strip()
            if value:
                links.append((child.attrib.get("rel", "").casefold(), value))

        link = ""
        if is_atom:
            link = next((value for rel, value in links if rel == "alternate"), "")
            if not link:
                link = next((value for rel, value in links if rel in {"", "canonical"}), "")
        elif links:
            link = links[0][1]

        if not link and not is_atom:
            for child in element:
                if _local_name(child.tag) != "guid":
                    continue
                if child.attrib.get("isPermaLink", "true").casefold() == "false":
                    continue
                link = "".join(child.itertext()).strip()
                if link:
                    break

        if title and link:
            items.append(
                {
                    "title": _strip_html(title),
                    "url": urljoin(base_url, link),
                    "summary": _strip_html(summary),
                    "published_at": _normalise_date(published, default_timezone),
                }
            )

    return items


def parse_html_links(text, source):
    """Extract article links from a source page using its configured pattern."""
    parser = _LinkParser()
    parser.feed(text)
    parser.close()

    pattern = re.compile(source["link_pattern"])
    base_url = source["url"]
    items = []
    seen = set()

    for raw_href, raw_title in parser.links:
        absolute_url = urljoin(base_url, raw_href)
        if not (pattern.search(raw_href) or pattern.search(absolute_url)):
            continue
        url = canonicalize_url(absolute_url)
        title = " ".join(unescape(raw_title).split())
        max_title_chars = int(source.get("max_title_chars", 180))
        if not title or len(title) > max_title_chars or url in seen:
            continue
        seen.add(url)
        items.append(
            {
                "title": title,
                "url": url,
                "summary": "",
                "published_at": "",
            }
        )

    return items


def _collect_variant(source, fetch_text):
    text = fetch_text(source["url"])
    source_type = source.get("type", "rss").lower()
    if source_type in {"rss", "atom", "feed"}:
        timezone_name = source.get("timezone")
        timezone = ZoneInfo(timezone_name) if timezone_name else dt.timezone.utc
        return parse_feed(text, source["url"], timezone)
    if source_type == "html":
        return parse_html_links(text, source)
    raise ValueError("지원하지 않는 소스 형식: {}".format(source_type))


def _collect_source(source, fetch_text):
    variants = [source]
    variants.extend(
        {**source, **fallback}
        for fallback in source.get("fallbacks", [])
        if isinstance(fallback, dict)
    )
    failures = []
    for variant in variants:
        try:
            items = _collect_variant(variant, fetch_text)
        except Exception as exc:
            failures.append(exc)
            continue
        if items:
            return items
    if failures:
        raise failures[-1]
    return []


def _title_keyword_matches(title, keyword):
    normalized = str(title or "").casefold()
    keyword = str(keyword or "").strip().casefold()
    if not keyword:
        return False
    if keyword.isascii():
        return re.search(
            r"(?<![a-z0-9]){}(?![a-z0-9])".format(re.escape(keyword)),
            normalized,
        ) is not None
    return keyword in normalized


def _source_item_matches(raw, source):
    title = raw.get("title", "")
    excluded = source.get("exclude_title_keywords", [])
    if any(_title_keyword_matches(title, keyword) for keyword in excluded):
        return False
    included = source.get("include_title_keywords", [])
    return not included or any(
        _title_keyword_matches(title, keyword) for keyword in included
    )


def _source_item_is_recent(raw, max_age_days, now):
    if max_age_days is None:
        return True
    published = str(raw.get("published_at") or "").strip()
    if not published:
        return True
    if published.endswith("Z"):
        published = published[:-1] + "+00:00"
    try:
        published_at = dt.datetime.fromisoformat(published)
    except ValueError:
        return True
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=dt.timezone.utc)
    age = now - published_at.astimezone(dt.timezone.utc)
    return age <= dt.timedelta(days=max(0, int(max_age_days)))


def load_recent_processed_urls(days_dir, day_id, lookback_days=14):
    """Return canonical URLs saved in recent processed daily articles."""
    target_day = dt.date.fromisoformat(validate_day_id(day_id))
    output = Path(days_dir)
    urls = set()

    for days_ago in range(1, max(0, int(lookback_days)) + 1):
        prior_day = target_day - dt.timedelta(days=days_ago)
        path = output / "{}.json".format(prior_day.isoformat())
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for item in payload.get("news", []):
            url = canonicalize_url(item.get("url", ""))
            if url:
                urls.add(url)

    return urls


def build_inbox(config, fetch_text, now=None, day_id=None, excluded_urls=None):
    """Collect, rank, and select candidates without publishing anything."""
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    now = now.astimezone(dt.timezone.utc)
    day_id = day_id or now.date().isoformat()

    candidates = []
    errors = []
    default_limit = int(config.get("max_items_per_source", 20))

    for source in config.get("sources", []):
        if not source.get("enabled", True):
            continue
        try:
            raw_items = _collect_source(source, fetch_text)
        except Exception as exc:  # One failed source must not stop the daily inbox.
            errors.append({"source_id": source.get("id", ""), "message": str(exc)})
            continue

        limit = int(source.get("max_items", default_limit))
        max_age_days = source.get("max_age_days", config.get("max_age_days"))
        filtered_items = [
            raw
            for raw in raw_items
            if _source_item_matches(raw, source)
            and _source_item_is_recent(raw, max_age_days, now)
        ]
        for raw in filtered_items[:limit]:
            candidate_input = dict(raw)
            if source.get("include_summary") is False:
                candidate_input["summary"] = ""
            candidate = make_candidate(candidate_input, source)
            if candidate["title"] and candidate["url"]:
                candidates.append(candidate)

    candidates = deduplicate_candidates(candidates)
    for candidate in candidates:
        score_candidate(
            candidate,
            config.get("interest_keywords", []),
            now=now,
            audience_lanes=config.get("audience_lanes", {}),
            topic_keywords=config.get("topic_keywords", {}),
        )
    candidates.sort(
        key=lambda item: (item.get("score", 0), item.get("published_at", "")),
        reverse=True,
    )

    canonical_excluded_urls = set()
    for url in excluded_urls or set():
        canonical_url = canonicalize_url(url)
        if canonical_url:
            canonical_excluded_urls.add(canonical_url)
    eligible_candidates = [
        candidate
        for candidate in candidates
        if candidate.get("url") not in canonical_excluded_urls
    ]
    selection = dict(config.get("selection", {}))
    selection["recently_selected_excluded"] = len(candidates) - len(eligible_candidates)
    selected = select_candidates(
        eligible_candidates,
        max_items=int(selection.get("max_items", 3)),
        max_per_source=int(selection.get("max_per_source", 1)),
        max_per_family=selection.get("max_per_family"),
        preferred_groups=selection.get("preferred_groups", []),
        audience_lanes=selection.get("audience_lanes", []),
        max_topic_items=selection.get("max_topic_items", {}),
        max_research_items=selection.get("max_research_items", 1),
        require_topic_coherence=bool(selection.get("require_topic_coherence", False)),
    )

    return {
        "schema_version": 1,
        "day": day_id,
        "generated_at": now.isoformat(),
        "review_required": True,
        "selection": selection,
        "candidates": candidates,
        "selected": selected,
        "errors": errors,
    }


def _candidate_card(item, featured=False):
    title = escape(str(item.get("title", "")))
    url = escape(str(item.get("url", "")), quote=True)
    summary = escape(str(item.get("summary", "")))
    source = escape(str(item.get("source_name", "")))
    group = escape(str(item.get("group", "other")))
    score = escape(str(item.get("score", 0)))
    reasons = " · ".join(escape(str(reason)) for reason in item.get("score_reasons", []))
    review_badge = (
        '<span class="badge badge-review">맥락 확인 필요</span>'
        if item.get("requires_manual_review")
        else ""
    )
    summary_html = (
        '\n        <p class="summary">{}</p>'.format(summary) if summary else ""
    )
    card_class = "card featured" if featured else "card"
    return """
      <article class="{card_class}">
        <div class="meta"><span class="badge">{source}</span><span>{group}</span><span>점수 {score}</span>{review_badge}</div>
        <h3><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></h3>{summary_html}
        <p class="reasons">{reasons}</p>
      </article>""".format(
        card_class=card_class,
        source=source,
        group=group,
        score=score,
        review_badge=review_badge,
        url=url,
        title=title,
        summary_html=summary_html,
        reasons=reasons,
    )


def render_inbox_html(inbox):
    """Render a small editorial review page. External text is always escaped."""
    selected = inbox.get("selected", [])
    selected_ids = {item.get("id") for item in selected}
    remaining = [
        item for item in inbox.get("candidates", []) if item.get("id") not in selected_ids
    ]
    selected_html = "".join(_candidate_card(item, featured=True) for item in selected)
    if not selected_html:
        selected_html = '<p class="empty">추천 후보가 없습니다. 수집 오류를 확인해 주세요.</p>'
    remaining_html = "".join(_candidate_card(item) for item in remaining)
    if not remaining_html:
        remaining_html = '<p class="empty">추가 후보가 없습니다.</p>'

    errors = inbox.get("errors", [])
    error_html = "".join(
        "<li><strong>{}</strong> — {}</li>".format(
            escape(str(error.get("source_id", ""))),
            escape(str(error.get("message", ""))),
        )
        for error in errors
    )
    if not error_html:
        error_html = "<li>모든 출처를 정상적으로 확인했습니다.</li>"

    day = escape(str(inbox.get("day", "")))
    generated_at = escape(str(inbox.get("generated_at", "")))
    return """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow,noarchive">
  <title>{day} 뉴스 후보함</title>
  <style>
    :root {{ color-scheme: light; --ink:#1f2933; --muted:#65717d; --line:#dfe4e8; --paper:#fff; --wash:#f5f6f4; --accent:#28684a; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; color:var(--ink); background:var(--wash); font:15px/1.65 -apple-system,BlinkMacSystemFont,"Noto Sans KR",sans-serif; }}
    main {{ width:min(860px,calc(100% - 32px)); margin:0 auto; padding:56px 0 80px; }}
    header {{ margin-bottom:36px; }}
    h1 {{ margin:0 0 8px; font-size:clamp(28px,5vw,42px); letter-spacing:-.045em; }}
    h2 {{ margin:44px 0 14px; font-size:20px; letter-spacing:-.025em; }}
    h3 {{ margin:10px 0 6px; font-size:19px; line-height:1.45; letter-spacing:-.02em; }}
    a {{ color:inherit; text-decoration-thickness:1px; text-underline-offset:4px; }}
    .intro,.generated,.summary,.reasons,.empty {{ color:var(--muted); }}
    .generated {{ font-size:12px; }}
    .grid {{ display:grid; gap:12px; }}
    .card {{ padding:20px 22px; background:var(--paper); border:1px solid var(--line); border-radius:12px; }}
    .featured {{ border-left:4px solid var(--accent); }}
    .meta {{ display:flex; flex-wrap:wrap; gap:7px 12px; align-items:center; color:var(--muted); font-size:12px; }}
    .badge {{ color:var(--accent); font-weight:700; }}
    .badge-review {{ padding:1px 7px; border:1px solid #d7a64a; border-radius:999px; color:#835a0a; }}
    .summary,.reasons {{ margin:6px 0 0; }}
    .reasons {{ font-size:12px; }}
    .errors {{ padding:16px 20px 16px 38px; background:#fff; border:1px solid var(--line); border-radius:12px; color:var(--muted); }}
    footer {{ margin-top:40px; padding-top:18px; border-top:1px solid var(--line); color:var(--muted); font-size:13px; }}
  </style>
</head>
<body>
<main>
  <header>
    <p class="generated">{day} · 생성 {generated_at}</p>
    <h1>뉴스 후보함</h1>
    <p class="intro">자동 수집과 점수 계산까지만 했습니다. 원문을 읽고 내 관점 한두 문장을 더한 뒤 글감으로 사용하세요.</p>
  </header>
  <section>
    <h2>오늘의 추천 {selected_count}건</h2>
    <div class="grid">{selected_html}</div>
  </section>
  <section>
    <h2>추가 후보 {remaining_count}건</h2>
    <div class="grid">{remaining_html}</div>
  </section>
  <section>
    <h2>수집 상태</h2>
    <ul class="errors">{error_html}</ul>
  </section>
  <footer>후보함은 게시물이 아닙니다. 사실관계·출처·인용 범위를 확인한 뒤 직접 발행하세요.</footer>
</main>
</body>
</html>
""".format(
        day=day,
        generated_at=generated_at,
        selected_count=len(selected),
        selected_html=selected_html,
        remaining_count=len(remaining),
        remaining_html=remaining_html,
        error_html=error_html,
    )


def write_inbox(inbox, output_dir):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    validate_day_id(inbox["day"])
    latest_json = output / "latest.json"
    index_html = output / "index.html"
    payload = dict(inbox)

    if latest_json.exists():
        try:
            previous = json.loads(latest_json.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            previous = None
        if previous:
            previous_content = {key: value for key, value in previous.items() if key != "generated_at"}
            current_content = {key: value for key, value in payload.items() if key != "generated_at"}
            if previous_content == current_content:
                payload["generated_at"] = previous.get("generated_at", payload.get("generated_at", ""))

    json_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    html_text = render_inbox_html(payload)
    latest_json.write_text(json_text, encoding="utf-8")
    index_html.write_text(html_text, encoding="utf-8")

    removed = []
    for path in output.iterdir() if output.is_dir() else ():
        if not path.is_file() or path.suffix not in {".json", ".html"}:
            continue
        try:
            validate_day_id(path.stem)
        except ValueError:
            continue
        path.unlink()
        removed.append(path)

    return {
        "json": str(latest_json),
        "html": str(index_html),
        "removed": [str(path) for path in removed],
    }


def fetch_url(url, timeout=20):
    request = Request(
        url,
        headers={
            "User-Agent": "blog-writing-news-review/1.0",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/html;q=0.9, */*;q=0.5",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def main(argv=None):
    parser = argparse.ArgumentParser(description="여러 출처의 뉴스 후보함을 생성합니다.")
    day_group = parser.add_mutually_exclusive_group()
    day_group.add_argument("--today", action="store_true", help="한국 시간 기준 오늘 날짜 사용")
    day_group.add_argument("--day", help="후보함 날짜 (YYYY-MM-DD)")
    parser.add_argument("--config", default="config/news_sources.json")
    parser.add_argument("--output-dir", default="docs/inbox")
    parser.add_argument("--published-days-dir", default="data/days")
    args = parser.parse_args(argv)

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    now = dt.datetime.now(ZoneInfo("Asia/Seoul"))
    try:
        day_id = validate_day_id(args.day or now.date().isoformat())
    except ValueError as exc:
        parser.error(str(exc))
    lookback_days = int(config.get("selection", {}).get("exclude_recent_days", 14))
    excluded_urls = load_recent_processed_urls(
        args.published_days_dir, day_id, lookback_days
    )
    inbox = build_inbox(
        config,
        fetch_text=fetch_url,
        now=now,
        day_id=day_id,
        excluded_urls=excluded_urls,
    )
    paths = write_inbox(inbox, args.output_dir)
    print(
        "뉴스 후보함 생성: 추천 {}건 / 전체 {}건 / 오류 {}건 / 과거 원뉴스 {}개 정리\n{}".format(
            len(inbox["selected"]),
            len(inbox["candidates"]),
            len(inbox["errors"]),
            len(paths["removed"]),
            paths["html"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
