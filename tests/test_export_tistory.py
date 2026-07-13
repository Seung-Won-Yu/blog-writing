import unittest

from export_tistory import (
    build_meta_description,
    build_publish_checklist,
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


if __name__ == "__main__":
    unittest.main()
