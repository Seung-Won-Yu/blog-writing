"""Collect news candidates from RSS, Atom, and simple HTML source pages."""

import datetime as dt
import email.utils
import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

from news_pipeline import (
    canonicalize_url,
    deduplicate_candidates,
    make_candidate,
    score_candidate,
    select_candidates,
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


def _normalise_date(value):
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
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc).isoformat()


def parse_feed(text, base_url):
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
        link = ""
        for child in element:
            if _local_name(child.tag) != "link":
                continue
            link = child.attrib.get("href") or "".join(child.itertext()).strip()
            if link:
                break

        if title and link:
            items.append(
                {
                    "title": _strip_html(title),
                    "url": urljoin(base_url, link),
                    "summary": _strip_html(summary),
                    "published_at": _normalise_date(published),
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
        if not title or url in seen:
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


def _collect_source(source, fetch_text):
    text = fetch_text(source["url"])
    source_type = source.get("type", "rss").lower()
    if source_type in {"rss", "atom", "feed"}:
        return parse_feed(text, source["url"])
    if source_type == "html":
        return parse_html_links(text, source)
    raise ValueError("지원하지 않는 소스 형식: {}".format(source_type))


def build_inbox(config, fetch_text, now=None, day_id=None):
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
        for raw in raw_items[:limit]:
            candidate = make_candidate(raw, source)
            if candidate["title"] and candidate["url"]:
                candidates.append(candidate)

    candidates = deduplicate_candidates(candidates)
    for candidate in candidates:
        score_candidate(candidate, config.get("interest_keywords", []), now=now)
    candidates.sort(
        key=lambda item: (item.get("score", 0), item.get("published_at", "")),
        reverse=True,
    )

    selection = config.get("selection", {})
    selected = select_candidates(
        candidates,
        max_items=int(selection.get("max_items", 3)),
        max_per_source=int(selection.get("max_per_source", 1)),
        preferred_groups=selection.get("preferred_groups", []),
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
