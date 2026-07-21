"""Cache public Tistory post URLs from the blog sitemap."""

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

from .collect_news import fetch_url


BLOG_URL = "https://won0322.tistory.com"
SITEMAP_URL = f"{BLOG_URL}/sitemap.xml"
POST_PATH_RE = re.compile(r"/(\d+)")


def parse_public_posts(xml_text, *, blog_url=BLOG_URL):
    expected_host = urlsplit(blog_url).netloc.lower()
    root = ET.fromstring(xml_text)
    posts = []
    for node in root:
        values = {
            child.tag.rsplit("}", 1)[-1].lower(): (child.text or "").strip()
            for child in node
        }
        url = values.get("loc", "")
        parsed = urlsplit(url)
        match = POST_PATH_RE.fullmatch(parsed.path.rstrip("/"))
        if parsed.scheme != "https" or parsed.netloc.lower() != expected_host or not match:
            continue
        posts.append(
            {
                "id": int(match.group(1)),
                "url": f"{blog_url}/{match.group(1)}",
                "lastmod": values.get("lastmod", ""),
            }
        )
    return sorted(posts, key=lambda post: post["id"])


def build_catalog(xml_text, *, previous=None, now=None):
    posts = parse_public_posts(xml_text)
    previous_posts = previous.get("posts", []) if isinstance(previous, dict) else []
    minimum = max(1, int(len(previous_posts) * 0.9))
    if len(posts) < minimum:
        raise ValueError(
            f"tistory_sitemap_shrank:{len(posts)}<{minimum}"
        )
    stable = {
        "schema_version": 1,
        "blog_url": BLOG_URL,
        "sitemap_url": SITEMAP_URL,
        "posts": posts,
    }
    previous_stable = {
        key: previous.get(key) for key in stable
    } if isinstance(previous, dict) else {}
    if previous_stable == stable and previous.get("synced_at"):
        synced_at = previous["synced_at"]
    else:
        current = now or dt.datetime.now(ZoneInfo("Asia/Seoul"))
        synced_at = current.isoformat(timespec="seconds")
    return {**stable, "synced_at": synced_at}


def write_catalog(catalog, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == payload:
        return False
    path.write_text(payload, encoding="utf-8")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Tistory sitemap에서 실제 공개 글 URL 목록을 동기화합니다."
    )
    parser.add_argument("--sitemap-url", default=SITEMAP_URL)
    parser.add_argument("--output", default="config/tistory_public_posts.json")
    args = parser.parse_args(argv)

    output = Path(args.output)
    previous = None
    if output.exists():
        try:
            previous = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            previous = None
    catalog = build_catalog(fetch_url(args.sitemap_url), previous=previous)
    changed = write_catalog(catalog, output)
    print(
        "Tistory 공개 글 동기화: {}건 / {}".format(
            len(catalog["posts"]), "변경" if changed else "변경 없음"
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
