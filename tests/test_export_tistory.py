import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from export_tistory import (
    build_key_summary,
    build_meta_description,
    build_publish_checklist,
    estimate_read_minutes,
    post_title,
    render_post,
    write_post,
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
            "throughline": "세 소식은 결국 자동화 결과를 어떻게 확인할지라는 질문으로 이어진다.",
            "closing": "결국 오래 남는 것은 결과를 판단하는 힘이다.",
            "action": "기사 하나를 골라 적용 지점을 한 줄로 적어보자.",
        }

        html = render_post("2026-07-13", day)

        self.assertIn("도구보다 검증 과정", html)
        self.assertIn('class="digest-throughline"', html)
        self.assertIn("자동화 결과를 어떻게 확인", html)
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

    def test_renders_explicit_option_numbers_matching_the_answer_number(self):
        day = dict(FALLBACK_DAY)
        day["quiz"] = {
            "category": "소프트웨어 공학",
            "question": "형상 관리의 목적은?",
            "options": ["변경 추적", "광고", "채용", "결제"],
            "answer": 2,
            "explain_kr": "산출물의 변경 이력을 관리한다.",
        }

        html = render_post("2026-07-13", day)

        for number, option in enumerate(day["quiz"]["options"], 1):
            self.assertIn(
                f'<span class="digest-option-number">{number}.</span><span>{option}</span>',
                html,
            )
        self.assertIn("<b>정답</b> 3번 · 채용", html)
        self.assertIn("list-style:none", html)
        self.assertIn('class="digest-options" role="list"', html)

    def test_estimates_a_short_but_nonzero_read_time(self):
        self.assertGreaterEqual(estimate_read_minutes(FALLBACK_DAY), 2)

    def test_hidden_quiz_explanation_does_not_inflate_read_time(self):
        day = dict(FALLBACK_DAY)
        day["quiz"] = {
            "category": "소프트웨어 개발",
            "question": "형상 관리의 목적은?",
            "options": ["변경 추적", "광고", "채용", "결제"],
            "answer": 0,
            "explain_kr": "",
        }
        without_hidden_answer = estimate_read_minutes(day)
        day["quiz"] = {**day["quiz"], "explain_kr": "숨겨진 해설 " * 500}

        self.assertEqual(estimate_read_minutes(day), without_hidden_answer)

    def test_invalid_legacy_answer_does_not_break_the_export(self):
        day = dict(FALLBACK_DAY)
        day["quiz"] = {
            "category": "소프트웨어 개발",
            "question": "형상 관리의 목적은?",
            "options": ["변경 추적", "광고", "채용", "결제"],
            "answer": "not-a-number",
            "explain_kr": "변경 이력을 관리한다.",
        }

        html = render_post("2026-07-13", day)

        self.assertIn("정답 확인 필요", html)

    def test_summary_uses_only_the_explicit_numbering(self):
        day = dict(FALLBACK_DAY)
        day["news"] = [{"title_kr": "첫 뉴스"}, {"title_kr": "두 번째 뉴스"}]

        html = render_post("2026-07-13", day)

        self.assertIn('class="digest-summary"', html)
        self.assertIn("list-style:none", html)
        self.assertIn("<li>1. 첫 뉴스</li>", html)


class EditorialImageIntegrationTests(unittest.TestCase):
    def image_day(self):
        day = dict(FALLBACK_DAY)
        day["news"] = [
            dict(FALLBACK_DAY["news"][0]),
            {
                "title_kr": "두 번째 개발 뉴스",
                "source": "GeekNews",
                "url": "https://example.com/news-2",
                "blurb_kr": "두 번째 소식의 핵심이다.",
                "content": [],
            },
        ]
        day["images"] = {
            "cover": {
                "url": "https://blog.example/assets/cover.png?a=1&b=2",
                "path": "docs/tistory/assets/2026-07-13/cover.png",
                "alt": '오늘의 대표 <이미지> "테스트"',
                "width": 1200,
                "height": 630,
            },
            "flow": {
                "url": "https://blog.example/assets/flow.png",
                "path": "docs/tistory/assets/2026-07-13/flow.png",
                "alt": "오늘의 뉴스 흐름",
                "width": 1200,
                "height": 675,
            },
            "story_1": {
                "url": "https://blog.example/assets/story-01.png",
                "path": "docs/tistory/assets/2026-07-13/story-01.png",
                "alt": "AI 개발 도구 업데이트 관련 이미지",
                "width": 1200,
                "height": 630,
            },
            "story_2": {
                "url": "https://blog.example/assets/story-02.png",
                "path": "docs/tistory/assets/2026-07-13/story-02.png",
                "alt": "두 번째 개발 뉴스 관련 이미지",
                "width": 1200,
                "height": 630,
            },
        }
        return day

    def test_places_each_generated_story_image_before_its_matching_story(self):
        html = render_post("2026-07-13", self.image_day())

        cover_index = html.index('class="digest-cover-image"')
        summary_index = html.index('class="digest-summary"')
        first_image_index = html.index("story-01.png")
        first_title_index = html.index(">AI 개발 도구 업데이트</h3>")
        second_image_index = html.index("story-02.png")
        second_title_index = html.index(">두 번째 개발 뉴스</h3>")
        self.assertLess(cover_index, summary_index)
        self.assertLess(first_image_index, first_title_index)
        self.assertLess(second_image_index, second_title_index)
        self.assertNotIn('class="digest-flow-image"', html)
        self.assertIn("cover.png?a=1&amp;b=2", html)
        self.assertIn("오늘의 대표 &lt;이미지&gt; &quot;테스트&quot;", html)
        self.assertEqual(html.count('class="digest-story-image"'), 2)
        self.assertEqual(html.count("<img"), 3)
        self.assertTrue(any("이미지" in item for item in build_publish_checklist(self.image_day())))

    def test_keeps_legacy_flow_image_when_story_images_are_absent(self):
        day = self.image_day()
        day["images"].pop("story_1")
        day["images"].pop("story_2")

        html = render_post("2026-07-13", day)

        story_index = html.index('class="digest-news-card"')
        flow_index = html.index('class="digest-flow-image"')
        self.assertLess(story_index, flow_index)

    def test_writes_generated_images_first_in_copy_page_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("export_tistory.OUT_DIR", Path(directory)):
                write_post("2026-07-13", day=self.image_day())

            meta = json.loads(Path(directory, "2026-07-13.json").read_text(encoding="utf-8"))
            self.assertEqual(
                [asset["kind"] for asset in meta["image_assets"]],
                ["cover", "story_1", "story_2", "flow"],
            )
            self.assertEqual(
                meta["image_assets"][0]["path"],
                "docs/tistory/assets/2026-07-13/cover.png",
            )
            self.assertEqual(
                (meta["image_assets"][0]["width"], meta["image_assets"][0]["height"]),
                (1200, 630),
            )


if __name__ == "__main__":
    unittest.main()
