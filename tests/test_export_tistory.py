import unittest

from export_tistory import (
    build_key_summary,
    build_meta_description,
    build_publish_checklist,
    estimate_read_minutes,
    post_title,
    render_post,
)


FALLBACK_DAY = {
    "date_label": "2026. 7. 13",
    "weekday": "월",
    "news": [
        {
            "title_kr": "AI 개발 도구 업데이트",
            "source": "공식 블로그",
            "url": "https://example.com/news",
            "blurb_kr": "새 기능을 공개했다.",
            "content": [],
        }
    ],
    "quiz": {},
    "terms": [],
    "generation": {"provider": "deterministic-fallback"},
}


class OptionalLearningSectionsTests(unittest.TestCase):
    def test_fallback_copy_does_not_claim_to_have_quiz_or_images(self):
        html = render_post("2026-07-13", FALLBACK_DAY)

        self.assertNotIn("정처기 문제", post_title(FALLBACK_DAY))
        self.assertNotIn("정보처리기사", build_meta_description(FALLBACK_DAY))
        self.assertNotIn("학습용 문제로 구성", html)
        self.assertNotIn("자동 생성 데일리 다이제스트", html)
        self.assertFalse(any("이미지" in item for item in build_publish_checklist(FALLBACK_DAY)))

    def test_normal_draft_keeps_quiz_copy(self):
        day = dict(FALLBACK_DAY)
        day["quiz"] = {
            "category": "소프트웨어 공학",
            "question": "형상 관리의 목적은?",
            "options": ["A", "B", "C", "D"],
            "answer": 0,
            "explain_kr": "변경 이력을 관리한다.",
        }

        self.assertIn("정처기 문제", post_title(day))
        self.assertIn("소프트웨어 공학", build_meta_description(day))


class EditorialReadingFlowTests(unittest.TestCase):
    def test_key_summary_splits_news_into_scannable_rows(self):
        day = dict(FALLBACK_DAY)
        day["news"] = [
            {"title_kr": "첫 번째 뉴스"},
            {"title_kr": "두 번째 뉴스"},
            {"title_kr": "세 번째 뉴스"},
        ]

        rows = build_key_summary(day)

        self.assertEqual(rows[:3], ["1. 첫 번째 뉴스", "2. 두 번째 뉴스", "3. 세 번째 뉴스"])

    def test_renders_opening_closing_action_and_dynamic_news_count(self):
        day = dict(FALLBACK_DAY)
        day["editorial"] = {
            "opening": "오늘은 도구보다 검증 과정에 초점을 맞춰봤다.",
            "closing": "결국 오래 남는 것은 결과를 판단하는 힘이다.",
            "action": "기사 하나를 골라 적용 지점을 한 줄로 적어보자.",
        }

        html = render_post("2026-07-13", day)

        self.assertIn("도구보다 검증 과정", html)
        self.assertIn("오늘의 뉴스 1개", html)
        self.assertIn('class="digest-closing"', html)
        self.assertIn("오늘 해볼 것", html)
        self.assertIn("적용 지점을 한 줄", html)
        self.assertNotIn("linear-gradient", html)
        self.assertNotIn("box-shadow", html)

    def test_keeps_blurb_visible_and_hides_quiz_answer_until_expanded(self):
        day = dict(FALLBACK_DAY)
        day["news"] = [dict(FALLBACK_DAY["news"][0])]
        day["news"][0]["content"] = [
            {"t": "h", "text": "무슨 소식인가"},
            {"t": "p", "text": "기능의 핵심 내용이다."},
        ]
        day["quiz"] = {
            "category": "소프트웨어 공학",
            "question": "형상 관리의 목적은?",
            "options": ["변경 추적", "광고", "채용", "결제"],
            "answer": 0,
            "explain_kr": "변경 이력을 관리한다.",
        }

        html = render_post("2026-07-13", day)

        self.assertIn("새 기능을 공개했다.", html)
        self.assertIn("<details", html)
        self.assertIn("정답과 해설 보기", html)
        self.assertNotIn("class=\"digest-option is-answer\"", html)

    def test_estimates_a_short_but_nonzero_read_time(self):
        self.assertGreaterEqual(estimate_read_minutes(FALLBACK_DAY), 2)


if __name__ == "__main__":
    unittest.main()
