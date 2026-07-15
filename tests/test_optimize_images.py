import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from blog_pipeline.publishing.optimize_images import (
    IMAGE_FILE_BUDGET,
    IMAGE_SET_BUDGET,
    inspect_day_images,
    optimize_day_images,
)


class OptimizeImagesTests(unittest.TestCase):
    def _write_day(self, root):
        day_id = "2026-07-16"
        asset_dir = root / "docs" / "tistory" / "assets" / day_id
        asset_dir.mkdir(parents=True)
        images = {}
        for index, kind in enumerate(("cover", "story_1", "story_2", "story_3")):
            filename = "cover.png" if kind == "cover" else f"story-{index:02d}.png"
            path = asset_dir / filename
            image = Image.effect_noise((600, 315), 50).convert("RGB")
            image.save(path, "PNG")
            images[kind] = {
                "path": f"docs/tistory/assets/{day_id}/{filename}",
                "url": f"https://blog.example/assets/{day_id}/{filename}",
                "alt": f"{kind} image",
                "width": 1200,
                "height": 630,
            }
        day_path = root / "data" / "days" / f"{day_id}.json"
        day_path.parent.mkdir(parents=True)
        day_path.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "generation": {"provider": "codex-agent"},
                    "images": images,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return day_id, day_path, asset_dir

    def test_converts_daily_images_to_bounded_webp_and_updates_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day_id, day_path, asset_dir = self._write_day(root)

            result = optimize_day_images(day_id, root=root)

            stored = json.loads(day_path.read_text(encoding="utf-8"))
            self.assertEqual(stored["generation"]["image_policy"], "webp-v1")
            self.assertLessEqual(result["total_bytes"], IMAGE_SET_BUDGET)
            self.assertFalse((asset_dir / "cover.png").exists())
            for asset in stored["images"].values():
                self.assertTrue(asset["path"].endswith(".webp"))
                self.assertTrue(asset["url"].endswith(".webp"))
                self.assertEqual(asset["format"], "webp")
                self.assertLessEqual(asset["bytes"], IMAGE_FILE_BUDGET)
                path = root / asset["path"]
                with Image.open(path) as image:
                    self.assertEqual(image.format, "WEBP")
                    self.assertEqual(image.size, (1200, 630))

            self.assertEqual(inspect_day_images(day_id, root=root)["reasons"], [])

    def test_can_preserve_source_files_for_already_published_posts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day_id, _, asset_dir = self._write_day(root)

            optimize_day_images(day_id, root=root, preserve_sources=True)

            self.assertTrue((asset_dir / "cover.png").exists())
            self.assertTrue((asset_dir / "cover.webp").exists())

    def test_second_optimization_keeps_existing_compliant_webp_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day_id, day_path, _ = self._write_day(root)
            optimize_day_images(day_id, root=root)
            stored = json.loads(day_path.read_text(encoding="utf-8"))
            before = {
                kind: (root / asset["path"]).read_bytes()
                for kind, asset in stored["images"].items()
            }

            optimize_day_images(day_id, root=root)

            after = json.loads(day_path.read_text(encoding="utf-8"))
            for kind, asset in after["images"].items():
                self.assertEqual((root / asset["path"]).read_bytes(), before[kind])


if __name__ == "__main__":
    unittest.main()
