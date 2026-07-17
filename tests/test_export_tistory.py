import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from blog_pipeline.publishing.export_tistory import (
    build_key_summary,
    build_adfit_ready_html,
    build_meta_description,
    build_publish_checklist,
    build_title_candidates,
    draft_files,
    estimate_read_minutes,
    post_title,
    render_post,
    should_preserve_published_export,
    split_post_around_first_story,
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


LEAD_DAY = {
    "schema_version": 3,
    "format": "lead-story-v1",
    "date_label": "2026. 7. 17",
    "weekday": "금",
    "primary_query": "GitHub Copilot agent mode 보안 변경",
    "tags": ["Dependabot", "GitHub", "의존성 관리"],
    "editorial": {
        "headline": "GitHub Copilot 에이전트 모드, 개발 흐름은 어떻게 바뀐나",
        "opening": "코드를 제안하던 도구가 작업 단위를 스스로 수행하는 단계로 넘어갔다.",
        "closing": "자동화 범위가 커질수록 검증 기준도 더 명확해져야 한다.",
        "action": "팀 저장소에서 에이전트가 바꿔도 되는 파일 범위를 먼저 정해보자.",
    },
    "news": [
        {
            "title_kr": "GitHub Copilot 에이전트 모드 보안 제어 강화",
            "source": "GitHub Blog",
            "url": "https://github.blog/example",
            "published_at": "2026-07-16T01:00:00+00:00",
            "blurb_kr": "자동 작업과 권한 제어의 변화를 실제 개발 흐름 기준으로 살펴봤다.",
            "references": [
                {
                    "title": "GitHub 공식 발표",
                    "url": "https://github.blog/example",
                    "kind": "official",
                },
                {
                    "title": "GitHub Docs 권한 설명",
                    "url": "https://docs.github.com/example",
                    "kind": "documentation",
                },
                {
                    "title": "보안 전문가 분석",
                    "url": "https://security.example/analysis",
                    "kind": "independent",
                },
            ],
            "content": [
                {"t": "h", "text": "정확히 무슨 일이 있었나"},
                {"t": "p", "text": "에이전트가 다룰 수 있는 작업과 확인 절차가 바뀌었다."},
                {
                    "t": "visual",
                    "image": "visual_1",
                    "caption": "요청에서 검증까지의 에이전트 작업 흐름",
                },
                {"t": "h", "text": "기존 방식과 무엇이 다른가"},
                {
                    "t": "table",
                    "caption": "코드 제안과 에이전트 모드 비교",
                    "headers": ["구분", "코드 제안", "에이전트 모드"],
                    "rows": [
                        ["작업 범위", "현재 파일", "여러 파일과 도구"],
                        ["확인 지점", "수락 전", "작업 단계별"],
                    ],
                },
                {"t": "ad_break"},
                {"t": "h", "text": "실제 팀에 무슨 의미인가"},
                {
                    "t": "code",
                    "language": "yaml",
                    "text": "cooldown:\n  default-days: 5\n  semver-major-days: 30",
                },
                {"t": "p", "text": "속도보다 수정 범위와 로그를 보는 규칙이 먼저다."},
                {
                    "t": "visual",
                    "image": "visual_2",
                    "caption": "권한·실행·검증의 세 단계",
                },
                {"t": "h", "text": "지금 확인할 것"},
                {
                    "t": "ul",
                    "items": ["작업 허용 범위", "실행 로그", "리뷰 책임자"],
                },
                {"t": "p", "text": "권한 변경은 팀에 사전 공유한다."},
                {"t": "p", "text": "문제가 생기면 되돌릴 경로도 함께 정한다."},
            ],
        }
    ],
    "related_posts": [
        {
            "title": "GitHub Actions 기초",
            "url": "https://won0322.tistory.com/120",
            "reason": "자동화 실행 단위를 함께 보기 좋다.",
        },
        {
            "title": "AI 코딩 도구 선택 기준",
            "url": "https://won0322.tistory.com/121",
            "reason": "권한과 검증 기준을 이어서 비교할 수 있다.",
        },
    ],
    "images": {
        "cover": {
            "url": "https://blog.example/cover.webp",
            "path": "docs/tistory/assets/2026-07-17/cover.webp",
            "alt": "GitHub Copilot 에이전트 모드 대표 이미지",
            "width": 1200,
            "height": 630,
        },
        "visual_1": {
            "url": "https://blog.example/visual-01.webp",
            "path": "docs/tistory/assets/2026-07-17/visual-01.webp",
            "alt": "에이전트 작업 흐름도",
            "width": 1200,
            "height": 630,
        },
        "visual_2": {
            "url": "https://blog.example/visual-02.webp",
            "path": "docs/tistory/assets/2026-07-17/visual-02.webp",
            "alt": "권한 실행 검증 도식",
            "width": 1200,
            "height": 630,
        },
    },
    "generation": {"provider": "codex-agent", "revision": 8},
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


class ExportProtectionTests(unittest.TestCase):
    def test_all_export_preserves_a_snapshot_linked_to_a_published_post(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "2026-07-13.html").write_text("수동 특집", encoding="utf-8")
            (output / "2026-07-13.json").write_text(
                json.dumps({"source_page": "https://won0322.tistory.com/121"}),
                encoding="utf-8",
            )

            self.assertTrue(
                should_preserve_published_export("2026-07-13", output_dir=output)
            )

    def test_all_export_may_rebuild_an_unpublished_draft(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "2026-07-14.html").write_text("초안", encoding="utf-8")
            (output / "2026-07-14.json").write_text(
                json.dumps({"source_page": None}), encoding="utf-8"
            )

            self.assertFalse(
                should_preserve_published_export("2026-07-14", output_dir=output)
            )


class SaturdayAutomationExportTests(unittest.TestCase):
    def test_rejects_missing_saturday_category_or_schedule(self):
        automation = copy.deepcopy(LEAD_DAY)
        automation.update(
            {
                "draft_id": "2026-07-18-automation",
                "publish_date": "2026-07-18",
                "content_type": "automation_case",
                "content_label": "업무자동화 실험",
            }
        )

        with tempfile.TemporaryDirectory() as directory, patch(
            "blog_pipeline.publishing.export_tistory.OUT_DIR", Path(directory)
        ):
            with self.assertRaisesRegex(ValueError, "category"):
                write_post("2026-07-18-automation", day=automation)
            automation["category"] = "업무자동화"
            with self.assertRaisesRegex(ValueError, "scheduled_at"):
                write_post("2026-07-18-automation", day=automation)

    def test_bulk_discovery_includes_daily_and_automation_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            daily = root / "days"
            automation = root / "automation_cases"
            daily.mkdir()
            automation.mkdir()
            (daily / "2026-07-18.json").write_text("{}", encoding="utf-8")
            (automation / "2026-07-18.json").write_text("{}", encoding="utf-8")

            discovered = draft_files(daily, automation)

        self.assertEqual(
            [(identity.draft_id, path.name) for identity, path in discovered],
            [
                ("2026-07-18", "2026-07-18.json"),
                ("2026-07-18-automation", "2026-07-18.json"),
            ],
        )

    def test_exports_a_second_saturday_draft_without_overwriting_daily_news(self):
        automation = copy.deepcopy(LEAD_DAY)
        automation.update(
            {
                "draft_id": "2026-07-18-automation",
                "content_type": "automation_case",
                "content_label": "업무자동화 실험",
                "publish_date": "2026-07-18",
                "scheduled_at": "2026-07-18T18:00:00+09:00",
                "category": "업무자동화",
            }
        )
        automation["editorial"]["headline"] = (
            "GitHub Actions로 반복 보고서 자동화해 본 과정"
        )
        for kind, asset in automation["images"].items():
            filename = "cover.webp" if kind == "cover" else kind.replace("_", "-") + ".webp"
            asset["path"] = (
                "docs/tistory/assets/2026-07-18-automation/" + filename
            )
            asset["url"] = (
                "https://blog.example/assets/2026-07-18-automation/" + filename
            )

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with patch(
                "blog_pipeline.publishing.export_tistory.OUT_DIR", output
            ):
                write_post("2026-07-18", day=copy.deepcopy(LEAD_DAY))
                daily_before = {
                    path.name: path.read_bytes()
                    for path in output.glob("2026-07-18*")
                }
                write_post(
                    "2026-07-18-automation",
                    day=automation,
                )
                daily_after = {
                    name: (output / name).read_bytes() for name in daily_before
                }

            meta = json.loads(
                (output / "2026-07-18-automation.json").read_text(encoding="utf-8")
            )
            body = (output / "2026-07-18-automation.html").read_text(
                encoding="utf-8"
            )

        self.assertEqual(meta["draft_id"], "2026-07-18-automation")
        self.assertEqual(meta["publish_date"], "2026-07-18")
        self.assertEqual(meta["content_type"], "automation_case")
        self.assertEqual(meta["content_label"], "업무자동화 실험")
        self.assertEqual(meta["scheduled_at"], "2026-07-18T18:00:00+09:00")
        self.assertEqual(meta["category"], "업무자동화")
        self.assertEqual(meta["source"], "data/automation_cases/2026-07-18.json")
        self.assertEqual(daily_after, daily_before)
        self.assertTrue(
            all(
                asset["path"].startswith(
                    "docs/tistory/assets/2026-07-18-automation/"
                )
                for asset in meta["image_assets"]
            )
        )
        self.assertIn("업무자동화 실험", body)
        self.assertNotIn("오늘의 핵심뉴스", body)
        self.assertTrue(meta["publish_ready"])


class EditorialReadingFlowTests(unittest.TestCase):
    def test_renders_one_deep_story_with_variable_visuals_table_and_related_posts(self):
        html = render_post("2026-07-17", LEAD_DAY)

        self.assertIn('data-digest-version="3"', html)
        self.assertEqual(html.count('class="digest-news-card digest-lead-story"'), 1)
        self.assertIn("오늘의 핵심뉴스", html)
        self.assertIn('class="digest-data-table"', html)
        self.assertIn("코드 제안과 에이전트 모드 비교", html)
        self.assertIn('class="digest-code-block language-yaml"', html)
        self.assertIn("semver-major-days: 30", html)
        self.assertIn("visual-01.webp", html)
        self.assertIn("visual-02.webp", html)
        self.assertEqual(html.count('class="digest-content-image"'), 2)
        self.assertIn('class="digest-related-posts"', html)
        self.assertIn('href="https://won0322.tistory.com/120"', html)
        self.assertIn('href="https://won0322.tistory.com/121"', html)
        self.assertIn('class="digest-reference-list"', html)
        self.assertIn("<span>공식</span>", html)
        self.assertIn("<span>공식 문서</span>", html)
        self.assertNotIn("<span>official</span>", html)
        self.assertNotIn("세 소식을 함께 보면", html)
        self.assertNotIn("글 순서", html)
        self.assertNotIn("오늘의 정처기 문제", html)
        self.assertNotIn("오늘의 IT · 개발 · 기획 용어", html)

    def test_deep_links_ignore_non_http_reference_and_related_urls(self):
        day = copy.deepcopy(LEAD_DAY)
        day["news"][0]["references"].append(
            {"title": "실행 링크", "url": "javascript:alert(1)", "kind": "bad"}
        )
        day["related_posts"].append(
            {"title": "위험한 관련 글", "url": "data:text/html,bad"}
        )

        html = render_post("2026-07-17", day)

        self.assertNotIn("javascript:", html)
        self.assertNotIn("data:text/html", html)
        self.assertNotIn("실행 링크", html)
        self.assertNotIn("위험한 관련 글", html)

    def test_places_one_adfit_marker_at_the_explicit_deep_story_break(self):
        post_html = render_post("2026-07-17", LEAD_DAY)
        html = build_adfit_ready_html(post_html)

        before = html.index("기존 방식과 무엇이 다른가")
        adfit = html.index('data-ad-vendor="adfit"')
        after = html.index("실제 팀에 무슨 의미인가")
        self.assertLess(before, adfit)
        self.assertLess(adfit, after)
        self.assertEqual(html.count('data-ad-vendor="adfit"'), 1)
        self.assertNotIn("data-digest-ad-break", html)

        before_ad, after_ad = split_post_around_first_story(post_html)
        self.assertIn("기존 방식과 무엇이 다른가", before_ad)
        self.assertNotIn("실제 팀에 무슨 의미인가", before_ad)
        self.assertIn("실제 팀에 무슨 의미인가", after_ad)
        self.assertNotIn("data-digest-ad-break", before_ad + after_ad)

    def test_splits_copy_ready_html_into_valid_before_and_after_ad_fragments(self):
        day = dict(FALLBACK_DAY)
        day["news"] = [
            {"title_kr": "첫 뉴스", "content": []},
            {"title_kr": "둘째 뉴스", "content": []},
            {"title_kr": "셋째 뉴스", "content": []},
        ]

        before_ad, after_ad = split_post_around_first_story(
            render_post("2026-07-13", day)
        )

        self.assertIn("첫 뉴스", before_ad)
        self.assertNotIn('id="digest-news-2"', before_ad)
        self.assertTrue(before_ad.rstrip().endswith("</article>"))
        self.assertNotIn('id="digest-news-1"', after_ad)
        self.assertIn("둘째 뉴스", after_ad)
        self.assertIn("셋째 뉴스", after_ad)
        self.assertTrue(
            after_ad.lstrip().startswith(
                '<div class="daily-digest-continuation daily-digest-post"'
            )
        )
        self.assertTrue(after_ad.rstrip().endswith("</div>"))

    def test_builds_one_paste_html_with_adfit_between_first_and_second_story(self):
        day = dict(FALLBACK_DAY)
        day["news"] = [
            {"title_kr": "첫 뉴스", "content": []},
            {"title_kr": "둘째 뉴스", "content": []},
        ]

        html = build_adfit_ready_html(render_post("2026-07-13", day))

        first_end = html.index("</section>", html.index('id="digest-news-1"'))
        adfit = html.index('data-ad-vendor="adfit"')
        second = html.index('id="digest-news-2"')
        self.assertLess(first_end, adfit)
        self.assertLess(adfit, second)
        self.assertLess(second, html.rindex("</article>"))
        self.assertEqual(html.count('data-ad-vendor="adfit"'), 1)

    def test_uses_plain_recording_voice_in_the_intro_note(self):
        html = render_post("2026-07-13", FALLBACK_DAY)

        self.assertIn('class="digest-lead"', html)
        self.assertNotIn("확인한 사실과 의미, 직접 살펴볼 지점을 차례로 정리했다.", html)
        self.assertNotIn("digest-meta-intro", html)
        self.assertNotIn("권장합니다", html)

    def test_renders_an_in_page_reading_guide_without_internal_editor_notes(self):
        day = dict(FALLBACK_DAY)
        day["news"] = [
            {
                **FALLBACK_DAY["news"][0],
                "author_note": "개발자 관점에서는 실제 설정과 권한 범위를 먼저 비교해볼 만하다.",
            },
            {
                "title_kr": "두 번째 흐름",
                "source": "공식 블로그",
                "url": "https://example.com/2",
                "author_note": "개발자 관점에서는 버전별 차이를 표로 남겨볼 만하다.",
                "content": [],
            },
        ]

        html = render_post("2026-07-13", day)

        self.assertIn("글 순서", html)
        self.assertIn('href="#digest-news-1"', html)
        self.assertIn('id="digest-news-1"', html)
        self.assertIn("NEWS 01", html)
        self.assertIn("NEWS 02", html)
        self.assertNotIn("오늘의 메인 이슈", html)
        self.assertNotIn("함께 볼 흐름", html)
        self.assertNotIn("digest-author-note", html)
        self.assertNotIn("개발자 편집자의 체크포인트", html)
        self.assertNotIn("승원의 메모", html)
        self.assertNotIn("실제 설정과 권한 범위", html)

    def test_uses_a_specific_editorial_headline_for_publish_metadata_without_body_duplication(self):
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
        self.assertNotIn(day["editorial"]["headline"], html)
        self.assertNotIn('class="digest-title"', html)
        self.assertIn('data-digest-version="2"', html)
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
        self.assertIn("세 소식을 함께 보면", html)
        self.assertNotIn("WHY THESE STORIES", html)
        self.assertIn("자동화 결과를 어떻게 확인", html)
        self.assertIn("오늘 고른 뉴스", html)
        self.assertIn('class="digest-closing"', html)
        self.assertIn("직접 확인해보려면", html)
        self.assertNotIn("CLOSING NOTE", html)
        self.assertNotIn("오늘의 메모", html)
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
        self.assertIn("NEWS 01 · 공식 블로그 · 2026. 7. 13", html)
        self.assertNotIn("일반 독자", html)
        self.assertNotIn("초안 생성에 자동화를 사용", html)
        self.assertNotIn('class="digest-note"', html)

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
        self.assertIn('class="digest-options" role="list"', html)
        self.assertNotIn("style=", html)

    def test_estimates_a_short_but_nonzero_read_time(self):
        self.assertGreaterEqual(estimate_read_minutes(FALLBACK_DAY), 2)

    def test_deep_read_time_counts_tables_lists_captions_and_code(self):
        day = {
            "editorial": {},
            "news": [
                {
                    "content": [
                        {"t": "ul", "items": ["가" * 900, "나" * 900]},
                        {
                            "t": "table",
                            "caption": "비교표 " * 150,
                            "headers": ["항목", "설명"],
                            "rows": [["조건", "다" * 900]],
                        },
                        {"t": "visual", "caption": "라" * 450},
                        {"t": "code", "text": "마" * 450},
                    ]
                }
            ],
        }

        self.assertGreaterEqual(estimate_read_minutes(day), 9)

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

    def test_body_uses_one_reading_guide_instead_of_duplicate_summary(self):
        day = dict(FALLBACK_DAY)
        day["news"] = [{"title_kr": "첫 뉴스"}, {"title_kr": "두 번째 뉴스"}]

        html = render_post("2026-07-13", day)

        self.assertNotIn('class="digest-summary"', html)
        self.assertEqual(html.count('class="digest-reading-guide"'), 1)
        self.assertIn('<span class="digest-reading-index">01</span>첫 뉴스', html)


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
        guide_index = html.index('class="digest-reading-guide"')
        first_image_index = html.index("story-01.png")
        first_title_index = html.index(">AI 개발 도구 업데이트</h3>")
        second_image_index = html.index("story-02.png")
        second_title_index = html.index(">두 번째 개발 뉴스</h3>")
        self.assertLess(cover_index, guide_index)
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

    def test_structural_sections_are_class_only_and_do_not_embed_competing_styles(self):
        html = render_post("2026-07-13", self.image_day())

        self.assertIn('class="daily-digest-post" data-digest-version="2"', html)
        self.assertIn('class="digest-news-card"', html)
        self.assertIn('class="digest-news-copy"', html)
        self.assertIn('class="digest-hero" aria-label="글 소개"', html)
        self.assertIn('class="digest-reading-guide"', html)
        self.assertNotIn('style="', html)
        self.assertNotIn("<style", html.lower())
        self.assertNotIn('class="digest-title"', html)
        self.assertNotIn('class="digest-summary"', html)

    def test_reading_guide_is_compact_and_does_not_repeat_landing_page_headings(self):
        html = render_post("2026-07-13", self.image_day())

        guide = html[html.index('class="digest-reading-guide"') : html.index("</nav>")]
        self.assertIn("글 순서", guide)
        self.assertNotIn("READING GUIDE", guide)
        self.assertNotIn("<h2", guide)
        self.assertIn('<span class="digest-reading-index">01</span>', guide)
        self.assertIn('role="list"', guide)
        self.assertIn('role="listitem"', guide)
        self.assertNotIn("style=", guide)
        self.assertNotIn("<ol", guide)
        self.assertNotIn("<li", guide)

    def test_terms_and_quiz_are_structural_components_without_inline_gutters(self):
        day = self.image_day()
        day["terms"] = [
            {"term": "회귀 테스트", "kind": "개발", "meaning_kr": "변경 뒤 기존 기능을 확인한다."}
        ]

        html = render_post("2026-07-13", day)

        self.assertIn('class="digest-terms"', html)
        self.assertNotIn("style=", html)

    def test_writes_generated_images_first_in_copy_page_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("blog_pipeline.publishing.export_tistory.OUT_DIR", Path(directory)):
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
            self.assertTrue(Path(directory, "2026-07-13-before-ad.html").is_file())
            self.assertTrue(Path(directory, "2026-07-13-after-ad.html").is_file())
            self.assertTrue(Path(directory, "2026-07-13-adfit.html").is_file())
            self.assertEqual(meta["before_ad_html"], "docs/tistory/2026-07-13-before-ad.html")
            self.assertEqual(meta["after_ad_html"], "docs/tistory/2026-07-13-after-ad.html")
            self.assertEqual(meta["adfit_html"], "docs/tistory/2026-07-13-adfit.html")

    def test_writes_every_declared_deep_story_visual_to_copy_metadata(self):
        day = json.loads(json.dumps(LEAD_DAY))
        day["images"]["visual_3"] = {
            "url": "https://blog.example/visual-03.webp",
            "path": "docs/tistory/assets/2026-07-17/visual-03.webp",
            "alt": "추가 비교 차트",
            "width": 1200,
            "height": 630,
        }
        with tempfile.TemporaryDirectory() as directory:
            with patch("blog_pipeline.publishing.export_tistory.OUT_DIR", Path(directory)):
                write_post("2026-07-17", day=day)

            meta = json.loads(Path(directory, "2026-07-17.json").read_text(encoding="utf-8"))

        self.assertEqual(
            [asset["kind"] for asset in meta["image_assets"]],
            ["cover", "visual_1", "visual_2", "visual_3"],
        )
        self.assertEqual(meta["tags"], LEAD_DAY["tags"])
        self.assertFalse(any("관련된 정처기" in item for item in meta["publish_checklist"]))

    def test_marks_only_model_generated_drafts_ready_for_human_review(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("blog_pipeline.publishing.export_tistory.OUT_DIR", Path(directory)):
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

                codex_day = dict(FALLBACK_DAY)
                codex_day["generation"] = {
                    "provider": "codex-agent",
                    "model": "gpt-5.6-terra",
                    "revision": 7,
                }
                write_post("2026-07-15", day=codex_day)
                codex_meta = json.loads(
                    Path(directory, "2026-07-15.json").read_text(encoding="utf-8")
                )

        self.assertEqual(fallback_meta["generation_provider"], "deterministic-fallback")
        self.assertFalse(fallback_meta["publish_ready"])
        self.assertEqual(gemini_meta["generation_provider"], "gemini")
        self.assertTrue(gemini_meta["publish_ready"])
        self.assertEqual(codex_meta["generation_provider"], "codex-agent")
        self.assertTrue(codex_meta["publish_ready"])

        legacy_day = dict(FALLBACK_DAY)
        legacy_day["generation"] = {"provider": "github-models", "revision": 4}
        with tempfile.TemporaryDirectory() as directory:
            with patch("blog_pipeline.publishing.export_tistory.OUT_DIR", Path(directory)):
                write_post("2026-07-12", day=legacy_day)
            legacy_meta = json.loads(
                Path(directory, "2026-07-12.json").read_text(encoding="utf-8")
            )
        self.assertFalse(legacy_meta["publish_ready"])


if __name__ == "__main__":
    unittest.main()
