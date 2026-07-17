import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from blog_pipeline.publishing.daily_guard import (
    find_recent_duplicates,
    inspect_daily_state,
    inspect_draft_state,
)


class DailyGuardTests(unittest.TestCase):
    def write_json(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def test_daily_complete_and_saturday_automation_new_are_independent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = "2026-07-11"
            self.write_json(
                root / "data" / "days" / f"{day}.json",
                {
                    "news": [
                        {"title_kr": "첫 뉴스", "url": "https://example.com/1"},
                        {"title_kr": "둘째 뉴스", "url": "https://example.com/2"},
                        {"title_kr": "셋째 뉴스", "url": "https://example.com/3"},
                    ]
                },
            )
            self.write_json(
                root / "docs" / "tistory" / f"{day}.json",
                {
                    "publish_ready": True,
                    "image_assets": [
                        {"kind": "cover"},
                        {"kind": "story_1"},
                        {"kind": "story_2"},
                        {"kind": "story_3"},
                    ],
                },
            )
            body = (
                '<article class="daily-digest-post">'
                '<section id="digest-news-1" class="digest-news-card">1</section>'
                '<section id="digest-news-2" class="digest-news-card">2</section>'
                '<section id="digest-news-3" class="digest-news-card">3</section>'
                "</article>"
            )
            tistory = root / "docs" / "tistory"
            (tistory / f"{day}.html").write_text(body, encoding="utf-8")
            (tistory / f"{day}-adfit.html").write_text(
                body.replace(
                    '<section id="digest-news-2"',
                    '<figure data-ad-vendor="adfit"></figure><section id="digest-news-2"',
                ),
                encoding="utf-8",
            )
            preview = root / "docs" / "preview"
            preview.mkdir(parents=True)
            (preview / f"{day}.html").write_text(body, encoding="utf-8")

            daily_before = inspect_daily_state(day, root=root)
            automation = inspect_draft_state(f"{day}-automation", root=root)
            daily_after = inspect_daily_state(day, root=root)

        self.assertEqual(daily_before["status"], "COMPLETE")
        self.assertEqual(automation["status"], "NEW")
        self.assertEqual(automation["draft_id"], f"{day}-automation")
        self.assertEqual(daily_after, daily_before)

    def test_saturday_automation_requires_at_least_three_explanatory_visuals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = "2026-07-18"
            self.write_json(
                root / "data" / "automation_cases" / f"{day}.json",
                {
                    "draft_id": f"{day}-automation",
                    "publish_date": day,
                    "content_type": "automation_case",
                    "content_label": "업무자동화 실험",
                    "format": "lead-story-v1",
                    "primary_query": "반복 보고서 자동화",
                    "images": {
                        "cover": {},
                        "visual_1": {},
                        "visual_2": {},
                    },
                    "news": [
                        {
                            "title_kr": "반복 보고서 자동화 실험",
                            "references": [
                                {
                                    "kind": "official",
                                    "title": "공식 문서",
                                    "url": "https://example.com/docs",
                                },
                                {
                                    "kind": "independent",
                                    "title": "보조 자료",
                                    "url": "https://example.net/guide",
                                },
                            ],
                            "content": [
                                {"t": "h", "text": "문제"},
                                {"t": "visual", "image": "visual_1"},
                                {"t": "h", "text": "준비"},
                                {"t": "p", "text": "환경"},
                                {"t": "ad_break"},
                                {"t": "h", "text": "실행"},
                                {"t": "visual", "image": "visual_2"},
                                {"t": "h", "text": "결과"},
                            ],
                        }
                    ],
                    "related_posts": [
                        {
                            "title": "관련 1",
                            "url": "https://won0322.tistory.com/120",
                        },
                        {
                            "title": "관련 2",
                            "url": "https://won0322.tistory.com/121",
                        },
                    ],
                },
            )

            result = inspect_draft_state(f"{day}-automation", root=root)

        self.assertIn("lead_explanatory_visuals", result["reasons"])

    def test_saturday_guard_rejects_mismatched_publish_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = "2026-07-18"
            draft_id = f"{day}-automation"
            self.write_json(
                root / "data" / "automation_cases" / f"{day}.json",
                {
                    "draft_id": draft_id,
                    "publish_date": day,
                    "content_type": "automation_case",
                    "content_label": "업무자동화 실험",
                    "news": [],
                },
            )
            self.write_json(
                root / "docs" / "tistory" / f"{draft_id}.json",
                {
                    "draft_id": day,
                    "publish_date": day,
                    "content_type": "daily_news",
                    "content_label": "뉴스 심층글",
                    "source": f"data/days/{day}.json",
                    "publish_ready": True,
                },
            )

            result = inspect_draft_state(draft_id, root=root)

        self.assertIn("invalid_publish_identity", result["reasons"])
        self.assertIn("invalid_publish_source", result["reasons"])

    def test_complete_day_stops_a_second_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = "2026-07-14"
            self.write_json(
                root / "data" / "days" / f"{day}.json",
                {
                    "news": [
                        {"title_kr": "첫 뉴스", "url": "https://example.com/1"},
                        {"title_kr": "둘째 뉴스", "url": "https://example.com/2"},
                        {"title_kr": "셋째 뉴스", "url": "https://example.com/3"},
                    ]
                },
            )
            self.write_json(
                root / "docs" / "tistory" / f"{day}.json",
                {
                    "publish_ready": True,
                    "image_assets": [
                        {"kind": "cover"},
                        {"kind": "story_1"},
                        {"kind": "story_2"},
                        {"kind": "story_3"},
                    ],
                },
            )
            html = (
                '<article class="daily-digest-post">'
                '<section id="digest-news-1" class="digest-news-card">1</section>'
                '<section id="digest-news-2" class="digest-news-card">2</section>'
                '<section id="digest-news-3" class="digest-news-card">3</section>'
                "</article>"
            )
            tistory = root / "docs" / "tistory"
            (tistory / f"{day}.html").write_text(html, encoding="utf-8")
            (tistory / f"{day}-adfit.html").write_text(
                html.replace(
                    '<section id="digest-news-2"',
                    '<figure data-ad-vendor="adfit"></figure><section id="digest-news-2"',
                ),
                encoding="utf-8",
            )
            preview = root / "docs" / "preview"
            preview.mkdir(parents=True)
            (preview / f"{day}.html").write_text(html, encoding="utf-8")

            result = inspect_daily_state(day, root=root)

        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["duplicates"], [])

    def test_existing_source_without_outputs_is_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_json(
                root / "data" / "days" / "2026-07-14.json",
                {"news": [{"title_kr": "작성 중", "url": "https://example.com/1"}]},
            )

            result = inspect_daily_state("2026-07-14", root=root)

        self.assertEqual(result["status"], "PARTIAL")
        self.assertIn("news_count", result["reasons"])
        self.assertIn("missing_publish_meta", result["reasons"])

    def test_new_daily_runs_require_the_webp_image_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_json(
                root / "data" / "days" / "2026-07-16.json",
                {
                    "generation": {"provider": "codex-agent"},
                    "news": [
                        {"title_kr": "첫 뉴스", "url": "https://example.com/1"},
                        {"title_kr": "둘째 뉴스", "url": "https://example.com/2"},
                        {"title_kr": "셋째 뉴스", "url": "https://example.com/3"},
                    ],
                },
            )

            result = inspect_daily_state("2026-07-16", root=root)

        self.assertIn("missing_image_policy", result["reasons"])

    def test_invalid_new_day_json_reports_partial_instead_of_crashing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "data" / "days" / "2026-07-16.json"
            path.parent.mkdir(parents=True)
            path.write_text("{invalid", encoding="utf-8")

            result = inspect_daily_state("2026-07-16", root=root)

        self.assertEqual(result["status"], "PARTIAL")
        self.assertIn("missing_or_invalid_source", result["reasons"])
        self.assertIn("invalid_image_manifest", result["reasons"])

    def test_complete_deep_story_accepts_one_news_and_variable_explanatory_visuals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = "2026-07-17"
            asset_dir = root / "docs" / "tistory" / "assets" / day
            asset_dir.mkdir(parents=True)
            images = {}
            for kind in ("cover", "visual_1", "visual_2"):
                path = asset_dir / f"{kind}.webp"
                Image.new("RGB", (1200, 630), "#23483c").save(path, "WEBP")
                images[kind] = {
                    "path": path.relative_to(root).as_posix(),
                    "url": f"https://blog.example/{kind}.webp",
                }
            content = [
                {"t": "h", "text": "무슨 일이 있었나"},
                {"t": "p", "text": "핵심 사실"},
                {"t": "visual", "image": "visual_1", "caption": "흐름도"},
                {"t": "h", "text": "무엇이 다른가"},
                {"t": "table", "headers": ["구분", "변경"], "rows": [["전", "후"]]},
                {"t": "ad_break"},
                {"t": "h", "text": "무슨 의미인가"},
                {"t": "p", "text": "실제 영향"},
                {"t": "visual", "image": "visual_2", "caption": "비교 도식"},
                {"t": "h", "text": "무엇을 확인할까"},
                {"t": "p", "text": "권한 범위를 확인한다."},
                {"t": "p", "text": "실행 로그를 남긴다."},
                {"t": "p", "text": "리뷰 책임자를 정한다."},
            ]
            source = {
                "schema_version": 3,
                "format": "lead-story-v1",
                "primary_query": "GitHub Copilot agent mode",
                "generation": {"provider": "codex-agent", "image_policy": "webp-v1"},
                "images": images,
                "news": [
                    {
                        "title_kr": "GitHub Copilot 에이전트 모드 변경",
                        "url": "https://github.blog/example",
                        "references": [
                            {"kind": "official", "title": "공식", "url": "https://github.blog/example"},
                            {"kind": "independent", "title": "분석", "url": "https://security.example/analysis"},
                        ],
                        "content": content,
                    }
                ],
                "related_posts": [
                    {"title": "관련 글 1", "url": "https://won0322.tistory.com/120"},
                    {"title": "관련 글 2", "url": "https://won0322.tistory.com/121"},
                ],
            }
            self.write_json(root / "data" / "days" / f"{day}.json", source)
            self.write_json(
                root / "docs" / "tistory" / f"{day}.json",
                {
                    "publish_ready": True,
                    "image_assets": [{"kind": kind} for kind in images],
                },
            )
            html = (
                '<article class="daily-digest-post" data-digest-version="3">'
                '<section id="digest-news-1" class="digest-news-card digest-lead-story">1</section>'
                '<div data-digest-ad-break="true"></div>'
                '<section class="digest-lead-continuation">2</section></article>'
            )
            tistory = root / "docs" / "tistory"
            (tistory / f"{day}.html").write_text(html, encoding="utf-8")
            (tistory / f"{day}-adfit.html").write_text(
                html.replace(
                    '<div data-digest-ad-break="true"></div>',
                    '<figure data-ad-vendor="adfit"></figure>',
                ),
                encoding="utf-8",
            )
            preview = root / "docs" / "preview"
            preview.mkdir(parents=True)
            (preview / f"{day}.html").write_text(html, encoding="utf-8")

            result = inspect_daily_state(day, root=root)

        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["reasons"], [])

    def test_deep_story_rejects_missing_research_visuals_and_internal_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = "2026-07-17"
            self.write_json(
                root / "data" / "days" / f"{day}.json",
                {
                    "format": "lead-story-v1",
                    "primary_query": "AI agent",
                    "news": [{"title_kr": "심층 글", "content": [{"t": "ad_break"}]}],
                },
            )

            result = inspect_daily_state(day, root=root)

        self.assertIn("lead_references", result["reasons"])
        self.assertIn("lead_explanatory_visuals", result["reasons"])
        self.assertIn("related_posts", result["reasons"])

    def test_deep_story_rejects_a_declared_visual_that_is_not_used_in_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = "2026-07-17"
            content = [
                {"t": "h", "text": "변화"},
                {"t": "p", "text": "사실"},
                {"t": "visual", "image": "visual_1"},
                {"t": "h", "text": "비교"},
                {"t": "p", "text": "차이"},
                {"t": "ad_break"},
                {"t": "h", "text": "영향"},
                {"t": "visual", "image": "visual_2"},
                {"t": "h", "text": "확인"},
                {"t": "p", "text": "검토"},
                {"t": "p", "text": "테스트"},
                {"t": "p", "text": "승인"},
                {"t": "p", "text": "복구"},
            ]
            self.write_json(
                root / "data" / "days" / f"{day}.json",
                {
                    "format": "lead-story-v1",
                    "primary_query": "의존성 업데이트",
                    "images": {
                        "cover": {},
                        "visual_1": {},
                        "visual_2": {},
                        "visual_3": {},
                    },
                    "news": [
                        {
                            "title_kr": "심층 글",
                            "references": [
                                {"kind": "official", "title": "공식", "url": "https://example.com/official"},
                                {"kind": "independent", "title": "분석", "url": "https://example.net/analysis"},
                            ],
                            "content": content,
                        }
                    ],
                    "related_posts": [
                        {"title": "관련 1", "url": "https://won0322.tistory.com/120"},
                        {"title": "관련 2", "url": "https://won0322.tistory.com/121"},
                    ],
                },
            )

            result = inspect_daily_state(day, root=root)

        self.assertIn("lead_explanatory_visuals", result["reasons"])

    def test_deep_story_does_not_count_non_http_research_or_related_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = "2026-07-17"
            content = [
                {"t": "h", "text": "변화"},
                {"t": "p", "text": "사실"},
                {"t": "visual", "image": "visual_1"},
                {"t": "h", "text": "비교"},
                {"t": "p", "text": "차이"},
                {"t": "ad_break"},
                {"t": "h", "text": "영향"},
                {"t": "visual", "image": "visual_2"},
                {"t": "h", "text": "확인"},
                {"t": "p", "text": "검토"},
                {"t": "p", "text": "테스트"},
                {"t": "p", "text": "승인"},
                {"t": "p", "text": "복구"},
            ]
            self.write_json(
                root / "data" / "days" / f"{day}.json",
                {
                    "format": "lead-story-v1",
                    "primary_query": "의존성 업데이트",
                    "images": {"cover": {}, "visual_1": {}, "visual_2": {}},
                    "news": [
                        {
                            "title_kr": "심층 글",
                            "references": [
                                {"kind": "official", "title": "위험", "url": "javascript:alert(1)"},
                                {"kind": "documentation", "title": "내부", "url": "/docs/local"},
                            ],
                            "content": content,
                        }
                    ],
                    "related_posts": [
                        {"title": "위험 1", "url": "data:text/html,bad"},
                        {"title": "위험 2", "url": "javascript:alert(2)"},
                    ],
                },
            )

            result = inspect_daily_state(day, root=root)

        self.assertIn("lead_references", result["reasons"])
        self.assertIn("related_posts", result["reasons"])

    def test_deep_story_caps_explanatory_visuals_at_six(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = "2026-07-17"
            content = [
                {"t": "h", "text": "변화"},
                {"t": "p", "text": "사실"},
                {"t": "visual", "image": "visual_1"},
                {"t": "visual", "image": "visual_2"},
                {"t": "h", "text": "비교"},
                {"t": "p", "text": "차이"},
                {"t": "visual", "image": "visual_3"},
                {"t": "ad_break"},
                {"t": "h", "text": "영향"},
                {"t": "visual", "image": "visual_4"},
                {"t": "visual", "image": "visual_5"},
                {"t": "p", "text": "검토"},
                {"t": "h", "text": "확인"},
                {"t": "visual", "image": "visual_6"},
                {"t": "visual", "image": "visual_7"},
                {"t": "p", "text": "테스트"},
                {"t": "p", "text": "승인"},
                {"t": "p", "text": "복구"},
            ]
            self.write_json(
                root / "data" / "days" / f"{day}.json",
                {
                    "format": "lead-story-v1",
                    "primary_query": "의존성 업데이트",
                    "images": {
                        "cover": {},
                        **{f"visual_{index}": {} for index in range(1, 8)},
                    },
                    "news": [
                        {
                            "title_kr": "심층 글",
                            "references": [
                                {"kind": "official", "title": "공식", "url": "https://example.com/official"},
                                {"kind": "independent", "title": "분석", "url": "https://example.net/analysis"},
                            ],
                            "content": content,
                        }
                    ],
                    "related_posts": [
                        {"title": "관련 1", "url": "https://won0322.tistory.com/120"},
                        {"title": "관련 2", "url": "https://won0322.tistory.com/121"},
                    ],
                },
            )

            result = inspect_daily_state(day, root=root)

        self.assertIn("lead_explanatory_visuals", result["reasons"])

    def test_blocks_same_canonical_url_from_recent_days(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_json(
                root / "data" / "days" / "2026-07-13.json",
                {
                    "news": [
                        {
                            "title_kr": "인스타 사진 AI 연동 중단",
                            "url": "https://example.com/story?utm_source=rss&id=7",
                        }
                    ]
                },
            )
            current = {
                "news": [
                    {
                        "title_kr": "메타, 인스타 사진 AI 자동 연동 철회",
                        "url": "https://example.com/story?id=7&utm_medium=feed",
                    }
                ]
            }

            duplicates = find_recent_duplicates(
                "2026-07-14", current, root=root, window_days=14
            )

        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["reason"], "same_url")
        self.assertEqual(duplicates[0]["previous_day"], "2026-07-13")

    def test_blocks_a_nearly_identical_title_on_a_different_url(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_json(
                root / "data" / "days" / "2026-07-10.json",
                {
                    "news": [
                        {
                            "title_kr": "GitHub CodeQL, AI 시스템 프롬프트 인젝션 탐지 추가",
                            "url": "https://example.com/old",
                        }
                    ]
                },
            )
            current = {
                "news": [
                    {
                        "title_kr": "GitHub CodeQL AI 시스템 프롬프트 인젝션 탐지 추가",
                        "url": "https://example.com/new",
                    }
                ]
            }

            duplicates = find_recent_duplicates(
                "2026-07-14", current, root=root, window_days=14
            )

        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["reason"], "similar_title")


if __name__ == "__main__":
    unittest.main()
