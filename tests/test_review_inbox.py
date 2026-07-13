import json
import copy
import tempfile
import unittest
from pathlib import Path

from collect_news import render_inbox_html, write_inbox


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

    def test_writes_dated_and_latest_json_and_html(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = write_inbox(self.inbox, directory)

            dated_json = Path(directory, "2026-07-12.json")
            self.assertTrue(dated_json.exists())
            self.assertTrue(Path(directory, "2026-07-12.html").exists())
            self.assertTrue(Path(directory, "latest.json").exists())
            self.assertTrue(Path(directory, "index.html").exists())
            self.assertEqual(json.loads(dated_json.read_text())["day"], "2026-07-12")
            self.assertEqual(paths["json"], str(dated_json))

    def test_same_candidates_do_not_change_files_only_for_new_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            write_inbox(self.inbox, directory)
            dated_json = Path(directory, "2026-07-12.json")
            first_text = dated_json.read_text(encoding="utf-8")

            rerun = copy.deepcopy(self.inbox)
            rerun["generated_at"] = "2026-07-12T10:00:00+00:00"
            write_inbox(rerun, directory)

            self.assertEqual(dated_json.read_text(encoding="utf-8"), first_text)


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
        self.assertTrue(config["selection"]["require_topic_coherence"])
        self.assertEqual(config["selection"]["max_topic_items"]["ai"], 3)
        yozmit = next(source for source in enabled if source["id"] == "yozmit")
        self.assertTrue(yozmit.get("fallbacks"))
        for source_id in ("aitimes", "geeknews", "yozmit"):
            source = next(item for item in enabled if item["id"] == source_id)
            self.assertFalse(source["include_summary"])
            self.assertTrue(source["runtime_summary"])


if __name__ == "__main__":
    unittest.main()
