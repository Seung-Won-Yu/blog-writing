"""Stop duplicate daily work and reject recently repeated news topics."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from blog_pipeline.collection.news_pipeline import validate_day_id
from .draft_identity import (
    category_for_identity,
    regular_schedule_for_identity,
    resolve_draft_identity,
)
from .editorial_format import image_kinds_for_day, is_lead_story, lead_visual_kinds
from .editorial_quality import (
    DEPTH_POLICIES,
    EDITORIAL_LENGTH_RULES,
    PUBLISH_GATE_START,
    estimate_read_minutes,
    source_authoring_reasons,
    source_quality_reasons,
)


ROOT = Path(__file__).resolve().parents[2]
TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source"}
VISUAL_EVIDENCE_TYPES = {"diagram", "screenshot", "chart"}
VISUAL_LOGIC_TYPES = {
    "flow",
    "before_after",
    "comparison",
    "conditional",
    "timeline",
    "architecture",
    "evidence",
}
PRODUCT_UI_PATTERN = re.compile(
    r"(?:설정(?:법|\s*방법)?|사용법|대시보드|configuration|configure|setup|how\s+to)",
    re.IGNORECASE,
)
AUTOMATION_VISUAL_POLICY_START = date(2026, 7, 25)
AUTOMATION_PUBLISHABLE_ORIGINS = {
    "capture",
    "annotated_capture",
    "measured_chart",
    "imagegen",
}
AUTOMATION_ORIGIN_EVIDENCE = {
    "capture": "screenshot",
    "annotated_capture": "screenshot",
    "measured_chart": "chart",
    "imagegen": "diagram",
}
SCHEMA_EXCEPTIONS = (
    AttributeError,
    KeyError,
    IndexError,
    TypeError,
    ValueError,
    OverflowError,
)


def canonical_url(value):
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = urlsplit(text)
    except ValueError:
        return ""
    query = sorted(
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_KEYS
        and not key.lower().startswith(TRACKING_QUERY_PREFIXES)
    )
    path = re.sub(r"/+", "/", parsed.path or "/").rstrip("/") or "/"
    return urlunsplit(
        (
            parsed.scheme.lower() or "https",
            parsed.netloc.lower().removeprefix("www."),
            path,
            urlencode(query),
            "",
        )
    )


def normalized_title(value):
    return re.sub(r"[^0-9a-z가-힣]+", "", str(value or "").lower())


def has_inline_post_style(body_html):
    """Detect actual style tags/attributes without flagging code sample text."""
    value = str(body_html or "")
    return bool(
        re.search(r"<style(?:\s|>)", value, re.IGNORECASE)
        or re.search(r"<[a-z][^>]*\sstyle\s*=", value, re.IGNORECASE)
    )


def _is_http_url(value):
    try:
        parsed = urlsplit(str(value or "").strip())
    except ValueError:
        return False
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)


def _is_internal_tistory_post_url(value):
    if not _is_http_url(value):
        return False
    parsed = urlsplit(str(value).strip())
    host = parsed.netloc.lower().removeprefix("www.")
    path = re.sub(r"/+", "/", parsed.path or "/").rstrip("/")
    return host == "won0322.tistory.com" and bool(
        re.fullmatch(r"/(?:m/)?\d+", path)
    )


def _read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None


def _file_sha256(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return ""


def artifact_freshness_reasons(source_path, meta, html_path, adfit_path):
    """Prove preview and final-copy artifacts came from the current source."""
    reasons = []
    expected = {
        "source_sha256": (Path(source_path), "stale_source_export"),
        "html_sha256": (Path(html_path), "stale_html_artifact"),
        "adfit_sha256": (Path(adfit_path), "stale_adfit_artifact"),
    }
    for key, (path, reason) in expected.items():
        recorded = str(meta.get(key) or "").strip().lower()
        actual = _file_sha256(path)
        if not re.fullmatch(r"[0-9a-f]{64}", recorded) or recorded != actual:
            reasons.append(reason)
    return reasons


def preview_artifact_reasons(preview_path, final_adfit_html, meta=None):
    """Require the standalone preview to equal its deterministic current build."""
    try:
        preview_html = Path(preview_path).read_text(encoding="utf-8")
    except OSError:
        return ["missing_preview"]
    fragment = str(final_adfit_html or "")
    if not fragment:
        return ["stale_preview_artifact"]
    if isinstance(meta, dict):
        from .build_copy_page import render_preview_page

        if preview_html != render_preview_page(meta, fragment):
            return ["stale_preview_artifact"]
        return []
    uncommented = re.sub(r"<!--.*?-->", "", preview_html, flags=re.DOTALL)
    article_pattern = re.compile(
        r'<article\b[^>]*class=["\'][^"\']*\bdaily-digest-post\b[^"\']*["\'][^>]*>',
        re.IGNORECASE,
    )
    starts = list(article_pattern.finditer(uncommented))
    if len(starts) != 1:
        return ["stale_preview_artifact"]
    close_at = uncommented.find("</article>", starts[0].end())
    if close_at < 0:
        return ["stale_preview_artifact"]
    actual = uncommented[starts[0].start() : close_at + len("</article>")]
    if actual != fragment:
        return ["stale_preview_artifact"]
    return []


def _lead_visual_evidence_reasons(source):
    reasons = []
    visual = source.get("visual") if isinstance(source.get("visual"), dict) else {}
    assets = visual.get("assets") if isinstance(visual.get("assets"), list) else []
    valid_assets = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        scene_labels = asset.get("scene_label")
        valid_scene_labels = (
            isinstance(scene_labels, list)
            and 2 <= len(scene_labels) <= 4
            and all(str(label or "").strip() for label in scene_labels)
        )
        evidence_type = str(asset.get("evidence_type") or "").strip()
        logic_type = str(asset.get("logic_type") or "").strip()
        valid = (
            str(asset.get("label") or "").strip()
            and valid_scene_labels
            and str(asset.get("steps") or "").strip()
            and str(asset.get("curiosity_hook") or "").strip()
            and evidence_type in VISUAL_EVIDENCE_TYPES
            and logic_type in VISUAL_LOGIC_TYPES
        )
        if logic_type == "conditional" and not str(
            asset.get("condition") or ""
        ).strip():
            valid = False
        if evidence_type == "screenshot" and not (
            _is_http_url(asset.get("source_url"))
            or str(asset.get("capture_note") or "").strip()
        ):
            valid = False
        if valid:
            valid_assets.append(asset)

    if len(valid_assets) != len(assets) or len(valid_assets) < 2:
        reasons.append("lead_visual_briefs")

    editorial = source.get("editorial") if isinstance(source.get("editorial"), dict) else {}
    news = source.get("news") if isinstance(source.get("news"), list) else []
    item = news[0] if news and isinstance(news[0], dict) else {}
    content = item.get("content") if isinstance(item.get("content"), list) else []
    search_text = " ".join(
        [
            str(source.get("primary_query") or ""),
            str(editorial.get("headline") or ""),
            str(item.get("title_kr") or ""),
            *[
                str(block.get("text") or "")
                for block in content
                if isinstance(block, dict) and block.get("t") == "h"
            ],
        ]
    )
    has_product_ui_evidence = any(
        asset.get("evidence_type") == "screenshot" for asset in valid_assets
    )
    has_unavailable_reason = bool(
        str(visual.get("screenshot_unavailable_reason") or "").strip()
    )
    if (
        PRODUCT_UI_PATTERN.search(search_text)
        and not has_product_ui_evidence
        and not has_unavailable_reason
    ):
        reasons.append("lead_product_ui_evidence")
    return reasons


def _automation_visual_quality_reasons(source):
    """Reject low-fidelity fallback art from publish-ready automation posts."""
    reasons = []
    visual = source.get("visual") if isinstance(source.get("visual"), dict) else {}
    briefs = visual.get("assets") if isinstance(visual.get("assets"), list) else []
    images = source.get("images") if isinstance(source.get("images"), dict) else {}
    origins = []
    fallback_found = False
    declared_visual_keys = lead_visual_kinds(images)
    expected_visual_keys = [
        f"visual_{index}" for index in range(1, len(briefs) + 1)
    ]
    if declared_visual_keys != expected_visual_keys:
        reasons.append("automation_image_provenance")
    for kind in declared_visual_keys:
        image = images.get(kind) if isinstance(images.get(kind), dict) else {}
        if (
            image.get("origin") == "deterministic_fallback"
            or image.get("style") == "text-free-editorial-scene"
        ):
            fallback_found = True

    cover = images.get("cover") if isinstance(images.get("cover"), dict) else {}
    cover_origin = str(cover.get("origin") or "").strip()
    if (
        cover_origin not in AUTOMATION_PUBLISHABLE_ORIGINS
        or cover.get("style") == "text-free-editorial-scene"
    ):
        reasons.append("automation_image_provenance")
    if cover_origin == "deterministic_fallback":
        fallback_found = True

    for index, brief in enumerate(briefs, start=1):
        if not isinstance(brief, dict):
            reasons.append("automation_image_provenance")
            continue
        origin = str(brief.get("origin") or "").strip()
        evidence_type = str(brief.get("evidence_type") or "").strip()
        image = images.get(f"visual_{index}")
        image = image if isinstance(image, dict) else {}
        image_origin = str(image.get("origin") or "").strip()

        if origin == "deterministic_fallback" or image_origin == "deterministic_fallback":
            fallback_found = True
        if image.get("style") == "text-free-editorial-scene":
            fallback_found = True
        if (
            origin not in AUTOMATION_PUBLISHABLE_ORIGINS
            or image_origin != origin
            or AUTOMATION_ORIGIN_EVIDENCE.get(origin) != evidence_type
        ):
            reasons.append("automation_image_provenance")
            continue
        origins.append(origin)
        if origin == "imagegen" and not (
            str(brief.get("generation_prompt") or "").strip()
            and str(brief.get("generation_model") or "").strip()
        ):
            reasons.append("automation_imagegen_brief")

    if fallback_found:
        reasons.append("automation_fallback_image")
    if not any(origin in {"capture", "annotated_capture"} for origin in origins):
        reasons.append("automation_real_capture")
    if "imagegen" not in origins:
        reasons.append("automation_imagegen_explanation")
    return list(dict.fromkeys(reasons))


def _lead_source_reasons(
    source, *, min_visuals=2, require_visual_evidence=False
):
    reasons = []
    news = source.get("news") if isinstance(source.get("news"), list) else []
    item = news[0] if len(news) == 1 and isinstance(news[0], dict) else {}
    if not str(source.get("primary_query") or "").strip():
        reasons.append("lead_primary_query")

    references = item.get("references") if isinstance(item.get("references"), list) else []
    valid_references = [
        reference
        for reference in references
        if isinstance(reference, dict)
        and str(reference.get("title") or "").strip()
        and _is_http_url(reference.get("url"))
    ]
    reference_kinds = {
        str(reference.get("kind") or "").strip().lower()
        for reference in valid_references
    }
    if len(valid_references) < 2 or not reference_kinds.intersection(
        {"official", "documentation"}
    ):
        reasons.append("lead_references")

    content = item.get("content") if isinstance(item.get("content"), list) else []
    blocks = [block for block in content if isinstance(block, dict)]
    headings = [block for block in blocks if block.get("t") == "h"]
    if len(headings) < 4:
        reasons.append("lead_structure")
    visual_blocks = [block for block in blocks if block.get("t") == "visual"]
    visual_keys = {
        str(block.get("image") or "").strip() for block in visual_blocks
    }
    images = source.get("images") if isinstance(source.get("images"), dict) else {}
    declared_visual_keys = set(lead_visual_kinds(images))
    required_visual_keys = {
        f"visual_{index}" for index in range(1, min_visuals + 1)
    }
    if (
        not min_visuals <= len(visual_keys) <= 6
        or not required_visual_keys.issubset(visual_keys)
        or not visual_keys.issubset(images)
        or declared_visual_keys != visual_keys
    ):
        reasons.append("lead_explanatory_visuals")

    ad_indexes = [index for index, block in enumerate(blocks) if block.get("t") == "ad_break"]
    if len(ad_indexes) != 1:
        reasons.append("lead_ad_break")
    else:
        content_count = max(1, len(blocks) - 1)
        position = ad_indexes[0] / content_count
        if not 0.35 <= position <= 0.45:
            reasons.append("lead_ad_break_position")

    related = source.get("related_posts") if isinstance(source.get("related_posts"), list) else []
    valid_related = [
        post
        for post in related
        if isinstance(post, dict)
        and str(post.get("title") or "").strip()
        and _is_internal_tistory_post_url(post.get("url"))
    ]
    if len(valid_related) < 2:
        reasons.append("related_posts")
    if require_visual_evidence:
        reasons.extend(_lead_visual_evidence_reasons(source))
    return reasons


def find_recent_draft_duplicates(
    draft_id, current_day, *, root=ROOT, window_days=14
):
    """Compare one draft with prior drafts in the same content lane."""
    identity = resolve_draft_identity(draft_id)
    current_date = date.fromisoformat(identity.publish_date)
    current_news = current_day.get("news") if isinstance(current_day, dict) else []
    current_news = current_news if isinstance(current_news, list) else []
    current_editorial = (
        current_day.get("editorial")
        if isinstance(current_day.get("editorial"), dict)
        else {}
    )
    current_topic_key = str(current_editorial.get("topic_key") or "").strip().casefold()
    current_entities = {
        str(value or "").strip().casefold()
        for value in current_editorial.get("entities", [])
        if str(value or "").strip()
    }
    rotation_exception = str(
        current_editorial.get("rotation_exception") or ""
    ).strip()
    current_verification = (
        current_day.get("verification")
        if isinstance(current_day.get("verification"), dict)
        else {}
    )
    if identity.content_type == "automation_case":
        from blog_pipeline.collection.collect_automation import (
            _automation_source_fingerprint,
            _matches_recent_primary_query,
        )

        current_fingerprints = {
            _automation_source_fingerprint(canonical_url(item.get("url")))
            for item in current_news
            if isinstance(item, dict)
        }
        current_fingerprints.discard("")
        current_primary_query = str(
            current_day.get("primary_query") or ""
        ).strip()
    duplicates = []
    automation_rotation_checked = False

    for offset in range(1, window_days + 1):
        previous_day = (current_date - timedelta(days=offset)).isoformat()
        previous_draft_id = (
            f"{previous_day}-automation"
            if identity.content_type == "automation_case"
            else (
                f"{previous_day}-guide"
                if identity.content_type == "evergreen_guide"
                else previous_day
            )
        )
        previous_identity = resolve_draft_identity(previous_draft_id)
        previous = _read_json(Path(root) / previous_identity.source)
        if not isinstance(previous, dict):
            continue
        if identity.content_type == "automation_case":
            previous_meta = _read_json(
                Path(root)
                / "docs"
                / "tistory"
                / f"{previous_draft_id}.json"
            )
            if not (
                isinstance(previous_meta, dict)
                and previous_meta.get("draft_id") == previous_draft_id
                and previous_meta.get("publish_date") == previous_day
                and previous_meta.get("content_type") == "automation_case"
                and previous_meta.get("source") == previous_identity.source
                and previous_meta.get("publish_ready") is True
            ):
                continue
        previous_news = previous.get("news")
        if not isinstance(previous_news, list):
            continue

        if identity.content_type == "automation_case":
            previous_fingerprints = {
                _automation_source_fingerprint(canonical_url(item.get("url")))
                for item in previous_news
                if isinstance(item, dict)
            }
            previous_fingerprints.discard("")
            shared_fingerprints = current_fingerprints & previous_fingerprints
            previous_primary_query = str(
                previous.get("primary_query") or ""
            ).strip()
            automation_reason = ""
            automation_match = ""
            if shared_fingerprints:
                automation_reason = "same_repository"
                automation_match = sorted(shared_fingerprints)[0]
            elif current_primary_query and previous_primary_query and (
                _matches_recent_primary_query(
                    {"title": current_primary_query, "summary": ""},
                    {previous_primary_query},
                )
            ):
                automation_reason = "similar_primary_query"
                automation_match = previous_primary_query
            if automation_reason:
                current_item = next(
                    (item for item in current_news if isinstance(item, dict)), {}
                )
                previous_item = next(
                    (item for item in previous_news if isinstance(item, dict)), {}
                )
                duplicates.append(
                    {
                        "current_index": 1,
                        "current_title": str(current_item.get("title_kr") or ""),
                        "previous_day": previous_day,
                        "previous_draft_id": previous_draft_id,
                        "previous_index": 1,
                        "previous_title": str(previous_item.get("title_kr") or ""),
                        "reason": automation_reason,
                        "match": automation_match,
                        "similarity": 1.0,
                    }
                )
                continue

        previous_editorial = (
            previous.get("editorial")
            if isinstance(previous.get("editorial"), dict)
            else {}
        )
        previous_topic_key = str(
            previous_editorial.get("topic_key") or ""
        ).strip().casefold()
        previous_entities = {
            str(value or "").strip().casefold()
            for value in previous_editorial.get("entities", [])
            if str(value or "").strip()
        }
        semantic_reason = ""
        semantic_match = ""
        if current_topic_key and current_topic_key == previous_topic_key:
            semantic_reason = "same_topic_key"
            semantic_match = current_topic_key
        elif (
            identity.content_type == "daily_news"
            and offset <= 3
            and len(rotation_exception) < 40
            and current_entities.intersection(previous_entities)
        ):
            semantic_reason = "recent_entity"
            semantic_match = sorted(current_entities.intersection(previous_entities))[0]
        elif (
            identity.content_type == "automation_case"
            and not automation_rotation_checked
            and len(rotation_exception) < 40
        ):
            previous_verification = (
                previous.get("verification")
                if isinstance(previous.get("verification"), dict)
                else {}
            )
            current_lane = str(
                current_verification.get("problem_lane") or ""
            ).strip().casefold()
            previous_lane = str(
                previous_verification.get("problem_lane") or ""
            ).strip().casefold()
            current_brand = str(
                current_verification.get("tool_brand") or ""
            ).strip().casefold()
            previous_brand = str(
                previous_verification.get("tool_brand") or ""
            ).strip().casefold()
            if current_lane and current_lane == previous_lane:
                semantic_reason = "recent_problem_lane"
                semantic_match = current_lane
            elif current_brand and current_brand == previous_brand:
                semantic_reason = "recent_tool_brand"
                semantic_match = current_brand
        if identity.content_type == "automation_case":
            automation_rotation_checked = True
        if semantic_reason:
            current_item = next(
                (item for item in current_news if isinstance(item, dict)), {}
            )
            previous_item = next(
                (item for item in previous_news if isinstance(item, dict)), {}
            )
            duplicates.append(
                {
                    "current_index": 1,
                    "current_title": str(current_item.get("title_kr") or ""),
                    "previous_day": previous_day,
                    "previous_draft_id": previous_draft_id,
                    "previous_index": 1,
                    "previous_title": str(previous_item.get("title_kr") or ""),
                    "reason": semantic_reason,
                    "match": semantic_match,
                    "similarity": 1.0,
                }
            )
            continue

        for current_index, current in enumerate(current_news, 1):
            if not isinstance(current, dict):
                continue
            current_url = canonical_url(current.get("url"))
            current_title = normalized_title(current.get("title_kr"))
            for previous_index, old in enumerate(previous_news, 1):
                if not isinstance(old, dict):
                    continue
                old_url = canonical_url(old.get("url"))
                old_title = normalized_title(old.get("title_kr"))
                reason = ""
                score = 0.0
                if current_url and old_url and current_url == old_url:
                    reason = "same_url"
                    score = 1.0
                elif len(current_title) >= 12 and len(old_title) >= 12:
                    score = SequenceMatcher(None, current_title, old_title).ratio()
                    if score >= 0.88:
                        reason = "similar_title"
                if reason:
                    duplicates.append(
                        {
                            "current_index": current_index,
                            "current_title": str(current.get("title_kr") or ""),
                            "previous_day": previous_day,
                            "previous_draft_id": previous_draft_id,
                            "previous_index": previous_index,
                            "previous_title": str(old.get("title_kr") or ""),
                            "reason": reason,
                            "similarity": round(score, 3),
                        }
                    )
                    break
    return duplicates


def find_recent_duplicates(day_id, current_day, *, root=ROOT, window_days=14):
    """Backward-compatible daily duplicate comparison."""
    day_id = validate_day_id(day_id)
    return find_recent_draft_duplicates(
        day_id, current_day, root=root, window_days=window_days
    )


def _inspect_draft_state(draft_id, *, root=ROOT, window_days=14):
    """Return NEW, PARTIAL, or COMPLETE for one collision-safe draft."""
    identity = resolve_draft_identity(draft_id)
    root = Path(root)
    source_path = root / identity.source
    tistory_dir = root / "docs" / "tistory"
    meta_path = tistory_dir / f"{identity.draft_id}.json"
    html_path = tistory_dir / f"{identity.draft_id}.html"
    adfit_path = tistory_dir / f"{identity.draft_id}-adfit.html"
    preview_path = root / "docs" / "preview" / f"{identity.draft_id}.html"
    output_paths = (source_path, meta_path, html_path, adfit_path, preview_path)

    if not any(path.exists() for path in output_paths):
        return {
            "day": identity.publish_date,
            "draft_id": identity.draft_id,
            "content_type": identity.content_type,
            "status": "NEW",
            "reasons": [],
            "duplicates": [],
        }

    reasons = []
    source = _read_json(source_path)
    if not isinstance(source, dict):
        reasons.append("missing_or_invalid_source")
        source = {}
    else:
        try:
            resolve_draft_identity(identity.draft_id, source)
        except ValueError:
            reasons.append("invalid_draft_identity")
    news = source.get("news")
    lead_story = is_lead_story(source)
    expected_news_count = 1 if lead_story else 3
    if not isinstance(news, list) or len(news) != expected_news_count:
        reasons.append("news_count")
    if lead_story:
        reasons.extend(
            _lead_source_reasons(
                source,
                min_visuals=(
                    3
                    if identity.content_type in {"automation_case", "evergreen_guide"}
                    else 2
                ),
                require_visual_evidence=(
                    date.fromisoformat(identity.publish_date) >= date(2026, 7, 18)
                ),
            )
        )
        if (
            identity.content_type == "automation_case"
            and date.fromisoformat(identity.publish_date)
            >= AUTOMATION_VISUAL_POLICY_START
        ):
            reasons.extend(_automation_visual_quality_reasons(source))
    reasons.extend(source_quality_reasons(source, identity))

    if date.fromisoformat(identity.publish_date) >= date(2026, 7, 16):
        from .optimize_images import inspect_draft_images

        try:
            image_result = inspect_draft_images(identity.draft_id, root=root)
        except (OSError, TypeError, ValueError):
            reasons.append("invalid_image_manifest")
        else:
            reasons.extend(image_result["reasons"])

    duplicates = find_recent_draft_duplicates(
        identity.draft_id,
        source,
        root=root,
        window_days=max(window_days, 60) if lead_story else window_days,
    )
    if duplicates:
        reasons.append("recent_duplicate")

    meta = _read_json(meta_path)
    if not isinstance(meta, dict):
        reasons.append("missing_publish_meta")
        meta = {}
    else:
        try:
            resolve_draft_identity(identity.draft_id, meta)
        except ValueError:
            reasons.append("invalid_publish_identity")
        meta_source = str(meta.get("source") or "").strip()
        if (
            meta_source
            and meta_source != identity.source
        ) or (
            identity.content_type in {"automation_case", "evergreen_guide"}
            and meta_source != identity.source
        ):
            reasons.append("invalid_publish_source")
        if not meta.get("publish_ready"):
            reasons.append("not_publish_ready")
        if date.fromisoformat(identity.publish_date) >= PUBLISH_GATE_START:
            from .export_tistory import (
                build_image_assets,
                build_recommended_tags,
                post_title,
            )

            try:
                expected_meta = {
                    "source": identity.source,
                    "draft_id": identity.draft_id,
                    "publish_date": identity.publish_date,
                    "content_type": identity.content_type,
                    "content_label": identity.content_label,
                    "category": source.get("category"),
                    "scheduled_at": source.get("scheduled_at"),
                    "tags": build_recommended_tags(source),
                    "title": post_title(source),
                    "image_assets": build_image_assets(source),
                }
            except SCHEMA_EXCEPTIONS:
                reasons.append("invalid_publish_metadata")
            else:
                if any(
                    meta.get(key) != value for key, value in expected_meta.items()
                ):
                    reasons.append("invalid_publish_metadata")

    image_kinds = {
        item.get("kind")
        for item in meta.get("image_assets", [])
        if isinstance(item, dict)
    }
    required_images = set(image_kinds_for_day(source))
    if lead_story:
        required_images.update({"cover", "visual_1", "visual_2"})
        if identity.content_type == "automation_case":
            required_images.add("visual_3")
    if not required_images.issubset(image_kinds):
        reasons.append("missing_editorial_images")

    try:
        body_html = html_path.read_text(encoding="utf-8")
    except OSError:
        body_html = ""
    if body_html.count('class="daily-digest-post"') != 1:
        reasons.append("body_count")
    if (
        date.fromisoformat(identity.publish_date) >= PUBLISH_GATE_START
        and has_inline_post_style(body_html)
    ):
        reasons.append("inline_post_style")
    rendered_news_marker = (
        'class="digest-news-card digest-lead-story"'
        if lead_story
        else 'class="digest-news-card"'
    )
    if body_html.count(rendered_news_marker) != expected_news_count:
        reasons.append("rendered_news_count")
    if lead_story and body_html.count('data-digest-ad-break="true"') != 1:
        reasons.append("rendered_ad_break")

    try:
        adfit_html = adfit_path.read_text(encoding="utf-8")
    except OSError:
        adfit_html = ""
    ad_at = adfit_html.find('data-ad-vendor="adfit"')
    first_at = adfit_html.find('id="digest-news-1"')
    second_at = (
        adfit_html.find('class="digest-lead-continuation"')
        if lead_story
        else adfit_html.find('id="digest-news-2"')
    )
    if adfit_html.count('data-ad-vendor="adfit"') != 1:
        reasons.append("adfit_count")
    elif not (0 <= first_at < ad_at < second_at):
        reasons.append("adfit_position")

    if date.fromisoformat(identity.publish_date) >= PUBLISH_GATE_START:
        from .export_tistory import build_adfit_ready_html, render_post

        try:
            canonical_body = render_post(identity.publish_date, source)
            canonical_adfit = build_adfit_ready_html(canonical_body)
        except SCHEMA_EXCEPTIONS:
            reasons.append("invalid_render_contract")
            canonical_body = ""
            canonical_adfit = ""
        if canonical_body and body_html != canonical_body:
            reasons.append("stale_html_artifact")
        if canonical_adfit and adfit_html != canonical_adfit:
            reasons.append("stale_adfit_artifact")

        if build_adfit_ready_html(body_html) != adfit_html:
            reasons.append("stale_adfit_artifact")
        if (
            adfit_html.count('data-ke-type="revenue"') != 1
            or adfit_html.count('data-ad-id-pc="713977"') != 1
            or adfit_html.count('data-ad-id-mobile="713980"') != 1
        ):
            reasons.append("invalid_adfit_markup")
        reasons.extend(
            artifact_freshness_reasons(source_path, meta, html_path, adfit_path)
        )

    if date.fromisoformat(identity.publish_date) >= PUBLISH_GATE_START:
        reasons.extend(preview_artifact_reasons(preview_path, adfit_html, meta))
    elif not preview_path.is_file():
        reasons.append("missing_preview")

    return {
        "day": identity.publish_date,
        "draft_id": identity.draft_id,
        "content_type": identity.content_type,
        "status": "COMPLETE" if not reasons else "PARTIAL",
        "reasons": list(dict.fromkeys(reasons)),
        "duplicates": duplicates,
    }


def inspect_draft_state(draft_id, *, root=ROOT, window_days=14):
    """Return NEW, PARTIAL, or COMPLETE and fail closed on malformed JSON."""
    identity = resolve_draft_identity(draft_id)
    try:
        return _inspect_draft_state(
            identity.draft_id,
            root=root,
            window_days=window_days,
        )
    except SCHEMA_EXCEPTIONS:
        return {
            "day": identity.publish_date,
            "draft_id": identity.draft_id,
            "content_type": identity.content_type,
            "status": "PARTIAL",
            "reasons": ["invalid_source_schema"],
            "duplicates": [],
        }


def inspect_daily_state(day_id, *, root=ROOT, window_days=14):
    """Backward-compatible strict daily guard."""
    day_id = validate_day_id(day_id)
    return inspect_draft_state(day_id, root=root, window_days=window_days)


def _source_preflight_diagnostics(source, identity):
    publish_day = date.fromisoformat(identity.publish_date)
    weekday_labels = ["월", "화", "수", "목", "금", "토", "일"]
    expected_category = category_for_identity(identity)
    regular_schedule = regular_schedule_for_identity(identity)
    is_manual_extra = source.get("publication_mode") == "manual_extra"
    publication_mode = (
        "manual_extra" if is_manual_extra or not regular_schedule else "scheduled"
    )
    scheduled_at = (
        str(source.get("scheduled_at") or "").strip()
        if is_manual_extra
        else regular_schedule
    ) or f"{identity.publish_date}T14:00:00+09:00"
    expected_identity = {
        "schema_version": 3,
        "format": "lead-story-v1",
        "draft_id": identity.draft_id,
        "publish_date": identity.publish_date,
        "date_label": f"{publish_day.year}. {publish_day.month}. {publish_day.day}",
        "weekday": weekday_labels[publish_day.weekday()],
        "content_type": identity.content_type,
        "content_label": identity.content_label,
        "category": expected_category,
        "publication_mode": publication_mode,
        "scheduled_at": scheduled_at,
    }
    editorial = source.get("editorial") if isinstance(source.get("editorial"), dict) else {}
    editorial_lengths = {
        key: {
            "actual": len(" ".join(str(editorial.get(key) or "").split())),
            "minimum": minimum,
            "maximum": maximum,
        }
        for key, (minimum, maximum) in EDITORIAL_LENGTH_RULES.items()
    }
    visual = source.get("visual") if isinstance(source.get("visual"), dict) else {}
    briefs = visual.get("assets") if isinstance(visual.get("assets"), list) else []
    invalid_scene_labels = []
    for index, brief in enumerate(briefs, 1):
        labels = brief.get("scene_label") if isinstance(brief, dict) else None
        if not (
            isinstance(labels, list)
            and 2 <= len(labels) <= 4
            and all(isinstance(label, str) and label.strip() for label in labels)
        ):
            invalid_scene_labels.append(f"visual_{index}")

    news = source.get("news") if isinstance(source.get("news"), list) else []
    item = news[0] if len(news) == 1 and isinstance(news[0], dict) else {}
    content = item.get("content") if isinstance(item.get("content"), list) else []
    blocks = [block for block in content if isinstance(block, dict)]
    headings = sum(block.get("t") == "h" for block in blocks)
    visuals = sum(block.get("t") == "visual" for block in blocks)
    ad_indexes = [index for index, block in enumerate(blocks) if block.get("t") == "ad_break"]
    ad_position = None
    if len(ad_indexes) == 1:
        ad_position = round(ad_indexes[0] / max(1, len(blocks) - 1), 3)
    policy = DEPTH_POLICIES[identity.content_type]
    depth = {
        "estimated_minutes": estimate_read_minutes(source),
        "blocks": len(blocks),
        "headings": headings,
        "visuals": visuals,
        "ad_position": ad_position,
        "required": {
            **{
                key: value
                for key, value in policy.items()
                if key != "required_block_types"
            },
            "required_block_types": sorted(policy["required_block_types"]),
            "ad_position": [0.35, 0.45],
        },
    }
    return {
        "expected_identity": expected_identity,
        "editorial_lengths": editorial_lengths,
        "invalid_scene_labels": invalid_scene_labels,
        "depth": depth,
    }


def inspect_source_state(draft_id, *, root=ROOT, window_days=14):
    """Validate the written JSON before generating image files or exports."""
    identity = resolve_draft_identity(draft_id)
    root = Path(root)
    source = _read_json(root / identity.source)
    if not isinstance(source, dict):
        return {
            "day": identity.publish_date,
            "draft_id": identity.draft_id,
            "content_type": identity.content_type,
            "status": "PARTIAL",
            "reasons": ["missing_or_invalid_source"],
            "duplicates": [],
        }

    reasons = []
    try:
        resolve_draft_identity(identity.draft_id, source)
    except ValueError:
        reasons.append("invalid_draft_identity")
    news = source.get("news")
    lead_story = is_lead_story(source)
    if not isinstance(news, list) or len(news) != (1 if lead_story else 3):
        reasons.append("news_count")
    if lead_story:
        lead_reasons = _lead_source_reasons(
            source,
            min_visuals=(
                3
                if identity.content_type in {"automation_case", "evergreen_guide"}
                else 2
            ),
            require_visual_evidence=True,
        )
        # Image records and files are deliberately created only after this gate.
        reasons.extend(
            reason for reason in lead_reasons if reason != "lead_explanatory_visuals"
        )
    reasons.extend(source_authoring_reasons(source, identity))
    duplicates = find_recent_draft_duplicates(
        identity.draft_id,
        source,
        root=root,
        window_days=window_days,
    )
    if duplicates:
        reasons.append("duplicate_topic")
    result = {
        "day": identity.publish_date,
        "draft_id": identity.draft_id,
        "content_type": identity.content_type,
        "status": "READY" if not reasons else "PARTIAL",
        "reasons": list(dict.fromkeys(reasons)),
        "duplicates": duplicates,
    }
    result.update(_source_preflight_diagnostics(source, identity))
    return result


def inspect_publish_ready_drafts(*, root=ROOT):
    """Fail CI when any committed future draft is partial or not publish-ready."""
    root = Path(root)
    failures = []
    draft_ids = set()
    for source_path in sorted((root / "data" / "days").glob("*.json")):
        try:
            identity = resolve_draft_identity(source_path.stem)
            publish_date = date.fromisoformat(identity.publish_date)
        except (TypeError, ValueError):
            continue
        if publish_date >= PUBLISH_GATE_START:
            draft_ids.add(identity.draft_id)
    for source_path in sorted(
        (root / "data" / "automation_cases").glob("*.json")
    ):
        try:
            identity = resolve_draft_identity(f"{source_path.stem}-automation")
            publish_date = date.fromisoformat(identity.publish_date)
        except (TypeError, ValueError):
            continue
        if publish_date >= PUBLISH_GATE_START:
            draft_ids.add(identity.draft_id)
    for source_path in sorted((root / "data" / "guides").glob("*.json")):
        try:
            identity = resolve_draft_identity(f"{source_path.stem}-guide")
            publish_date = date.fromisoformat(identity.publish_date)
        except (TypeError, ValueError):
            continue
        if publish_date >= PUBLISH_GATE_START:
            draft_ids.add(identity.draft_id)
    for meta_path in sorted((root / "docs" / "tistory").glob("*.json")):
        try:
            identity = resolve_draft_identity(meta_path.stem)
            publish_date = date.fromisoformat(identity.publish_date)
        except (TypeError, ValueError):
            continue
        if publish_date >= PUBLISH_GATE_START:
            draft_ids.add(identity.draft_id)

    for draft_id in sorted(draft_ids):
        identity = resolve_draft_identity(draft_id)
        result = inspect_draft_state(
            draft_id,
            root=root,
            window_days={
                "automation_case": 90,
                "evergreen_guide": 365,
            }.get(identity.content_type, 60),
        )
        if result.get("status") != "COMPLETE":
            failures.append(result)
    return {"checked": len(draft_ids), "failures": failures}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Guard one daily editorial run.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--today", action="store_true")
    group.add_argument("--day")
    group.add_argument("--draft-id")
    group.add_argument("--all-publish-ready", action="store_true")
    parser.add_argument("--check-duplicates", action="store_true")
    parser.add_argument("--source-only", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--window-days", type=int, default=14)
    args = parser.parse_args(argv)

    if args.all_publish_ready:
        result = inspect_publish_ready_drafts(root=ROOT)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result["failures"] else 0

    draft_id = (
        args.draft_id
        or args.day
        or datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
    )
    if args.source_only:
        result = inspect_source_state(
            draft_id, window_days=max(1, args.window_days)
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "READY" else 1

    result = inspect_draft_state(draft_id, window_days=max(1, args.window_days))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.check_duplicates and result["duplicates"]:
        return 2
    if args.require_complete and result["status"] != "COMPLETE":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
