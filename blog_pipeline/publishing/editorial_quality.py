"""Future-facing quality gates shared by export, copy UI, and CI."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .draft_identity import category_for_identity, regular_schedule_for_identity


DAILY_QUALITY_POLICY_START = date(2026, 7, 19)
AUTOMATION_QUALITY_POLICY_START = date(2026, 7, 25)
GUIDE_QUALITY_POLICY_START = date(2026, 7, 21)
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
DAILY_COVERAGE = {
    "change",
    "mechanism",
    "comparison",
    "application",
    "limits",
    "checklist",
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
GUIDE_COVERAGE = {
    "foundation",
    "request_flow",
    "stack",
    "data",
    "security",
    "operations",
    "plan",
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
    "승원의 메모",
}
EDITORIAL_LENGTH_RULES = {
    "headline": (25, 70),
    "opening": (180, 1200),
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
}


def plain(value):
    return " ".join(str(value or "").split())


def policy_active(identity):
    publish_date = date.fromisoformat(identity.publish_date)
    start = {
        "automation_case": AUTOMATION_QUALITY_POLICY_START,
        "evergreen_guide": GUIDE_QUALITY_POLICY_START,
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

    if identity.content_type == "automation_case":
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
            invalid = invalid or publication_mode != "scheduled"
            invalid = invalid or publish_day.weekday() != 5
            invalid = invalid or source.get("scheduled_at") != (
                f"{identity.publish_date}T18:00:00+09:00"
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
        invalid = invalid or publication_mode != "scheduled"
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
    required_coverage = {
        "automation_case": AUTOMATION_COVERAGE,
        "evergreen_guide": GUIDE_COVERAGE,
    }.get(identity.content_type, DAILY_COVERAGE)
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
    if (
        identity.content_type == "daily_news"
        and published < scheduled - timedelta(days=14)
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
    policy = DEPTH_POLICIES[identity.content_type]
    block_types = {block.get("t") for block in blocks}
    invalid = (
        malformed_blocks
        or not policy["minimum_headings"]
        <= len(headings)
        <= policy["maximum_headings"]
        or not policy["minimum_visuals"]
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
    return ["quality_depth"] if invalid else []


def _prose_reasons(source):
    values = [plain(value) for value in _text_values(source)]
    searchable = "\n".join(values).casefold()
    reasons = []
    if any(phrase in searchable for phrase in BANNED_EDITORIAL_PHRASES):
        reasons.append("quality_style")

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
            valid_time = bool(
                scheduled
                and captured
                and scheduled - timedelta(days=14)
                <= captured
                <= scheduled + timedelta(hours=6)
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
    if identity.content_type == "automation_case" and not any(
        origin in {"capture", "annotated_capture"} for origin in origins
    ):
        reasons.append("quality_visual_provenance")
    return reasons


def _experiment_reasons(source, identity):
    if identity.content_type != "automation_case":
        return []
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
    valid_execution_time = bool(
        started
        and completed
        and scheduled
        and scheduled - timedelta(days=14)
        <= started
        <= completed
        <= scheduled + timedelta(hours=6)
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
        lambda: _korean_content_reasons(source),
        lambda: _reference_reasons(source),
        lambda: _source_freshness_reasons(source, identity),
        lambda: _depth_reasons(source, identity),
        lambda: _prose_reasons(source),
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
        lambda: _experiment_reasons(source, identity),
    )
    reasons.extend(_run_quality_validators(validators))
    return list(dict.fromkeys(reasons))
