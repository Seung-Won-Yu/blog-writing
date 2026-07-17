"""Stop duplicate daily work and reject recently repeated news topics."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from blog_pipeline.collection.news_pipeline import validate_day_id
from .draft_identity import resolve_draft_identity
from .editorial_format import image_kinds_for_day, is_lead_story, lead_visual_kinds


ROOT = Path(__file__).resolve().parents[2]
TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source"}


def canonical_url(value):
    text = str(value or "").strip()
    if not text:
        return ""
    parsed = urlsplit(text)
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


def _is_http_url(value):
    try:
        parsed = urlsplit(str(value or "").strip())
    except ValueError:
        return False
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)


def _read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None


def _lead_source_reasons(source, *, min_visuals=2):
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
        and _is_http_url(post.get("url"))
    ]
    if len(valid_related) < 2:
        reasons.append("related_posts")
    return reasons


def find_recent_draft_duplicates(
    draft_id, current_day, *, root=ROOT, window_days=14
):
    """Compare one draft with prior drafts in the same content lane."""
    identity = resolve_draft_identity(draft_id)
    current_date = date.fromisoformat(identity.publish_date)
    current_news = current_day.get("news") if isinstance(current_day, dict) else []
    current_news = current_news if isinstance(current_news, list) else []
    duplicates = []

    for offset in range(1, window_days + 1):
        previous_day = (current_date - timedelta(days=offset)).isoformat()
        previous_draft_id = (
            f"{previous_day}-automation"
            if identity.content_type == "automation_case"
            else previous_day
        )
        previous_identity = resolve_draft_identity(previous_draft_id)
        previous = _read_json(Path(root) / previous_identity.source)
        if not isinstance(previous, dict):
            continue
        previous_news = previous.get("news")
        if not isinstance(previous_news, list):
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


def inspect_draft_state(draft_id, *, root=ROOT, window_days=14):
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
                min_visuals=3
                if identity.content_type == "automation_case"
                else 2,
            )
        )

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
            identity.content_type == "automation_case"
            and meta_source != identity.source
        ):
            reasons.append("invalid_publish_source")
        if not meta.get("publish_ready"):
            reasons.append("not_publish_ready")

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

    if not preview_path.is_file():
        reasons.append("missing_preview")

    return {
        "day": identity.publish_date,
        "draft_id": identity.draft_id,
        "content_type": identity.content_type,
        "status": "COMPLETE" if not reasons else "PARTIAL",
        "reasons": list(dict.fromkeys(reasons)),
        "duplicates": duplicates,
    }


def inspect_daily_state(day_id, *, root=ROOT, window_days=14):
    """Backward-compatible strict daily guard."""
    day_id = validate_day_id(day_id)
    return inspect_draft_state(day_id, root=root, window_days=window_days)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Guard one daily editorial run.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--today", action="store_true")
    group.add_argument("--day")
    group.add_argument("--draft-id")
    parser.add_argument("--check-duplicates", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--window-days", type=int, default=14)
    args = parser.parse_args(argv)

    draft_id = (
        args.draft_id
        or args.day
        or datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
    )
    result = inspect_draft_state(
        draft_id, window_days=max(1, args.window_days)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.check_duplicates and result["duplicates"]:
        return 2
    if args.require_complete and result["status"] != "COMPLETE":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
