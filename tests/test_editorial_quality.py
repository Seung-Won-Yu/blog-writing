import copy
import json
import math
import unittest
from datetime import date, timedelta
from pathlib import Path

from blog_pipeline.publishing.draft_identity import (
    category_for_content_type,
    editorial_lane_for_identity,
    publication_mode_for_identity,
    regular_schedule_for_identity,
    resolve_draft_identity,
)
from blog_pipeline.publishing.editorial_quality import (
    depth_policy_for,
    estimate_read_minutes,
    measurement_digest,
    project_reader_scores,
    reader_access_scores,
    source_quality_reasons,
)


ROOT = Path(__file__).resolve().parents[1]


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
        "content_label": resolve_draft_identity(day).content_label,
        "category": category_for_content_type("daily_news", day),
        "publication_mode": publication_mode_for_identity(resolve_draft_identity(day)),
        "scheduled_at": regular_schedule_for_identity(resolve_draft_identity(day)),
        "primary_query": "일반 사용자가 확인할 최신 기능 변경과 적용 조건",
        "tags": ["기능 변경", "사용 방법", "적용 조건", "업데이트", "체크리스트"],
        "reader_access": {
            "quick_summary": [
                "새 기능이 적용되지 않는 문제와 독자가 먼저 확인할 조건을 설명한다.",
                "업데이트의 적용 조건과 실제 사용 장면을 연결해 판단 순서를 보여 준다.",
                "새 기능의 결과가 환경마다 달라질 수 있어 확인할 한계를 함께 남긴다.",
            ],
            "glossary": [
                {"term": "새 기능", "meaning": "업데이트로 추가돼 사용자가 새로 확인하거나 선택할 수 있는 동작이다."},
                {"term": "적용 조건", "meaning": "새 기능이나 규칙이 실제로 작동하기 위해 먼저 맞아야 하는 기준이다."},
                {"term": "사용 장면", "meaning": "독자가 기능을 실제로 켜고 결과를 확인하게 되는 구체적인 상황이다."},
            ],
        },
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
    if publish_day >= date(2026, 8, 26):
        source["editorial"]["original_value"] = {
            "durable_question": "공식 발표가 지난 뒤에도 내 환경에 적용할 조건을 어떻게 판단할까?",
            "source_gap": "원문은 기능을 소개하지만 기존 설정과 충돌하는 순서와 실패 조건을 함께 설명하지 않는다.",
            "contribution": "공식 문서를 서로 비교해 적용 조건과 우선순위, 확인 신호, 돌아갈 기준을 하나의 판단표로 재구성한다.",
            "proof_method": "document_comparison",
            "reader_outcome": "독자는 자신의 설정값을 표에 대입해 적용 여부와 다음 행동을 결정할 수 있다.",
            "limits": "문서에서 확인할 수 없는 계정별 배포 시점과 비공개 내부 조건은 추측하지 않는다.",
        }
        trend = {
            "editorial_treatment": "tactile_realism",
            "focal_subject": "새 기능 적용 전후를 확인하는 사용자의 손과 설정 표시",
            "texture_cue": "살짝 구겨진 설정 메모지와 무광 화면 질감",
            "authenticity_cue": "실제로 사용한 흔적이 남은 메모와 자연스러운 손 동작",
        }
        source["visual"]["cover"].update(trend)
        source["images"]["cover"].update(trend)
    if publish_day >= date(2026, 8, 31):
        identity = resolve_draft_identity(day)
        lane = editorial_lane_for_identity(identity)
        source["editorial"]["weekly_lane"] = lane
        source["editorial"]["reader_hook"] = {
            "scene": "설정 화면을 열었지만 새 기능의 적용 조건과 확인 위치가 서로 달라 멈춘 장면",
            "stakes": "조건을 잘못 읽으면 기존 설정을 덮어쓰거나 실제 적용 여부를 놓칠 수 있다.",
            "payoff": "공식 문서를 비교한 판단표로 내 환경의 적용 여부와 다음 행동을 결정한다.",
            "open_question": "새 기능은 내 계정에서 어떤 조건으로 켜지고 어디에서 결과를 확인할까?",
        }
        source["editorial"]["opening"] = (
            "설정 화면을 열었지만 새 기능의 적용 조건과 확인 위치가 서로 달라 손이 멈춘다. "
            "기존 값을 먼저 기록하지 않으면 설정을 덮어쓰고도 실제 적용 여부를 놓칠 수 있다. "
            "공식 문서를 비교한 판단표로 내 환경의 적용 여부와 다음 행동을 결정해 본다."
        )
        if lane == "change_explainer":
            source["editorial"]["article_shape"] = "change_impact"
    return source


def valid_curiosity_source(day="2026-09-01"):
    source = valid_daily_source(day)
    source.update(
        {
            "primary_query": "QR코드 손상 인식",
            "tags": ["QR코드", "QR코드 인식", "오류 복원", "스마트폰 카메라", "리드 솔로몬"],
        }
    )
    source["editorial"].update(
        {
            "headline": "QR코드 손상 인식: 일부가 지워져도 읽히는 이유와 복원 원리",
            "article_shape": "research_interpretation",
            "topic_key": "qr-code-error-correction-principle",
            "reader_question": "QR코드 일부가 찢어지거나 가려져도 스마트폰이 내용을 읽을 수 있는 이유는 무엇일까?",
            "entities": ["QR코드", "리드-솔로몬 오류 정정"],
            "coverage": [
                "question",
                "mechanism",
                "example",
                "misconception",
                "evidence",
                "takeaway",
            ],
            "search_intent": {
                "query": "QR코드 손상 인식",
                "reader_need": "QR코드 일부가 가려져도 인식되는 이유와 실패하는 경계를 알고 싶다.",
                "answer_format": "오류 복원 원리와 손상 범위별 결과를 그림과 표로 보여 준다.",
            },
            "reader_hook": {
                "scene": "종이에 인쇄한 QR코드 모서리가 찢어졌는데도 스마트폰 카메라가 링크를 읽는 장면",
                "stakes": "손상돼도 무조건 읽힌다고 믿으면 중요한 안내나 결제 코드가 필요한 순간 실패할 수 있다.",
                "payoff": "오류 정정 원리와 손상 위치별 경계를 이해해 다시 인쇄해야 할 때를 판단한다.",
                "open_question": "QR코드는 어떤 정보를 여분으로 담고 어디까지 손상된 데이터를 복원할 수 있을까?",
            },
            "opening": (
                "종이에 인쇄한 QR코드 모서리가 찢어졌는데도 스마트폰 카메라는 링크를 읽는다. "
                "하지만 손상돼도 무조건 인식되는 것은 아니다. "
                "오류 정정 원리와 손상 위치별 경계를 알면 언제 다시 인쇄해야 하는지 분명히 판단할 수 있다."
            ),
            "original_value": {
                "durable_question": "QR코드가 일부 손상된 뒤에도 데이터를 읽는 원리와 실패 경계는 무엇일까?",
                "source_gap": "표준 설명은 오류 정정 수준을 정의하지만 일상에서 보이는 손상 위치와 실패 장면을 함께 연결하지 않는다.",
                "contribution": "공식 오류 정정 수준과 실제 손상 위치를 비교해 인식 가능한 경우와 다시 인쇄할 경우를 한 표로 재구성한다.",
                "proof_method": "source_triangulation",
                "reader_outcome": "독자는 손상된 QR코드가 실패할 조건을 이해하고 교체 여부를 판단할 수 있다.",
                "limits": "카메라 성능과 인쇄 품질에 따른 모든 인식률을 하나의 수치로 단정하지 않는다.",
            },
        }
    )
    source["news"][0].update(
        {
            "title_kr": "QR코드 오류 정정과 손상 복원의 원리",
            "source": "QR Code 표준과 오류 정정 참고 자료",
            "url": "https://www.qrcode.com/en/about/error_correction.html",
            "published_at": "2020-01-01T00:00:00+09:00",
            "blurb_kr": "QR코드는 오류 정정 수준에 따라 일부가 손상돼도 데이터를 복원할 수 있다.",
            "references": [
                {
                    "kind": "official",
                    "title": "QR Code error correction",
                    "url": "https://www.qrcode.com/en/about/error_correction.html",
                },
                {
                    "kind": "documentation",
                    "title": "QR Code standard overview",
                    "url": "https://www.iso.org/standard/83389.html",
                },
                {
                    "kind": "research",
                    "title": "Error correction reference",
                    "url": "https://www.thonky.com/qr-code-tutorial/error-correction-coding",
                },
            ],
        }
    )
    source["news"][0]["content"] = [
        {"t": "h", "text": "찢어진 모서리보다 먼저 보는 세 개의 큰 사각형"},
        {"t": "p", "text": repeated_text("위치 찾기 패턴", 3)},
        {"t": "p", "text": repeated_text("카메라가 방향을 잡는 과정", 3)},
        {"t": "visual", "image": "visual_1", "caption": "QR코드의 위치 패턴과 데이터 영역, 오류 정정 영역을 구분해 보여 준다."},
        {"t": "p", "text": repeated_text("손상 위치에 따른 차이", 3)},
        {"t": "h", "text": "사라진 정보를 추측하는 대신 여분의 조각으로 복원한다"},
        {"t": "p", "text": repeated_text("리드 솔로몬 오류 정정", 3)},
        {"t": "ad_break"},
        {"t": "h", "text": "같은 크기의 얼룩도 위치가 다르면 결과가 달라진다"},
        {"t": "p", "text": repeated_text("중앙과 모서리 손상 비교", 3)},
        {"t": "visual", "image": "visual_2", "caption": "같은 면적이 가려져도 위치 패턴과 데이터 영역의 손상 결과가 달라지는 이유를 비교한다."},
        {"t": "p", "text": repeated_text("인식 실패 경계", 3)},
        {
            "t": "table",
            "caption": "손상 장면별로 먼저 확인할 QR코드 영역",
            "headers": ["장면", "영향", "확인"],
            "rows": [["모서리 얼룩", "위치 패턴 영향 가능", "다른 카메라로 재확인"], ["중앙 가림", "데이터와 로고 영역 영향", "원본 크기와 대비 확인"]],
        },
        {"t": "h", "text": "오류 정정 수준이 높다고 언제나 좋은 것은 아니다"},
        {"t": "p", "text": repeated_text("용량과 복원력의 교환", 3)},
        {"t": "ul", "items": ["세 위치 패턴이 가려졌는지 본다.", "인쇄 대비와 초점 상태를 확인한다.", "중요한 용도라면 새 코드로 교체한다."]},
        {"t": "p", "text": repeated_text("다시 인쇄할 판단", 3)},
        {"t": "p", "text": repeated_text("남는 한계와 다음 확인", 3)},
    ]
    source["visual"]["assets"][0].update(
        {
            "label": "QR코드의 위치·데이터·오류 정정 영역",
            "steps": "위치 패턴 확인 → 데이터 조각 판독 → 오류 정정으로 복원",
            "curiosity_hook": "찢어진 부분의 정보는 어디에서 다시 가져올까?",
            "korean_labels": ["위치 패턴", "데이터", "오류 정정"],
        }
    )
    source["visual"]["assets"][1].update(
        {
            "label": "같은 면적의 손상이 위치에 따라 만드는 차이",
            "steps": "모서리 손상 → 중앙 손상 → 위치 패턴 손상 비교",
            "curiosity_hook": "같은 크기로 가려도 왜 한쪽만 실패할까?",
            "korean_labels": ["모서리", "중앙", "위치 패턴"],
        }
    )
    trend = {
        "editorial_treatment": "tactile_realism",
        "focal_subject": "모서리가 찢어진 종이 QR코드를 스마트폰 카메라로 확인하는 손",
        "texture_cue": "접힌 종이와 번진 잉크, 무광 스마트폰 화면 질감",
        "authenticity_cue": "실제로 주머니에서 꺼낸 듯한 구김과 자연스러운 손 그림자",
    }
    source["visual"]["cover"].update(trend)
    source["images"]["cover"].update(
        {
            **trend,
            "alt": "모서리가 찢어진 QR코드를 스마트폰으로 인식하며 오류 복원 원리를 확인하는 장면",
        }
    )
    source["images"]["visual_1"]["alt"] = "QR코드 위치 패턴과 데이터·오류 정정 영역 설명도"
    source["images"]["visual_2"]["alt"] = "QR코드 손상 위치에 따른 인식 결과 비교도"
    source["reader_access"] = {
        "quick_summary": [
            "QR코드가 일부 찢어져도 남은 정보 조각으로 내용을 복원할 수 있다.",
            "위치 패턴과 데이터 영역의 손상은 같은 크기여도 인식 결과가 다르다.",
            "오류 정정 수준이 높아도 인쇄 상태와 카메라 환경에 따라 실패할 수 있다.",
        ],
        "glossary": [
            {"term": "QR코드", "meaning": "카메라로 읽을 수 있도록 정보를 검고 흰 사각형에 담은 이차원 코드다."},
            {"term": "위치 패턴", "meaning": "카메라가 QR코드의 방향과 범위를 찾도록 모서리에 둔 큰 사각형 표시다."},
            {"term": "오류 정정", "meaning": "일부 정보가 사라져도 여분의 데이터 조각으로 원래 내용을 복원하는 방식이다."},
        ],
    }
    return source


def valid_automation_source(day="2026-07-25"):
    source = valid_daily_source(day)
    identity = resolve_draft_identity(f"{day}-automation")
    cover_image = copy.deepcopy(source["images"]["cover"])
    source.update(
        {
            "draft_id": f"{day}-automation",
            "content_type": "automation_case",
            "content_label": identity.content_label,
            "category": category_for_content_type("automation_case", day),
            "publication_mode": publication_mode_for_identity(identity),
            "scheduled_at": regular_schedule_for_identity(identity),
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
    if (
        date.fromisoformat(day) >= date(2026, 8, 28)
        and editorial_lane_for_identity(identity) == "executed_experiment"
    ):
        source["editorial"]["weekly_lane"] = editorial_lane_for_identity(identity)
        source["editorial"]["article_shape"] = "hands_on_test"
        source["editorial"]["reader_walkthrough"] = {
            "reader_level": "beginner",
            "prerequisites": [
                "Python이 설치된 개인 테스트 컴퓨터",
                "원본이 아닌 첨부파일 복사본 폴더",
            ],
            "steps": [
                "복사본 파일을 테스트 입력 폴더에 넣는다.",
                "제공된 명령을 복사해 작은 예제를 실행한다.",
                "성공 목록과 오류 목록을 실제 파일과 대조한다.",
            ],
            "success_check": "성공 목록의 파일 수와 날짜별 출력 폴더의 실제 파일 수가 같으면 성공이다.",
            "recovery": "오류가 나면 출력 폴더만 비우고 보존된 입력 복사본으로 같은 단계를 다시 실행한다.",
            "easiest_method_considered": "운영체제 기본 기능이나 안전한 로컬 화면 도구로 같은 일을 더 짧게 해결할 수 있는지 먼저 비교한다.",
            "code_needed_when": "같은 규칙의 작업이 정기적으로 반복되어 매번 누르고 확인하는 시간이 코드 준비보다 커질 때만 사용한다.",
        }
        source["editorial"]["reader_hook"] = {
            "scene": "다운로드 폴더에 같은 이름의 첨부파일이 쌓여 필요한 파일을 다시 찾는 장면",
            "stakes": "바로 이동시키면 중복 파일을 덮어쓰고 잘못 분류한 결과를 되돌리기 어렵다.",
            "payoff": "미리보기와 실행 기록, 원상복구 절차를 함께 검증해 안전한 자동화 기준을 얻는다.",
            "open_question": "자동 정리가 실제 파일을 잃지 않고 실패 뒤에도 되돌아올 수 있을까?",
        }
        source["editorial"]["opening"] = (
            "다운로드 폴더에 같은 이름의 첨부파일이 쌓이면 필요한 파일을 다시 찾느라 시간이 든다. "
            "바로 이동시키면 중복 파일을 덮어쓰고 잘못 분류한 결과를 되돌리기 어렵다. "
            "미리보기와 실행 기록, 원상복구까지 직접 검증해 안전한 자동화 기준을 확인한다."
        )
        headings = [
            block
            for block in source["news"][0]["content"]
            if block.get("t") == "h"
        ]
        headings[0]["text"] = "먼저 결과부터 확인한다"
        headings[1]["text"] = "준비물과 테스트 복사본을 챙긴다"
        headings[2]["text"] = "1단계: 작은 예제를 실행한다"
        headings[-1]["text"] = "개발 기록: 실패한 입력과 복구 방법"
    elif editorial_lane_for_identity(identity) == "developer_insight":
        source["primary_query"] = "Agent Skills 사용처"
        source["tags"] = [
            "Agent Skills",
            "AI 에이전트",
            "GitHub",
            "Codex",
            "Claude Code",
        ]
        source["editorial"].update(
            {
                "headline": "Agent Skills는 어디에 쓰일까: GitHub 공개 스킬 생태계 지도",
                "topic_key": "agent-skills-github-use-case-map",
                "reader_question": "GitHub와 공식 문서에 공개된 Agent Skills는 개발 과정의 어느 작업에서 실제로 쓰일까?",
                "entities": ["Agent Skills", "GitHub", "Codex", "Claude Code"],
                "coverage": [
                    "question",
                    "sources",
                    "mechanism",
                    "comparison",
                    "application",
                    "limits",
                    "judgment",
                ],
                "weekly_lane": "developer_insight",
                "article_shape": "ecosystem_map",
                "search_intent": {
                    "query": "Agent Skills",
                    "reader_need": "공개 스킬이 어떤 개발 업무에서 쓰이고 무엇을 기준으로 골라야 하는지 알고 싶다.",
                    "answer_format": "공식 문서와 GitHub 표본을 용도별 지도와 비교표로 설명한다.",
                },
                "reader_hook": {
                    "scene": "GitHub에서 Agent Skill을 검색했지만 비슷한 저장소가 너무 많아 용도를 구분하기 어려운 장면",
                    "stakes": "인기 순위만 따라 설치하면 현재 프로젝트와 맞지 않는 지침이 작업 범위를 불필요하게 키울 수 있다.",
                    "payoff": "공식 정의와 공개 표본을 개발 단계별로 분류해 지금 필요한 스킬을 고르는 지도를 얻는다.",
                    "open_question": "공개 Agent Skills는 코딩·검증·문서화 중 어디에 가장 많이 쓰이고 어떤 빈틈이 남아 있을까?",
                },
                "opening": (
                    "GitHub에서 Agent Skill을 검색하면 비슷한 저장소가 너무 많아 용도를 구분하기 어렵다. "
                    "인기 순위만 따라 설치하면 프로젝트와 맞지 않는 지침이 작업 범위를 키울 수 있다. "
                    "공식 정의와 공개 표본을 개발 단계별로 분류해 필요한 스킬을 고르는 기준을 만든다."
                ),
            }
        )
        source["editorial"]["revisit"]["artifact_type"] = "source_map"
        source["reader_access"] = {
            "quick_summary": [
                "GitHub에서 Agent Skills를 찾을 때 인기보다 실제 개발 업무와의 연결을 먼저 봐야 한다.",
                "공식 정의와 공개 스킬 표본을 비교하면 코딩·검증·문서화의 사용처를 구분할 수 있다.",
                "개발 단계에 맞지 않는 스킬은 지침 범위를 키울 수 있어 설치 전 확인이 필요하다.",
            ],
            "glossary": [
                {"term": "Agent Skills", "meaning": "에이전트가 특정 작업을 일관되게 수행하도록 지침과 자료를 묶은 단위다."},
                {"term": "GitHub", "meaning": "코드와 문서를 공개하거나 협업하며 스킬 예제를 확인할 수 있는 저장소 서비스다."},
                {"term": "개발 단계", "meaning": "기획·코딩·검증·문서화·운영처럼 소프트웨어 작업을 목적별로 나눈 구간이다."},
            ],
        }
        source["editorial"]["original_value"].update(
            {
                "durable_question": "Agent Skills가 개발 업무의 어느 단계에 쓰이고 어떤 기준으로 선택해야 하는가?",
                "source_gap": "공식 문서는 형식과 기능을 설명하지만 공개 스킬의 실제 용도 분포와 선택 기준은 한눈에 보여 주지 않는다.",
                "contribution": "공식 문서와 GitHub 공개 표본을 같은 분류표에 놓고 개발 단계별 사용처와 선택 한계를 새로 정리한다.",
                "proof_method": "source_triangulation",
                "reader_outcome": "독자는 자신의 개발 단계에 맞는 스킬 유형과 설치 전 확인 기준을 고를 수 있다.",
                "limits": "표본은 확인 시점의 공개 저장소에 한정되며 전체 생태계의 사용량을 대표하지 않는다.",
            }
        )
        source["verification"] = {
            "mode": "source_research",
            "checked_at": f"{day}T09:05:00+09:00",
            "source_count": 3,
            "source_urls": [
                "https://learn.chatgpt.com/docs/build-skills",
                "https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills",
                "https://github.com/anthropics/skills",
            ],
            "scope": "OpenAI와 Anthropic의 공식 문서, 공개 GitHub 스킬 저장소를 같은 기준으로 조사한다.",
            "method": "스킬의 설명과 파일 구조를 읽고 코딩·검증·문서화·운영 용도로 분류한 뒤 공통점과 차이를 대조한다.",
            "selection_rule": "공식 출처이거나 출처와 라이선스를 확인할 수 있는 공개 저장소만 표본에 포함한다.",
            "limitations": "확인 시점의 공개 자료만 다루며 설치 수나 실제 조직 사용량으로 해석하지 않는다.",
            "evidence_files": ["visual_3"],
            "problem_lane": "Agent Skills 생태계",
            "tool_brand": "OpenAI·Anthropic·GitHub",
        }
        cover_trend = {
            "editorial_treatment": "documentary_closeup",
            "focal_subject": "Agent Skills 공식 문서와 GitHub 저장소를 나란히 분류하는 개발자의 손",
            "texture_cue": "실제 문서 화면과 인쇄한 분류 메모, 연필 표시의 질감",
            "authenticity_cue": "공개 저장소 이름과 분류 흔적이 남은 현실적인 조사 책상",
        }
        source["visual"]["cover"].update(cover_trend)
        source["images"]["cover"].update(
            {
                **cover_trend,
                "alt": "Agent Skills 공식 문서와 GitHub 공개 스킬의 사용처를 분류하는 개발자 조사 장면",
            }
        )
        readable_content = []
        for block in source["news"][0]["content"]:
            text = str(block.get("text") or "") if isinstance(block, dict) else ""
            if isinstance(block, dict) and block.get("t") == "p" and len(text) > 220:
                for start in range(0, len(text), 200):
                    readable_content.append({"t": "p", "text": text[start:start + 200]})
            else:
                readable_content.append(block)
        rhythmic_content = []
        paragraph_run = 0
        for block in readable_content:
            if isinstance(block, dict) and block.get("t") == "p":
                if paragraph_run == 4:
                    rhythmic_content.append(
                        {
                            "t": "quote",
                            "text": "여기까지의 근거를 실제 선택 기준과 다시 연결한다.",
                        }
                    )
                    paragraph_run = 0
                paragraph_run += 1
            else:
                paragraph_run = 0
            rhythmic_content.append(block)
        source["news"][0]["content"] = rhythmic_content
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
    def test_all_new_weekday_lanes_score_reader_access_above_eight_point_five(self):
        monday = valid_daily_source("2026-08-31")
        wednesday = valid_daily_source("2026-09-02")
        for source in (monday, wednesday):
            for index, block in enumerate(source["news"][0]["content"]):
                if block.get("t") == "p":
                    block["text"] = repeated_text(f"읽기 쉬운 문단 {index}", 2)
        cases = [
            ("2026-08-31", monday),
            ("2026-09-01", valid_curiosity_source("2026-09-01")),
            ("2026-09-02", wednesday),
            (
                "2026-09-04-automation",
                valid_automation_source("2026-09-04"),
            ),
        ]

        for draft_id, source in cases:
            with self.subTest(draft_id=draft_id):
                identity = resolve_draft_identity(draft_id, source)
                scores = reader_access_scores(source, identity)
                self.assertGreaterEqual(
                    scores["general_reader_understanding"], 8.5
                )
                self.assertGreaterEqual(scores["public_readability"], 8.5)
                self.assertNotIn(
                    "quality_reader_access",
                    source_quality_reasons(source, identity),
                )

    def test_new_weekday_article_rewrites_long_mobile_paragraphs(self):
        source = valid_curiosity_source("2026-09-01")
        paragraph = next(
            block
            for block in source["news"][0]["content"]
            if block.get("t") == "p"
        )
        paragraph["text"] = "모바일에서 읽기 어려운 긴 설명 " * 30
        identity = resolve_draft_identity("2026-09-01", source)

        scores = reader_access_scores(source, identity)

        self.assertLess(scores["public_readability"], 8.5)
        self.assertIn(
            "quality_reader_access",
            source_quality_reasons(source, identity),
        )

    def test_new_weekday_article_requires_plain_summary_and_glossary(self):
        source = valid_daily_source("2026-08-31")
        source.pop("reader_access")
        identity = resolve_draft_identity("2026-08-31", source)

        scores = reader_access_scores(source, identity)

        self.assertLess(scores["general_reader_understanding"], 8.5)
        self.assertIn(
            "quality_reader_access",
            source_quality_reasons(source, identity),
        )

    def test_unrelated_reader_aid_cannot_mask_a_difficult_article(self):
        source = valid_curiosity_source("2026-09-01")
        source["reader_access"] = {
            "quick_summary": [
                "세탁기 사용 시간과 빨래 양을 맞추면 생활 전기 사용량을 줄일 수 있다.",
                "운동화 보관 장소의 습도를 낮추면 냄새와 소재 손상을 함께 줄일 수 있다.",
                "식재료 보관 온도는 종류마다 달라 냉장고 칸을 나눠 사용하는 편이 안전하다.",
            ],
            "glossary": [
                {"term": "세탁기", "meaning": "물과 세제를 사용해 옷의 오염을 자동으로 씻어 내는 생활 가전이다."},
                {"term": "운동화", "meaning": "걷기와 운동에 맞게 충격을 줄이도록 만든 신발 종류다."},
                {"term": "식재료", "meaning": "조리해 음식을 만들 때 사용하는 채소·고기·양념 같은 재료다."},
            ],
        }
        identity = resolve_draft_identity("2026-09-01", source)

        scores = reader_access_scores(source, identity)

        self.assertLess(scores["general_reader_understanding"], 8.5)
        self.assertIn(
            "quality_reader_access",
            source_quality_reasons(source, identity),
        )

    def test_single_five_block_reading_wall_cannot_pass_at_exactly_eight_point_five(self):
        source = valid_curiosity_source("2026-09-01")
        source["news"][0]["content"][1:1] = [
            {"t": "p", "text": f"이어지는 설명 문단 {index}"}
            for index in range(3)
        ]
        identity = resolve_draft_identity("2026-09-01", source)

        scores = reader_access_scores(source, identity)

        self.assertLess(scores["public_readability"], 8.5)
        self.assertIn(
            "quality_reader_access",
            source_quality_reasons(source, identity),
        )

    def test_project_story_scores_above_eight_point_five_for_general_readers(self):
        source = json.loads(
            (ROOT / "data/project_logs/2026-08-29.json").read_text(encoding="utf-8")
        )
        identity = resolve_draft_identity("2026-08-29-project", source)

        scores = project_reader_scores(source, identity)

        self.assertGreaterEqual(scores["general_reader_understanding"], 8.5)
        self.assertGreaterEqual(scores["public_readability"], 8.5)
        self.assertNotIn("quality_reader_access", source_quality_reasons(source, identity))

    def test_project_story_rewrites_instead_of_accepting_missing_reader_aids(self):
        source = json.loads(
            (ROOT / "data/project_logs/2026-08-29.json").read_text(encoding="utf-8")
        )
        source.pop("reader_access")
        identity = resolve_draft_identity("2026-08-29-project", source)

        scores = project_reader_scores(source, identity)

        self.assertLess(scores["general_reader_understanding"], 8.5)
        self.assertIn("quality_reader_access", source_quality_reasons(source, identity))

    def test_project_story_rejects_jargon_in_summary_and_long_mobile_paragraphs(self):
        source = json.loads(
            (ROOT / "data/project_logs/2026-08-29.json").read_text(encoding="utf-8")
        )
        source["reader_access"]["quick_summary"][0] = (
            "SMA20과 ATR을 적용해 S1 후보를 거르는 내부 알고리즘의 실행 결과를 확인한다."
        )
        source["news"][0]["content"][1]["text"] = "긴 모바일 문단 " * 40
        identity = resolve_draft_identity("2026-08-29-project", source)

        scores = project_reader_scores(source, identity)

        self.assertLess(scores["general_reader_understanding"], 8.5)
        self.assertLess(scores["public_readability"], 8.5)
        self.assertIn("quality_reader_access", source_quality_reasons(source, identity))

    def test_all_future_content_lanes_satisfy_new_contract(self):
        cases = [
            ("2026-08-04", valid_daily_source("2026-08-04")),
            ("2026-08-05-guide", valid_guide_source("2026-08-05")),
            ("2026-08-08-automation", valid_automation_source("2026-08-08")),
            ("2026-09-04-automation", valid_automation_source("2026-09-04")),
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

    def test_durable_article_requires_original_value_beyond_source_rewriting(self):
        source = valid_daily_source("2026-08-26")
        source["editorial"]["original_value"].pop("contribution")

        self.assertIn(
            "quality_original_value",
            source_quality_reasons(
                source, resolve_draft_identity("2026-08-26")
            ),
        )

    def test_future_monday_and_wednesday_require_distinct_weekly_lanes(self):
        monday = valid_daily_source("2026-08-31")
        wednesday = valid_daily_source("2026-09-02")

        monday_reasons = source_quality_reasons(
            monday, resolve_draft_identity("2026-08-31")
        )
        wednesday_reasons = source_quality_reasons(
            wednesday, resolve_draft_identity("2026-09-02")
        )

        self.assertNotIn("quality_weekly_lane", monday_reasons)
        self.assertNotIn("quality_weekly_lane", wednesday_reasons)
        monday["editorial"]["weekly_lane"] = "change_explainer"
        self.assertIn(
            "quality_weekly_lane",
            source_quality_reasons(monday, resolve_draft_identity("2026-08-31")),
        )

    def test_developer_insight_requires_traceable_source_research(self):
        source = valid_automation_source("2026-09-04")
        identity = resolve_draft_identity("2026-09-04-automation")

        self.assertNotIn("quality_reader_walkthrough", source_quality_reasons(source, identity))
        source["verification"]["source_urls"] = source["verification"]["source_urls"][:2]
        source["verification"]["source_count"] = 2

        reasons = source_quality_reasons(source, identity)
        self.assertIn("quality_insight_evidence", reasons)

    def test_developer_insight_does_not_require_a_code_block(self):
        source = valid_automation_source("2026-09-04")
        source["news"][0]["content"] = [
            block
            for block in source["news"][0]["content"]
            if block.get("t") != "code"
        ]

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-09-04-automation")
        )
        self.assertNotIn("quality_depth", reasons)

    def test_tuesday_and_thursday_curiosity_articles_use_timeless_quality_rules(self):
        for day in ("2026-09-01", "2026-09-03"):
            source = valid_curiosity_source(day)
            reasons = source_quality_reasons(source, resolve_draft_identity(day))

            with self.subTest(day=day):
                self.assertEqual(reasons, [])

    def test_curiosity_article_rejects_generic_daily_coverage(self):
        source = valid_curiosity_source()
        source["editorial"]["coverage"] = [
            "change",
            "mechanism",
            "comparison",
            "application",
            "limits",
            "decision",
        ]

        self.assertIn(
            "quality_editorial",
            source_quality_reasons(source, resolve_draft_identity("2026-09-01")),
        )

    def test_future_weekly_articles_require_a_hook_grounded_in_the_opening(self):
        source = valid_daily_source("2026-08-31")
        source["editorial"]["reader_hook"].pop("stakes")

        self.assertIn(
            "quality_reader_hook",
            source_quality_reasons(source, resolve_draft_identity("2026-08-31")),
        )

    def test_trend_cover_requires_specific_treatment_and_matching_image_metadata(self):
        source = valid_daily_source("2026-08-26")
        source["visual"]["cover"]["editorial_treatment"] = "generic_ai_card"
        source["images"]["cover"]["focal_subject"] = "다른 장면"

        self.assertIn(
            "quality_visual_trend",
            source_quality_reasons(
                source, resolve_draft_identity("2026-08-26")
            ),
        )

    def test_trend_cover_requires_descriptive_search_relevant_alt_text(self):
        source = valid_daily_source("2026-08-26")
        source["images"]["cover"]["alt"] = "대표 이미지"

        self.assertIn(
            "quality_visual_trend",
            source_quality_reasons(
                source, resolve_draft_identity("2026-08-26")
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

    def test_identity_accepts_friday_and_rejects_saturday_after_transition(self):
        friday = valid_automation_source("2026-08-28")
        saturday = valid_automation_source("2026-08-29")

        friday_reasons = source_quality_reasons(
            friday, resolve_draft_identity("2026-08-28-automation")
        )
        saturday_reasons = source_quality_reasons(
            saturday, resolve_draft_identity("2026-08-29-automation")
        )

        self.assertNotIn("quality_identity", friday_reasons)
        self.assertIn("quality_identity", saturday_reasons)

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

    def test_evergreen_daily_accepts_five_day_source_without_exception(self):
        source = valid_daily_source("2026-08-25")
        source["news"][0]["published_at"] = "2026-08-20T09:00:00+09:00"

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-08-25")
        )

        self.assertNotIn("quality_source_freshness", reasons)

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

    def test_change_impact_uses_a_concise_depth_range(self):
        identity = resolve_draft_identity("2026-08-26")

        policy = depth_policy_for(identity, "change_impact")

        self.assertEqual(policy["minimum_minutes"], 6)
        self.assertEqual(policy["maximum_minutes"], 12)

    def test_mobile_readability_rejects_wall_of_text_paragraphs(self):
        source = valid_daily_source("2026-08-26")

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-08-26")
        )

        self.assertIn("quality_readability", reasons)

    def test_mobile_readability_accepts_short_opening_and_paragraphs(self):
        source = valid_daily_source("2026-08-26")
        source["editorial"]["opening"] = (
            "로그인은 통과했지만 가입 마지막 단계에서 이메일 검증이 멈춘다. "
            "새 도메인을 기존 규칙과 함께 허용하면 해결할 수 있고, 배포 전 신규·기존 계정을 모두 확인한다."
        )
        for index, block in enumerate(source["news"][0]["content"]):
            if block.get("t") == "p":
                block["text"] = (
                    f"{index + 1}번째 확인 지점은 한 문단에 한 가지 조건만 설명한다. "
                    "모바일에서 빠르게 읽고 실제 설정과 결과를 바로 대조할 수 있다."
                )

        reasons = source_quality_reasons(
            source, resolve_draft_identity("2026-08-26")
        )

        self.assertNotIn("quality_readability", reasons)

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

    def test_project_story_accepts_a_thumbnail_first_infographic_cover(self):
        source = json.loads(
            (ROOT / "data/project_logs/2026-08-29.json").read_text(
                encoding="utf-8"
            )
        )
        identity = resolve_draft_identity("2026-08-29-project", source)

        reasons = source_quality_reasons(source, identity)

        self.assertNotIn("quality_visual_variety", reasons)
        self.assertNotIn("quality_visual_trend", reasons)
        self.assertNotIn("quality_visual_provenance", reasons)

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
