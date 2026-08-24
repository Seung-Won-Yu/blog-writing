"""Guard the separate weekly hands-on automation draft.

The module path is retained for compatibility with existing jobs and history.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

from blog_pipeline.collection.news_pipeline import validate_day_id
from .daily_guard import ROOT, inspect_draft_state
from .draft_identity import automation_draft_id, is_regular_automation_day


def inspect_saturday_state(day_id, *, root=ROOT, window_days=90):
    """Return SKIP off the configured weekly day; otherwise inspect the draft."""
    day_id = validate_day_id(day_id)
    publish_date = date.fromisoformat(day_id)
    draft_id = automation_draft_id(day_id)
    if not is_regular_automation_day(publish_date):
        return {
            "day": day_id,
            "draft_id": draft_id,
            "content_type": "automation_case",
            "status": "SKIP",
            "reason": "not_regular_automation_day",
            "reasons": [],
            "duplicates": [],
        }
    return inspect_draft_state(
        draft_id, root=root, window_days=max(1, window_days)
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="금요일 업무자동화 실험 초안의 중복 실행을 막습니다."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--today", action="store_true")
    group.add_argument("--day")
    parser.add_argument("--check-duplicates", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--window-days", type=int, default=90)
    args = parser.parse_args(argv)

    day_id = args.day or datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
    result = inspect_saturday_state(
        day_id, window_days=max(1, args.window_days)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "SKIP":
        return 0
    if args.check_duplicates and result["duplicates"]:
        return 2
    if args.require_complete and result["status"] != "COMPLETE":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
