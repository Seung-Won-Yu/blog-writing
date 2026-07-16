import json
import copy
import tempfile
import unittest
from pathlib import Path

from blog_pipeline.collection.collect_news import render_inbox_html, write_inbox


class ReviewInboxTests(unittest.TestCase):
    def setUp(self):
        self.inbox = {
            "day": "2026-07-12",
            "generated_at": "2026-07-12T09:00:00+00:00",
            "selected": [
                {
                    "id": "safe-id",
                    "title": "AI <Agent> 업데이트",
                    "url": "https://example.com/article?a=1&b=2",
                    "summary": "개발자용 기능 & 실제 사례",
                    "source_name": "Official",
                    "group": "official",
                    "score": 10,
                    "score_reasons": ["공식 출처", "48시간 이내"],
                    "requires_manual_review": False,
                }
            ],
            "candidates": [],
            "errors": [{"source_id": "broken", "message": "timeout <60s>"}],
        }

    def test_renders_review_page_and_escapes_external_content(self):
        html = render_inbox_html(self.inbox)

        self.assertIn("오늘의 추천 1건", html)
        self.assertIn("AI &lt;Agent&gt; 업데이트", html)
        self.assertIn("a=1&amp;b=2", html)
        self.assertNotIn("AI <Agent>", html)
        self.assertIn("broken", html)
        self.assertIn("timeout &lt;60s&gt;", html)

    def test_writes_only_latest_files_and_removes_legacy_dated_files(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "2026-07-11.json").write_text("{}", encoding="utf-8")
            Path(directory, "2026-07-11.html").write_text("legacy", encoding="utf-8")
            paths = write_inbox(self.inbox, directory)

            latest_json = Path(directory, "latest.json")
            index_html = Path(directory, "index.html")
            self.assertFalse(Path(directory, "2026-07-11.json").exists())
            self.assertFalse(Path(directory, "2026-07-11.html").exists())
            self.assertFalse(Path(directory, "2026-07-12.json").exists())
            self.assertFalse(Path(directory, "2026-07-12.html").exists())
            self.assertTrue(latest_json.exists())
            self.assertTrue(index_html.exists())
            self.assertEqual(json.loads(latest_json.read_text())["day"], "2026-07-12")
            self.assertEqual(paths["json"], str(latest_json))
            self.assertEqual(paths["html"], str(index_html))
            self.assertEqual(
                {Path(path).name for path in paths["removed"]},
                {"2026-07-11.json", "2026-07-11.html"},
            )

    def test_same_candidates_do_not_change_files_only_for_new_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            write_inbox(self.inbox, directory)
            latest_json = Path(directory, "latest.json")
            first_text = latest_json.read_text(encoding="utf-8")

            rerun = copy.deepcopy(self.inbox)
            rerun["generated_at"] = "2026-07-12T10:00:00+00:00"
            write_inbox(rerun, directory)

            self.assertEqual(latest_json.read_text(encoding="utf-8"), first_text)


class SourceConfigTests(unittest.TestCase):
    def test_config_covers_official_community_editorial_and_research(self):
        config_path = Path(__file__).parents[1] / "config" / "news_sources.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        enabled = [source for source in config["sources"] if source.get("enabled", True)]

        self.assertTrue({"official", "community", "korean_editorial", "research"}.issubset(
            {source["group"] for source in enabled}
        ))
        self.assertEqual(len({source["id"] for source in enabled}), len(enabled))
        self.assertEqual(config["selection"]["max_items"], 3)
        self.assertIn("aitimes", {source["id"] for source in enabled})
        self.assertEqual(
            config["selection"]["audience_lanes"],
            ["broad", "practical", "deep"],
        )
        self.assertEqual(config["selection"]["max_research_items"], 0)
        self.assertEqual(config["selection"]["exclude_recent_days"], 14)
        self.assertEqual(config["max_age_days"], 14)
        self.assertEqual(config["selection"]["max_per_family"], 1)
        self.assertNotIn("inbox_retention_days", config["selection"])
        self.assertTrue(config["selection"]["require_topic_coherence"])
        self.assertEqual(config["selection"]["max_topic_items"]["ai"], 3)
        self.assertTrue(
            {
                "cloudflare-blog",
                "github-engineering",
                "huggingface-blog",
                "google-security",
            }.issubset({source["id"] for source in enabled})
        )
        github_sources = [
            source for source in enabled if source["id"].startswith("github-")
        ]
        self.assertTrue(
            all(source.get("source_family") == "github" for source in github_sources)
        )
        yozmit = next(source for source in enabled if source["id"] == "yozmit")
        self.assertTrue(yozmit.get("fallbacks"))
        for source_id in ("aitimes", "geeknews", "yozmit"):
            source = next(item for item in enabled if item["id"] == source_id)
            self.assertFalse(source["include_summary"])


if __name__ == "__main__":
    unittest.main()
