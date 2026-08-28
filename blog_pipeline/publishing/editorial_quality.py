"""Future-facing quality gates shared by export, copy UI, and CI."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .draft_identity import (
    EVERGREEN_DAILY_START,
    FRIDAY_AUTOMATION_SCHEDULE_START,
    WEEKLY_EDITORIAL_LANES_START,
    category_for_identity,
    editorial_lane_for_identity,
    is_regular_automation_day,
    publication_mode_for_identity,
    regular_schedule_for_identity,
)


DAILY_QUALITY_POLICY_START = date(2026, 7, 19)
AUTOMATION_QUALITY_POLICY_START = date(2026, 7, 25)
GUIDE_QUALITY_POLICY_START = date(2026, 7, 21)
PROJECT_QUALITY_POLICY_START = date(2026, 8, 28)
VISUAL_ROLE_POLICY_START = date(2026, 7, 22)
COVER_VARIETY_POLICY_START = date(2026, 7, 29)
REVISIT_VALUE_POLICY_START = date(2026, 8, 4)
NATURAL_VOICE_POLICY_START = date(2026, 8, 4)
AD_FLOW_POLICY_START = date(2026, 8, 4)
SOURCE_RECENCY_POLICY_START = date(2026, 8, 6)
SEARCH_CONVERSION_POLICY_START = date(2026, 8, 11)
ORIGINAL_VALUE_POLICY_START = date(2026, 8, 26)
VISUAL_TREND_POLICY_START = date(2026, 8, 26)
MOBILE_READABILITY_POLICY_START = date(2026, 8, 26)
READER_HOOK_POLICY_START = date(2026, 8, 28)
PUBLISH_GATE_START = DAILY_QUALITY_POLICY_START

PUBLISHABLE_ORIGINS = {
    "capture",
    "annotated_capture",
    "measured_chart",
    "imagegen",
}
ORIGIN_EVIDENCE = {
    "capture": "screenshot",
    "annotated_capture": "screenshot",
    "measured_chart": "chart",
    "imagegen": "diagram",
}
VISUAL_QA_KEYS = {
    "topic_match",
    "caption_match",
    "mobile_readable",
    "text_reviewed",
    "not_generic",
}
DAILY_COVERAGE_LEGACY = {
    "change",
    "mechanism",
    "comparison",
    "application",
    "limits",
    "checklist",
}
DAILY_COVERAGE = {
    "change",
    "mechanism",
    "comparison",
    "application",
    "limits",
    "decision",
}
CURIOSITY_COVERAGE = {
    "question",
    "mechanism",
    "example",
    "misconception",
    "evidence",
    "takeaway",
}
CURIOSITY_LANES = {
    "curiosity_mechanism",
    "curiosity_myth_history",
}
AUTOMATION_COVERAGE = {
    "problem",
    "setup",
    "implementation",
    "evidence",
    "comparison",
    "failure",
    "rollback",
}
DEVELOPER_INSIGHT_COVERAGE = {
    "question",
    "sources",
    "mechanism",
    "comparison",
    "application",
    "limits",
    "judgment",
}
GUIDE_COVERAGE = {
    "foundation",
    "request_flow",
    "stack",
    "data",
    "security",
    "operations",
    "plan",
}
PROJECT_COVERAGE = {
    "motivation",
    "architecture",
    "safety",
    "evidence",
    "limits",
    "next_step",
}
RENDERABLE_BLOCK_TYPES = {
    "h",
    "p",
    "table",
    "visual",
    "code",
    "ul",
    "quote",
    "ad_break",
}
FALLBACK_IMAGE_PROVIDERS = {
    "deterministic-fallback",
    "deterministic_fallback",
    "pillow",
}
CAPTURE_TOOLS = {
    "browser",
    "computer-use",
    "playwright",
    "system-screenshot",
    "terminal",
}
BANNED_EDITORIAL_PHRASES = {
    "정리해보겠습니다",
    "개발자 편집자의 견해",
    "자동화로 작성했습니다",
    "ai로 작성했습니다",
    "자동 생성 데일리 다이제스트",
    "본문은 핵심 내용 요약과 학습용 문제로 구성",
    "승원의 메모",
}
FUTURE_AI_CLICHES = {
    "이번 글에서는",
    "본 글에서는",
    "지금부터 알아보겠습니다",
    "살펴보겠습니다",
    "알아보겠습니다",
    "다음과 같습니다",
    "결론적으로",
    "요약하자면",
    "도움이 되길 바랍니다",
}
INTERNAL_REVISIT_LABELS = {
    "다시 찾을 때",
    "처음 읽기",
    "적용할 때",
    "막혔을 때",
    "다시 확인할 변화",
    "재방문 가치",
    "reuse_case",
    "failure_case",
    "update_triggers",
}
REPORT_ONLY_HEADINGS = {
    "개요",
    "배경",
    "현황",
    "분석",
    "결론",
    "요약",
    "시사점",
    "제언",
}
EXPLICIT_EDITORIAL_HEADINGS = {
    "독자에게 미치는 영향",
    "사용자에게 미치는 영향",
    "개발자에게 미치는 영향",
    "우리에게 미치는 영향",
    "왜 중요한가",
    "독자가 얻는 것",
}
CLICKBAIT_TITLE_PHRASES = {
    "충격",
    "소름",
    "대박",
    "역대급",
    "무조건 봐야",
    "안 보면 손해",
}
TITLE_INTENT_MARKERS = {
    "방법",
    "이유",
    "차이",
    "기준",
    "확인",
    "해결",
    "바뀐",
    "적용",
    "막는",
    "줄이는",
    "늘리는",
    "어떻게",
    "왜",
    "까지",
    "전후",
    "순서",
    "선택",
    "설정",
    "실험",
    "구현",
    "로드맵",
    "맵",
    "분석",
    "활용",
    "쓰는",
    "쓰일",
}
GENERIC_TAGS = {
    "ai",
    "it",
    "개발",
    "뉴스",
    "정보",
    "최신",
    "오늘",
    "블로그",
}
SEARCH_STOP_WORDS = {
    "그리고",
    "그러나",
    "위한",
    "대한",
    "에서",
    "으로",
    "하는",
    "있는",
    "없는",
    "이번",
    "오늘",
    "최신",
}
RELATED_POST_ROLES = {"foundation", "next_step"}
BANNED_COVER_COMPOSITIONS = {
    "three_column_cards",
    "four_step_cards",
    "centered_dashboard_grid",
    "title_slide",
    "linear_flow",
    "process_diagram",
    "roadmap",
    "comparison_grid",
    "timeline_cards",
    "split_panel_infographic",
    "dashboard",
}
REQUIRED_COVER_KIND = "editorial_scene"
REQUIRED_COVER_PROMPT_PREFIXES = (
    "use case: illustration-story",
    "use case: photorealistic-natural",
    "use case: stylized-concept",
)
REQUIRED_COVER_PROMPT_TOKEN = "asset intent: editorial-scene"
ARTICLE_SHAPES = {
    "change_impact",
    "hands_on_test",
    "decision_guide",
    "incident_trace",
    "troubleshooting",
    "research_interpretation",
    "ecosystem_map",
    "official_document_guide",
    "evidence_based_list",
    "developer_career_analysis",
}
REVISIT_ARTIFACT_TYPES = {
    "command_recipe",
    "configuration",
    "decision_matrix",
    "checklist",
    "troubleshooting_tree",
    "experiment_fixture",
    "source_map",
    "evaluation_matrix",
    "skill_map",
    "reading_guide",
}
RENDER_FAMILIES = {
    "photorealistic_natural",
    "editorial_collage",
    "flat_illustration",
    "ink_drawing",
    "isometric_model",
    "tactile_paper",
    "macro_object",
}
ORIGINAL_PROOF_METHODS = {
    "executed_test",
    "document_comparison",
    "source_triangulation",
    "configuration_walkthrough",
    "incident_trace",
    "measured_comparison",
}
EDITORIAL_TREATMENTS = {
    "tactile_realism",
    "documentary_closeup",
    "quiet_minimalism",
    "playful_surrealism",
    "local_workplace",
}
EDITORIAL_LENGTH_RULES = {
    "headline": (25, 60),
    "opening": (120, 600),
    "closing": (100, 1000),
    "action": (30, 500),
    "audience_problem": (40, 500),
    "reader_takeaway": (40, 500),
    "why_now": (40, 500),
    "topic_key": (6, 100),
    "reader_question": (30, 300),
}
DEPTH_POLICIES = {
    "daily_news": {
        "minimum_headings": 5,
        "maximum_headings": 7,
        "minimum_visuals": 2,
        "maximum_visuals": 6,
        "minimum_minutes": 8,
        "maximum_minutes": 16,
        "minimum_blocks": 15,
        "required_block_types": {"table", "ul"},
    },
    "automation_case": {
        "minimum_headings": 5,
        "maximum_headings": 8,
        "minimum_visuals": 3,
        "maximum_visuals": 6,
        "minimum_minutes": 10,
        "maximum_minutes": 20,
        "minimum_blocks": 17,
        "required_block_types": {"table", "ul", "code"},
    },
    "evergreen_guide": {
        "minimum_headings": 6,
        "maximum_headings": 9,
        "minimum_visuals": 3,
        "maximum_visuals": 6,
        "minimum_minutes": 10,
        "maximum_minutes": 20,
        "minimum_blocks": 19,
        "required_block_types": {"table", "ul"},
    },
    "project_log": {
        "minimum_headings": 5,
        "maximum_headings": 7,
        "minimum_visuals": 2,
        "maximum_visuals": 5,
        "minimum_minutes": 8,
        "maximum_minutes": 16,
        "minimum_blocks": 15,
        "required_block_types": {"table", "ul"},
    },
}


def depth_policy_for(identity, article_shape=""):
    """Return a copy so a concise change alert is not padded into a report."""
    policy = dict(DEPTH_POLICIES[identity.content_type])
    if editorial_lane_for_identity(identity) in CURIOSITY_LANES:
        policy.update(
            minimum_headings=4,
            maximum_headings=7,
            minimum_visuals=2,
            maximum_visuals=5,
            minimum_minutes=6,
            maximum_minutes=12,
            minimum_blocks=13,
        )
    if identity.content_type == "daily_news" and plain(article_shape) == "change_impact":
        policy.update(minimum_minutes=6, maximum_minutes=12)
    if editorial_lane_for_identity(identity) == "developer_insight":
        policy.update(
            minimum_headings=5,
            maximum_headings=8,
            minimum_visuals=3,
            maximum_visuals=6,
            minimum_minutes=8,
            maximum_minutes=20,
            minimum_blocks=15,
            required_block_types={"table", "ul"},
        )
    return policy


def plain(value):
    return " ".join(str(value or "").split())


def policy_active(identity):
    publish_date = date.fromisoformat(identity.publish_date)
    start = {
        "automation_case": AUTOMATION_QUALITY_POLICY_START,
        "evergreen_guide": GUIDE_QUALITY_POLICY_START,
        "project_log": PROJECT_QUALITY_POLICY_START,
    }.get(identity.content_type, DAILY_QUALITY_POLICY_START)
    return publish_date >= start


def _is_http_url(value):
    try:
        parsed = urlsplit(plain(value))
    except ValueError:
        return False
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)


def _canonical_url(value):
    text = plain(value)
    if not _is_http_url(text):
        return ""
    parsed = urlsplit(text)
    query = sorted(
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower() not in {"fbclid", "gclid", "ref", "source"}
    )
    path = re.sub(r"/+", "/", parsed.path or "/").rstrip("/") or "/"
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower().removeprefix("www."),
            path,
            urlencode(query),
            "",
        )
    )


def _text_values(day):
    editorial = day.get("editorial") if isinstance(day.get("editorial"), dict) else {}
    values = [
        editorial.get("opening"),
        editorial.get("closing"),
        editorial.get("action"),
    ]
    for item in day.get("news", []) if isinstance(day.get("news"), list) else []:
        if not isinstance(item, dict):
            continue
        values.extend([item.get("title_kr"), item.get("blurb_kr")])
        for block in item.get("content", []) if isinstance(item.get("content"), list) else []:
            if not isinstance(block, dict):
                continue
            values.extend([block.get("text"), block.get("caption")])
            values.extend(block.get("items") if isinstance(block.get("items"), list) else [])
            values.extend(block.get("headers") if isinstance(block.get("headers"), list) else [])
            for row in block.get("rows") if isinstance(block.get("rows"), list) else []:
                if isinstance(row, list):
                    values.extend(row)
    for post in day.get("related_posts", []) if isinstance(day.get("related_posts"), list) else []:
        if isinstance(post, dict):
            values.extend([post.get("title"), post.get("reason")])
    return values


def estimate_read_minutes(day):
    length = sum(len(plain(value)) for value in _text_values(day))
    return max(2, (length + 449) // 450)


def _has_complete_qa(value):
    qa = value.get("qa") if isinstance(value, dict) else None
    return isinstance(qa, dict) and all(qa.get(key) is True for key in VISUAL_QA_KEYS)


def _aware_datetime(value):
    try:
        parsed = datetime.fromisoformat(plain(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _backfill_deadline(source, scheduled):
    """Allow truthful evidence timestamps for an explicitly recorded short backfill."""
    backfill = source.get("backfill") if isinstance(source.get("backfill"), dict) else {}
    created = _aware_datetime(backfill.get("created_at"))
    reason = plain(backfill.get("reason"))
    if not scheduled or not created or len(reason) < 20:
        return None
    if created.utcoffset() != timedelta(hours=9):
        return None
    if not scheduled < created <= scheduled + timedelta(hours=72):
        return None
    return created


def measurement_digest(brief):
    record = {
        key: brief.get(key)
        for key in (
            "measurement_source",
            "unit",
            "sample_count",
            "measurement_environment",
            "data_points",
        )
    }
    payload = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _strict_text(value, *, allow_empty=False):
    return isinstance(value, str) and (allow_empty or bool(plain(value)))


def _strict_text_list(value, *, minimum=0):
    return (
        isinstance(value, list)
        and len(value) >= minimum
        and all(_strict_text(item) for item in value)
    )


def _search_terms(value):
    return {
        token
        for token in re.findall(r"[0-9a-z가-힣+#.]+", plain(value).casefold())
        if len(token) >= 2 and token not in SEARCH_STOP_WORDS
    }


def _shares_search_term(value, terms):
    compact = re.sub(r"\s+", "", plain(value).casefold())
    return any(term in compact or compact in term for term in terms if len(term) >= 2)


def _schema_reasons(source, identity, *, require_images=True):
    """Reject JSON values that would otherwise render as Python repr strings."""
    invalid = False
    required_top_text = (
        "draft_id",
        "publish_date",
        "date_label",
        "weekday",
        "content_type",
        "content_label",
        "category",
        "scheduled_at",
        "primary_query",
    )
    invalid |= any(not _strict_text(source.get(key)) for key in required_top_text)
    invalid |= not _strict_text_list(source.get("tags"), minimum=1)

    editorial = source.get("editorial")
    if not isinstance(editorial, dict):
        invalid = True
        editorial = {}
    for key in (
        "headline",
        "opening",
        "closing",
        "action",
        "audience_problem",
        "reader_takeaway",
        "why_now",
        "topic_key",
        "reader_question",
    ):
        invalid |= not _strict_text(editorial.get(key))
    invalid |= not _strict_text_list(editorial.get("entities"), minimum=1)
    invalid |= not _strict_text_list(editorial.get("coverage"), minimum=1)

    news = source.get("news")
    item = news[0] if isinstance(news, list) and len(news) == 1 else None
    if not isinstance(item, dict):
        invalid = True
        item = {}
    for key in ("title_kr", "source", "url", "published_at", "blurb_kr"):
        invalid |= not _strict_text(item.get(key))
    references = item.get("references")
    if not isinstance(references, list):
        invalid = True
        references = []
    for reference in references:
        if not isinstance(reference, dict):
            invalid = True
            continue
        invalid |= any(
            not _strict_text(reference.get(key))
            for key in ("kind", "title", "url")
        )

    content = item.get("content")
    if not isinstance(content, list):
        invalid = True
        content = []
    for block in content:
        if not isinstance(block, dict) or not _strict_text(block.get("t")):
            invalid = True
            continue
        kind = block["t"]
        if kind in {"h", "p", "code", "quote"}:
            invalid |= not _strict_text(block.get("text"))
            if "language" in block:
                invalid |= not _strict_text(block.get("language"))
        elif kind == "visual":
            invalid |= not _strict_text(block.get("image"))
            invalid |= not _strict_text(block.get("caption"))
        elif kind == "ul":
            invalid |= not _strict_text_list(block.get("items"), minimum=1)
        elif kind == "table":
            invalid |= not _strict_text(block.get("caption"))
            invalid |= not _strict_text_list(block.get("headers"), minimum=1)
            rows = block.get("rows")
            if not isinstance(rows, list) or not rows:
                invalid = True
            else:
                invalid |= any(
                    not _strict_text_list(row, minimum=1) for row in rows
                )
        elif kind != "ad_break":
            invalid = True
        if "reusable" in block:
            invalid |= not isinstance(block.get("reusable"), bool)
        if "reuse_label" in block:
            invalid |= not _strict_text(block.get("reuse_label"))
        if "collapsed" in block:
            invalid |= kind != "code" or not isinstance(block.get("collapsed"), bool)
        if "summary" in block:
            invalid |= kind != "code" or not _strict_text(block.get("summary"))

    related = source.get("related_posts")
    if not isinstance(related, list):
        invalid = True
        related = []
    for post in related:
        if not isinstance(post, dict):
            invalid = True
            continue
        invalid |= any(
            not _strict_text(post.get(key)) for key in ("title", "url", "reason")
        )

    visual = source.get("visual")
    briefs = visual.get("assets") if isinstance(visual, dict) else None
    if not isinstance(briefs, list):
        invalid = True
        briefs = []
    for brief in briefs:
        if not isinstance(brief, dict):
            invalid = True
            continue
        invalid |= any(
            not _strict_text(brief.get(key))
            for key in (
                "label",
                "steps",
                "curiosity_hook",
                "evidence_type",
                "logic_type",
                "origin",
            )
        )
        invalid |= not _strict_text_list(brief.get("scene_label"), minimum=2)
        if "condition" in brief:
            invalid |= not _strict_text(brief.get("condition"))
        origin = brief.get("origin")
        if origin == "imagegen":
            invalid |= any(
                not _strict_text(brief.get(key))
                for key in ("generation_prompt", "generation_model")
            )
            invalid |= not _strict_text_list(
                brief.get("korean_labels"), minimum=2
            )
        elif origin in {"capture", "annotated_capture"}:
            invalid |= any(
                not _strict_text(brief.get(key))
                for key in ("capture_tool", "capture_target", "captured_at")
            )
            for key in ("capture_note", "source_url"):
                if key in brief:
                    invalid |= not _strict_text(brief.get(key))
        elif origin == "measured_chart":
            invalid |= any(
                not _strict_text(brief.get(key))
                for key in (
                    "measurement_source",
                    "unit",
                    "measurement_environment",
                )
            )
            sample_count = brief.get("sample_count")
            invalid |= not isinstance(sample_count, int) or isinstance(
                sample_count, bool
            )
            points = brief.get("data_points")
            if not isinstance(points, list):
                invalid = True
            else:
                invalid |= any(
                    not isinstance(point, dict)
                    or not _strict_text(point.get("label"))
                    or not isinstance(point.get("value"), (int, float))
                    or isinstance(point.get("value"), bool)
                    for point in points
                )

    images = source.get("images")
    if not isinstance(images, dict):
        invalid |= require_images
        images = {}
    for key, image in images.items():
        if key != "cover" and not re.fullmatch(r"visual_\d+", str(key)):
            continue
        if not isinstance(image, dict):
            invalid = True
            continue
        invalid |= any(
            not _strict_text(image.get(field)) for field in ("origin", "alt")
        )
        for field in (
            "path",
            "url",
            "sha256",
            "generation_prompt",
            "generation_model",
            "capture_tool",
            "capture_target",
            "captured_at",
            "capture_sha256",
            "measurement_sha256",
        ):
            if field in image:
                invalid |= not _strict_text(image.get(field))

    generation = source.get("generation")
    if not isinstance(generation, dict):
        invalid = True
        generation = {}
    invalid |= any(
        not _strict_text(generation.get(key))
        for key in ("provider", "model", "image_provider", "image_policy")
    )
    revision = generation.get("revision")
    invalid |= not isinstance(revision, int) or isinstance(revision, bool)

    if (
        identity.content_type == "automation_case"
        and editorial_lane_for_identity(identity) == "developer_insight"
    ):
        verification = source.get("verification")
        if not isinstance(verification, dict):
            invalid = True
            verification = {}
        for key in (
            "mode",
            "checked_at",
            "scope",
            "method",
            "selection_rule",
            "limitations",
            "problem_lane",
            "tool_brand",
        ):
            invalid |= not _strict_text(verification.get(key))
        invalid |= not _strict_text_list(
            verification.get("source_urls"), minimum=3
        )
        invalid |= not _strict_text_list(
            verification.get("evidence_files"), minimum=1
        )
        source_count = verification.get("source_count")
        invalid |= not isinstance(source_count, int) or isinstance(
            source_count, bool
        )
    elif identity.content_type == "automation_case":
        verification = source.get("verification")
        if not isinstance(verification, dict):
            invalid = True
            verification = {}
        for key in (
            "mode",
            "started_at",
            "completed_at",
            "stdout_excerpt",
            "input_fixture",
            "expected",
            "actual",
            "failure",
            "rollback",
            "problem_lane",
            "tool_brand",
        ):
            invalid |= not _strict_text(verification.get(key))
        invalid |= not _strict_text_list(
            verification.get("commands"), minimum=1
        )
        invalid |= not _strict_text_list(
            verification.get("evidence_files"), minimum=1
        )
        exit_code = verification.get("command_exit_code")
        invalid |= not isinstance(exit_code, int) or isinstance(exit_code, bool)
        environment = verification.get("environment")
        if not isinstance(environment, dict):
            invalid = True
            environment = {}
        invalid |= any(
            not _strict_text(environment.get(key))
            for key in ("os", "runtime", "tool_version", "source_revision")
        )
        if "measurement_files" in verification:
            invalid |= not _strict_text_list(
                verification.get("measurement_files")
            )
        if "measurement_note" in verification:
            invalid |= not _strict_text(verification.get("measurement_note"))

    return ["quality_schema"] if invalid else []


def _meaningful_blocks(content):
    output = []
    for block in content if isinstance(content, list) else []:
        if not isinstance(block, dict):
            continue
        kind = block.get("t")
        if not isinstance(kind, str) or kind not in RENDERABLE_BLOCK_TYPES:
            continue
        if kind == "ad_break":
            output.append(block)
        elif kind in {"h", "p", "code", "quote"} and plain(block.get("text")):
            output.append(block)
        elif kind == "visual" and plain(block.get("image")) and plain(block.get("caption")):
            output.append(block)
        elif (
            kind == "ul"
            and isinstance(block.get("items"), list)
            and any(plain(item) for item in block["items"])
        ):
            output.append(block)
        elif (
            kind == "table"
            and isinstance(block.get("headers"), list)
            and block["headers"]
            and isinstance(block.get("rows"), list)
            and block["rows"]
            and plain(block.get("caption"))
        ):
            output.append(block)
    return output


def _identity_reasons(source, identity):
    publish_day = date.fromisoformat(identity.publish_date)
    weekday_labels = ["월", "화", "수", "목", "금", "토", "일"]
    publication_mode = plain(source.get("publication_mode")) or "scheduled"
    manual_extra = publication_mode == "manual_extra"
    expected_publication_mode = publication_mode_for_identity(identity)
    expected_category = category_for_identity(identity)
    expected = {
        "schema_version": 3,
        "format": "lead-story-v1",
        "draft_id": identity.draft_id,
        "publish_date": identity.publish_date,
        "date_label": (
            f"{publish_day.year}. {publish_day.month}. {publish_day.day}"
        ),
        "weekday": weekday_labels[publish_day.weekday()],
        "content_type": identity.content_type,
        "content_label": identity.content_label,
        "category": expected_category,
    }
    invalid = any(source.get(key) != value for key, value in expected.items())
    if identity.content_type == "automation_case":
        if manual_extra:
            scheduled = _aware_datetime(source.get("scheduled_at"))
            invalid = invalid or not (
                scheduled
                and scheduled.date() == publish_day
                and scheduled.utcoffset() == timedelta(hours=9)
                and len(plain(source.get("manual_extra_reason"))) >= 20
            )
        else:
            invalid = invalid or publication_mode != expected_publication_mode
            invalid = invalid or not is_regular_automation_day(publish_day)
            invalid = invalid or source.get("scheduled_at") != regular_schedule_for_identity(
                identity
            )
    elif identity.content_type == "evergreen_guide":
        if manual_extra:
            scheduled = _aware_datetime(source.get("scheduled_at"))
            invalid = invalid or not (
                scheduled
                and scheduled.date() == publish_day
                and scheduled.utcoffset() == timedelta(hours=9)
            )
        else:
            expected_schedule = regular_schedule_for_identity(identity)
            invalid = invalid or publication_mode != "scheduled"
            invalid = invalid or not expected_schedule
            invalid = invalid or source.get("scheduled_at") != expected_schedule
    else:
        invalid = invalid or publication_mode != expected_publication_mode
        invalid = invalid or source.get("scheduled_at") != regular_schedule_for_identity(
            identity
        )
    if invalid:
        return ["quality_identity"]
    return []


def _editorial_reasons(source, identity):
    reasons = []
    editorial = source.get("editorial") if isinstance(source.get("editorial"), dict) else {}
    if any(
        not minimum <= len(plain(editorial.get(key))) <= maximum
        for key, (minimum, maximum) in EDITORIAL_LENGTH_RULES.items()
    ):
        reasons.append("quality_editorial")
    entities = editorial.get("entities")
    if not (
        isinstance(entities, list)
        and 1 <= len(entities) <= 6
        and all(2 <= len(plain(item)) <= 80 for item in entities)
        and len({plain(item).casefold() for item in entities if plain(item)}) == len(entities)
    ):
        reasons.append("quality_editorial")
    weekly_lane = editorial_lane_for_identity(identity)
    required_coverage = {
        "automation_case": AUTOMATION_COVERAGE,
        "evergreen_guide": GUIDE_COVERAGE,
        "project_log": PROJECT_COVERAGE,
    }.get(identity.content_type)
    if weekly_lane == "developer_insight":
        required_coverage = DEVELOPER_INSIGHT_COVERAGE
    if weekly_lane in CURIOSITY_LANES:
        required_coverage = CURIOSITY_COVERAGE
    if required_coverage is None:
        required_coverage = (
            DAILY_COVERAGE
            if date.fromisoformat(identity.publish_date) >= NATURAL_VOICE_POLICY_START
            else DAILY_COVERAGE_LEGACY
        )
    coverage_values = editorial.get("coverage")
    coverage = {
        plain(value).casefold()
        for value in (coverage_values if isinstance(coverage_values, list) else [])
        if plain(value)
    }
    if not required_coverage.issubset(coverage):
        reasons.append("quality_editorial")

    tags = source.get("tags")
    normalized_tags = [plain(tag).casefold() for tag in tags] if isinstance(tags, list) else []
    if not (
        5 <= len(normalized_tags) <= 8
        and all(len(tag) >= 2 for tag in normalized_tags)
        and len(set(normalized_tags)) == len(normalized_tags)
    ):
        reasons.append("quality_tags")
    return reasons


def _search_metadata_reasons(source, identity):
    """Keep future titles useful in search without turning them into clickbait."""
    if date.fromisoformat(identity.publish_date) < NATURAL_VOICE_POLICY_START:
        return []
    editorial = source.get("editorial") if isinstance(source.get("editorial"), dict) else {}
    headline = plain(editorial.get("headline"))
    searchable = headline.casefold()
    primary_terms = _search_terms(source.get("primary_query"))
    entities = editorial.get("entities") if isinstance(editorial.get("entities"), list) else []
    primary_terms.update(
        term for entity in entities for term in _search_terms(entity)
    )
    tags = source.get("tags") if isinstance(source.get("tags"), list) else []
    normalized_tags = [plain(tag).casefold() for tag in tags]
    matched_tags = sum(_shares_search_term(tag, primary_terms) for tag in tags)
    invalid = (
        not primary_terms
        or not _shares_search_term(headline, primary_terms)
        or not any(marker in searchable for marker in TITLE_INTENT_MARKERS)
        or any(phrase in searchable for phrase in CLICKBAIT_TITLE_PHRASES)
        or any(tag.startswith("#") or len(tag) > 30 for tag in normalized_tags)
        or any(tag in GENERIC_TAGS for tag in normalized_tags)
        or matched_tags < 2
    )
    return ["quality_search_metadata"] if invalid else []


def _search_conversion_reasons(source, identity):
    """Turn one real search question into a focused title and useful next clicks."""
    if date.fromisoformat(identity.publish_date) < SEARCH_CONVERSION_POLICY_START:
        return []
    editorial = source.get("editorial") if isinstance(source.get("editorial"), dict) else {}
    intent = editorial.get("search_intent") if isinstance(editorial.get("search_intent"), dict) else {}
    query = plain(intent.get("query"))
    query_terms = _search_terms(query)
    primary_terms = _search_terms(source.get("primary_query"))
    headline = plain(editorial.get("headline"))
    headline_prefix = re.sub(r"\s+", "", headline[:20].casefold())
    compact_query = re.sub(r"\s+", "", query.casefold())

    related = source.get("related_posts") if isinstance(source.get("related_posts"), list) else []
    roles = {
        plain(post.get("role")).casefold()
        for post in related
        if isinstance(post, dict)
    }
    related_valid = (
        len(related) >= 2
        and RELATED_POST_ROLES.issubset(roles)
        and all(
            isinstance(post, dict)
            and plain(post.get("role")).casefold() in RELATED_POST_ROLES
            and len(plain(post.get("reason"))) >= 12
            for post in related
        )
    )
    invalid = (
        not 2 <= len(query) <= 40
        or not query_terms
        or not query_terms.intersection(primary_terms)
        or compact_query not in headline_prefix
        or len(plain(intent.get("reader_need"))) < 20
        or len(plain(intent.get("answer_format"))) < 10
        or not related_valid
    )
    return ["quality_search_conversion"] if invalid else []


def _revisit_value_reasons(source, identity):
    """Require one durable artifact and three explicit return reasons."""
    if date.fromisoformat(identity.publish_date) < REVISIT_VALUE_POLICY_START:
        return []
    editorial = source.get("editorial") if isinstance(source.get("editorial"), dict) else {}
    revisit = editorial.get("revisit") if isinstance(editorial.get("revisit"), dict) else {}
    triggers = revisit.get("update_triggers")
    normalized_triggers = (
        [plain(value).casefold() for value in triggers]
        if isinstance(triggers, list)
        else []
    )
    invalid = (
        plain(editorial.get("article_shape")) not in ARTICLE_SHAPES
        or any(
            not _strict_text(revisit.get(key))
            for key in ("quick_answer", "reuse_case", "failure_case")
        )
        or plain(revisit.get("artifact_type")) not in REVISIT_ARTIFACT_TYPES
        or not 2 <= len(normalized_triggers) <= 4
        or any(len(value) < 4 for value in normalized_triggers)
        or len(set(normalized_triggers)) != len(normalized_triggers)
    )

    news = source.get("news") if isinstance(source.get("news"), list) else []
    item = news[0] if len(news) == 1 and isinstance(news[0], dict) else {}
    content = item.get("content") if isinstance(item.get("content"), list) else []
    marked_reusable = [
        block
        for block in content
        if isinstance(block, dict)
        and block.get("reusable") is True
    ]
    reusable_count_invalid = (
        len(marked_reusable) != 1
        if identity.content_type
        in {"evergreen_guide", "automation_case", "project_log"}
        else len(marked_reusable) > 1
    )
    reusable_metadata_invalid = bool(marked_reusable) and (
        marked_reusable[0].get("t") not in {"code", "table", "ul"}
        or not _strict_text(marked_reusable[0].get("reuse_label"))
    )
    if reusable_count_invalid or reusable_metadata_invalid:
        invalid = True
    return ["quality_revisit_value"] if invalid else []


def _original_value_reasons(source, identity):
    """Require an explicit value-add plan beyond rewriting the source article."""
    if date.fromisoformat(identity.publish_date) < ORIGINAL_VALUE_POLICY_START:
        return []
    editorial = (
        source.get("editorial")
        if isinstance(source.get("editorial"), dict)
        else {}
    )
    original = (
        editorial.get("original_value")
        if isinstance(editorial.get("original_value"), dict)
        else {}
    )
    minimum_lengths = {
        "durable_question": 20,
        "source_gap": 24,
        "contribution": 30,
        "reader_outcome": 20,
        "limits": 16,
    }
    invalid = (
        plain(original.get("proof_method")) not in ORIGINAL_PROOF_METHODS
        or any(
            len(plain(original.get(key))) < minimum
            for key, minimum in minimum_lengths.items()
        )
    )
    return ["quality_original_value"] if invalid else []


def _weekly_lane_reasons(source, identity):
    """Keep Monday, Wednesday, and Friday from becoming the same generic post."""
    publish_day = date.fromisoformat(identity.publish_date)
    expected = editorial_lane_for_identity(identity)
    policy_applies = (
        identity.content_type == "daily_news"
        and publish_day >= WEEKLY_EDITORIAL_LANES_START
    ) or (
        identity.content_type == "automation_case"
        and publish_day >= FRIDAY_AUTOMATION_SCHEDULE_START
    )
    if not policy_applies:
        return []

    editorial = source.get("editorial") if isinstance(source.get("editorial"), dict) else {}
    article_shape = plain(editorial.get("article_shape"))
    invalid = not expected or plain(editorial.get("weekly_lane")) != expected

    news = source.get("news") if isinstance(source.get("news"), list) else []
    item = news[0] if len(news) == 1 and isinstance(news[0], dict) else {}
    content = item.get("content") if isinstance(item.get("content"), list) else []
    reusable = [
        block
        for block in content
        if isinstance(block, dict) and block.get("reusable") is True
    ]
    if expected == "evergreen_problem":
        invalid |= article_shape == "change_impact" or len(reusable) != 1
    elif expected == "change_explainer":
        invalid |= article_shape not in {
            "change_impact",
            "incident_trace",
            "research_interpretation",
            "troubleshooting",
        }
    elif expected == "executed_experiment":
        invalid |= article_shape not in {
            "hands_on_test",
            "incident_trace",
            "troubleshooting",
        }
    elif expected == "developer_insight":
        invalid |= article_shape not in {
            "ecosystem_map",
            "official_document_guide",
            "evidence_based_list",
            "developer_career_analysis",
            "research_interpretation",
            "decision_guide",
            "hands_on_test",
            "troubleshooting",
        }
    elif expected in CURIOSITY_LANES:
        invalid |= article_shape not in {
            "research_interpretation",
            "decision_guide",
            "incident_trace",
            "troubleshooting",
        }
    return ["quality_weekly_lane"] if invalid else []


def _automation_walkthrough_reasons(source, identity):
    """Keep Friday experiments usable by a beginner before showing proof details."""
    publish_day = date.fromisoformat(identity.publish_date)
    if (
        identity.content_type != "automation_case"
        or publish_day < FRIDAY_AUTOMATION_SCHEDULE_START
        or editorial_lane_for_identity(identity) == "developer_insight"
    ):
        return []

    editorial = source.get("editorial") if isinstance(source.get("editorial"), dict) else {}
    walkthrough = (
        editorial.get("reader_walkthrough")
        if isinstance(editorial.get("reader_walkthrough"), dict)
        else {}
    )
    prerequisites = walkthrough.get("prerequisites")
    prerequisites = prerequisites if isinstance(prerequisites, list) else []
    steps = walkthrough.get("steps")
    steps = steps if isinstance(steps, list) else []

    news = source.get("news") if isinstance(source.get("news"), list) else []
    item = news[0] if len(news) == 1 and isinstance(news[0], dict) else {}
    content = item.get("content") if isinstance(item.get("content"), list) else []
    headings = [
        plain(block.get("text"))
        for block in content
        if isinstance(block, dict) and block.get("t") == "h"
    ]
    heading_text = "\n".join(headings)
    first_code_index = next(
        (
            index
            for index, block in enumerate(content)
            if isinstance(block, dict) and block.get("t") == "code"
        ),
        -1,
    )
    developer_record_index = next(
        (
            index
            for index, block in enumerate(content)
            if isinstance(block, dict)
            and block.get("t") == "h"
            and "개발 기록" in plain(block.get("text"))
        ),
        -1,
    )
    early_blocks = (
        content[:developer_record_index] if developer_record_index >= 0 else content
    )
    early_text = "\n".join(
        plain(block.get("text"))
        for block in early_blocks
        if isinstance(block, dict) and block.get("t") in {"h", "p", "quote"}
    ).casefold()
    developer_only_markers = (
        "sha-256",
        "커밋 해시",
        "소스 커밋",
        "output_exists",
        "fixture 생성",
    )

    invalid = (
        plain(walkthrough.get("reader_level")) not in {"beginner", "general"}
        or not 2 <= len(prerequisites) <= 6
        or any(not 10 <= len(plain(value)) <= 120 for value in prerequisites)
        or not 3 <= len(steps) <= 7
        or any(not 12 <= len(plain(value)) <= 160 for value in steps)
        or len(plain(walkthrough.get("success_check"))) < 30
        or len(plain(walkthrough.get("recovery"))) < 30
        or len(plain(walkthrough.get("easiest_method_considered"))) < 30
        or len(plain(walkthrough.get("code_needed_when"))) < 30
        or "준비" not in heading_text
        or not any(marker in heading_text for marker in ("단계", "실행"))
        or not any(marker in heading_text for marker in ("결과", "확인"))
        or first_code_index < 0
        or not any(
            isinstance(block, dict) and block.get("t") == "ul"
            for block in content[:first_code_index]
        )
        or developer_record_index < int(len(content) * 0.65)
        or any(marker in early_text for marker in developer_only_markers)
        or any(
            isinstance(block, dict)
            and block.get("t") == "code"
            and len(str(block.get("text") or "").splitlines()) > 20
            and (
                block.get("collapsed") is not True
                or len(plain(block.get("summary"))) < 8
            )
            for block in content
        )
    )
    return ["quality_reader_walkthrough"] if invalid else []


def _reader_hook_reasons(source, identity):
    """Require a concrete scene, stakes, and payoff that appear in the opening."""
    publish_day = date.fromisoformat(identity.publish_date)
    active = (
        identity.content_type == "daily_news"
        and publish_day >= WEEKLY_EDITORIAL_LANES_START
    ) or (
        identity.content_type == "automation_case"
        and publish_day >= READER_HOOK_POLICY_START
    )
    if not active:
        return []

    editorial = source.get("editorial") if isinstance(source.get("editorial"), dict) else {}
    hook = editorial.get("reader_hook") if isinstance(editorial.get("reader_hook"), dict) else {}
    fields = ("scene", "stakes", "payoff", "open_question")
    values = [plain(hook.get(key)) for key in fields]
    opening_terms = _search_terms(editorial.get("opening"))
    overlap_count = sum(
        bool(opening_terms.intersection(_search_terms(value))) for value in values
    )
    invalid = (
        any(not 20 <= len(value) <= 180 for value in values)
        or len({value.casefold() for value in values}) != len(values)
        or overlap_count < 2
        or any(
            phrase in " ".join(values).casefold()
            for phrase in CLICKBAIT_TITLE_PHRASES
        )
    )
    return ["quality_reader_hook"] if invalid else []


def _visual_trend_reasons(source, identity, *, require_image=False):
    """Keep generated covers specific, human, and useful in image search."""
    if date.fromisoformat(identity.publish_date) < VISUAL_TREND_POLICY_START:
        return []
    visual = source.get("visual") if isinstance(source.get("visual"), dict) else {}
    cover = visual.get("cover") if isinstance(visual.get("cover"), dict) else {}
    fields = ("editorial_treatment", "focal_subject", "texture_cue", "authenticity_cue")
    invalid = (
        plain(cover.get("editorial_treatment")) not in EDITORIAL_TREATMENTS
        or any(len(plain(cover.get(key))) < 6 for key in fields[1:])
    )
    if not require_image:
        return ["quality_visual_trend"] if invalid else []

    images = source.get("images") if isinstance(source.get("images"), dict) else {}
    cover_image = images.get("cover") if isinstance(images.get("cover"), dict) else {}
    invalid |= any(
        plain(cover.get(key)) != plain(cover_image.get(key)) for key in fields
    )
    alt = plain(cover_image.get("alt"))
    alt_terms = _search_terms(alt)
    context_terms = _search_terms(source.get("primary_query"))
    context_terms.update(_search_terms(cover.get("focal_subject")))
    invalid |= (
        not 15 <= len(alt) <= 160
        or not alt_terms.intersection(context_terms)
        or alt.casefold() in {"대표 이미지", "블로그 이미지", "설명 이미지"}
    )
    path = plain(cover_image.get("path"))
    if path:
        stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0].casefold()
        invalid |= bool(re.fullmatch(r"(?:image|visual|cover|img)[-_]?\d*", stem))
    return ["quality_visual_trend"] if invalid else []


def _korean_content_reasons(source):
    editorial = source.get("editorial") if isinstance(source.get("editorial"), dict) else {}
    news = source.get("news") if isinstance(source.get("news"), list) else []
    item = news[0] if len(news) == 1 and isinstance(news[0], dict) else {}
    core_values = [
        editorial.get("headline"),
        editorial.get("opening"),
        editorial.get("closing"),
        editorial.get("action"),
        item.get("title_kr"),
        item.get("blurb_kr"),
    ]
    if any(not re.search(r"[가-힣]", plain(value)) for value in core_values):
        return ["quality_korean_content"]

    prose_values = []
    for block in item.get("content", []) if isinstance(item.get("content"), list) else []:
        if not isinstance(block, dict) or block.get("t") == "code":
            continue
        prose_values.extend([block.get("text"), block.get("caption")])
        prose_values.extend(block.get("items") if isinstance(block.get("items"), list) else [])
        prose_values.extend(block.get("headers") if isinstance(block.get("headers"), list) else [])
        for row in block.get("rows") if isinstance(block.get("rows"), list) else []:
            if isinstance(row, list):
                prose_values.extend(row)
    prose = " ".join(plain(value) for value in prose_values if plain(value))
    hangul = len(re.findall(r"[가-힣]", prose))
    letters = len(re.findall(r"[A-Za-z가-힣]", prose))
    if hangul < 100 or not letters or hangul / letters < 0.25:
        return ["quality_korean_content"]
    return []


def _reference_reasons(source):
    news = source.get("news") if isinstance(source.get("news"), list) else []
    item = news[0] if len(news) == 1 and isinstance(news[0], dict) else {}
    required_item_fields = ("title_kr", "source", "url", "published_at", "blurb_kr")
    references = item.get("references") if isinstance(item.get("references"), list) else []
    valid = [
        reference
        for reference in references
        if isinstance(reference, dict)
        and plain(reference.get("title"))
        and _is_http_url(reference.get("url"))
        and plain(reference.get("kind"))
    ]
    urls = {_canonical_url(reference.get("url")) for reference in valid}
    kinds = {plain(reference.get("kind")).casefold() for reference in valid}
    if (
        any(not plain(item.get(key)) for key in required_item_fields)
        or not _is_http_url(item.get("url"))
        or not 3 <= len(valid) <= 6
        or len(urls) != len(valid)
        or not kinds.intersection({"official", "documentation"})
        or not kinds.intersection({"independent", "reference", "research"})
    ):
        return ["quality_reference_mix"]
    return []


def _source_freshness_reasons(source, identity):
    news = source.get("news") if isinstance(source.get("news"), list) else []
    item = news[0] if len(news) == 1 and isinstance(news[0], dict) else {}
    raw_published = plain(item.get("published_at"))
    try:
        published = datetime.fromisoformat(raw_published.replace("Z", "+00:00"))
        scheduled = datetime.fromisoformat(plain(source.get("scheduled_at")))
    except ValueError:
        return ["quality_source_freshness"]
    if published.tzinfo is None or scheduled.tzinfo is None:
        return ["quality_source_freshness"]
    published = published.astimezone(timezone.utc)
    scheduled = scheduled.astimezone(timezone.utc)
    if published > scheduled + timedelta(hours=6):
        return ["quality_source_freshness"]
    curiosity_article = editorial_lane_for_identity(identity) in CURIOSITY_LANES
    if (
        identity.content_type == "daily_news"
        and date.fromisoformat(identity.publish_date) >= SOURCE_RECENCY_POLICY_START
        and not curiosity_article
    ):
        source_age = scheduled - published
        if source_age > timedelta(days=7):
            return ["quality_source_freshness"]
        if (
            date.fromisoformat(identity.publish_date) < EVERGREEN_DAILY_START
            and source_age > timedelta(hours=72)
        ):
            editorial = (
                source.get("editorial")
                if isinstance(source.get("editorial"), dict)
                else {}
            )
            exception = editorial.get("freshness_exception")
            if not isinstance(exception, dict):
                return ["quality_source_freshness"]
            reason = plain(exception.get("reason"))
            lasting_value = plain(exception.get("lasting_value"))
            rejected = exception.get("fresher_candidates_rejected")
            rejected = rejected if isinstance(rejected, list) else []
            rejected = [plain(item) for item in rejected if plain(item)]
            if (
                not 40 <= len(reason) <= 500
                or not 40 <= len(lasting_value) <= 500
                or not 2 <= len(rejected) <= 5
                or any(not 20 <= len(item) <= 300 for item in rejected)
            ):
                return ["quality_source_freshness"]
    if (
        identity.content_type == "daily_news"
        and published < scheduled - timedelta(days=14)
        and not curiosity_article
    ):
        return ["quality_source_freshness"]
    return []


def _depth_reasons(source, identity):
    news = source.get("news") if isinstance(source.get("news"), list) else []
    item = news[0] if len(news) == 1 and isinstance(news[0], dict) else {}
    content = item.get("content") if isinstance(item.get("content"), list) else []
    malformed_blocks = any(
        not isinstance(block, dict)
        or not isinstance(block.get("t"), str)
        or block.get("t") not in RENDERABLE_BLOCK_TYPES
        for block in content
    )
    blocks = _meaningful_blocks(content)
    headings = [block for block in blocks if block.get("t") == "h"]
    visuals = [block for block in blocks if block.get("t") == "visual"]
    ad_indexes = [index for index, block in enumerate(blocks) if block.get("t") == "ad_break"]
    editorial = source.get("editorial") if isinstance(source.get("editorial"), dict) else {}
    article_shape = plain(editorial.get("article_shape"))
    policy = depth_policy_for(identity, article_shape)
    minimum_visuals = policy["minimum_visuals"]
    if (
        date.fromisoformat(identity.publish_date) >= REVISIT_VALUE_POLICY_START
        and article_shape in {"hands_on_test", "troubleshooting", "research_interpretation"}
        and editorial_lane_for_identity(identity) not in CURIOSITY_LANES
    ):
        minimum_visuals = max(minimum_visuals, 3)
    block_types = {block.get("t") for block in blocks}
    invalid = (
        malformed_blocks
        or not policy["minimum_headings"]
        <= len(headings)
        <= policy["maximum_headings"]
        or not minimum_visuals
        <= len(visuals)
        <= policy["maximum_visuals"]
        or not policy["minimum_minutes"]
        <= estimate_read_minutes(source)
        <= policy["maximum_minutes"]
        or len(blocks) < policy["minimum_blocks"]
        or not policy["required_block_types"].issubset(block_types)
        or len(ad_indexes) != 1
    )
    if not invalid:
        non_ad_count = max(1, len(blocks) - 1)
        position = ad_indexes[0] / non_ad_count
        invalid = not 0.35 <= position <= 0.45
    if not invalid and date.fromisoformat(identity.publish_date) >= AD_FLOW_POLICY_START:
        ad_index = ad_indexes[0]
        previous_type = blocks[ad_index - 1].get("t") if ad_index > 0 else ""
        next_type = blocks[ad_index + 1].get("t") if ad_index + 1 < len(blocks) else ""
        invalid = previous_type not in {"p", "table", "ul", "code", "quote"} or next_type != "h"
    return ["quality_depth"] if invalid else []


def _prose_reasons(source, identity):
    values = [plain(value) for value in _text_values(source)]
    searchable = "\n".join(values).casefold()
    reasons = []
    if any(phrase in searchable for phrase in BANNED_EDITORIAL_PHRASES):
        reasons.append("quality_style")

    if date.fromisoformat(identity.publish_date) >= NATURAL_VOICE_POLICY_START:
        news = source.get("news") if isinstance(source.get("news"), list) else []
        item = news[0] if len(news) == 1 and isinstance(news[0], dict) else {}
        content = item.get("content") if isinstance(item.get("content"), list) else []
        headings = [
            plain(block.get("text"))
            for block in content
            if isinstance(block, dict) and block.get("t") == "h"
        ]
        paragraphs = [
            plain(block.get("text"))
            for block in content
            if isinstance(block, dict) and block.get("t") == "p" and plain(block.get("text"))
        ]
        opening = plain(
            (source.get("editorial") or {}).get("opening")
            if isinstance(source.get("editorial"), dict)
            else ""
        ).casefold()
        unnatural = (
            any(phrase in searchable for phrase in FUTURE_AI_CLICHES)
            or any(phrase in searchable for phrase in INTERNAL_REVISIT_LABELS)
            or any(heading in REPORT_ONLY_HEADINGS for heading in headings)
            or any(
                phrase in heading
                for heading in headings
                for phrase in EXPLICIT_EDITORIAL_HEADINGS
            )
            or any(opening.startswith(prefix) for prefix in ("오늘은", "이번 글은", "이 글은"))
            or len(paragraphs) < max(4, len(headings) - 1)
        )
        if unnatural:
            reasons.append("quality_natural_voice")

    if date.fromisoformat(identity.publish_date) >= MOBILE_READABILITY_POLICY_START:
        editorial = source.get("editorial") if isinstance(source.get("editorial"), dict) else {}
        opening = plain(editorial.get("opening"))
        news = source.get("news") if isinstance(source.get("news"), list) else []
        item = news[0] if len(news) == 1 and isinstance(news[0], dict) else {}
        content = item.get("content") if isinstance(item.get("content"), list) else []
        paragraphs = [
            plain(block.get("text"))
            for block in content
            if isinstance(block, dict) and block.get("t") == "p" and plain(block.get("text"))
        ]
        if len(opening) > 320 or any(len(paragraph) > 220 for paragraph in paragraphs):
            reasons.append("quality_readability")

    long_segments = [
        re.sub(r"\s+", " ", value).strip().casefold()
        for value in values
        if len(value) >= 80
    ]
    if len(long_segments) != len(set(long_segments)):
        reasons.append("quality_repetition")
    if "quality_repetition" not in reasons:
        for value in values:
            sentences = [
                re.sub(r"\s+", " ", sentence).strip().casefold()
                for sentence in re.split(r"[.!?。！？]+", value)
                if len(re.sub(r"\s+", " ", sentence).strip()) >= 12
            ]
            if any(count >= 3 for count in Counter(sentences).values()):
                reasons.append("quality_repetition")
                break
    return reasons


def _visual_reasons(source, identity):
    reasons = []
    visual = source.get("visual") if isinstance(source.get("visual"), dict) else {}
    briefs = visual.get("assets") if isinstance(visual.get("assets"), list) else []
    images = source.get("images") if isinstance(source.get("images"), dict) else {}
    generation = source.get("generation") if isinstance(source.get("generation"), dict) else {}
    expected_keys = [f"visual_{index}" for index in range(1, len(briefs) + 1)]
    declared_keys = sorted(
        (key for key in images if re.fullmatch(r"visual_\d+", str(key))),
        key=lambda key: int(str(key).split("_")[-1]),
    )
    if declared_keys != expected_keys:
        reasons.append("quality_visual_provenance")

    provider = plain(generation.get("image_provider")).casefold()
    if not provider or provider in FALLBACK_IMAGE_PROVIDERS:
        reasons.append("quality_fallback_image")

    cover = images.get("cover") if isinstance(images.get("cover"), dict) else {}
    cover_origin = plain(cover.get("origin"))
    if cover_origin != "imagegen":
        reasons.append("quality_visual_provenance")
    if cover_origin == "imagegen" and not (
        len(plain(cover.get("generation_prompt"))) >= 30
        and plain(cover.get("generation_model"))
    ):
        reasons.append("quality_visual_provenance")
    if not _has_complete_qa(cover):
        reasons.append("quality_visual_qa")
    if plain(cover.get("style")) == "text-free-editorial-scene" or cover_origin == "deterministic_fallback":
        reasons.append("quality_fallback_image")

    origins = []
    for index, brief in enumerate(briefs, 1):
        if not isinstance(brief, dict):
            reasons.append("quality_visual_provenance")
            continue
        image = images.get(f"visual_{index}")
        image = image if isinstance(image, dict) else {}
        origin = plain(brief.get("origin"))
        image_origin = plain(image.get("origin"))
        evidence_type = plain(brief.get("evidence_type"))
        origins.append(origin)
        if (
            origin not in PUBLISHABLE_ORIGINS
            or image_origin != origin
            or ORIGIN_EVIDENCE.get(origin) != evidence_type
            or plain(image.get("style")) == "text-free-editorial-scene"
        ):
            reasons.append("quality_visual_provenance")
        if origin == "deterministic_fallback" or image_origin == "deterministic_fallback":
            reasons.append("quality_fallback_image")
        if not _has_complete_qa(brief) or not _has_complete_qa(image):
            reasons.append("quality_visual_qa")
        if origin == "imagegen":
            labels = brief.get("korean_labels")
            prompt = plain(brief.get("generation_prompt"))
            model = plain(brief.get("generation_model"))
            if not (
                len(prompt) >= 30
                and model
                and isinstance(labels, list)
                and 2 <= len(labels) <= 6
                and all(re.search(r"[가-힣]", plain(label)) for label in labels)
                and len(plain(image.get("generation_prompt"))) >= 30
                and plain(image.get("generation_prompt")) == prompt
                and plain(image.get("generation_model")) == model
            ):
                reasons.append("quality_visual_provenance")
        elif origin in {"capture", "annotated_capture"} and not (
            _is_http_url(brief.get("source_url"))
            or len(plain(brief.get("capture_note"))) >= 20
        ):
            reasons.append("quality_visual_provenance")
        if origin in {"capture", "annotated_capture"}:
            scheduled = _aware_datetime(source.get("scheduled_at"))
            captured = _aware_datetime(brief.get("captured_at"))
            matching_fields = all(
                plain(brief.get(key)) == plain(image.get(key))
                for key in ("capture_tool", "capture_target", "captured_at")
            )
            capture_deadline = (
                scheduled.replace(hour=23, minute=59, second=59, microsecond=999999)
                if scheduled
                else None
            )
            backfill_deadline = _backfill_deadline(source, scheduled)
            if capture_deadline and backfill_deadline:
                capture_deadline = max(capture_deadline, backfill_deadline)
            valid_time = bool(
                scheduled
                and captured
                and scheduled - timedelta(days=14)
                <= captured
                <= capture_deadline
            )
            image_digest = plain(image.get("sha256")).casefold()
            capture_digest = plain(image.get("capture_sha256")).casefold()
            if not (
                plain(brief.get("capture_tool")) in CAPTURE_TOOLS
                and len(plain(brief.get("capture_target"))) >= 8
                and matching_fields
                and valid_time
                and re.fullmatch(r"[0-9a-f]{64}", image_digest)
                and capture_digest == image_digest
                and not plain(image.get("generation_prompt"))
            ):
                reasons.append("quality_visual_provenance")
        if origin == "measured_chart":
            points = brief.get("data_points")
            valid_points = (
                isinstance(points, list)
                and 2 <= len(points) <= 20
                and len({plain(point.get("label")) for point in points if isinstance(point, dict)})
                == len(points)
                and all(
                    isinstance(point, dict)
                    and plain(point.get("label"))
                    and isinstance(point.get("value"), (int, float))
                    and not isinstance(point.get("value"), bool)
                    and math.isfinite(float(point.get("value")))
                    for point in points
                )
            )
            digest = measurement_digest(brief) if valid_points else ""
            if not (
                valid_points
                and len(plain(brief.get("measurement_source"))) >= 8
                and len(plain(brief.get("unit"))) >= 1
                and isinstance(brief.get("sample_count"), int)
                and not isinstance(brief.get("sample_count"), bool)
                and brief.get("sample_count") >= len(points)
                and len(plain(brief.get("measurement_environment"))) >= 10
                and plain(image.get("measurement_sha256")).casefold() == digest
            ):
                reasons.append("quality_visual_provenance")

    if "imagegen" not in origins:
        reasons.append("quality_visual_provenance")
    expected_provider = (
        "mixed" if any(origin != "imagegen" for origin in origins) else "codex-imagegen"
    )
    if provider != expected_provider:
        reasons.append("quality_visual_provenance")
    if identity.content_type == "automation_case":
        required_evidence_origins = (
            {"annotated_capture", "measured_chart"}
            if editorial_lane_for_identity(identity) == "developer_insight"
            else {"capture", "annotated_capture"}
        )
        if not any(origin in required_evidence_origins for origin in origins):
            reasons.append("quality_visual_provenance")
    if date.fromisoformat(identity.publish_date) >= REVISIT_VALUE_POLICY_START:
        editorial = source.get("editorial") if isinstance(source.get("editorial"), dict) else {}
        article_shape = plain(editorial.get("article_shape"))
        if article_shape in {"hands_on_test", "troubleshooting", "incident_trace"} and not any(
            origin in {"capture", "annotated_capture", "measured_chart"}
            for origin in origins
        ):
            reasons.append("quality_visual_evidence")
        if (
            article_shape == "research_interpretation"
            and editorial_lane_for_identity(identity) not in CURIOSITY_LANES
            and not any(
                origin in {"annotated_capture", "measured_chart"}
                for origin in origins
            )
        ):
            reasons.append("quality_visual_evidence")
    return reasons


def _visual_role_reasons(source, identity):
    if date.fromisoformat(identity.publish_date) < VISUAL_ROLE_POLICY_START:
        return []
    visual = source.get("visual") if isinstance(source.get("visual"), dict) else {}
    cover = visual.get("cover") if isinstance(visual.get("cover"), dict) else {}
    briefs = visual.get("assets") if isinstance(visual.get("assets"), list) else []
    required = ("label", "steps", "curiosity_hook", "logic_type", "content_role")
    if (
        any(not _strict_text(cover.get(key)) for key in required)
        or cover.get("content_role") != "hook"
        or not _strict_text_list(cover.get("scene_label"), minimum=2)
        or any(
            not isinstance(brief, dict)
            or brief.get("content_role") != "explanation"
            for brief in briefs
        )
    ):
        return ["quality_visual_roles"]

    labels = [plain(cover.get("label")), *[plain(brief.get("label")) for brief in briefs]]
    normalized = [re.sub(r"\s+", " ", label).strip().casefold() for label in labels]
    if len(set(normalized)) != len(normalized):
        return ["quality_visual_roles"]
    token_sets = [
        set(re.findall(r"[가-힣A-Za-z0-9]+", label.casefold()))
        for label in labels
    ]
    for index, left in enumerate(token_sets):
        for right in token_sets[index + 1 :]:
            if not left or not right:
                return ["quality_visual_roles"]
            similarity = len(left & right) / min(len(left), len(right))
            if similarity >= 0.75:
                return ["quality_visual_roles"]

    if date.fromisoformat(identity.publish_date) >= COVER_VARIETY_POLICY_START:
        images = source.get("images") if isinstance(source.get("images"), dict) else {}
        cover_image = images.get("cover") if isinstance(images.get("cover"), dict) else {}
        style_keys = ("art_direction", "composition_type", "palette_family")
        cover_prompt = plain(cover_image.get("generation_prompt")).casefold()
        if (
            any(not _strict_text(cover.get(key)) for key in style_keys)
            or any(not _strict_text(cover_image.get(key)) for key in style_keys)
            or any(
                plain(cover.get(key)) != plain(cover_image.get(key))
                for key in style_keys
            )
            or plain(cover.get("composition_type")).casefold()
            in BANNED_COVER_COMPOSITIONS
            or plain(cover.get("cover_kind")).casefold() != REQUIRED_COVER_KIND
            or plain(cover_image.get("cover_kind")).casefold() != REQUIRED_COVER_KIND
            or not cover_prompt.startswith(REQUIRED_COVER_PROMPT_PREFIXES)
            or REQUIRED_COVER_PROMPT_TOKEN not in cover_prompt
        ):
            return ["quality_visual_variety"]
        if date.fromisoformat(identity.publish_date) >= REVISIT_VALUE_POLICY_START:
            render_family = plain(cover.get("render_family"))
            raw_cover_labels = cover.get("korean_labels", [])
            cover_labels = (
                [plain(label) for label in raw_cover_labels]
                if isinstance(raw_cover_labels, list)
                else []
            )
            if (
                render_family not in RENDER_FAMILIES
                or render_family != plain(cover_image.get("render_family"))
                or not isinstance(raw_cover_labels, list)
                or len(cover_labels) > 3
                or len({label.casefold() for label in cover_labels})
                != len(cover_labels)
                or any(
                    not re.search(r"[가-힣]", label) or len(label) > 12
                    for label in cover_labels
                )
            ):
                return ["quality_visual_variety"]
    return []


def _developer_insight_evidence_reasons(source, identity):
    """Require traceable research evidence without pretending every article is a test."""
    verification = (
        source.get("verification")
        if isinstance(source.get("verification"), dict)
        else {}
    )
    mode = plain(verification.get("mode"))
    source_urls = verification.get("source_urls")
    source_urls = source_urls if isinstance(source_urls, list) else []
    canonical_sources = [_canonical_url(url) for url in source_urls]
    evidence_files = verification.get("evidence_files")
    evidence_files = evidence_files if isinstance(evidence_files, list) else []
    images = source.get("images") if isinstance(source.get("images"), dict) else {}
    evidence_valid = bool(evidence_files) and all(
        isinstance(key, str)
        and re.fullmatch(r"visual_\d+", plain(key))
        and isinstance(images.get(plain(key)), dict)
        and plain(images[plain(key)].get("origin"))
        in {"annotated_capture", "measured_chart"}
        for key in evidence_files
    )

    checked_at = _aware_datetime(verification.get("checked_at"))
    scheduled = _aware_datetime(source.get("scheduled_at"))
    deadline = _backfill_deadline(source, scheduled)
    if not deadline and scheduled:
        deadline = scheduled + timedelta(hours=6)
    checked_at_valid = bool(
        checked_at
        and scheduled
        and scheduled - timedelta(days=30) <= checked_at <= deadline
    )

    invalid = (
        mode not in {"source_research", "measured_analysis", "executed"}
        or len(source_urls) < 3
        or any(not value for value in canonical_sources)
        or len(set(canonical_sources)) != len(canonical_sources)
        or verification.get("source_count") != len(source_urls)
        or isinstance(verification.get("source_count"), bool)
        or not checked_at_valid
        or len(plain(verification.get("scope"))) < 30
        or len(plain(verification.get("method"))) < 30
        or len(plain(verification.get("selection_rule"))) < 30
        or len(plain(verification.get("limitations"))) < 20
        or len(plain(verification.get("problem_lane"))) < 2
        or len(plain(verification.get("tool_brand"))) < 2
        or not evidence_valid
    )

    if mode == "measured_analysis":
        measured = verification.get("measurement_files")
        invalid |= not (
            isinstance(measured, list)
            and measured
            and all(
                plain(key) in evidence_files
                and isinstance(images.get(plain(key)), dict)
                and plain(images[plain(key)].get("origin")) == "measured_chart"
                for key in measured
            )
            and len(plain(verification.get("measurement_note"))) >= 20
        )

    if mode == "executed":
        environment = (
            verification.get("environment")
            if isinstance(verification.get("environment"), dict)
            else {}
        )
        commands = verification.get("commands")
        started = _aware_datetime(verification.get("started_at"))
        completed = _aware_datetime(verification.get("completed_at"))
        invalid |= (
            verification.get("command_exit_code") != 0
            or isinstance(verification.get("command_exit_code"), bool)
            or not started
            or not completed
            or not scheduled
            or not scheduled - timedelta(days=14)
            <= started
            <= completed
            <= deadline
            or not isinstance(commands, list)
            or not commands
            or any(not _strict_text(command) for command in commands)
            or any(
                len(plain(verification.get(key))) < 20
                for key in ("input_fixture", "expected", "actual", "failure", "rollback")
            )
            or any(
                not _strict_text(environment.get(key))
                for key in ("os", "runtime", "tool_version", "source_revision")
            )
        )
    return ["quality_insight_evidence"] if invalid else []


def _experiment_reasons(source, identity):
    if identity.content_type != "automation_case":
        return []
    if editorial_lane_for_identity(identity) == "developer_insight":
        return _developer_insight_evidence_reasons(source, identity)
    verification = source.get("verification") if isinstance(source.get("verification"), dict) else {}
    environment = verification.get("environment") if isinstance(verification.get("environment"), dict) else {}
    required_environment = {"os", "runtime", "tool_version", "source_revision"}
    commands = verification.get("commands")
    evidence_files = verification.get("evidence_files")
    visual = source.get("visual") if isinstance(source.get("visual"), dict) else {}
    briefs = visual.get("assets") if isinstance(visual.get("assets"), list) else []
    measured_files = [
        f"visual_{index}"
        for index, brief in enumerate(briefs, 1)
        if isinstance(brief, dict) and brief.get("origin") == "measured_chart"
    ]
    raw_bound_measurements = verification.get("measurement_files")
    images = source.get("images") if isinstance(source.get("images"), dict) else {}
    valid_evidence_keys = (
        [plain(key) for key in evidence_files]
        if isinstance(evidence_files, list)
        and evidence_files
        and all(isinstance(key, str) and plain(key) for key in evidence_files)
        and len({plain(key) for key in evidence_files}) == len(evidence_files)
        else []
    )
    evidence_is_capture = (
        bool(valid_evidence_keys)
        and all(
            re.fullmatch(r"visual_\d+", key)
            and isinstance(images.get(key), dict)
            and plain(images[key].get("origin")) in {"capture", "annotated_capture"}
            for key in valid_evidence_keys
        )
    )
    valid_bound_measurements = (
        [plain(key) for key in raw_bound_measurements]
        if isinstance(raw_bound_measurements, list)
        and all(
            isinstance(key, str)
            and re.fullmatch(r"visual_\d+", plain(key))
            for key in raw_bound_measurements
        )
        and len({plain(key) for key in raw_bound_measurements})
        == len(raw_bound_measurements)
        else None
    )
    measurement_binding_valid = (
        set(valid_bound_measurements or []) == set(measured_files)
        and (
            bool(measured_files)
            or raw_bound_measurements is None
            or raw_bound_measurements == []
        )
    )
    required_text = {
        "input_fixture": 20,
        "expected": 20,
        "actual": 20,
        "failure": 20,
        "rollback": 20,
        "problem_lane": 2,
        "tool_brand": 2,
        "stdout_excerpt": 20,
    }
    started = _aware_datetime(verification.get("started_at"))
    completed = _aware_datetime(verification.get("completed_at"))
    scheduled = _aware_datetime(source.get("scheduled_at"))
    execution_deadline = _backfill_deadline(source, scheduled)
    if not execution_deadline and scheduled:
        execution_deadline = scheduled + timedelta(hours=6)
    valid_execution_time = bool(
        started
        and completed
        and scheduled
        and scheduled - timedelta(days=14)
        <= started
        <= completed
        <= execution_deadline
    )
    invalid = (
        verification.get("mode") != "executed"
        or verification.get("command_exit_code") != 0
        or isinstance(verification.get("command_exit_code"), bool)
        or not valid_execution_time
        or not required_environment.issubset(environment)
        or any(
            not _strict_text(environment.get(key))
            for key in required_environment
        )
        or not isinstance(commands, list)
        or not commands
        or any(not _strict_text(command) for command in commands)
        or any(
            not _strict_text(verification.get(key))
            or len(plain(verification.get(key))) < minimum
            for key, minimum in required_text.items()
        )
        or not evidence_is_capture
        or not measurement_binding_valid
        or (
            measured_files
            and len(plain(verification.get("measurement_note"))) < 20
        )
    )
    return ["quality_experiment_evidence"] if invalid else []


def _run_quality_validators(validators):
    reasons = []
    for validate in validators:
        try:
            reasons.extend(validate())
        except (TypeError, ValueError, OverflowError):
            # A malformed JSON field must make the draft unpublishable, never
            # abort the whole scheduled quality scan.
            reasons.append("quality_schema")
    return reasons


def _generation_reasons(source):
    generation = source.get("generation") if isinstance(source.get("generation"), dict) else {}
    try:
        revision = int(generation.get("revision") or 0)
    except (TypeError, ValueError):
        revision = 0
    if (
        plain(generation.get("provider")) != "codex-agent"
        or not plain(generation.get("model"))
        or revision < 7
    ):
        return ["quality_generation"]
    return []


def source_authoring_reasons(source, identity):
    """Validate the article contract before image files or exports exist."""
    if not isinstance(source, dict) or not policy_active(identity):
        return []
    validators = (
        lambda: _identity_reasons(source, identity),
        lambda: _schema_reasons(source, identity, require_images=False),
        lambda: _editorial_reasons(source, identity),
        lambda: _search_metadata_reasons(source, identity),
        lambda: _search_conversion_reasons(source, identity),
        lambda: _revisit_value_reasons(source, identity),
        lambda: _original_value_reasons(source, identity),
        lambda: _weekly_lane_reasons(source, identity),
        lambda: _automation_walkthrough_reasons(source, identity),
        lambda: _reader_hook_reasons(source, identity),
        lambda: _korean_content_reasons(source),
        lambda: _reference_reasons(source),
        lambda: _source_freshness_reasons(source, identity),
        lambda: _depth_reasons(source, identity),
        lambda: _prose_reasons(source, identity),
        lambda: _visual_role_reasons(source, identity),
        lambda: _visual_trend_reasons(source, identity),
    )
    reasons = _run_quality_validators(validators)
    reasons.extend(_generation_reasons(source))
    return list(dict.fromkeys(reasons))


def source_quality_reasons(source, identity):
    """Return durable reason codes for one future publishable source."""
    if not isinstance(source, dict) or not policy_active(identity):
        return []
    reasons = source_authoring_reasons(source, identity)
    validators = (
        lambda: _schema_reasons(source, identity),
        lambda: _visual_reasons(source, identity),
        lambda: _visual_trend_reasons(source, identity, require_image=True),
        lambda: _experiment_reasons(source, identity),
    )
    reasons.extend(_run_quality_validators(validators))
    return list(dict.fromkeys(reasons))
