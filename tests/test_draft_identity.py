import unittest

from blog_pipeline.publishing.draft_identity import (
    automation_draft_id,
    guide_draft_id,
    resolve_draft_identity,
)


class DraftIdentityTests(unittest.TestCase):
    def test_resolves_daily_and_saturday_namespaces_independently(self):
        daily = resolve_draft_identity("2026-07-18")
        automation = resolve_draft_identity("2026-07-18-automation")
        guide = resolve_draft_identity("2026-07-18-guide")

        self.assertEqual(daily.source, "data/days/2026-07-18.json")
        self.assertEqual(daily.content_type, "daily_news")
        self.assertEqual(
            automation.source, "data/automation_cases/2026-07-18.json"
        )
        self.assertEqual(automation.content_type, "automation_case")
        self.assertEqual(guide.source, "data/guides/2026-07-18.json")
        self.assertEqual(guide.content_type, "evergreen_guide")
        self.assertEqual(guide.content_label, "개발 가이드")
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


if __name__ == "__main__":
    unittest.main()
