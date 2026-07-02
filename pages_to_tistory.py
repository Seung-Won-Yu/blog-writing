# -*- coding: utf-8 -*-
"""
Convert an already-published GitHub Pages digest into a Tistory-ready post.

This is the fast path for daily posting: use the public Pages HTML as the
source of truth for news text and media, then reuse the local/raw day JSON for
quiz and terms.

usage:
  python pages_to_tistory.py --day 2026-07-01
  python pages_to_tistory.py --today
"""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from export_tistory import DAYS_DIR, HERE, OUT_DIR, latest_or_today, today_day_id, write_post

DEFAULT_BASE_URL = "https://ihan0316.github.io/ai-weekly-newsroom/"
DEFAULT_RAW_URL = (
    "https://raw.githubusercontent.com/Ihan0316/ai-weekly-newsroom/main/"
    "data/days/{day}.json"
)
DEFAULT_ASSET_BASE_URL = "https://seung-won-yu.github.io/blog-writing/tistory/assets/"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
UA += "(KHTML, like Gecko) Chrome/124 Safari/537.36"

CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
}


class ScriptByIdParser(HTMLParser):
    def __init__(self, target_id):
        super().__init__()
        self.target_id = target_id
        self.in_target = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag != "script":
            return
        values = dict(attrs)
        if values.get("id") == self.target_id:
            self.in_target = True

    def handle_endtag(self, tag):
        if tag == "script" and self.in_target:
            self.in_target = False

    def handle_data(self, data):
        if self.in_target:
            self.parts.append(data)

    def text(self):
        return "".join(self.parts).strip()


def fetch_text(url):
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/json,*/*"})
    with urlopen(req, timeout=45) as response:
        raw = response.read()
    return raw.decode("utf-8", "ignore")


def fetch_binary(url):
    req = Request(url, headers={"User-Agent": UA, "Accept": "image/*,*/*"})
    with urlopen(req, timeout=45) as response:
        return response.read(), response.headers.get("Content-Type", "").split(";")[0].strip().lower()


def page_url(base_url, day_id):
    return urljoin(base_url.rstrip("/") + "/", f"days/{day_id}.html")


def extract_news_data(page_html):
    parser = ScriptByIdParser("news-data")
    parser.feed(page_html)
    raw = parser.text()
    if not raw:
        raise SystemExit("published page does not contain #news-data JSON")
    return json.loads(raw)


def load_structured_day(day_id, raw_url_template=DEFAULT_RAW_URL):
    local_path = DAYS_DIR / f"{day_id}.json"
    if local_path.exists():
        with local_path.open("r", encoding="utf-8") as f:
            return json.load(f), f"local:{local_path}"

    raw_url = raw_url_template.format(day=day_id)
    try:
        return json.loads(fetch_text(raw_url)), raw_url
    except Exception as error:
        raise SystemExit(f"day JSON not found locally or on GitHub raw: {day_id} ({error})")


def normalized_url(item):
    return str(item.get("url") or "").strip()


def image_extension(url, content_type):
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    return CONTENT_TYPE_EXTENSIONS.get(content_type, ".jpg")


def cache_image(url, day_id, index, asset_base_url):
    data, content_type = fetch_binary(url)
    ext = image_extension(url, content_type)
    assets_dir = OUT_DIR / "assets" / day_id
    assets_dir.mkdir(parents=True, exist_ok=True)
    filename = f"news-{index:02d}{ext}"
    path = assets_dir / filename
    path.write_bytes(data)
    public_url = urljoin(asset_base_url.rstrip("/") + "/", f"{day_id}/{filename}")
    return path, public_url


def merge_page_news(day_id, day, page_news, source_page, asset_base_url=DEFAULT_ASSET_BASE_URL):
    local_news = day.get("news") or []
    by_url = {normalized_url(item): item for item in local_news if normalized_url(item)}
    merged_news = []

    for index, page_item in enumerate(page_news):
        url = normalized_url(page_item)
        base = dict(by_url.get(url) or (local_news[index] if index < len(local_news) else {}))

        image = str(page_item.get("image") or "").strip()
        audio = str(page_item.get("audio") or "").strip()
        base.update(
            {
                "title_kr": page_item.get("title") or base.get("title_kr") or "",
                "source": page_item.get("source") or base.get("source") or "",
                "url": url or base.get("url") or "",
                "blurb_kr": page_item.get("blurb") or base.get("blurb_kr") or "",
                "content": page_item.get("content") or base.get("content") or [],
            }
        )
        if image:
            original_image_url = urljoin(source_page, image)
            base["original_image_url"] = original_image_url
            try:
                saved_path, saved_url = cache_image(
                    original_image_url,
                    day_id,
                    index + 1,
                    asset_base_url,
                )
                base["image_url"] = saved_url
                base["saved_image_path"] = str(saved_path.relative_to(HERE))
            except Exception as error:
                print(f"image cache failed: {original_image_url} ({error})")
                base["image_url"] = original_image_url
        if audio:
            base["audio_url"] = urljoin(source_page, audio)
        merged_news.append(base)

    day["news"] = merged_news
    return day


def write_page_post(
    day_id,
    base_url=DEFAULT_BASE_URL,
    raw_url_template=DEFAULT_RAW_URL,
    asset_base_url=DEFAULT_ASSET_BASE_URL,
):
    source_page = page_url(base_url, day_id)
    page_html = fetch_text(source_page)
    page_news = extract_news_data(page_html)
    day, structured_source = load_structured_day(day_id, raw_url_template)
    day = merge_page_news(day_id, day, page_news, source_page, asset_base_url)
    write_post(day_id, day=day, source_page=source_page)
    image_count = sum(1 for item in day.get("news", []) if item.get("image_url"))
    saved_count = sum(1 for item in day.get("news", []) if item.get("saved_image_path"))
    print(f"pages source: {source_page}")
    print(f"structured source: {structured_source}")
    print(f"news: {len(day.get('news') or [])} | images: {image_count} | saved images: {saved_count}")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--today", action="store_true", help="import today's published Pages digest")
    group.add_argument("--latest", action="store_true", help="import newest local day only when it is today")
    group.add_argument("--day", help="import one YYYY-MM-DD day")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--raw-url-template", default=DEFAULT_RAW_URL)
    parser.add_argument("--asset-base-url", default=DEFAULT_ASSET_BASE_URL)
    args = parser.parse_args()

    if args.today:
        day_id = today_day_id()
    elif args.latest:
        day_id = latest_or_today()
    else:
        day_id = args.day

    write_page_post(day_id, args.base_url, args.raw_url_template, args.asset_base_url)


if __name__ == "__main__":
    main()
