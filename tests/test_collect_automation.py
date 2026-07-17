import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from blog_pipeline.collection.collect_automation import (
    build_automation_inbox,
    load_recent_automation_history,
    load_recent_automation_urls,
    render_automation_inbox_html,
    score_automation_candidate,
    select_automation_candidates,
    write_automation_inbox,
)


NOW = dt.datetime(2026, 7, 18, 3, 17, tzinfo=dt.timezone.utc)
ROOT = Path(__file__).parents[1]
DEFAULT_CONFIG = ROOT / "config" / "automation_sources.json"

TRENDING_HTML = """
<main>
  <article class="Box-row">
    <h2><a href="/n8n-io/n8n">n8n-io / n8n</a></h2>
    <p class="col-9 color-fg-muted my-1 pr-4">
      Workflow automation with templates, schedules, logs and self-hosted Docker.
    </p>
  </article>
  <article class="Box-row">
    <h2><a href="/example/visual-tool">example / visual-tool</a></h2>
    <p class="col-9 color-fg-muted my-1 pr-4">
      Dashboard for monitoring files and sending notifications.
    </p>
  </article>
</main>
"""

RELEASE_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>v1.4 workflow retry and execution logs</title>
    <link rel="alternate" href="https://github.com/activepieces/activepieces/releases/tag/v1.4" />
    <summary>Docker quickstart and retry settings for failed automation runs.</summary>
    <updated>2026-07-17T01:00:00Z</updated>
  </entry>
</feed>
"""


def automation_config():
    return {
        "max_items_per_source": 10,
        "max_age_days": 45,
        "criteria": {
            "search_durability": {
                "label": "검색 지속성",
                "weight": 30,
                "target_matches": 2,
                "keywords": ["workflow", "automation", "self-hosted", "docker"],
            },
            "problem_solving": {
                "label": "문제 해결성",
                "weight": 30,
                "target_matches": 2,
                "keywords": ["retry", "monitoring", "notification", "schedule"],
            },
            "reproducibility": {
                "label": "재현 가능성",
                "weight": 20,
                "target_matches": 2,
                "keywords": ["quickstart", "docker", "template", "settings"],
            },
            "visual_evidence": {
                "label": "시각 설명 가능성",
                "weight": 10,
                "target_matches": 2,
                "keywords": ["dashboard", "logs", "workflow"],
            },
            "blog_connection": {
                "label": "기존 글 연결성",
                "weight": 10,
                "target_matches": 2,
                "keywords": ["github", "ai", "automation"],
            },
        },
        "selection": {
            "max_items": 2,
            "max_candidates": 2,
            "max_per_source": 1,
            "max_per_family": 1,
            "min_score": 20,
            "exclude_recent_days": 90,
        },
        "sources": [
            {
                "id": "github-trending",
                "name": "GitHub Trending",
                "group": "discovery",
                "type": "github_trending",
                "url": "https://github.com/trending?since=weekly",
                "weight": 3,
                "experiment_type": "공개 도구 적용 사례",
                "criteria_bias": {"blog_connection": 3},
            },
            {
                "id": "activepieces-releases",
                "name": "Activepieces Releases",
                "group": "official_release",
                "type": "atom",
                "url": "https://github.com/activepieces/activepieces/releases.atom",
                "repository": "activepieces/activepieces",
                "candidate_prefix": "activepieces/activepieces",
                "weight": 4,
                "experiment_type": "따라하기",
                "criteria_bias": {"reproducibility": 4},
            },
        ],
    }


class AutomationScoringTests(unittest.TestCase):
    def test_shortlist_reserves_space_for_distinct_source_kinds(self):
        candidates = [
            {"id": "release-1", "source_id": "r1", "source_family": "r1", "source_kind": "release", "provisional_score": 90},
            {"id": "release-2", "source_id": "r2", "source_family": "r2", "source_kind": "release", "provisional_score": 80},
            {"id": "guide", "source_id": "guide", "source_family": "guide", "source_kind": "official_guide", "provisional_score": 50},
            {"id": "trending", "source_id": "trend", "source_family": "trend", "source_kind": "trending", "provisional_score": 40},
        ]
        selection = {
            "max_items": 3,
            "max_per_source": 1,
            "max_per_family": 1,
            "min_score": 20,
            "preferred_source_kinds": ["official_guide", "trending", "release"],
        }

        selected = select_automation_candidates(candidates, selection)

        self.assertEqual(
            {item["source_kind"] for item in selected},
            {"official_guide", "trending", "release"},
        )
        self.assertEqual(
            [item["provisional_score"] for item in selected],
            [90, 50, 40],
        )

    def test_default_config_matches_the_saturday_editorial_weights_and_sources(self):
        config = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))

        self.assertEqual(
            sum(item["weight"] for item in config["criteria"].values()),
            100,
        )
        self.assertEqual(config["selection"]["max_items"], 5)
        self.assertEqual(config["selection"]["max_candidates"], 25)
        self.assertEqual(config["selection"]["exclude_recent_days"], 90)
        source_types = {source["type"] for source in config["sources"]}
        self.assertIn("github_trending", source_types)
        self.assertIn("atom", source_types)
        self.assertIn("rss", source_types)
        self.assertTrue(all(source.get("enabled", True) for source in config["sources"]))

    def test_scores_each_editorial_criterion_within_its_weight(self):
        config = automation_config()
        candidate = {
            "title": "n8n workflow automation",
            "summary": "Docker template, schedule, monitoring dashboard and logs",
        }
        source = config["sources"][0]

        score_automation_candidate(candidate, config["criteria"], source)

        self.assertGreaterEqual(candidate["provisional_score"], 70)
        self.assertEqual(set(candidate["score_breakdown"]), set(config["criteria"]))
        for key, value in candidate["score_breakdown"].items():
            self.assertLessEqual(value, config["criteria"][key]["weight"])
        self.assertEqual(candidate["experiment_type"], "공개 도구 적용 사례")
        self.assertEqual(candidate["verification_status"], "metadata_only")

    def test_builds_a_diverse_shortlist_and_excludes_recently_used_urls(self):
        config = automation_config()

        def fetch(url):
            return TRENDING_HTML if "trending" in url else RELEASE_ATOM

        result = build_automation_inbox(
            config,
            fetch_text=fetch,
            now=NOW,
            day_id="2026-07-18",
            excluded_urls={"https://github.com/n8n-io/n8n"},
        )

        self.assertEqual(result["content_type"], "automation_candidates")
        self.assertEqual(len(result["selected"]), 2)
        self.assertEqual(len(result["candidates"]), 2)
        self.assertTrue(
            {item["id"] for item in result["selected"]}
            <= {item["id"] for item in result["candidates"]}
        )
        self.assertNotIn(
            "https://github.com/n8n-io/n8n",
            [item["url"] for item in result["selected"]],
        )
        self.assertEqual(
            {item["source_id"] for item in result["selected"]},
            {"github-trending", "activepieces-releases"},
        )
        self.assertTrue(all(item["provisional_score"] >= 20 for item in result["selected"]))
        release = next(
            item
            for item in result["selected"]
            if item["source_id"] == "activepieces-releases"
        )
        self.assertTrue(release["title"].startswith("activepieces/activepieces "))
        self.assertEqual(release["repository"], "activepieces/activepieces")
        self.assertEqual(result["selection"]["recently_selected_excluded"], 1)
        self.assertEqual(result["execution_status"], "not_run")
        self.assertEqual(
            [item["rank"] for item in result["selected"]],
            [1, 2],
        )
        self.assertTrue(
            all(item["execution_status"] == "not_run" for item in result["selected"])
        )

    def test_excludes_recent_repository_and_matching_primary_query_fingerprints(self):
        config = automation_config()
        config["selection"]["max_candidates"] = 3

        def fetch(url):
            return TRENDING_HTML if "trending" in url else RELEASE_ATOM

        result = build_automation_inbox(
            config,
            fetch_text=fetch,
            now=NOW,
            day_id="2026-07-18",
            excluded_fingerprints={"repo:activepieces/activepieces"},
            excluded_queries={"monitoring dashboard notification"},
        )

        release = next(
            item
            for item in result["candidates"]
            if item["source_id"] == "activepieces-releases"
        )
        visual_tool = next(
            item
            for item in result["candidates"]
            if item["title"] == "example/visual-tool"
        )
        self.assertTrue(release["recently_used"])
        self.assertEqual(release["recent_match"], "same_repository")
        self.assertTrue(visual_tool["recently_used"])
        self.assertEqual(visual_tool["recent_match"], "similar_primary_query")
        self.assertNotIn(
            "activepieces-releases",
            {item["source_id"] for item in result["selected"]},
        )


class AutomationInboxTests(unittest.TestCase):
    def test_loads_history_from_publish_ready_automation_cases_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = root / "data" / "automation_cases"
            metadata = root / "docs" / "tistory"
            cases.mkdir(parents=True)
            metadata.mkdir(parents=True)
            (cases / "2026-07-11.json").write_text(
                json.dumps(
                    {
                        "draft_id": "2026-07-11-automation",
                        "publish_date": "2026-07-11",
                        "content_type": "automation_case",
                        "primary_query": "n8n 실패 워크플로 알림",
                        "news": [
                            {
                                "title_kr": "n8n 실패 알림 자동화",
                                "url": "https://github.com/n8n-io/n8n/releases/tag/v2?ref=blog",
                            }
                        ],
                        "references": [{"url": "https://example.com/not-primary"}],
                    }
                ),
                encoding="utf-8",
            )
            (metadata / "2026-07-11-automation.json").write_text(
                json.dumps(
                    {
                        "draft_id": "2026-07-11-automation",
                        "publish_date": "2026-07-11",
                        "content_type": "automation_case",
                        "source": "data/automation_cases/2026-07-11.json",
                        "publish_ready": True,
                    }
                ),
                encoding="utf-8",
            )
            (cases / "2026-07-12.json").write_text(
                json.dumps(
                    {
                        "draft_id": "2026-07-12-automation",
                        "publish_date": "2026-07-12",
                        "content_type": "automation_case",
                        "primary_query": "미완성 주제",
                        "news": [{"url": "https://github.com/example/incomplete"}],
                    }
                ),
                encoding="utf-8",
            )

            history = load_recent_automation_history(
                cases,
                "2026-07-18",
                lookback_days=90,
                publish_meta_dir=metadata,
            )
            urls = load_recent_automation_urls(
                cases,
                "2026-07-18",
                lookback_days=90,
                publish_meta_dir=metadata,
            )

        self.assertEqual(
            urls,
            {"https://github.com/n8n-io/n8n/releases/tag/v2"},
        )
        self.assertEqual(history["urls"], urls)
        self.assertEqual(history["fingerprints"], {"repo:n8n-io/n8n"})
        self.assertIn("n8n 실패 워크플로 알림", history["queries"])
        self.assertNotIn("미완성 주제", history["queries"])

    def test_review_page_escapes_external_text_and_is_not_indexable(self):
        page = render_automation_inbox_html(
            {
                "day": "2026-07-18",
                "generated_at": "",
                "selected": [
                    {
                        "id": "unsafe",
                        "title": "<script>alert(1)</script>",
                        "url": "https://example.com/tool",
                        "summary": "<b>unsafe</b>",
                        "source_name": "Official",
                        "provisional_score": 50,
                        "score_breakdown": {},
                        "experiment_type": "따라하기",
                        "score_reasons": [],
                    }
                ],
                "candidates": [],
                "errors": [],
                "criteria": {},
            }
        )

        self.assertIn('name="robots" content="noindex,nofollow,noarchive"', page)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertIn("&lt;b&gt;unsafe&lt;/b&gt;", page)

    def test_writes_latest_json_and_review_page(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            inbox = {
                "schema_version": 1,
                "content_type": "automation_candidates",
                "execution_status": "not_run",
                "day": "2026-07-18",
                "generated_at": NOW.isoformat(),
                "selected": [],
                "candidates": [],
                "errors": [],
                "criteria": {},
            }

            paths = write_automation_inbox(inbox, output)

            self.assertEqual(Path(paths["json"]).name, "latest.json")
            self.assertEqual(Path(paths["html"]).name, "index.html")
            self.assertTrue((output / "latest.json").is_file())
            self.assertTrue((output / "index.html").is_file())


if __name__ == "__main__":
    unittest.main()
