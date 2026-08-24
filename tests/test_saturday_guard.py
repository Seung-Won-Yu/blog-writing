import tempfile
import unittest
from pathlib import Path

from blog_pipeline.publishing.saturday_guard import inspect_saturday_state


class SaturdayGuardTests(unittest.TestCase):
    def test_off_schedule_day_is_a_safe_skip(self):
        result = inspect_saturday_state("2026-07-17")

        self.assertEqual(result["status"], "SKIP")
        self.assertEqual(result["reason"], "not_regular_automation_day")

    def test_saturday_uses_the_automation_draft_namespace(self):
        with tempfile.TemporaryDirectory() as directory:
            result = inspect_saturday_state(
                "2026-07-18", root=Path(directory)
            )

        self.assertEqual(result["status"], "NEW")
        self.assertEqual(result["draft_id"], "2026-07-18-automation")
        self.assertEqual(result["content_type"], "automation_case")

    def test_friday_is_regular_after_schedule_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            friday = inspect_saturday_state(
                "2026-08-28", root=Path(directory)
            )
            saturday = inspect_saturday_state(
                "2026-08-29", root=Path(directory)
            )

        self.assertEqual(friday["status"], "NEW")
        self.assertEqual(friday["draft_id"], "2026-08-28-automation")
        self.assertEqual(saturday["status"], "SKIP")


if __name__ == "__main__":
    unittest.main()
