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
                "allow_unknown_date": True,
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
        self.assertGreaterEqual(config["max_workers"], 4)
        self.assertEqual(config["selection"]["max_items"], 5)
        self.assertEqual(config["selection"]["max_candidates"], 25)
        self.assertEqual(config["selection"]["exclude_recent_days"], 90)
        self.assertGreaterEqual(
            config["selection"]["minimum_criterion_scores"]["broad_appeal"],
            8,
        )
        self.assertEqual(config["criteria"]["broad_appeal"]["label"], "대중 공감도")
        source_types = {source["type"] for source in config["sources"]}
        self.assertIn("github_trending", source_types)
        self.assertIn("atom", source_types)
        self.assertIn("rss", source_types)
        self.assertTrue(all(source.get("enabled", True) for source in config["sources"]))
        source_ids = {source["id"] for source in config["sources"]}
        self.assertIn("google-workspace-updates", source_ids)
        self.assertIn("power-automate-blog", source_ids)
        self.assertIn("zapier-guides", source_ids)
        self.assertIn("yozmit-evergreen-dev", source_ids)
        self.assertIn(
            "evergreen_editorial",
            config["selection"]["preferred_source_kinds"],
        )
        yozmit = next(
            source
            for source in config["sources"]
            if source["id"] == "yozmit-evergreen-dev"
        )
        self.assertEqual(
            yozmit["url"],
            "https://yozm.wishket.com/magazine/feed/",
        )
        self.assertTrue(yozmit["allow_unknown_date"])
        self.assertTrue(yozmit["manual_review"])
        evergreen_ids = {
            item["id"] for item in config["evergreen_candidates"]
        }
        self.assertIn("im-not-ai-korean-writing-test", evergreen_ids)
        self.assertIn("vibe-coding-recovery-basics", evergreen_ids)
        self.assertGreaterEqual(len(config["evergreen_candidates"]), 6)
        self.assertTrue(
            all(
                item.get("problem_lane")
                for item in config["evergreen_candidates"]
            )
        )
        self.assertTrue(
            all(
                item.get("tool_brand")
                for item in config["evergreen_candidates"]
            )
        )
        self.assertTrue(
            all(source.get("problem_lane") for source in config["sources"])
        )
        self.assertTrue(
            all(source.get("tool_brand") for source in config["sources"])
        )

    def test_shortlist_rejects_tool_only_candidates_below_a_required_criterion(self):
        candidates = [
            {
                "id": "tool-release",
                "source_id": "developer-tool",
                "source_family": "developer-tool",
                "source_kind": "release",
                "provisional_score": 95,
                "score_breakdown": {"broad_appeal": 0},
            },
            {
                "id": "email-files",
                "source_id": "office-guide",
                "source_family": "office-guide",
                "source_kind": "official_guide",
                "provisional_score": 72,
                "score_breakdown": {"broad_appeal": 14},
            },
        ]
        selection = {
            "max_items": 2,
            "max_per_source": 1,
            "max_per_family": 1,
            "min_score": 20,
            "minimum_criterion_scores": {"broad_appeal": 7},
        }

        selected = select_automation_candidates(candidates, selection)

        self.assertEqual([item["id"] for item in selected], ["email-files"])

    def test_source_bias_cannot_satisfy_the_broad_appeal_hard_gate(self):
        candidate = {
            "id": "developer-runner",
            "title": "Developer runner v2.4.1",
            "summary": "Internal workflow release notes",
            "source_id": "developer-release",
            "source_family": "developer-release",
            "source_kind": "release",
        }
        criteria = {
            "broad_appeal": {
                "label": "대중 공감도",
                "weight": 20,
                "target_matches": 2,
                "match_scope": "title",
                "keywords": ["파일", "일정", "메일", "보고서"],
            }
        }
        source = {"criteria_bias": {"broad_appeal": 20}}
        selection = {
            "max_items": 1,
            "max_per_source": 1,
            "max_per_family": 1,
            "min_score": 0,
            "minimum_criterion_scores": {"broad_appeal": 8},
        }
        score_automation_candidate(candidate, criteria, source)

        selected = select_automation_candidates([candidate], selection)

        self.assertEqual(candidate["raw_score_breakdown"]["broad_appeal"], 0)
        self.assertEqual(candidate["score_breakdown"]["broad_appeal"], 20)
        self.assertEqual(selected, [])

    def test_shortlist_avoids_the_last_problem_lane_and_tool_brand_when_an_alternative_exists(self):
        candidates = [
            {
                "id": "same-lane",
                "source_id": "python-guide",
                "source_family": "python-guide",
                "source_kind": "official_guide",
                "problem_lane": "이메일·문서",
                "tool_brand": "Python",
                "provisional_score": 95,
            },
            {
                "id": "same-brand",
                "source_id": "workspace-guide",
                "source_family": "workspace-guide",
                "source_kind": "official_guide",
                "problem_lane": "일정·알림",
                "tool_brand": "Google Workspace",
                "provisional_score": 90,
            },
            {
                "id": "fresh-topic",
                "source_id": "local-guide",
                "source_family": "local-guide",
                "source_kind": "official_guide",
                "problem_lane": "백업·복구",
                "tool_brand": "Python",
                "provisional_score": 80,
            },
        ]
        selection = {
            "max_items": 1,
            "max_per_source": 1,
            "max_per_family": 1,
            "min_score": 20,
            "last_problem_lane": "이메일·문서",
            "last_tool_brand": "Google Workspace",
        }

        selected = select_automation_candidates(candidates, selection)

        self.assertEqual([item["id"] for item in selected], ["fresh-topic"])

    def test_shortlist_does_not_recommend_a_repeated_lane_or_brand_without_an_alternative(self):
        candidates = [
            {
                "id": "same-lane-only",
                "source_id": "python-guide",
                "source_family": "python-guide",
                "source_kind": "official_guide",
                "problem_lane": "이메일·문서",
                "tool_brand": "Python",
                "provisional_score": 95,
            },
            {
                "id": "same-brand-only",
                "source_id": "workspace-guide",
                "source_family": "workspace-guide",
                "source_kind": "official_guide",
                "problem_lane": "일정·알림",
                "tool_brand": "Google Workspace",
                "provisional_score": 90,
            },
        ]
        selection = {
            "max_items": 2,
            "max_per_source": 1,
            "max_per_family": 1,
            "min_score": 20,
            "last_problem_lane": "이메일·문서",
            "last_tool_brand": "Google Workspace",
        }

        selected = select_automation_candidates(candidates, selection)

        self.assertEqual(selected, [])

    def test_title_scoped_broad_appeal_ignores_generic_terms_hidden_in_release_notes(self):
        candidate = {
            "title": "Developer runner v2.4.1",
            "summary": "Internal file report and notification fixes",
        }
        criteria = {
            "broad_appeal": {
                "label": "대중 공감도",
                "weight": 20,
                "target_matches": 2,
                "match_scope": "title",
                "keywords": ["file", "report", "notification"],
            }
        }

        score_automation_candidate(candidate, criteria)

        self.assertEqual(candidate["score_breakdown"]["broad_appeal"], 0)

    def test_default_policy_rejects_a_tool_release_with_only_one_generic_title_word(self):
        config = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
        candidate = {
            "id": "file-api",
            "title": "File API v2.0",
            "summary": (
                "automation workflow retry schedule quickstart template "
                "dashboard logs report"
            ),
            "source_id": "developer-release",
            "source_family": "developer-release",
            "source_kind": "release",
        }
        score_automation_candidate(candidate, config["criteria"])

        selected = select_automation_candidates(
            [candidate],
            config["selection"],
        )

        self.assertEqual(candidate["score_breakdown"]["broad_appeal"], 7)
        self.assertEqual(selected, [])

    def test_default_policy_accepts_a_specific_evergreen_development_topic(self):
        config = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
        candidate = {
            "id": "vibe-coding-recovery",
            "title": "바이브 코딩이 막힐 때 되돌리는 법",
            "summary": "Git 복구와 로컬·배포 차이를 직접 실습한다.",
            "source_id": "yozmit-evergreen-dev",
            "source_family": "yozmit-evergreen",
            "source_kind": "evergreen_editorial",
        }
        score_automation_candidate(candidate, config["criteria"])

        selected = select_automation_candidates(
            [candidate],
            config["selection"],
        )

        self.assertGreaterEqual(
            candidate["raw_score_breakdown"]["broad_appeal"],
            8,
        )
        self.assertEqual([item["id"] for item in selected], [candidate["id"]])

    def test_adds_problem_first_evergreen_candidates_without_fetching_a_feed(self):
        config = automation_config()
        config["sources"] = []
        config["criteria"]["broad_appeal"] = {
            "label": "대중 공감도",
            "weight": 20,
            "target_matches": 2,
            "match_scope": "title",
            "keywords": ["파일", "폴더"],
        }
        config["selection"]["minimum_criterion_scores"] = {"broad_appeal": 1}
        config["evergreen_candidates"] = [
            {
                "id": "downloads-file-sort",
                "title": "다운로드 폴더를 파일 종류별로 자동 정리하기",
                "summary": "임시 파일로 분류 전후를 확인하는 로컬 실험",
                "url": "https://docs.python.org/3/library/pathlib.html",
                "source_name": "Python 공식 문서",
                "problem_lane": "파일·문서",
                "experiment_type": "직접 실행 실험기",
                "verification_hint": "임시 폴더와 테스트 파일만 사용",
                "criteria_bias": {"broad_appeal": 8},
            }
        ]

        result = build_automation_inbox(
            config,
            fetch_text=lambda _url: self.fail("feed fetch should not run"),
            now=NOW,
            day_id="2026-07-18",
        )

        self.assertEqual(
            [item["title"] for item in result["selected"]],
            ["다운로드 폴더를 파일 종류별로 자동 정리하기"],
        )
        self.assertEqual(result["selected"][0]["source_kind"], "evergreen_guide")

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
    def test_history_infers_legacy_playwright_lane_and_brand_for_rotation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = root / "data" / "automation_cases"
            metadata = root / "docs" / "tistory"
            cases.mkdir(parents=True)
            metadata.mkdir(parents=True)
            (cases / "2026-07-18.json").write_text(
                json.dumps(
                    {
                        "draft_id": "2026-07-18-automation",
                        "publish_date": "2026-07-18",
                        "content_type": "automation_case",
                        "primary_query": "Playwright 1.61.1 웹 자동화 테스트",
                        "editorial": {
                            "headline": "Playwright로 반복 점검 등록 자동화하기"
                        },
                        "news": [
                            {
                                "title_kr": "Playwright로 웹 반복 작업 자동화",
                                "url": "https://playwright.dev/docs/intro",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (metadata / "2026-07-18-automation.json").write_text(
                json.dumps(
                    {
                        "draft_id": "2026-07-18-automation",
                        "publish_date": "2026-07-18",
                        "content_type": "automation_case",
                        "source": "data/automation_cases/2026-07-18.json",
                        "publish_ready": True,
                    }
                ),
                encoding="utf-8",
            )

            history = load_recent_automation_history(
                cases,
                "2026-07-25",
                lookback_days=90,
                publish_meta_dir=metadata,
            )

        self.assertEqual(history["last_problem_lane"], "웹 반복 작업")
        self.assertEqual(history["last_tool_brand"], "Playwright")

    def test_history_exposes_the_last_completed_problem_lane_and_tool_brand(self):
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
                        "primary_query": "Gmail 첨부파일 자동 정리",
                        "problem_lane": "이메일·문서",
                        "tool_brand": "Google Workspace",
                        "news": [
                            {
                                "title_kr": "Gmail 첨부파일을 Drive에 자동 저장",
                                "url": "https://workspace.google.com/blog/example",
                            }
                        ],
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
            (cases / "2026-07-04.json").write_text(
                json.dumps(
                    {
                        "draft_id": "2026-07-04-automation",
                        "publish_date": "2026-07-04",
                        "content_type": "automation_case",
                        "problem_lane": "백업·복구",
                        "tool_brand": "Python",
                        "news": [
                            {
                                "title_kr": "폴더 압축 백업",
                                "url": "https://docs.python.org/3/library/shutil.html",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (metadata / "2026-07-04-automation.json").write_text(
                json.dumps(
                    {
                        "draft_id": "2026-07-04-automation",
                        "publish_date": "2026-07-04",
                        "content_type": "automation_case",
                        "source": "data/automation_cases/2026-07-04.json",
                        "publish_ready": True,
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

        self.assertEqual(history["last_problem_lane"], "이메일·문서")
        self.assertEqual(history["last_tool_brand"], "Google Workspace")

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
        self.assertIn("-webkit-line-clamp:4", page)
        self.assertIn(".featured .summary", page)

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
