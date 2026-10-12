import copy
import datetime as dt
import json
import unittest

from blog_pipeline.publishing.growth_plan import DEFAULT_PLAN, ROOT, plan_for_day


class GrowthPlanTests(unittest.TestCase):
    def setUp(self):
        # Queue statuses change after real handoffs; behavior tests must not
        # expect the production queue to remain in its initial state forever.
        self.plan = {
            "started_on": "2026-10-12", "review_on": "2026-11-23",
            "evidence_observed_on": "2026-10-12",
            "weekday_modes": {
                "monday": "new_article", "tuesday": "refresh_existing",
                "wednesday": "new_article", "thursday": "refresh_existing",
                "friday": "new_article", "saturday": "off", "sunday": "off",
            },
            "refresh_queue": [
                {"priority": 1, "status": "planned",
                 "page_url": "https://won0322.tistory.com/197",
                 "draft_id": "2026-08-08-automation",
                 "source": "data/automation_cases/2026-08-08.json"},
                {"priority": 2, "status": "planned",
                 "page_url": "https://won0322.tistory.com/221",
                 "draft_id": "2026-09-03", "source": "data/days/2026-09-03.json"},
                {"priority": 3, "status": "planned",
                 "page_url": "https://won0322.tistory.com/209",
                 "draft_id": "2026-08-20", "source": "data/days/2026-08-20.json"},
            ],
        }

    def test_committed_plan_is_valid_and_points_to_preserved_sources(self):
        plan = json.loads(DEFAULT_PLAN.read_text(encoding="utf-8"))
        start = dt.date.fromisoformat(plan["started_on"])
        tuesday = start + dt.timedelta(days=(1 - start.weekday()) % 7)
        self.assertEqual(plan_for_day(plan, tuesday)["mode"], "refresh_existing")
        for item in plan["refresh_queue"]:
            self.assertTrue((ROOT / item["source"]).is_file(), item["source"])

    def test_week_is_three_new_two_refresh_and_no_weekend(self):
        modes = [
            plan_for_day(self.plan, dt.date(2026, 10, 12) + dt.timedelta(days=i))["mode"]
            for i in range(7)
        ]
        self.assertEqual(modes, [
            "new_article", "refresh_existing", "new_article", "refresh_existing",
            "new_article", "off", "off",
        ])

    def test_first_refresh_is_existing_im_not_ai_not_a_new_daily_draft(self):
        original = copy.deepcopy(self.plan)
        result = plan_for_day(self.plan, dt.date(2026, 10, 13))
        self.assertEqual(result["target"]["page_url"], "https://won0322.tistory.com/197")
        self.assertEqual(result["target"]["draft_id"], "2026-08-08-automation")
        self.assertEqual(self.plan, original)

    def test_completed_handoff_is_not_rewritten_while_waiting_for_user(self):
        self.plan["refresh_queue"][0]["status"] = "ready_for_review"
        result = plan_for_day(self.plan, dt.date(2026, 10, 15))
        self.assertEqual(result["target"]["page_url"], "https://won0322.tistory.com/221")

    def test_partial_work_is_resumed_before_another_target(self):
        self.plan["refresh_queue"][2]["status"] = "in_progress"
        result = plan_for_day(self.plan, dt.date(2026, 10, 13))
        self.assertEqual(result["target"]["page_url"], "https://won0322.tistory.com/209")

    def test_exhausted_queue_does_not_generate_filler(self):
        for item in self.plan["refresh_queue"]:
            item["status"] = "ready_for_review"
        result = plan_for_day(self.plan, dt.date(2026, 10, 15))
        self.assertEqual(result["mode"], "refresh_existing")
        self.assertIsNone(result["target"])
        self.assertIn("existing page", result["next_action"])

    def test_review_date_does_not_silently_restore_five_new_posts(self):
        result = plan_for_day(self.plan, dt.date(2026, 11, 24))
        self.assertTrue(result["review_due"])
        self.assertFalse(result["evidence_fresh"])
        self.assertEqual(result["mode"], "refresh_existing")

    def test_pre_trial_day_has_no_scheduled_work(self):
        self.assertEqual(plan_for_day(self.plan, dt.date(2026, 10, 9))["mode"], "off")

    def test_wrong_schedule_or_unsafe_refresh_target_is_rejected(self):
        self.plan["weekday_modes"]["saturday"] = "new_article"
        with self.assertRaises(ValueError):
            plan_for_day(self.plan, dt.date(2026, 10, 13))
        self.setUp()
        for field, value in [
            ("page_url", "https://example.com/197"),
            ("source", "../../outside.json"),
        ]:
            with self.subTest(field=field):
                bad = copy.deepcopy(self.plan)
                bad["refresh_queue"][0][field] = value
                with self.assertRaises(ValueError):
                    plan_for_day(bad, dt.date(2026, 10, 13))


if __name__ == "__main__":
    unittest.main()
