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
                    "durable_problem_score": 7,
                    "editorial_angle": {
                        "intent": "troubleshooting",
                        "recommended_shape": "troubleshooting",
                        "recommended_artifact": "troubleshooting_tree",
                    },
                    "requires_manual_review": False,
                }
            ],
            "problem_signals": [
                {
                    "id": "problem-id",
                    "title": "요즘 개발자가 반복해 묻는 배포 문제",
                    "url": "https://yozm.example/problem",
                    "source_name": "요즘IT",
                    "group": "korean_editorial",
                    "score": 7,
                    "score_reasons": ["문제 발견 단서"],
                    "durable_problem_score": 5,
                    "unknown_publication_date": True,
                    "editorial_angle": {
                        "intent": "troubleshooting",
                        "recommended_shape": "troubleshooting",
                        "recommended_artifact": "checklist",
                    },
                    "requires_manual_review": True,
                }
            ],
            "candidates": [],
            "errors": [{"source_id": "broken", "message": "timeout <60s>"}],
        }

    def test_renders_review_page_and_escapes_external_content(self):
        html = render_inbox_html(self.inbox)

        self.assertIn("실전 IT 아티클 후보함", html)
        self.assertIn("오늘의 추천 1건", html)
        self.assertIn("AI &lt;Agent&gt; 업데이트", html)
        self.assertIn("a=1&amp;b=2", html)
        self.assertNotIn("AI <Agent>", html)
        self.assertIn("broken", html)
        self.assertIn("timeout &lt;60s&gt;", html)
        self.assertIn("오래가는 문제 7점", html)
        self.assertIn("troubleshooting_tree", html)
        self.assertIn("문제 발굴 신호 1건", html)
        self.assertIn("요즘IT", html)
        self.assertIn("발행일 확인 필요", html)

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
        self.assertEqual(config["selection"]["mode"], "lead_shortlist")
        self.assertEqual(config["selection"]["max_items"], 5)
        self.assertIn("aitimes", {source["id"] for source in enabled})
        self.assertNotIn("audience_lanes", config["selection"])
        self.assertNotIn("max_research_items", config["selection"])
        self.assertEqual(config["selection"]["exclude_recent_days"], 60)
        self.assertEqual(config["selection"]["publisher_cooldown_days"], 2)
        self.assertEqual(config["selection"]["brand_cooldown_days"], 7)
        self.assertEqual(config["selection"]["topic_cooldown_days"], 7)
        self.assertEqual(config["selection"]["research_selection_penalty"], 2)
        self.assertEqual(config["selection"]["max_per_topic_family"], 1)
        self.assertEqual(
            config["selection"]["fallback_min_reader_relevance"],
            config["selection"]["min_reader_relevance"],
        )
        self.assertEqual(config["max_age_days"], 30)
        self.assertEqual(config["selection"]["max_per_family"], 1)
        self.assertEqual(config["selection"]["min_lead_score"], 8)
        self.assertEqual(config["selection"]["min_evergreen_fit"], 4)
        self.assertEqual(config["selection"]["fallback_min_evergreen_fit"], 2)
        self.assertEqual(config["selection"]["min_durable_problem_score"], 3)
        self.assertEqual(
            config["selection"]["fallback_min_durable_problem_score"], 1
        )
        self.assertNotIn("inbox_retention_days", config["selection"])
        self.assertTrue(
            {
                "cloudflare-blog",
                "github-engineering",
                "huggingface-blog",
                "google-security",
                "kakao-tech",
                "webdev",
                "aws-architecture",
                "slack-engineering",
                "spotify-engineering",
                "hacker-news",
                "lobsters",
            }.issubset({source["id"] for source in enabled})
        )
        for source_id in (
            "kakao-tech",
            "webdev",
            "aws-architecture",
            "slack-engineering",
            "spotify-engineering",
        ):
            source = next(item for item in enabled if item["id"] == source_id)
            self.assertGreaterEqual(source.get("evergreen_bias", 0), 4)
        for source_id in ("geeknews", "hacker-news", "lobsters"):
            source = next(item for item in enabled if item["id"] == source_id)
            self.assertEqual(source["group"], "community")
            self.assertGreaterEqual(source.get("evergreen_bias", 0), 2)
        github_sources = [
            source for source in enabled if source["id"].startswith("github-")
        ]
        self.assertTrue(
            all(source.get("source_family") == "github" for source in github_sources)
        )
        yozmit = next(source for source in enabled if source["id"] == "yozmit")
        self.assertTrue(yozmit["allow_unknown_date"])
        self.assertTrue(yozmit.get("fallbacks"))
        for source_id in ("aitimes", "geeknews", "yozmit"):
            source = next(item for item in enabled if item["id"] == source_id)
            self.assertFalse(source["include_summary"])


if __name__ == "__main__":
    unittest.main()
