import unittest

from blog_pipeline.publishing.draft_identity import (
    automation_draft_id,
    category_for_content_type,
    guide_draft_id,
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
            "2026-08-28T18:00:00+09:00",
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
            "2026-08-29T18:00:00+09:00",
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
        self.assertEqual(current.content_label, "실전 IT 아티클")
        self.assertEqual(
            category_for_content_type("daily_news", "2026-08-24"),
            "최신 IT·개발 소식",
        )
        self.assertEqual(
            category_for_content_type("daily_news", "2026-08-25"),
            "실전 IT 아티클",
        )

    def test_current_category_is_used_when_publish_date_is_missing_or_invalid(self):
        self.assertEqual(
            category_for_content_type("daily_news"),
            "실전 IT 아티클",
        )
        self.assertEqual(
            category_for_content_type("daily_news", "not-a-date"),
            "실전 IT 아티클",
        )


if __name__ == "__main__":
    unittest.main()
