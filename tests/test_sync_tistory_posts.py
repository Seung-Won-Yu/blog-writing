import datetime as dt
import tempfile
import unittest
from pathlib import Path

from blog_pipeline.collection.sync_tistory_posts import (
    build_catalog,
    parse_public_posts,
    write_catalog,
)


SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://won0322.tistory.com/category</loc></url>
  <url><loc>https://won0322.tistory.com/132</loc><lastmod>2026-07-20T09:00:00+09:00</lastmod></url>
  <url><loc>https://won0322.tistory.com/126</loc><lastmod>2026-07-18T09:00:00+09:00</lastmod></url>
  <url><loc>https://example.com/999</loc></url>
</urlset>
"""


class TistoryPostSyncTests(unittest.TestCase):
    def test_extracts_only_numeric_public_post_urls(self):
        posts = parse_public_posts(SITEMAP)

        self.assertEqual([post["id"] for post in posts], [126, 132])
        self.assertEqual(posts[1]["url"], "https://won0322.tistory.com/132")

    def test_preserves_sync_time_when_sitemap_is_unchanged(self):
        now = dt.datetime(2026, 7, 21, 9, 0, tzinfo=dt.timezone.utc)
        first = build_catalog(SITEMAP, now=now)
        second = build_catalog(SITEMAP, previous=first, now=now + dt.timedelta(days=1))

        self.assertEqual(second["synced_at"], first["synced_at"])

    def test_rejects_suspiciously_truncated_sitemap(self):
        previous = {"posts": [{"id": index} for index in range(20)]}

        with self.assertRaisesRegex(ValueError, "tistory_sitemap_shrank"):
            build_catalog(SITEMAP, previous=previous)

    def test_writes_only_changed_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            catalog = build_catalog(SITEMAP)

            self.assertTrue(write_catalog(catalog, path))
            self.assertFalse(write_catalog(catalog, path))
