import unittest

from blog_pipeline.publishing.draft_identity import (
    automation_draft_id,
    category_for_content_type,
    editorial_lane_for_identity,
    guide_draft_id,
    publication_mode_for_identity,
    regular_schedule_for_identity,
    resolve_draft_identity,
)


class DraftIdentityTests(unittest.TestCase):
    def test_resolves_daily_and_saturday_namespaces_independently(self):
        daily = resolve_draft_identity("2026-07-18")
        automation = resolve_draft_identity("2026-07-18-automation")
        guide = resolve_draft_identity("2026-07-18-guide")
        project = resolve_draft_identity("2026-08-29-project")

        self.assertEqual(daily.source, "data/days/2026-07-18.json")
        self.assertEqual(daily.content_type, "daily_news")
        self.assertEqual(
            automation.source, "data/automation_cases/2026-07-18.json"
        )
        self.assertEqual(automation.content_type, "automation_case")
        self.assertEqual(guide.source, "data/guides/2026-07-18.json")
        self.assertEqual(guide.content_type, "evergreen_guide")
        self.assertEqual(guide.content_label, "개발 가이드")
        self.assertEqual(project.source, "data/project_logs/2026-08-29.json")
        self.assertEqual(project.content_type, "project_log")
        self.assertEqual(project.content_label, "프로젝트 제작기")
        self.assertEqual(automation.publish_date, daily.publish_date)
        self.assertEqual(guide.publish_date, daily.publish_date)
        self.assertNotEqual(automation.draft_id, daily.draft_id)
        self.assertNotEqual(guide.draft_id, daily.draft_id)

    def test_automation_payload_requires_an_explicit_matching_identity(self):
        payload = {
            "draft_id": "2026-07-18-automation",
            "publish_date": "2026-07-18",
            "content_type": "automation_case",
            "content_label": "업무자동화 실험",
        }

        resolved = resolve_draft_identity("2026-07-18-automation", payload)

        self.assertEqual(resolved.draft_id, payload["draft_id"])
        with self.assertRaisesRegex(ValueError, "identity is incomplete"):
            resolve_draft_identity("2026-07-18-automation", {})
        with self.assertRaisesRegex(ValueError, "content_type"):
            resolve_draft_identity(
                "2026-07-18-automation",
                {**payload, "content_type": "daily_news"},
            )

    def test_rejects_unscoped_or_invalid_draft_ids(self):
        for value in (
            "2026-7-18",
            "2026-07-18-other",
            "../2026-07-18",
            "2026-02-30",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve_draft_identity(value)

    def test_builds_the_canonical_automation_id(self):
        self.assertEqual(
            automation_draft_id("2026-07-18"), "2026-07-18-automation"
        )

    def test_builds_the_canonical_guide_id(self):
        self.assertEqual(guide_draft_id("2026-07-18"), "2026-07-18-guide")

    def test_recurring_schedules_match_each_content_lane(self):
        self.assertEqual(
            regular_schedule_for_identity(resolve_draft_identity("2026-07-22")),
            "2026-07-22T09:00:00+09:00",
        )
        self.assertEqual(
            regular_schedule_for_identity(
                resolve_draft_identity("2026-07-25-automation")
            ),
            "2026-07-25T18:00:00+09:00",
        )
        self.assertEqual(
            regular_schedule_for_identity(
                resolve_draft_identity("2026-08-28-automation")
            ),
            "2026-08-28T09:00:00+09:00",
        )
        self.assertEqual(
            publication_mode_for_identity(
                resolve_draft_identity("2026-08-28-automation")
            ),
            "manual_review",
        )
        self.assertIsNone(
            regular_schedule_for_identity(
                resolve_draft_identity("2026-08-29-automation")
            )
        )
        self.assertEqual(
            regular_schedule_for_identity(resolve_draft_identity("2026-07-22-guide")),
            "2026-07-22T18:00:00+09:00",
        )
        self.assertIsNone(
            regular_schedule_for_identity(resolve_draft_identity("2026-07-23-guide"))
        )
        self.assertEqual(
            regular_schedule_for_identity(
                resolve_draft_identity("2026-08-29-project")
            ),
            "2026-08-29T09:00:00+09:00",
        )
        self.assertEqual(
            publication_mode_for_identity(
                resolve_draft_identity("2026-08-29-project")
            ),
            "manual_review",
        )
        self.assertIsNone(
            regular_schedule_for_identity(
                resolve_draft_identity("2026-08-28-project")
            )
        )

    def test_category_taxonomy_preserves_each_historical_epoch(self):
        self.assertEqual(
            category_for_content_type("daily_news", "2026-07-21"),
            "데일리IT뉴스",
        )
        self.assertEqual(
            category_for_content_type("daily_news", "2026-07-22"),
            "최신 IT·개발 소식",
        )
        self.assertEqual(
            category_for_content_type("automation_case", "2026-07-26"),
            "자동화·실험",
        )
        self.assertEqual(
            category_for_content_type("evergreen_guide", "2026-07-22"),
            "개발 가이드",
        )

    def test_daily_lane_becomes_an_evergreen_article_without_rewriting_history(self):
        previous = resolve_draft_identity("2026-08-24")
        current = resolve_draft_identity("2026-08-25")

        self.assertEqual(previous.content_label, "뉴스 심층글")
        self.assertEqual(current.content_label, "IT 트렌드 해설")
        self.assertEqual(
            category_for_content_type("daily_news", "2026-08-24"),
            "최신 IT·개발 소식",
        )
        self.assertEqual(
            category_for_content_type("daily_news", "2026-08-25"),
            "IT 트렌드 해설",
        )

    def test_current_category_is_used_when_publish_date_is_missing_or_invalid(self):
        self.assertEqual(
            category_for_content_type("daily_news"),
            "IT 트렌드 해설",
        )
        self.assertEqual(
            category_for_content_type("daily_news", "not-a-date"),
            "IT 트렌드 해설",
        )

    def test_new_weekly_lanes_separate_monday_and_wednesday(self):
        monday = resolve_draft_identity("2026-08-31")
        wednesday = resolve_draft_identity("2026-09-02")
        friday = resolve_draft_identity("2026-09-04")

        self.assertEqual(monday.content_label, "개발 가이드")
        self.assertEqual(category_for_content_type("daily_news", monday.publish_date), "개발 가이드")
        self.assertEqual(editorial_lane_for_identity(monday), "evergreen_problem")
        self.assertEqual(
            regular_schedule_for_identity(monday),
            "2026-08-31T09:00:00+09:00",
        )

        self.assertEqual(wednesday.content_label, "IT 트렌드 해설")
        self.assertEqual(category_for_content_type("daily_news", wednesday.publish_date), "IT 트렌드 해설")
        self.assertEqual(editorial_lane_for_identity(wednesday), "change_explainer")
        self.assertEqual(
            regular_schedule_for_identity(wednesday),
            "2026-09-02T09:00:00+09:00",
        )

        self.assertEqual(editorial_lane_for_identity(friday), "")
        self.assertIsNone(regular_schedule_for_identity(friday))

    def test_curiosity_lanes_fill_tuesday_and_thursday_without_rewriting_history(self):
        previous_tuesday = resolve_draft_identity("2026-08-25")
        tuesday = resolve_draft_identity("2026-09-01")
        thursday = resolve_draft_identity("2026-09-03")

        self.assertEqual(previous_tuesday.content_label, "IT 트렌드 해설")
        self.assertEqual(
            category_for_content_type("daily_news", previous_tuesday.publish_date),
            "IT 트렌드 해설",
        )

        for identity, lane in (
            (tuesday, "curiosity_mechanism"),
            (thursday, "curiosity_myth_history"),
        ):
            with self.subTest(day=identity.publish_date):
                self.assertEqual(identity.content_label, "궁금한 IT 원리")
                self.assertEqual(
                    category_for_content_type("daily_news", identity.publish_date),
                    "궁금한 IT 원리",
                )
                self.assertEqual(editorial_lane_for_identity(identity), lane)
                self.assertEqual(
                    regular_schedule_for_identity(identity),
                    f"{identity.publish_date}T09:00:00+09:00",
                )

    def test_friday_automation_has_an_executed_experiment_lane(self):
        identity = resolve_draft_identity("2026-08-28-automation")

        self.assertEqual(editorial_lane_for_identity(identity), "executed_experiment")


if __name__ == "__main__":
    unittest.main()
