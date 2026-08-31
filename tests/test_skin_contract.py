import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from blog_pipeline.publishing.skin_contract import (
    inspect_project_html_contract,
    inspect_skin_contract,
)


ROOT = Path(__file__).resolve().parents[1]


class SkinContractTests(unittest.TestCase):
    def test_current_skin_and_preview_share_the_project_contract(self):
        result = inspect_skin_contract(ROOT)

        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["reasons"], [])
        self.assertEqual(len(result["sha256"]), 64)

    def test_stale_preview_skin_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            design = root / "design" / "tistory"
            preview = root / "docs" / "preview"
            design.mkdir(parents=True)
            preview.mkdir(parents=True)
            style = (ROOT / "design" / "tistory" / "style.css").read_text(
                encoding="utf-8"
            )
            layer = (ROOT / "design" / "tistory" / "skin-layer.css").read_text(
                encoding="utf-8"
            )
            (design / "style.css").write_text(style, encoding="utf-8")
            (design / "skin-layer.css").write_text(layer, encoding="utf-8")
            (preview / "tistory-style.css").write_text(
                style + "\n/* stale preview copy */\n",
                encoding="utf-8",
            )

            result = inspect_skin_contract(root)

        self.assertEqual(result["status"], "PARTIAL")
        self.assertIn("stale_preview_skin_css", result["reasons"])

    def test_current_project_html_keeps_reader_aids_and_image_roles(self):
        body = (ROOT / "docs" / "tistory" / "2026-08-29-project.html").read_text(
            encoding="utf-8"
        )
        meta = json.loads(
            (ROOT / "docs" / "tistory" / "2026-08-29-project.json").read_text(
                encoding="utf-8"
            )
        )

        result = inspect_project_html_contract(body, meta["image_assets"])

        self.assertEqual(result, {"status": "COMPLETE", "reasons": []})

    def test_project_html_rejects_missing_reader_aid_and_wrong_loading_role(self):
        body = (ROOT / "docs" / "tistory" / "2026-08-29-project.html").read_text(
            encoding="utf-8"
        )
        meta = json.loads(
            (ROOT / "docs" / "tistory" / "2026-08-29-project.json").read_text(
                encoding="utf-8"
            )
        )
        body = body.replace('class="digest-project-glossary"', 'class="removed"')
        body = body.replace('loading="eager"', 'loading="lazy"', 1)

        result = inspect_project_html_contract(body, meta["image_assets"])

        self.assertIn("project_reader_aid_markup", result["reasons"])
        self.assertIn("project_image_loading_contract", result["reasons"])

    def test_project_html_rejects_an_image_from_the_wrong_draft(self):
        body = (ROOT / "docs" / "tistory" / "2026-08-29-project.html").read_text(
            encoding="utf-8"
        )
        meta = json.loads(
            (ROOT / "docs" / "tistory" / "2026-08-29-project.json").read_text(
                encoding="utf-8"
            )
        )
        body = body.replace(
            meta["image_assets"][0]["url"],
            "https://example.com/wrong-cover.webp",
            1,
        )

        result = inspect_project_html_contract(body, meta["image_assets"])

        self.assertIn("project_image_url_mismatch", result["reasons"])

    def test_project_daily_guard_runs_the_markup_contract(self):
        from blog_pipeline.publishing.daily_guard import inspect_draft_state

        with patch(
            "blog_pipeline.publishing.daily_guard.inspect_project_html_contract",
            return_value={"status": "PARTIAL", "reasons": ["project_contract_probe"]},
        ):
            result = inspect_draft_state(
                "2026-08-29-project",
                root=ROOT,
                window_days=365,
            )

        self.assertEqual(result["status"], "PARTIAL")
        self.assertIn("project_contract_probe", result["reasons"])

    def test_project_daily_guard_runs_the_shared_skin_contract(self):
        from blog_pipeline.publishing.daily_guard import inspect_draft_state

        with patch(
            "blog_pipeline.publishing.daily_guard.inspect_skin_contract",
            return_value={"status": "PARTIAL", "reasons": ["skin_contract_probe"]},
        ):
            result = inspect_draft_state(
                "2026-08-29-project",
                root=ROOT,
                window_days=365,
            )

        self.assertEqual(result["status"], "PARTIAL")
        self.assertIn("skin_contract_probe", result["reasons"])


if __name__ == "__main__":
    unittest.main()
