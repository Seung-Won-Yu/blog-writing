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


def _read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None


def find_recent_duplicates(day_id, current_day, *, root=ROOT, window_days=14):
    """Compare current news with prior days by canonical URL and close title."""
    current_date = date.fromisoformat(day_id)
    current_news = current_day.get("news") if isinstance(current_day, dict) else []
    current_news = current_news if isinstance(current_news, list) else []
    duplicates = []

    for offset in range(1, window_days + 1):
        previous_day = (current_date - timedelta(days=offset)).isoformat()
        previous = _read_json(Path(root) / "data" / "days" / f"{previous_day}.json")
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
                            "previous_index": previous_index,
                            "previous_title": str(old.get("title_kr") or ""),
                            "reason": reason,
                            "similarity": round(score, 3),
                        }
                    )
                    break
    return duplicates


def inspect_daily_state(day_id, *, root=ROOT, window_days=14):
    """Return NEW, PARTIAL, or COMPLETE using committed output invariants."""
    root = Path(root)
    source_path = root / "data" / "days" / f"{day_id}.json"
    tistory_dir = root / "docs" / "tistory"
    meta_path = tistory_dir / f"{day_id}.json"
    html_path = tistory_dir / f"{day_id}.html"
    adfit_path = tistory_dir / f"{day_id}-adfit.html"
    preview_path = root / "docs" / "preview" / f"{day_id}.html"
    output_paths = (source_path, meta_path, html_path, adfit_path, preview_path)

    if not any(path.exists() for path in output_paths):
        return {"day": day_id, "status": "NEW", "reasons": [], "duplicates": []}

    reasons = []
    source = _read_json(source_path)
    if not isinstance(source, dict):
        reasons.append("missing_or_invalid_source")
        source = {}
    news = source.get("news")
    if not isinstance(news, list) or len(news) != 3:
        reasons.append("news_count")

    duplicates = find_recent_duplicates(
        day_id, source, root=root, window_days=window_days
    )
    if duplicates:
        reasons.append("recent_duplicate")

    meta = _read_json(meta_path)
    if not isinstance(meta, dict):
        reasons.append("missing_publish_meta")
        meta = {}
    elif not meta.get("publish_ready"):
        reasons.append("not_publish_ready")

    image_kinds = {
        item.get("kind")
        for item in meta.get("image_assets", [])
        if isinstance(item, dict)
    }
    required_images = {"cover", "story_1", "story_2", "story_3"}
    if not required_images.issubset(image_kinds):
        reasons.append("missing_editorial_images")

    try:
        body_html = html_path.read_text(encoding="utf-8")
    except OSError:
        body_html = ""
    if body_html.count('class="daily-digest-post"') != 1:
        reasons.append("body_count")
    if body_html.count('class="digest-news-card"') != 3:
        reasons.append("rendered_news_count")

    try:
        adfit_html = adfit_path.read_text(encoding="utf-8")
    except OSError:
        adfit_html = ""
    ad_at = adfit_html.find('data-ad-vendor="adfit"')
    first_at = adfit_html.find('id="digest-news-1"')
    second_at = adfit_html.find('id="digest-news-2"')
    if adfit_html.count('data-ad-vendor="adfit"') != 1:
        reasons.append("adfit_count")
    elif not (0 <= first_at < ad_at < second_at):
        reasons.append("adfit_position")

    if not preview_path.is_file():
        reasons.append("missing_preview")

    return {
        "day": day_id,
        "status": "COMPLETE" if not reasons else "PARTIAL",
        "reasons": list(dict.fromkeys(reasons)),
        "duplicates": duplicates,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Guard one daily editorial run.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--today", action="store_true")
    group.add_argument("--day")
    parser.add_argument("--check-duplicates", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--window-days", type=int, default=14)
    args = parser.parse_args(argv)

    day_id = args.day or datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
    result = inspect_daily_state(day_id, window_days=max(1, args.window_days))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.check_duplicates and result["duplicates"]:
        return 2
    if args.require_complete and result["status"] != "COMPLETE":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
