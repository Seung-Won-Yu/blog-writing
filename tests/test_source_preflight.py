import json
import tempfile
import unittest
from pathlib import Path

from blog_pipeline.publishing.daily_guard import inspect_source_state
from blog_pipeline.publishing.draft_identity import resolve_draft_identity
from blog_pipeline.publishing.editorial_quality import source_authoring_reasons
from tests.test_editorial_quality import valid_daily_source


class SourcePreflightTests(unittest.TestCase):
    def test_authoring_gate_does_not_require_generated_image_outputs(self):
        source = valid_daily_source("2026-07-21")
        source.pop("images")
        identity = resolve_draft_identity(source["draft_id"], source)

        self.assertEqual(source_authoring_reasons(source, identity), [])

    def test_preflight_reports_actionable_identity_editorial_and_brief_failures(self):
        day = "2026-07-21"
        source = valid_daily_source(day)
        source["category"] = "개발 도구"
        source["publication_mode"] = "reviewed_draft"
        source["date_label"] = "2026년 7월 21일"
        source["weekday"] = "화요일"
        source["editorial"]["opening"] = "너무 짧은 도입"
        source["visual"]["assets"][0]["scene_label"] = "변경 전, 변경 후"

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "data" / "days" / f"{day}.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps(source, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            result = inspect_source_state(day, root=root)

        self.assertEqual(result["status"], "PARTIAL")
        self.assertIn("quality_identity", result["reasons"])
        self.assertIn("quality_schema", result["reasons"])
        self.assertIn("quality_editorial", result["reasons"])
        self.assertEqual(result["expected_identity"]["category"], "데일리IT뉴스")
        self.assertEqual(result["expected_identity"]["publication_mode"], "scheduled")
        self.assertEqual(result["editorial_lengths"]["opening"]["minimum"], 180)
        self.assertLess(result["editorial_lengths"]["opening"]["actual"], 180)
        self.assertEqual(result["invalid_scene_labels"], ["visual_1"])

    def test_preflight_is_ready_before_image_files_and_exports_exist(self):
        day = "2026-07-21"
        source = valid_daily_source(day)
        source.pop("images")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "data" / "days" / f"{day}.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps(source, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            result = inspect_source_state(day, root=root)

        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["reasons"], [])
        self.assertFalse((root / "docs" / "tistory" / f"{day}.html").exists())


if __name__ == "__main__":
    unittest.main()
