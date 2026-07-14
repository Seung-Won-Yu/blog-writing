import json
import tempfile
import unittest
from pathlib import Path

from blog_pipeline.publishing.daily_guard import (
    find_recent_duplicates,
    inspect_daily_state,
)


class DailyGuardTests(unittest.TestCase):
    def write_json(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

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
