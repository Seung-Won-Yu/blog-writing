"""Record and inspect the handoff state between collection and editorial runs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .news_pipeline import editorial_lane_for_day, validate_day_id


ROOT = Path(__file__).resolve().parents[2]
STATUS_SCHEMA_VERSION = 1
INBOX_PATHS = {
    "news": Path("docs/inbox"),
    "automation": Path("docs/automation-inbox"),
}


def expected_lane(kind, day_id):
    if kind == "news":
        return editorial_lane_for_day(day_id)
    if kind == "automation":
        return "developer_insight"
    raise ValueError("kind must be news or automation")


def write_collection_status(
    output_dir,
    *,
    kind,
    day_id,
    generated_at,
    state,
    reasons=None,
    quality=None,
):
    """Persist a small status file even when the last good inbox is preserved."""
    day_id = validate_day_id(day_id)
    payload = {
        "schema_version": STATUS_SCHEMA_VERSION,
        "kind": kind,
        "target_day": day_id,
        "editorial_lane": expected_lane(kind, day_id),
        "generated_at": str(generated_at or ""),
        "state": str(state or "BLOCKED"),
        "reasons": [str(item) for item in reasons or [] if item],
        "quality": dict(quality or {}),
    }
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / "status.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _load_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _aware_datetime(value):
    try:
        parsed = dt.datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def inspect_inbox(
    *,
    kind,
    day_id,
    root=ROOT,
    now=None,
    max_age_minutes=240,
):
    """Return a safe editorial handoff state without consuming stale candidates."""
    day_id = validate_day_id(day_id)
    expected = expected_lane(kind, day_id)
    root = Path(root)
    inbox_dir = root / INBOX_PATHS[kind]
    status = _load_json(inbox_dir / "status.json")
    latest = _load_json(inbox_dir / "latest.json")
    reasons = []

    target_day = str(status.get("target_day") or latest.get("day") or "")
    lane = str(
        status.get("editorial_lane")
        or (latest.get("selection") or {}).get("editorial_lane")
        or ("developer_insight" if kind == "automation" and latest else "")
    )
    generated_at = _aware_datetime(
        status.get("generated_at") or latest.get("generated_at")
    )
    current = now or dt.datetime.now(ZoneInfo("Asia/Seoul"))
    if current.tzinfo is None:
        current = current.replace(tzinfo=ZoneInfo("Asia/Seoul"))

    if target_day != day_id:
        reasons.append("inbox_target_day")
    if lane != expected:
        reasons.append("inbox_editorial_lane")
    if generated_at is None:
        reasons.append("inbox_generated_at")
    else:
        age = current.astimezone(dt.timezone.utc) - generated_at.astimezone(
            dt.timezone.utc
        )
        if age < dt.timedelta(minutes=-5) or age > dt.timedelta(
            minutes=max(1, int(max_age_minutes))
        ):
            reasons.append("inbox_stale")
    if not latest:
        reasons.append("inbox_missing")
    elif str(latest.get("day") or "") != day_id:
        reasons.append("inbox_latest_day")

    collection_state = str(status.get("state") or "LEGACY")
    collection_reasons = [
        str(item) for item in status.get("reasons", []) if item
    ]
    if collection_state == "BLOCKED":
        reasons.append("collection_blocked")
        reasons.extend(collection_reasons)

    reasons = list(dict.fromkeys(reasons))
    if reasons:
        state = "RECOLLECT_REQUIRED"
    elif collection_state == "PARTIAL":
        state = "READY_WITH_RESEARCH_FALLBACK"
    else:
        state = "READY"
    return {
        "kind": kind,
        "target_day": day_id,
        "editorial_lane": expected,
        "state": state,
        "reasons": reasons or collection_reasons,
        "generated_at": generated_at.isoformat() if generated_at else "",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="09시 편집 전에 후보함 날짜·역할·신선도를 확인합니다."
    )
    parser.add_argument("--kind", choices=sorted(INBOX_PATHS), required=True)
    day_group = parser.add_mutually_exclusive_group()
    day_group.add_argument("--today", action="store_true")
    day_group.add_argument("--day")
    parser.add_argument("--max-age-minutes", type=int, default=240)
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    today = dt.datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
    try:
        day_id = validate_day_id(args.day or today)
        result = inspect_inbox(
            kind=args.kind,
            day_id=day_id,
            root=args.root,
            max_age_minutes=args.max_age_minutes,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["state"].startswith("READY") else 2


if __name__ == "__main__":
    raise SystemExit(main())
