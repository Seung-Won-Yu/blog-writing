import copy
import math
import unittest
from datetime import date, timedelta

from blog_pipeline.publishing.draft_identity import (
    category_for_content_type,
    resolve_draft_identity,
)
from blog_pipeline.publishing.editorial_quality import (
    estimate_read_minutes,
    measurement_digest,
    source_quality_reasons,
)


def repeated_text(label, count=80):
    return " ".join(
        f"{label} {index + 1}번째 조건에서 독자가 확인할 실제 결과와 예외, 다음 행동을 구체적으로 설명한다."
        for index in range(count)
    )


IMAGEGEN_PROMPT = "실제 제품의 변경 전후와 사용자가 확인할 결과를 한 장면에 보여 주는 한국어 설명 이미지"


def visual_asset(
    origin="imagegen",
    evidence_type="diagram",
    label="변화가 실제 사용 흐름에 미치는 영향",
):
    asset = {
        "label": label,
        "scene_label": ["변경 전", "변경 후"],
        "steps": "변경 전 상태 → 바뀐 조건 → 독자가 확인할 결과",
        "curiosity_hook": "어느 단계에서 결과가 달라질까?",
        "evidence_type": evidence_type,
        "logic_type": "comparison",
        "origin": origin,
        "content_role": "explanation",
        "qa": {
            "topic_match": True,
            "caption_match": True,
            "mobile_readable": True,
            "text_reviewed": True,
            "not_generic": True,
        },
    }
    if origin == "imagegen":
        asset.update(
            {
                "generation_prompt": IMAGEGEN_PROMPT,
                "generation_model": "gpt-image",
                "korean_labels": ["변경 전", "변경 후", "확인 결과"],
            }
        )
    else:
        asset.update(
            {
                "capture_note": "테스트 환경에서 직접 캡처하고 개인 정보와 로컬 경로를 가렸다.",
                "capture_tool": "playwright",
                "capture_target": "로컬 테스트 결과 화면",
                "captured_at": "2026-07-24T18:10:00+09:00",
            }
        )
    return asset


def image_asset(origin="imagegen"):
    asset = {
        "origin": origin,
        "alt": "변경 전후 조건과 독자가 확인할 실제 결과를 비교한 한국어 설명 이미지",
        "sha256": "a" * 64,
        "qa": {
            "topic_match": True,
            "caption_match": True,
            "mobile_readable": True,
            "text_reviewed": True,
            "not_generic": True,
        },
    }
    if origin == "imagegen":
        asset.update(
            {
                "generation_prompt": IMAGEGEN_PROMPT,
                "generation_model": "gpt-image",
            }
        )
    elif origin in {"capture", "annotated_capture"}:
        asset.update(
            {
                "capture_tool": "playwright",
                "capture_target": "로컬 테스트 결과 화면",
                "captured_at": "2026-07-24T18:10:00+09:00",
                "capture_sha256": "a" * 64,
            }
        )
    return asset


def valid_daily_source(day="2026-07-19"):
    publish_day = date.fromisoformat(day)
    decision_coverage = "decision" if publish_day >= date(2026, 8, 4) else "checklist"
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    first_visual = visual_asset(label="기존 방식과 새 방식의 조건 차이")
    second_visual = visual_asset(label="설정에서 결과를 확인하는 실제 순서")
    content = [
        {"t": "h", "text": "무엇이 바뀌었나"},
        {"t": "p", "text": repeated_text("확인된 변화", 22)},
        {"t": "visual", "image": "visual_1", "caption": "변경 전후의 조건과 독자가 실제로 확인할 차이를 한눈에 비교한다."},
        {"t": "h", "text": "왜 이런 변화가 생겼나"},
        {"t": "p", "text": repeated_text("작동 원리", 20)},
        {"t": "table", "caption": "기존 방식과 바뀐 방식 비교", "headers": ["구분", "기존", "변경"], "rows": [["조건", "이전 조건", "새 조건"], ["확인", "이전 신호", "새 신호"]]},
        {"t": "ad_break"},
        {"t": "h", "text": "실제로 확인하는 방법"},
        {"t": "p", "text": repeated_text("확인 절차", 20)},
        {"t": "visual", "image": "visual_2", "caption": "공식 문서에서 확인한 적용 조건과 결과 신호를 순서대로 보여 준다."},
        {"t": "h", "text": "적용 범위와 남는 한계"},
        {"t": "p", "text": repeated_text("적용 한계", 16)},
        {"t": "h", "text": "지금 확인할 체크리스트"},
        {"t": "ul", "items": ["내 환경이 적용 대상인지 확인한다.", "변경 전 값을 기록한다.", "결과 신호와 실패 조건을 함께 확인한다."]},
        {"t": "p", "text": repeated_text("실패 조건", 10)},
        {"t": "p", "text": repeated_text("다음 행동", 10)},
    ]
    source = {
        "schema_version": 3,
        "format": "lead-story-v1",
        "draft_id": day,
        "publish_date": day,
        "date_label": f"{publish_day.year}. {publish_day.month}. {publish_day.day}",
        "weekday": weekdays[publish_day.weekday()],
        "content_type": "daily_news",
        "content_label": "뉴스 심층글",
        "category": category_for_content_type("daily_news", day),
        "scheduled_at": f"{day}T09:00:00+09:00",
        "primary_query": "일반 사용자가 확인할 최신 기능 변경과 적용 조건",
        "tags": ["기능 변경", "사용 방법", "적용 조건", "업데이트", "체크리스트"],
        "editorial": {
            "headline": "새 기능 업데이트, 일반 사용자가 먼저 확인할 적용 조건과 바뀐 점",
            "opening": repeated_text("구체적인 사용 장면", 5),
            "closing": repeated_text("남는 판단 기준", 4),
            "action": "오늘 사용하는 설정에서 적용 대상과 결과 신호를 한 번 확인한다.",
            "audience_problem": "업데이트 소식은 들었지만 내 계정에 언제 적용되고 무엇을 확인해야 하는지 알기 어렵다.",
            "reader_takeaway": "적용 대상, 바뀐 흐름, 확인 신호와 실패 시 되돌릴 기준까지 한 번에 판단할 수 있다.",
            "why_now": "공식 배포가 시작됐고 계정별 적용 시점과 기존 설정의 우선순위가 달라 지금 확인이 필요하다.",
            "topic_key": "user-facing-update-conditions",
            "reader_question": "이번 변경이 내 사용 흐름에서 무엇을 바꾸고 어디서 확인할 수 있을까?",
            "entities": ["Example Product"],
            "coverage": ["change", "mechanism", "comparison", "application", "limits", decision_coverage],
        },
        "visual": {
            "cover": {
                "label": "업데이트 전 막힌 장면과 적용 뒤 얻는 결과",
                "scene_label": ["막힌 사용 흐름", "확인 가능한 결과"],
                "steps": "독자가 겪는 문제 → 새 기능 적용 뒤 달라지는 결과",
                "curiosity_hook": "이 변경이 지금 해결하는 불편은 무엇일까?",
                "logic_type": "before_after",
                "content_role": "hook",
                "cover_kind": "editorial_scene",
                "art_direction": "editorial_scenario",
                "composition_type": "asymmetric_single_scene",
                "palette_family": "cobalt_coral_paper",
                "render_family": "editorial_collage",
            },
            "assets": [first_visual, second_visual],
        },
        "generation": {
            "provider": "codex-agent",
            "model": "gpt-5.6",
            "revision": 7,
            "image_provider": "codex-imagegen",
            "image_policy": "webp-v1",
        },
        "images": {
            "cover": {
                **image_asset(),
                "generation_prompt": (
                    "Use case: illustration-story. "
                    "Asset intent: editorial-scene. 실제 사용자가 변경 전후의 "
                    "결과를 한 장면에서 발견하는 한국어 편집 일러스트"
                ),
                "cover_kind": "editorial_scene",
                "art_direction": "editorial_scenario",
                "composition_type": "asymmetric_single_scene",
                "palette_family": "cobalt_coral_paper",
                "render_family": "editorial_collage",
            },
            "visual_1": image_asset(),
            "visual_2": image_asset(),
        },
        "news": [
            {
                "title_kr": "일반 사용자가 확인할 새 기능 변경",
                "source": "공식 발표",
                "url": "https://example.com/announcement",
                "published_at": f"{(publish_day - timedelta(days=1)).isoformat()}T22:00:00+09:00",
                "blurb_kr": "새 기능의 적용 범위와 확인 방법이 공식 발표됐다.",
                "references": [
                    {"kind": "official", "title": "공식 발표", "url": "https://example.com/announcement"},
                    {"kind": "documentation", "title": "공식 설정 문서", "url": "https://docs.example.com/settings"},
                    {"kind": "independent", "title": "독립 분석", "url": "https://analysis.example.net/story"},
                ],
                "content": content,
            }
        ],
        "related_posts": [
            {"title": "관련 글 1", "url": "https://won0322.tistory.com/120", "reason": "설정 확인 기준을 이어서 볼 수 있다."},
            {"title": "관련 글 2", "url": "https://won0322.tistory.com/121", "reason": "업데이트 적용 전후 점검법을 연결해 볼 수 있다."},
        ],
    }
    if publish_day >= date(2026, 8, 4):
        source["editorial"].update(
            {
                "article_shape": "decision_guide",
                "revisit": {
                    "quick_answer": "변경의 핵심과 내 환경의 적용 여부를 먼저 판단한다.",
                    "reuse_case": "설정 전에 판단표를 복사해 현재 값과 목표 값을 기록한다.",
                    "failure_case": "적용 결과가 다르면 실패 조건과 되돌리기 순서부터 확인한다.",
                    "artifact_type": "decision_matrix",
                    "update_triggers": ["공식 기본값 변경", "지원 버전 변경"],
                },
            }
        )
        reusable = next(
            block for block in source["news"][0]["content"] if block.get("t") == "table"
        )
        reusable.update(
            {"reusable": True, "reuse_label": "적용 전후 판단표"}
        )
    if publish_day >= date(2026, 8, 11):
        source["primary_query"] = "새 기능 적용 조건과 확인 방법"
        source["editorial"]["headline"] = "새 기능 적용 조건: 일반 사용자가 먼저 확인할 바뀐 점"
        source["editorial"]["search_intent"] = {
            "query": "새 기능 적용 조건",
            "reader_need": "내 계정에 기능이 적용되는 조건과 확인 위치를 알고 싶다.",
            "answer_format": "적용 조건 비교와 확인 순서를 함께 보여 준다.",
        }
        source["related_posts"][0]["role"] = "foundation"
        source["related_posts"][1]["role"] = "next_step"
    return source


def valid_automation_source(day="2026-07-25"):
    source = valid_daily_source(day)
    cover_image = copy.deepcopy(source["images"]["cover"])
    source.update(
        {
            "draft_id": f"{day}-automation",
            "content_type": "automation_case",
            "content_label": "업무자동화 실험",
            "category": category_for_content_type("automation_case", day),
            "scheduled_at": f"{day}T18:00:00+09:00",
            "primary_query": "메일 첨부파일을 날짜별 폴더로 자동 정리하기",
            "tags": ["업무자동화", "메일 정리", "파일 정리", "반복 업무", "따라하기"],
        }
    )
    source["editorial"].update(
        {
            "headline": "메일 첨부파일을 날짜별로 자동 정리하는 방법: Python 실험",
            "topic_key": "email-attachment-folder-automation",
            "reader_question": "반복해서 내려받는 메일 첨부파일을 날짜별 폴더에 안전하게 자동 정리할 수 있을까?",
            "entities": ["Python"],
            "coverage": ["problem", "setup", "implementation", "evidence", "comparison", "failure", "rollback"],
        }
    )
    if date.fromisoformat(day) >= date(2026, 8, 11):
        source["editorial"]["search_intent"] = {
            "query": "메일 첨부파일",
            "reader_need": "반복해서 내려받는 첨부파일을 날짜별 폴더로 자동 분류하고 싶다.",
            "answer_format": "실행 코드와 성공·실패 결과 화면으로 검증한다.",
        }
    source["visual"]["assets"] = [
        visual_asset("capture", "screenshot", "자동화 실행 전 실제 입력 화면"),
        visual_asset("imagegen", "diagram", "입력부터 분류까지의 자동 처리 흐름"),
        visual_asset("annotated_capture", "screenshot", "성공과 예외가 나뉜 실제 실행 결과"),
    ]
    source["images"] = {
        "cover": cover_image,
        "visual_1": image_asset("capture"),
        "visual_2": image_asset("imagegen"),
        "visual_3": image_asset("annotated_capture"),
    }
    capture_time = f"{(date.fromisoformat(day) - timedelta(days=1)).isoformat()}T18:10:00+09:00"
    for index in (1, 3):
        source["visual"]["assets"][index - 1]["captured_at"] = capture_time
        source["images"][f"visual_{index}"]["captured_at"] = capture_time
    source["generation"]["image_provider"] = "mixed"
    source["verification"] = {
        "mode": "executed",
        "started_at": f"{(date.fromisoformat(day) - timedelta(days=1)).isoformat()}T18:00:00+09:00",
        "completed_at": f"{(date.fromisoformat(day) - timedelta(days=1)).isoformat()}T18:12:00+09:00",
        "command_exit_code": 0,
        "stdout_excerpt": "3개 파일 처리 완료, 1개 잘못된 날짜 형식은 오류 목록으로 분류됨",
        "environment": {
            "os": "macOS",
            "runtime": "Python 3.12",
            "tool_version": "Python 3.12.4",
            "source_revision": "CPython 3.12 documentation",
        },
        "commands": ["python3 automation_demo.py"],
        "input_fixture": "개인정보가 없는 테스트 메일 첨부파일 3개",
        "expected": "세 파일이 날짜별 폴더 두 곳으로 이동한다.",
        "actual": "세 파일이 예상한 폴더로 이동했고 파일명과 개수가 일치했다.",
        "failure": "잘못된 날짜 형식 한 건은 이동하지 않고 오류 목록에 남았다.",
        "rollback": "테스트 출력 폴더를 지우고 원본 fixture를 다시 복사한다.",
        "evidence_files": ["visual_1", "visual_3"],
        "problem_lane": "이메일·문서",
        "tool_brand": "Python",
    }
    source["news"][0]["content"].extend(
        [
            {"t": "h", "text": "실패한 입력과 복구 방법"},
            {"t": "code", "language": "bash", "text": "python3 automation_demo.py --fixture ./sample"},
            {"t": "visual", "image": "visual_3", "caption": "실제 실행 결과에서 성공한 파일과 오류로 남은 입력을 함께 확인한다."},
            {"t": "p", "text": repeated_text("실패와 복구", 20)},
        ]
    )
    content = source["news"][0]["content"]
    ad = next(block for block in content if block.get("t") == "ad_break")
    ad_index = content.index(ad)
    content.insert(
        ad_index,
        {"t": "p", "text": "구현에 들어가기 전 입력과 기대 결과를 한 번 더 확인한다."},
    )
    return source


def valid_guide_source(day="2026-07-22"):
    source = valid_daily_source(day)
    source.update(
        {
            "draft_id": f"{day}-guide",
            "content_type": "evergreen_guide",
            "content_label": "개발 가이드",
            "category": category_for_content_type("evergreen_guide", day),
            "publication_mode": "scheduled",
            "scheduled_at": f"{day}T18:00:00+09:00",
            "primary_query": "2026 백엔드 개발자 로드맵 Java Spring DB Docker 공부 순서",
            "tags": ["백엔드 개발자", "백엔드 로드맵", "Java", "Spring Boot", "PostgreSQL"],
        }
    )
    source["editorial"].update(
        {
            "headline": "2026 백엔드 개발자 로드맵: Java·Spring·PostgreSQL 공부 순서",
            "topic_key": "backend-developer-roadmap-2026",
            "reader_question": "백엔드 개발자가 되려면 2026년에는 어떤 기술을 어떤 순서로 공부해야 할까?",
            "entities": ["Java 25", "Spring Boot 4", "PostgreSQL 18"],
            "coverage": ["foundation", "request_flow", "stack", "data", "security", "operations", "plan"],
        }
    )
    if date.fromisoformat(day) >= date(2026, 8, 11):
        source["editorial"]["search_intent"] = {
            "query": "백엔드 개발자 로드맵",
            "reader_need": "백엔드 공부를 어떤 기술과 프로젝트 순서로 시작할지 알고 싶다.",
            "answer_format": "기술 선택표와 12주 학습 순서를 함께 제공한다.",
        }
    source["visual"]["assets"].append(
        visual_asset(label="12주 동안 기술을 쌓는 단계별 학습 순서")
    )
    source["images"]["visual_3"] = image_asset()
    content = source["news"][0]["content"]
    content.extend(
        [
            {"t": "h", "text": "12주 학습 계획"},
            {"t": "visual", "image": "visual_3", "caption": "기초부터 배포와 관측까지 이어지는 12주 학습 순서"},
            {"t": "p", "text": repeated_text("학습 계획", 16)},
        ]
    )
    ad = next(block for block in content if block.get("t") == "ad_break")
    ad_index = content.index(ad)
    content.insert(
        ad_index,
        {"t": "p", "text": "학습 순서를 고르기 전 현재 수준과 완성할 결과를 먼저 적는다."},
    )
    source["news"][0].update(
        {
            "source": "백엔드 로드맵 참고 자료",
            "url": "https://roadmap.sh/backend",
            "published_at": f"{(date.fromisoformat(day) - timedelta(days=2)).isoformat()}T12:00:00+09:00",
        }
    )
    return source


class EditorialQualityTests(unittest.TestCase):
    def test_all_future_content_lanes_satisfy_new_contract(self):
        cases = [
            ("2026-08-04", valid_daily_source("2026-08-04")),
            ("2026-08-05-guide", valid_guide_source("2026-08-05")),
            ("2026-08-08-automation", valid_automation_source("2026-08-08")),
        ]
        for draft_id, source in cases:
            with self.subTest(draft_id=draft_id):
                self.assertEqual(
                    source_quality_reasons(
                        source, resolve_draft_identity(draft_id)
                    ),
                    [],
                )

    def test_future_cover_requires_a_declared_render_family(self):
        source = valid_daily_source("2026-08-04")
        source["visual"]["cover"].pop("render_family")

        self.assertIn(
            "quality_visual_variety",
            source_quality_reasons(
                source, resolve_draft_identity("2026-08-04")
            ),
        )

    def test_hands_on_article_requires_real_visual_evidence(self):
        source = valid_daily_source("2026-08-04")
        source["editorial"]["article_shape"] = "hands_on_test"
        source["visual"]["assets"].append(
            visual_asset(label="실행 결과에서 성공과 실패를 구분하는 신호")
        )
        source["images"]["visual_3"] = image_asset()
        source["news"][0]["content"].insert(
            -1,
            {
                "t": "visual",
                "image": "visual_3",
                "caption": "실행 결과에서 성공과 실패를 가르는 신호를 보여 준다.",
            },
        )

        self.assertIn(
            "quality_visual_evidence",
            source_quality_reasons(
                source, resolve_draft_identity("2026-08-04")
            ),
        )

    def test_incident_trace_requires_real_visual_evidence(self):
        source = valid_daily_source("2026-08-04")
        source["editorial"]["article_shape"] = "incident_trace"

        self.assertIn(
            "quality_visual_evidence",
            source_quality_reasons(
                source, resolve_draft_identity("2026-08-04")
            ),
        )

        source["visual"]["assets"][0] = visual_asset(
            origin="capture",
            evidence_type="official_screen",
            label="공식 사고 공지에서 확인한 영향 범위",
        )
        source["images"]["visual_1"] = image_asset(origin="capture")
        source["generation"]["image_provider"] = "mixed"

        self.assertNotIn(
            "quality_visual_evidence",
            source_quality_reasons(
                source, resolve_draft_identity("2026-08-04")
            ),
        )

    def test_future_article_requires_revisit_value_contract(self):
        source = valid_daily_source("2026-08-04")
        self.assertNotIn(
            "quality_revisit_value",
            source_quality_reasons(
                source, resolve_draft_identity("2026-08-04")
            ),
        )

        del source["editorial"]["revisit"]
        self.assertIn(
            "quality_revisit_value",
            source_quality_reasons(
                source, resolve_draft_identity("2026-08-04")
            ),
        )

    def test_future_article_rejects_internal_revisit_labels_in_visible_copy(self):
        source = valid_daily_source("2026-08-04")
        source["news"][0]["content"][0]["text"] = "다시 찾을 때 · 점검표"

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-08-04")
        )

        self.assertIn("quality_natural_voice", reasons)

    def test_future_daily_allows_no_reusable_block_but_rejects_multiple(self):
        source = valid_daily_source("2026-08-04")
        reusable = next(
            block for block in source["news"][0]["content"] if block.get("reusable")
        )
        reusable.pop("reusable")
        reusable.pop("reuse_label")

        self.assertNotIn(
            "quality_revisit_value",
            source_quality_reasons(
                source, resolve_draft_identity("2026-08-04")
            ),
        )

    def test_future_guides_and_automation_require_one_practical_artifact(self):
        for draft_id, source in (
            ("2026-08-05-guide", valid_guide_source("2026-08-05")),
            ("2026-08-08-automation", valid_automation_source("2026-08-08")),
        ):
            reusable = next(
                block
                for block in source["news"][0]["content"]
                if block.get("reusable")
            )
            reusable.pop("reusable")
            reusable.pop("reuse_label")

            with self.subTest(draft_id=draft_id):
                self.assertIn(
                    "quality_revisit_value",
                    source_quality_reasons(
                        source, resolve_draft_identity(draft_id)
                    ),
                )

        source = valid_daily_source("2026-08-04")
        extra = next(
            block for block in source["news"][0]["content"] if block.get("t") == "ul"
        )
        extra["reusable"] = True
        self.assertIn(
            "quality_revisit_value",
            source_quality_reasons(
                source, resolve_draft_identity("2026-08-04")
            ),
        )

    def test_rejects_legacy_automatic_digest_language(self):
        source = valid_daily_source()
        source["editorial"]["opening"] = (
            "자동 생성 데일리 다이제스트 형식으로 여러 소식을 묶었습니다. "
            + repeated_text("낡은 다이제스트", 5)
        )

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-19")
        )

        self.assertIn("quality_style", reasons)

    def test_evergreen_guide_has_its_own_category_schedule_and_depth_policy(self):
        source = valid_guide_source()

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-22-guide")
        )

        self.assertNotIn("quality_identity", reasons)
        self.assertNotIn("quality_editorial", reasons)
        self.assertNotIn("quality_depth", reasons)

    def test_scheduled_guide_is_rejected_outside_wednesday(self):
        source = valid_guide_source("2026-07-23")

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-23-guide")
        )

        self.assertIn("quality_identity", reasons)

    def test_rendered_editorial_leaves_must_be_strings(self):
        mutations = (
            lambda source: source["editorial"].update(
                {"headline": {"가": "가" * 30}}
            ),
            lambda source: source["editorial"].update(
                {"opening": {"가": "가" * 200}}
            ),
            lambda source: source["tags"].__setitem__(0, {"가": "태그"}),
            lambda source: source["editorial"]["entities"].__setitem__(
                0, {"가": "대상"}
            ),
            lambda source: source["news"][0].update(
                {"title_kr": {"가": "가" * 30}}
            ),
            lambda source: source["news"][0]["content"][1].update(
                {"text": {"가": "가" * 1000}}
            ),
        )
        for mutate in mutations:
            source = valid_daily_source()
            mutate(source)

            reasons = source_quality_reasons(
                source, resolve_draft_identity("2026-07-19")
            )

            self.assertIn("quality_schema", reasons)

    def test_saturday_execution_evidence_requires_real_strings(self):
        source = valid_automation_source()
        source["verification"].update(
            {
                "commands": [True],
                "input_fixture": {"fake": "가" * 30},
                "expected": {"fake": "가" * 30},
                "actual": {"fake": "가" * 30},
                "failure": {"fake": "가" * 30},
                "rollback": {"fake": "가" * 30},
                "stdout_excerpt": {"fake": "가" * 30},
                "environment": {
                    "os": {"fake": True},
                    "runtime": {"fake": True},
                    "tool_version": {"fake": True},
                    "source_revision": {"fake": True},
                },
            }
        )

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-25-automation")
        )

        self.assertIn("quality_experiment_evidence", reasons)

    def test_imagegen_brief_and_file_metadata_must_match_exactly(self):
        source = valid_daily_source()
        source["visual"]["assets"][0]["generation_prompt"] = (
            "본문과 다른 장면을 지시하는 충분히 긴 한국어 이미지 생성 프롬프트"
        )
        source["visual"]["assets"][0]["generation_model"] = "other-model"

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-19")
        )

        self.assertIn("quality_visual_provenance", reasons)

    def test_image_provider_must_match_the_declared_asset_origins(self):
        daily = valid_daily_source()
        daily["generation"]["image_provider"] = "untracked-generator"
        automation = valid_automation_source()
        automation["generation"]["image_provider"] = "codex-imagegen"

        daily_reasons = source_quality_reasons(
            daily, resolve_draft_identity("2026-07-19")
        )
        automation_reasons = source_quality_reasons(
            automation, resolve_draft_identity("2026-07-25-automation")
        )

        self.assertIn("quality_visual_provenance", daily_reasons)
        self.assertIn("quality_visual_provenance", automation_reasons)

    def test_malformed_json_fields_fail_closed_without_crashing(self):
        mutations = {
            "coverage_null": lambda source: source["editorial"].update(
                {"coverage": None}
            ),
            "block_type_object": lambda source: source["news"][0]["content"][0].update(
                {"t": {"bad": True}}
            ),
            "list_items_integer": lambda source: next(
                block
                for block in source["news"][0]["content"]
                if block.get("t") == "ul"
            ).update({"items": 3}),
            "visual_assets_null": lambda source: source["visual"].update(
                {"assets": None}
            ),
            "image_origin_list": lambda source: source["images"]["visual_1"].update(
                {"origin": []}
            ),
            "evidence_files_object": lambda source: source["verification"].update(
                {"evidence_files": [{}]}
            ),
            "measurement_files_object": lambda source: source["verification"].update(
                {"measurement_files": [{}]}
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                source = valid_automation_source()
                mutate(source)

                reasons = source_quality_reasons(
                    source, resolve_draft_identity("2026-07-25-automation")
                )

                self.assertTrue(reasons)

    def test_malformed_measurement_binding_is_rejected_after_a_valid_chart(self):
        source = valid_automation_source()
        brief = source["visual"]["assets"][0]
        brief.update(
            {
                "origin": "measured_chart",
                "evidence_type": "chart",
                "measurement_source": "로컬 반복 실행 결과",
                "unit": "초",
                "sample_count": 2,
                "measurement_environment": "macOS Python 3.12 테스트",
                "data_points": [
                    {"label": "수동", "value": 10.0},
                    {"label": "자동", "value": 2.0},
                ],
            }
        )
        source["images"]["visual_1"].update(
            {
                "origin": "measured_chart",
                "measurement_sha256": measurement_digest(brief),
            }
        )
        source["verification"].update(
            {
                "evidence_files": ["visual_3"],
                "measurement_files": [{}],
                "measurement_note": "같은 입력을 반복 실행해 수동과 자동 처리 시간을 비교했다.",
            }
        )

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-25-automation")
        )

        self.assertIn("quality_experiment_evidence", reasons)

    def test_cover_is_an_article_specific_imagegen_asset_only(self):
        for origin in ("capture", "annotated_capture", "measured_chart"):
            with self.subTest(origin=origin):
                source = valid_daily_source()
                cover = source["images"]["cover"]
                cover["origin"] = origin
                cover.pop("generation_prompt")
                cover.pop("generation_model")

                reasons = source_quality_reasons(
                    source, resolve_draft_identity("2026-07-19")
                )

                self.assertIn("quality_visual_provenance", reasons)

    def test_measured_chart_rejects_non_finite_values(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                source = valid_automation_source()
                brief = source["visual"]["assets"][0]
                brief.update(
                    {
                        "origin": "measured_chart",
                        "evidence_type": "chart",
                        "measurement_source": "로컬 반복 실행 결과",
                        "unit": "초",
                        "sample_count": 2,
                        "measurement_environment": "macOS Python 3.12 테스트",
                        "data_points": [
                            {"label": "수동", "value": 10.0},
                            {"label": "자동", "value": value},
                        ],
                    }
                )
                source["images"]["visual_1"].update(
                    {"origin": "measured_chart", "measurement_sha256": "a" * 64}
                )
                source["verification"].update(
                    {
                        "measurement_files": ["visual_1"],
                        "measurement_note": "같은 테스트 입력을 두 번 실행해 총 소요 시간을 비교했다.",
                    }
                )

                reasons = source_quality_reasons(
                    source, resolve_draft_identity("2026-07-25-automation")
                )

                self.assertIn("quality_visual_provenance", reasons)

    def test_future_generation_provider_must_be_codex_agent(self):
        source = valid_daily_source()
        source["generation"]["provider"] = "gemini"

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-19")
        )

        self.assertIn("quality_generation", reasons)

    def test_measured_chart_requires_values_unit_sample_and_verification_binding(self):
        source = valid_automation_source()
        source["visual"]["assets"][0]["origin"] = "measured_chart"
        source["visual"]["assets"][0]["evidence_type"] = "chart"
        source["images"]["visual_1"]["origin"] = "measured_chart"

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-25-automation")
        )

        self.assertIn("quality_visual_provenance", reasons)
        self.assertIn("quality_experiment_evidence", reasons)

    def test_identity_rejects_wrong_display_date_and_non_saturday_automation(self):
        daily = valid_daily_source()
        daily["date_label"] = "2026. 7. 20"
        daily["weekday"] = "월"
        automation = valid_automation_source("2026-07-27")

        daily_reasons = source_quality_reasons(
            daily, resolve_draft_identity("2026-07-19")
        )
        automation_reasons = source_quality_reasons(
            automation, resolve_draft_identity("2026-07-27-automation")
        )

        self.assertIn("quality_identity", daily_reasons)
        self.assertIn("quality_identity", automation_reasons)

    def test_manual_extra_allows_explicit_same_day_non_saturday_publish(self):
        source = valid_automation_source("2026-07-26")
        source.update(
            {
                "publication_mode": "manual_extra",
                "manual_extra_reason": "사용자가 정규 토요일 일정과 별도로 오늘 즉시 발행을 요청했다.",
                "scheduled_at": "2026-07-26T18:40:00+09:00",
            }
        )
        source["verification"]["started_at"] = "2026-07-26T18:25:00+09:00"
        source["verification"]["completed_at"] = "2026-07-26T18:35:00+09:00"
        for brief in source["visual"]["assets"]:
            if brief["origin"] in {"capture", "annotated_capture"}:
                brief["captured_at"] = "2026-07-26T18:34:00+09:00"
        for image in source["images"].values():
            if image["origin"] in {"capture", "annotated_capture"}:
                image["captured_at"] = "2026-07-26T18:34:00+09:00"

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-26-automation")
        )

        self.assertNotIn("quality_identity", reasons)

    def test_manual_extra_requires_reason_and_same_day_kst_time(self):
        source = valid_automation_source("2026-07-26")
        source.update(
            {
                "publication_mode": "manual_extra",
                "scheduled_at": "2026-07-27T18:40:00+09:00",
            }
        )

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-26-automation")
        )

        self.assertIn("quality_identity", reasons)

    def test_saturday_capture_requires_bound_provenance(self):
        source = valid_automation_source()
        source["visual"]["assets"][0].pop("capture_tool")
        source["images"]["visual_1"].pop("capture_sha256")

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-25-automation")
        )

        self.assertIn("quality_visual_provenance", reasons)

    def test_daily_capture_allows_same_day_late_recovery(self):
        source = valid_daily_source("2026-07-24")
        source["visual"]["assets"][0] = visual_asset(
            "annotated_capture", "screenshot", "늦게 복구한 공식 화면"
        )
        source["images"]["visual_1"] = image_asset("annotated_capture")
        source["generation"]["image_provider"] = "mixed"
        capture_time = "2026-07-24T21:30:00+09:00"
        source["visual"]["assets"][0]["captured_at"] = capture_time
        source["images"]["visual_1"]["captured_at"] = capture_time

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-24")
        )

        self.assertNotIn("quality_visual_provenance", reasons)

    def test_daily_capture_rejects_next_day_recovery(self):
        source = valid_daily_source("2026-07-24")
        source["visual"]["assets"][0] = visual_asset(
            "annotated_capture", "screenshot", "다음 날 복구한 공식 화면"
        )
        source["images"]["visual_1"] = image_asset("annotated_capture")
        source["generation"]["image_provider"] = "mixed"
        capture_time = "2026-07-25T00:01:00+09:00"
        source["visual"]["assets"][0]["captured_at"] = capture_time
        source["images"]["visual_1"]["captured_at"] = capture_time

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-24")
        )

        self.assertIn("quality_visual_provenance", reasons)

    def test_saturday_execution_requires_timestamps_exit_code_and_output(self):
        source = valid_automation_source()
        source["verification"].pop("command_exit_code")
        source["verification"].pop("stdout_excerpt")

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-25-automation")
        )

        self.assertIn("quality_experiment_evidence", reasons)

    def test_daily_source_requires_valid_primary_url_and_fresh_iso_timestamp(self):
        source = valid_daily_source()
        source["news"][0]["url"] = "not a url"
        source["news"][0]["published_at"] = "someday"

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-19")
        )

        self.assertIn("quality_reference_mix", reasons)
        self.assertIn("quality_source_freshness", reasons)

    def test_daily_source_after_recency_policy_requires_exception_after_72_hours(self):
        source = valid_daily_source("2026-08-06")
        source["news"][0]["published_at"] = "2026-08-02T08:59:00+09:00"

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-08-06")
        )

        self.assertIn("quality_source_freshness", reasons)

    def test_daily_source_accepts_documented_high_value_exception_within_seven_days(self):
        source = valid_daily_source("2026-08-06")
        source["news"][0]["published_at"] = "2026-08-02T08:59:00+09:00"
        source["editorial"]["freshness_exception"] = {
            "reason": "최근 후보보다 자동화 비용을 직접 줄이는 모델 배치 판단을 구체적으로 설명할 수 있어 예외로 선택한다.",
            "lasting_value": "가격 발표 뒤에도 계획과 반복 실행을 분리하는 기준은 여러 에이전트 업무에서 계속 재사용할 수 있다.",
            "fresher_candidates_rejected": [
                "최신 보안 평가 발표는 독자가 당장 적용할 설정과 비용 판단 기준이 부족했다.",
                "최신 통신사 사례는 특정 기업 홍보 비중이 높고 일반 개발자가 재사용할 절차가 적었다.",
            ],
        }

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-08-06")
        )

        self.assertNotIn("quality_source_freshness", reasons)

    def test_daily_source_rejects_items_older_than_seven_days_even_with_exception(self):
        source = valid_daily_source("2026-08-06")
        source["news"][0]["published_at"] = "2026-07-29T08:59:00+09:00"
        source["editorial"]["freshness_exception"] = {
            "reason": "최근 후보보다 독자가 실제로 적용할 수 있는 판단 기준이 많아 예외로 선택하려는 오래된 원문이다.",
            "lasting_value": "발표 이후에도 여러 자동화 작업에서 반복해서 사용할 수 있는 비용과 품질 분리 원칙을 제공한다.",
            "fresher_candidates_rejected": [
                "최신 후보 하나는 단순 발표여서 독자가 적용할 구체적인 조건을 제공하지 못했다.",
                "최신 후보 다른 하나는 기존 글과 핵심 질문과 결론이 거의 같아 제외했다.",
            ],
        }

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-08-06")
        )

        self.assertIn("quality_source_freshness", reasons)

    def test_future_posts_require_korean_editorial_and_prose(self):
        source = valid_daily_source()
        source["editorial"]["headline"] = (
            "English only headline explains a product update and every condition"
        )
        source["editorial"]["opening"] = "English opening sentence. " * 20
        source["editorial"]["closing"] = "English closing sentence. " * 10
        source["news"][0]["title_kr"] = "English only source title"
        for block in source["news"][0]["content"]:
            if block.get("t") in {"h", "p", "quote"}:
                block["text"] = "English prose without Korean context. " * 30

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-19")
        )

        self.assertIn("quality_korean_content", reasons)

    def test_non_rendered_entities_cannot_inflate_reading_depth(self):
        source = valid_daily_source()
        baseline = estimate_read_minutes(source)
        source["editorial"]["entities"] = ["X" * 5000]

        inflated = estimate_read_minutes(source)
        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-19")
        )

        self.assertEqual(inflated, baseline)
        self.assertIn("quality_editorial", reasons)

    def test_headline_must_fit_the_exported_title_without_truncation(self):
        source = valid_daily_source()
        source["editorial"]["headline"] = "가" * 71

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-19")
        )

        self.assertIn("quality_editorial", reasons)

    def test_rejects_banned_ai_phrasing_and_repeated_filler_sentences(self):
        source = valid_daily_source()
        repeated = "같은 결론을 다시 말합니다. " * 6
        source["news"][0]["content"][1]["text"] = (
            "정리해보겠습니다. " + repeated
        )

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-07-19")
        )

        self.assertIn("quality_style", reasons)
        self.assertIn("quality_repetition", reasons)

    def test_august_posts_reject_report_headings_and_ai_intro_cliches(self):
        source = valid_daily_source("2026-08-04")
        source["editorial"]["opening"] = (
            "이번 글에서는 새 기능을 살펴보겠습니다. "
            + repeated_text("구체적인 사용 장면", 5)
        )
        source["news"][0]["content"][0]["text"] = "개요"

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-08-04")
        )

        self.assertIn("quality_natural_voice", reasons)

    def test_august_posts_reject_headings_that_expose_editorial_intent(self):
        fixtures = (
            (valid_daily_source("2026-08-04"), "2026-08-04"),
            (valid_guide_source("2026-08-05"), "2026-08-05-guide"),
            (valid_automation_source("2026-08-08"), "2026-08-08-automation"),
        )
        headings = (
            "독자에게 미치는 영향",
            "개발자에게 미치는 영향과 대응",
            "우리에게 미치는 영향",
        )

        for (source, draft_id), heading in zip(fixtures, headings):
            source["news"][0]["content"][0]["text"] = heading
            reasons = source_quality_reasons(
                source, resolve_draft_identity(draft_id)
            )
            self.assertIn("quality_natural_voice", reasons)

    def test_august_posts_require_search_aligned_title_and_tags(self):
        source = valid_daily_source("2026-08-04")
        source["editorial"]["headline"] = "충격적인 소식을 지금 확인해야 하는 이유와 놀라운 결과"
        source["tags"] = ["뉴스", "정보", "최신", "오늘", "블로그"]

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-08-04")
        )

        self.assertIn("quality_search_metadata", reasons)

    def test_search_conversion_contract_accepts_focused_query_and_link_roles(self):
        cases = (
            ("2026-08-11", valid_daily_source("2026-08-11")),
            ("2026-08-12-guide", valid_guide_source("2026-08-12")),
            ("2026-08-15-automation", valid_automation_source("2026-08-15")),
        )
        for draft_id, source in cases:
            with self.subTest(draft_id=draft_id):
                reasons = source_quality_reasons(
                    source, resolve_draft_identity(draft_id)
                )
                self.assertNotIn("quality_search_conversion", reasons)

    def test_search_conversion_contract_rejects_query_outside_title_opening(self):
        source = valid_daily_source("2026-08-11")
        source["editorial"]["headline"] = (
            "일반 사용자가 업데이트 뒤에 먼저 확인해야 하는 새 기능 적용 조건"
        )

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-08-11")
        )

        self.assertIn("quality_search_conversion", reasons)

    def test_search_conversion_contract_requires_intent_and_two_link_roles(self):
        source = valid_daily_source("2026-08-11")
        del source["editorial"]["search_intent"]
        source["related_posts"][1]["role"] = "foundation"

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-08-11")
        )

        self.assertIn("quality_search_conversion", reasons)

    def test_august_posts_reject_ad_between_heading_and_first_paragraph(self):
        source = valid_daily_source("2026-08-04")
        content = source["news"][0]["content"]
        ad = next(block for block in content if block.get("t") == "ad_break")
        content.remove(ad)
        heading_index = next(
            index
            for index, block in enumerate(content)
            if block.get("t") == "h" and block.get("text") == "실제로 확인하는 방법"
        )
        content.insert(heading_index + 1, ad)

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-08-04")
        )

        self.assertIn("quality_depth", reasons)

    def test_august_posts_accept_ad_after_complete_section_before_heading(self):
        source = valid_daily_source("2026-08-04")

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-08-04")
        )

        self.assertNotIn("quality_depth", reasons)

    def test_non_numeric_generation_revision_fails_closed_without_crashing(self):
        source = valid_daily_source()
        source["generation"]["revision"] = "draft"

        reasons = source_quality_reasons(source, resolve_draft_identity("2026-07-19"))

        self.assertIn("quality_generation", reasons)

    def test_future_daily_rejects_a_minimal_structural_shell(self):
        day = "2026-07-19"
        source = {
            "format": "lead-story-v1",
            "primary_query": "x",
            "images": {"cover": {}, "visual_1": {}, "visual_2": {}},
            "news": [{"title_kr": "x", "references": [], "content": []}],
        }

        reasons = source_quality_reasons(source, resolve_draft_identity(day))

        self.assertIn("quality_identity", reasons)
        self.assertIn("quality_editorial", reasons)
        self.assertIn("quality_depth", reasons)
        self.assertIn("quality_reference_mix", reasons)
        self.assertIn("quality_tags", reasons)

    def test_future_daily_rejects_fallback_images_and_unreviewed_korean_text(self):
        day = "2026-07-19"
        source = valid_daily_source(day)
        source["generation"]["image_provider"] = "deterministic-fallback"
        source["images"]["visual_2"]["origin"] = "deterministic_fallback"
        source["visual"]["assets"][1]["origin"] = "deterministic_fallback"
        source["visual"]["assets"][0]["qa"]["text_reviewed"] = False

        reasons = source_quality_reasons(source, resolve_draft_identity(day))

        self.assertIn("quality_fallback_image", reasons)
        self.assertIn("quality_visual_qa", reasons)

    def test_new_daily_rejects_cover_and_body_visuals_with_same_question(self):
        day = "2026-07-22"
        source = valid_daily_source(day)
        source["visual"]["cover"]["label"] = source["visual"]["assets"][0]["label"]

        reasons = source_quality_reasons(source, resolve_draft_identity(day))

        self.assertIn("quality_visual_roles", reasons)

    def test_new_daily_accepts_distinct_cover_and_body_visual_roles(self):
        day = "2026-07-22"
        source = valid_daily_source(day)

        reasons = source_quality_reasons(source, resolve_draft_identity(day))

        self.assertNotIn("quality_visual_roles", reasons)

    def test_july_29_cover_requires_a_declared_visual_signature(self):
        day = "2026-07-29"
        source = valid_daily_source(day)
        source["visual"]["cover"].pop("palette_family")

        reasons = source_quality_reasons(source, resolve_draft_identity(day))

        self.assertIn("quality_visual_variety", reasons)

    def test_july_29_cover_rejects_repeated_card_template_composition(self):
        day = "2026-07-29"
        source = valid_daily_source(day)
        source["visual"]["cover"]["composition_type"] = "three_column_cards"
        source["images"]["cover"]["composition_type"] = "three_column_cards"

        reasons = source_quality_reasons(source, resolve_draft_identity(day))

        self.assertIn("quality_visual_variety", reasons)

    def test_july_29_cover_rejects_infographic_prompt(self):
        day = "2026-07-29"
        source = valid_daily_source(day)
        source["images"]["cover"]["generation_prompt"] = (
            "Use case: infographic-diagram. 단계별 흐름을 보여 주는 도표"
        )

        reasons = source_quality_reasons(source, resolve_draft_identity(day))

        self.assertIn("quality_visual_variety", reasons)

    def test_july_29_cover_rejects_missing_editorial_scene_token(self):
        day = "2026-07-29"
        source = valid_daily_source(day)
        source["images"]["cover"]["generation_prompt"] = (
            "Use case: illustration-story. 실제 사용자의 문제를 보여 주는 장면"
        )

        reasons = source_quality_reasons(source, resolve_draft_identity(day))

        self.assertIn("quality_visual_variety", reasons)

    def test_july_29_cover_accepts_matching_editorial_scene_signature(self):
        day = "2026-07-29"
        source = valid_daily_source(day)

        reasons = source_quality_reasons(source, resolve_draft_identity(day))

        self.assertNotIn("quality_visual_variety", reasons)

    def test_august_cover_rejects_text_heavy_label_set(self):
        day = "2026-08-04"
        source = valid_daily_source(day)
        source["visual"]["cover"]["korean_labels"] = [
            "첫 번째 설명",
            "두 번째 설명",
            "세 번째 설명",
            "네 번째 설명",
        ]

        reasons = source_quality_reasons(source, resolve_draft_identity(day))

        self.assertIn("quality_visual_variety", reasons)

    def test_complete_future_daily_source_passes_the_source_quality_gate(self):
        day = "2026-07-19"
        source = valid_daily_source(day)

        reasons = source_quality_reasons(source, resolve_draft_identity(day))

        self.assertEqual(reasons, [])

    def test_saturday_requires_structured_execution_evidence(self):
        day = "2026-07-25"
        source = valid_automation_source(day)
        without_evidence = copy.deepcopy(source)
        without_evidence.pop("verification")

        missing = source_quality_reasons(
            without_evidence, resolve_draft_identity(f"{day}-automation")
        )
        complete = source_quality_reasons(
            source, resolve_draft_identity(f"{day}-automation")
        )

        self.assertIn("quality_experiment_evidence", missing)
        self.assertEqual(complete, [])

    def test_short_explicit_backfill_accepts_truthful_next_day_evidence(self):
        day = "2026-08-15"
        source = valid_automation_source(day)
        capture_time = "2026-08-16T09:10:00+09:00"
        for index in (1, 3):
            source["visual"]["assets"][index - 1]["captured_at"] = capture_time
            source["images"][f"visual_{index}"]["captured_at"] = capture_time
        source["verification"]["started_at"] = "2026-08-16T09:00:00+09:00"
        source["verification"]["completed_at"] = "2026-08-16T09:20:00+09:00"
        source["backfill"] = {
            "created_at": "2026-08-16T09:30:00+09:00",
            "reason": "정기 실행 누락 뒤 사용자가 전날 토요일 글의 재제작을 명시적으로 요청했다.",
        }

        reasons = source_quality_reasons(
            source, resolve_draft_identity(f"{day}-automation")
        )

        self.assertEqual(reasons, [])

    def test_backfill_outside_seventy_two_hours_is_rejected(self):
        day = "2026-08-15"
        source = valid_automation_source(day)
        capture_time = "2026-08-19T09:10:00+09:00"
        for index in (1, 3):
            source["visual"]["assets"][index - 1]["captured_at"] = capture_time
            source["images"][f"visual_{index}"]["captured_at"] = capture_time
        source["verification"]["started_at"] = "2026-08-19T09:00:00+09:00"
        source["verification"]["completed_at"] = "2026-08-19T09:20:00+09:00"
        source["backfill"] = {
            "created_at": "2026-08-19T09:30:00+09:00",
            "reason": "오래 지난 작업이 짧은 백필 예외로 통과하면 증거의 시점 검증 의미가 사라진다.",
        }

        reasons = source_quality_reasons(
            source, resolve_draft_identity(f"{day}-automation")
        )

        self.assertIn("quality_experiment_evidence", reasons)
        self.assertIn("quality_visual_provenance", reasons)


if __name__ == "__main__":
    unittest.main()
