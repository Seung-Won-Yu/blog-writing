import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from export_tistory import (
    build_key_summary,
    build_meta_description,
    build_publish_checklist,
    build_title_candidates,
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

        self.assertNotIn("정처기 문제", post_title(day))
        self.assertIn("소프트웨어 공학", build_meta_description(day))


class EditorialReadingFlowTests(unittest.TestCase):
    def test_uses_plain_recording_voice_in_the_intro_note(self):
        html = render_post("2026-07-13", FALLBACK_DAY)

        self.assertIn("세부 내용과 최신 변경 사항은 각 원문 링크에서 다시 확인할 수 있다.", html)
        self.assertNotIn("권장합니다", html)

    def test_renders_an_in_page_reading_guide_and_source_based_author_note(self):
        day = dict(FALLBACK_DAY)
        day["news"] = [
            {
                **FALLBACK_DAY["news"][0],
                "author_note": "승원의 관점에서는 실제 설정과 권한 범위를 먼저 비교해볼 만하다.",
            },
            {
                "title_kr": "두 번째 흐름",
                "source": "공식 블로그",
                "url": "https://example.com/2",
                "author_note": "승원의 관점에서는 버전별 차이를 표로 남겨볼 만하다.",
                "content": [],
            },
        ]

        html = render_post("2026-07-13", day)

        self.assertIn("이 글에서 볼 것", html)
        self.assertIn('href="#digest-news-1"', html)
        self.assertIn('id="digest-news-1"', html)
        self.assertIn("오늘의 메인 이슈", html)
        self.assertIn("함께 볼 흐름", html)
        self.assertIn("승원의 메모 · 자료 기반 해석", html)
        self.assertIn("실제 설정과 권한 범위", html)

    def test_uses_a_specific_editorial_headline_in_search_and_the_hero(self):
        day = dict(FALLBACK_DAY)
        day["editorial"] = {
            "headline": "인스타 사진을 가져가던 AI, 반발 뒤 무엇이 멈췄나",
            "opening": "내 사진이 어디에 쓰이는지 알기 어려운 기능은 편리함보다 먼저 불안을 만든다. 오늘은 자동 연동이 멈춘 이유와 사용자가 확인할 지점을 따져본다.",
            "throughline": "개인정보와 도구 업데이트는 결국 사용자가 알고 선택할 수 있는지의 문제로 연결된다.",
            "closing": "편리함이 커질수록 동작 방식을 설명하는 기준도 함께 높아져야 한다.",
            "action": "자주 쓰는 앱 하나의 AI 데이터 설정을 확인해보자.",
        }
        day["news"] = [
            {
                "title_kr": "메타, 인스타 사진 AI 자동 연동 중단",
                "source": "AI타임스",
                "url": "https://example.com/meta",
                "blurb_kr": "사용자 반발 뒤 자동 연동을 멈춘 배경을 짚어본다.",
                "content": [],
            },
            {"title_kr": "GitHub 대시보드 업데이트", "content": []},
            {"title_kr": "Postgres 19 그래프 쿼리", "content": []},
        ]

        candidates = build_title_candidates(day)
        html = render_post("2026-07-13", day)

        self.assertEqual(post_title(day), day["editorial"]["headline"])
        self.assertEqual(candidates[0], day["editorial"]["headline"])
        self.assertFalse(any(title.startswith("2026") for title in candidates))
        self.assertNotIn("핵심 정리", " ".join(candidates))
        self.assertIn(day["editorial"]["headline"], html)
        self.assertIn("내 사진이 어디에 쓰이는지", build_meta_description(day))

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
        self.assertIn("WHY THESE STORIES", html)
        self.assertNotIn("WHY THESE THREE", html)
        self.assertIn("자동화 결과를 어떻게 확인", html)
        self.assertIn("오늘의 뉴스 1개", html)
        self.assertIn('class="digest-closing"', html)
        self.assertIn("오늘 해볼 것", html)
        self.assertIn("적용 지점을 한 줄", html)
        self.assertNotIn("linear-gradient", html)
        self.assertNotIn("box-shadow", html)

    def test_outputs_clean_fragment_with_source_date_and_reader_lane(self):
        day = dict(FALLBACK_DAY)
        day["news"] = [
            {
                **FALLBACK_DAY["news"][0],
                "published_at": "2026-07-12T16:00:00+00:00",
                "audience_lane": "broad",
                "selection_reason": "일반 독자 적합도 5",
            }
        ]

        html = render_post("2026-07-13", day)

        self.assertTrue(html.lstrip().startswith('<article class="daily-digest-post"'))
        self.assertNotIn("<!--", html)
        self.assertIn("공식 블로그 · 2026. 7. 13 · 일반 독자", html)
        self.assertIn("초안 생성에 자동화를 사용", html)

    def test_publish_checklist_requires_original_human_review(self):
        checklist = build_publish_checklist(FALLBACK_DAY)

        self.assertTrue(any("직접 확인한 내용" in item for item in checklist))
        self.assertTrue(any("내 판단" in item for item in checklist))
        self.assertTrue(any("원문" in item and "사실" in item for item in checklist))

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

    def test_marks_only_model_generated_drafts_ready_for_human_review(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("export_tistory.OUT_DIR", Path(directory)):
                write_post("2026-07-13", day=FALLBACK_DAY)
                fallback_meta = json.loads(
                    Path(directory, "2026-07-13.json").read_text(encoding="utf-8")
                )

                gemini_day = dict(FALLBACK_DAY)
                gemini_day["generation"] = {
                    "provider": "gemini",
                    "model": "gemini-3.5-flash",
                    "revision": 7,
                }
                write_post("2026-07-14", day=gemini_day)
                gemini_meta = json.loads(
                    Path(directory, "2026-07-14.json").read_text(encoding="utf-8")
                )

        self.assertEqual(fallback_meta["generation_provider"], "deterministic-fallback")
        self.assertFalse(fallback_meta["publish_ready"])
        self.assertEqual(gemini_meta["generation_provider"], "gemini")
        self.assertTrue(gemini_meta["publish_ready"])

        legacy_day = dict(FALLBACK_DAY)
        legacy_day["generation"] = {"provider": "github-models", "revision": 4}
        with tempfile.TemporaryDirectory() as directory:
            with patch("export_tistory.OUT_DIR", Path(directory)):
                write_post("2026-07-12", day=legacy_day)
            legacy_meta = json.loads(
                Path(directory, "2026-07-12.json").read_text(encoding="utf-8")
            )
        self.assertFalse(legacy_meta["publish_ready"])


if __name__ == "__main__":
    unittest.main()
