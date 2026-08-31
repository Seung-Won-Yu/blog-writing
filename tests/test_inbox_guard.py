import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from blog_pipeline.collection.inbox_guard import (
    inspect_inbox,
    write_collection_status,
)


class InboxGuardTests(unittest.TestCase):
    def write_latest(self, root, *, kind, day, generated_at, lane=None):
        directory = root / (
            "docs/inbox" if kind == "news" else "docs/automation-inbox"
        )
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "day": day,
            "generated_at": generated_at,
            "selection": {"editorial_lane": lane} if lane else {},
            "selected": [{"title": "후보"}],
            "candidates": [{"title": "후보"}],
            "errors": [],
        }
        (directory / "latest.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        return directory

    def test_ready_news_status_matches_day_lane_and_freshness(self):
        now = dt.datetime(2026, 8, 31, 9, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inbox = self.write_latest(
                root,
                kind="news",
                day="2026-08-31",
                generated_at="2026-08-30T23:20:00+00:00",
                lane="evergreen_problem",
            )
            write_collection_status(
                inbox,
                kind="news",
                day_id="2026-08-31",
                generated_at="2026-08-30T23:20:00+00:00",
                state="READY",
                quality={"selected": 4},
            )

            result = inspect_inbox(
                kind="news", day_id="2026-08-31", root=root, now=now
            )

        self.assertEqual(result["state"], "READY")
        self.assertEqual(result["reasons"], [])

    def test_blocked_collection_never_falls_back_to_last_good_inbox(self):
        now = dt.datetime(2026, 9, 2, 9, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inbox = self.write_latest(
                root,
                kind="news",
                day="2026-08-31",
                generated_at="2026-08-31T00:20:00+00:00",
                lane="evergreen_problem",
            )
            write_collection_status(
                inbox,
                kind="news",
                day_id="2026-09-02",
                generated_at="2026-09-01T23:20:00+00:00",
                state="BLOCKED",
                reasons=["insufficient_candidates"],
            )

            result = inspect_inbox(
                kind="news", day_id="2026-09-02", root=root, now=now
            )

        self.assertEqual(result["state"], "RECOLLECT_REQUIRED")
        self.assertIn("collection_blocked", result["reasons"])
        self.assertIn("inbox_latest_day", result["reasons"])
        self.assertIn("insufficient_candidates", result["reasons"])

    def test_stale_automation_inbox_requires_recollection(self):
        now = dt.datetime(2026, 9, 4, 9, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inbox = self.write_latest(
                root,
                kind="automation",
                day="2026-09-04",
                generated_at="2026-09-03T18:00:00+00:00",
            )
            write_collection_status(
                inbox,
                kind="automation",
                day_id="2026-09-04",
                generated_at="2026-09-03T18:00:00+00:00",
                state="READY",
            )

            result = inspect_inbox(
                kind="automation", day_id="2026-09-04", root=root, now=now
            )

        self.assertEqual(result["state"], "RECOLLECT_REQUIRED")
        self.assertIn("inbox_stale", result["reasons"])

    def test_partial_inbox_is_explicitly_handed_to_research_fallback(self):
        now = dt.datetime(2026, 9, 2, 9, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inbox = self.write_latest(
                root,
                kind="news",
                day="2026-09-02",
                generated_at="2026-09-01T23:20:00+00:00",
                lane="change_explainer",
            )
            write_collection_status(
                inbox,
                kind="news",
                day_id="2026-09-02",
                generated_at="2026-09-01T23:20:00+00:00",
                state="PARTIAL",
                reasons=["insufficient_selected_candidates"],
            )

            result = inspect_inbox(
                kind="news", day_id="2026-09-02", root=root, now=now
            )

        self.assertEqual(result["state"], "READY_WITH_RESEARCH_FALLBACK")
        self.assertEqual(result["reasons"], ["insufficient_selected_candidates"])


if __name__ == "__main__":
    unittest.main()
