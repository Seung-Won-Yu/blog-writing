import unittest

from build_copy_page import render


class CopyPageTests(unittest.TestCase):
    def test_explains_manual_generation_without_upstream_copy(self):
        html = render([])

        self.assertIn("빠진 날짜 직접 생성", html)
        self.assertIn("날짜를 비우면 오늘", html)
        self.assertIn("Run workflow", html)
        self.assertNotIn("조이한", html)
        self.assertIn('role="status"', html)
        self.assertIn('aria-live="polite"', html)

    def test_draft_buttons_expose_selected_state_and_fetch_recovery(self):
        html = render(
            [
                {
                    "day": "2026-07-13",
                    "title": "오늘의 초안",
                    "title_candidates": [],
                    "category": "데일리IT뉴스",
                    "tags": "AI",
                    "meta_description": "설명",
                    "key_summary": [],
                    "publish_checklist": [],
                    "image_assets": [],
                    "source": "data/days/2026-07-13.json",
                    "source_page": "",
                    "html_path": "tistory/2026-07-13.html",
                    "meta_path": "tistory/2026-07-13.json",
                }
            ]
        )

        self.assertIn('aria-pressed="false"', html)
        self.assertIn('button.setAttribute("aria-pressed"', html)
        self.assertIn("초안을 불러오지 못했습니다", html)


if __name__ == "__main__":
    unittest.main()
