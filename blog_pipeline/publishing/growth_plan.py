"""Read-only routing for the three-new/two-refresh editorial experiment."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLAN = ROOT / "config/content_growth_trial.json"
WEEKDAYS = (
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
)


def plan_for_day(plan, day):
    """Select a mode and at most one unfinished refresh; never publish or mutate."""
    started = dt.date.fromisoformat(plan["started_on"])
    review = dt.date.fromisoformat(plan["review_on"])
    observed = dt.date.fromisoformat(plan["evidence_observed_on"])
    if review <= started:
        raise ValueError("review_on must follow started_on")
    modes = plan["weekday_modes"]
    expected = dict(zip(WEEKDAYS, (
        "new_article", "refresh_existing", "new_article", "refresh_existing",
        "new_article", "off", "off",
    )))
    if modes != expected:
        raise ValueError("Expected three new articles and two refresh slots, weekdays only")
    mode = modes[WEEKDAYS[day.weekday()]] if day >= started else "off"
    age = (day - observed).days
    evidence_fresh = -1 <= age <= 30
    result = {
        "day": day.isoformat(),
        "mode": mode,
        "started_on": started.isoformat(),
        "review_on": review.isoformat(),
        "review_due": day >= review,
        "evidence_fresh": evidence_fresh,
        "evidence_note": (
            "Page totals, not query-page metrics; verify the selected page's queries."
            if evidence_fresh else
            "Refresh Search Console evidence; do not present the old snapshot as current."
        ),
        "target": None,
    }
    if mode != "refresh_existing":
        return result

    queue = plan.get("refresh_queue", [])
    eligible = []
    for item in queue:
        if item.get("status") not in {"planned", "in_progress"}:
            continue
        url = urlsplit(item["page_url"])
        path = Path(item["source"])
        if (
            url.scheme != "https" or url.netloc != "won0322.tistory.com"
            or not url.path.strip("/").isdigit() or url.query or url.fragment
            or path.is_absolute() or ".." in path.parts
            or len(path.parts) != 3 or path.parts[:2] not in {
                ("data", "days"), ("data", "automation_cases"), ("data", "guides")
            } or path.suffix != ".json"
        ):
            raise ValueError("Invalid refresh target URL or source path")
        eligible.append(item)
    if eligible:
        result["target"] = min(
            eligible,
            key=lambda item: (item["status"] != "in_progress", item["priority"]),
        )
    else:
        result["next_action"] = (
            "Review pending handoffs and select another existing page using current "
            "Search Console evidence; do not replace this slot with a new article."
        )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    dates = parser.add_mutually_exclusive_group()
    dates.add_argument("--today", action="store_true")
    dates.add_argument("--day", type=dt.date.fromisoformat)
    args = parser.parse_args(argv)
    day = args.day or dt.datetime.now(ZoneInfo("Asia/Seoul")).date()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    print(json.dumps(plan_for_day(plan, day), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
