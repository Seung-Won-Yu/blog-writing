import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from blog_pipeline.publishing.optimize_images import (
    IMAGE_FILE_BUDGET,
    IMAGE_SET_BUDGET,
    LEAD_IMAGE_SET_BUDGET,
    _check_all,
    inspect_day_images,
    inspect_draft_images,
    optimize_draft_images,
    optimize_day_images,
    save_bounded_webp,
)


class OptimizeImagesTests(unittest.TestCase):
    def test_check_all_reports_malformed_generation_instead_of_crashing(self):
        from tests.test_editorial_quality import valid_daily_source

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = valid_daily_source("2026-07-19")
            source["generation"] = True
            path = root / "data" / "days" / "2026-07-19.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")

            result = _check_all(root)

        self.assertEqual(result["checked"], 1)
        self.assertEqual(result["failures"][0]["draft_id"], "2026-07-19")
        self.assertIn("invalid_image_manifest", result["failures"][0]["reasons"])

    def test_check_all_includes_evergreen_guide_sources(self):
        from tests.test_editorial_quality import valid_guide_source

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = valid_guide_source("2026-07-21")
            source["generation"] = True
            path = root / "data" / "guides" / "2026-07-21.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")

            result = _check_all(root)

        self.assertEqual(result["checked"], 1)
        self.assertEqual(result["failures"][0]["draft_id"], "2026-07-21-guide")
        self.assertIn("invalid_image_manifest", result["failures"][0]["reasons"])

    def test_inspection_rejects_duplicate_committed_image_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day_id = "2026-07-19"
            asset_dir = root / "docs" / "tistory" / "assets" / day_id
            asset_dir.mkdir(parents=True)
            shared = Image.effect_noise((1200, 630), 50).convert("RGB")
            assets = {}
            for kind, filename in (
                ("cover", "대표-이미지.webp"),
                ("visual_1", "본문-이미지.webp"),
                ("visual_2", "비교-이미지.webp"),
            ):
                path = asset_dir / filename
                image = shared if kind != "visual_2" else Image.effect_noise((1200, 630), 70).convert("RGB")
                image.save(path, "WEBP", quality=70)
                assets[kind] = {
                    "path": path.relative_to(root).as_posix(),
                    "url": f"https://blog.example/{filename}",
                    "alt": "기사 내용의 단계와 결과를 비교하는 한국어 설명 이미지",
                    "width": 1200,
                    "height": 630,
                    "format": "webp",
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            source = root / "data" / "days" / f"{day_id}.json"
            source.parent.mkdir(parents=True)
            source.write_text(
                json.dumps(
                    {
                        "schema_version": 3,
                        "format": "lead-story-v1",
                        "generation": {"image_policy": "webp-v1"},
                        "images": assets,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = inspect_draft_images(day_id, root=root)

        self.assertIn("duplicate_image_asset", result["reasons"])

    def test_source_and_webp_target_paths_must_be_unique_per_image_kind(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day_id, day_path, asset_dir = self._write_day(root)
            collision = asset_dir / "Cover.jpg"
            Image.effect_noise((600, 315), 45).convert("RGB").save(
                collision, "JPEG"
            )
            day = json.loads(day_path.read_text(encoding="utf-8"))
            day["images"]["story_1"].update(
                {
                    "path": collision.relative_to(root).as_posix(),
                    "url": "https://blog.example/assets/Cover.jpg",
                }
            )
            day_path.write_text(json.dumps(day), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unique"):
                optimize_day_images(day_id, root=root)

            self.assertTrue((asset_dir / "cover.png").is_file())
            self.assertTrue(collision.is_file())
            self.assertFalse((asset_dir / "cover.webp").exists())

    def test_failed_batch_does_not_commit_an_earlier_optimized_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day_id, day_path, asset_dir = self._write_day(root)
            original_json = day_path.read_bytes()
            (asset_dir / "story-01.png").unlink()

            with self.assertRaises(FileNotFoundError):
                optimize_day_images(day_id, root=root)

            self.assertEqual(day_path.read_bytes(), original_json)
            self.assertFalse((asset_dir / "cover.webp").exists())
            self.assertTrue((asset_dir / "cover.png").is_file())

    def test_future_image_inspection_opens_files_and_checks_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day_id = "2026-07-19"
            asset_dir = root / "docs" / "tistory" / "assets" / day_id
            asset_dir.mkdir(parents=True)
            paths = {
                "cover": asset_dir / "대표-이미지.webp",
                "visual_1": asset_dir / "설명-이미지.webp",
                "visual_2": asset_dir / "손상-이미지.webp",
            }
            Image.new("RGB", (1, 1), "#ffffff").save(paths["cover"], "WEBP")
            Image.new("RGB", (1200, 630), "#f2f2f2").save(
                paths["visual_1"], "WEBP"
            )
            paths["visual_2"].write_bytes(b"not-a-webp")
            source = root / "data" / "days" / f"{day_id}.json"
            source.parent.mkdir(parents=True)
            source.write_text(
                json.dumps(
                    {
                        "schema_version": 3,
                        "format": "lead-story-v1",
                        "generation": {"image_policy": "webp-v1"},
                        "images": {
                            "cover": {
                                "path": paths["cover"].relative_to(root).as_posix(),
                                "url": "https://blog.example/대표-이미지.webp",
                                "alt": "대표 이미지 설명이 충분히 들어간 대체 문구",
                                "width": 1200,
                                "height": 630,
                                "format": "webp",
                                "sha256": "0" * 64,
                            },
                            "visual_1": {
                                "path": paths["visual_1"].relative_to(root).as_posix(),
                                "url": "https://blog.example/다른-파일명.webp",
                                "alt": "",
                                "width": "wide",
                                "height": 630,
                                "format": "webp",
                                "sha256": "0" * 64,
                            },
                            "visual_2": {
                                "path": paths["visual_2"].relative_to(root).as_posix(),
                                "url": "https://blog.example/손상-이미지.webp",
                                "alt": "손상 여부를 확인할 본문 설명 이미지 대체 문구",
                                "width": 1200,
                                "height": 630,
                                "format": "webp",
                                "sha256": "0" * 64,
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = inspect_draft_images(day_id, root=root)

        self.assertIn("invalid_image_dimensions:cover", result["reasons"])
        self.assertIn("image_digest_mismatch:cover", result["reasons"])
        self.assertIn("missing_image_alt:visual_1", result["reasons"])
        self.assertIn("low_information_image:visual_1", result["reasons"])
        self.assertIn("image_metadata_mismatch:visual_1", result["reasons"])
        self.assertIn("image_url_mismatch:visual_1", result["reasons"])
        self.assertIn("image_digest_mismatch:visual_1", result["reasons"])
        self.assertIn("invalid_image_file:visual_2", result["reasons"])

    def test_rejects_an_automation_asset_that_points_into_the_daily_namespace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day_id = "2026-07-18"
            draft_id = f"{day_id}-automation"
            daily_asset = (
                root
                / "docs"
                / "tistory"
                / "assets"
                / day_id
                / "cover.png"
            )
            daily_asset.parent.mkdir(parents=True)
            Image.new("RGB", (600, 315), "#ffffff").save(daily_asset, "PNG")
            source = root / "data" / "automation_cases" / f"{day_id}.json"
            source.parent.mkdir(parents=True)
            source.write_text(
                json.dumps(
                    {
                        "draft_id": draft_id,
                        "publish_date": day_id,
                        "content_type": "automation_case",
                        "content_label": "업무자동화 실험",
                        "format": "lead-story-v1",
                        "generation": {"provider": "codex-agent"},
                        "images": {
                            "cover": {
                                "path": f"docs/tistory/assets/{day_id}/cover.png",
                                "url": "https://blog.example/cover.png",
                            },
                            "visual_1": {},
                            "visual_2": {},
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "draft asset namespace"):
                optimize_draft_images(draft_id, root=root)
            inspection = inspect_draft_images(draft_id, root=root)

            self.assertTrue(daily_asset.is_file())

        self.assertIn("foreign_image_path:cover", inspection["reasons"])

    def test_optimizes_automation_assets_in_their_own_namespace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            draft_id = "2026-07-18-automation"
            day_id = "2026-07-18"
            asset_dir = root / "docs" / "tistory" / "assets" / draft_id
            asset_dir.mkdir(parents=True)
            images = {}
            for kind in ("cover", "visual_1", "visual_2"):
                filename = f"{kind}.png"
                Image.effect_noise((600, 315), 40).convert("RGB").save(
                    asset_dir / filename, "PNG"
                )
                images[kind] = {
                    "path": f"docs/tistory/assets/{draft_id}/{filename}",
                    "url": f"https://blog.example/assets/{draft_id}/{filename}",
                    "alt": kind,
                }
            source_path = root / "data" / "automation_cases" / f"{day_id}.json"
            source_path.parent.mkdir(parents=True)
            source_path.write_text(
                json.dumps(
                    {
                        "draft_id": draft_id,
                        "publish_date": day_id,
                        "content_type": "automation_case",
                        "content_label": "업무자동화 실험",
                        "format": "lead-story-v1",
                        "generation": {"provider": "codex-agent"},
                        "images": images,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = optimize_draft_images(draft_id, root=root)
            stored = json.loads(source_path.read_text(encoding="utf-8"))
            inspection = inspect_draft_images(draft_id, root=root)

        self.assertEqual(result["draft_id"], draft_id)
        self.assertEqual(result["publish_date"], day_id)
        self.assertEqual(stored["generation"]["image_policy"], "webp-v1")
        self.assertTrue(
            all(
                asset["path"].startswith(
                    f"docs/tistory/assets/{draft_id}/"
                )
                and asset["path"].endswith(".webp")
                for asset in stored["images"].values()
            )
        )
        self.assertEqual(inspection["reasons"], [])

    def test_deep_diagram_can_preserve_the_full_frame_instead_of_cropping(self):
        image = Image.new("RGB", (600, 600), "#00aa00")
        for y in range(150):
            for x in range(600):
                image.putpixel((x, y), (220, 30, 30))
                image.putpixel((x, 599 - y), (30, 30, 220))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "diagram.webp"
            save_bounded_webp(image, path, preserve_full_frame=True)
            with Image.open(path) as optimized:
                top = optimized.getpixel((600, 10))
                bottom = optimized.getpixel((600, 620))

        self.assertGreater(top[0], top[2])
        self.assertGreater(bottom[2], bottom[0])

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

    def test_deep_story_optimizes_every_declared_visual_with_a_larger_set_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day_id = "2026-07-17"
            asset_dir = root / "docs" / "tistory" / "assets" / day_id
            asset_dir.mkdir(parents=True)
            images = {}
            for index, kind in enumerate(("cover", "visual_1", "visual_2", "visual_3")):
                filename = f"{kind.replace('_', '-')}.png"
                Image.effect_noise((600, 315), 50 + index).convert("RGB").save(
                    asset_dir / filename, "PNG"
                )
                images[kind] = {
                    "path": f"docs/tistory/assets/{day_id}/{filename}",
                    "url": f"https://blog.example/{filename}",
                    "alt": kind,
                }
            day_path = root / "data" / "days" / f"{day_id}.json"
            day_path.parent.mkdir(parents=True)
            day_path.write_text(
                json.dumps(
                    {
                        "schema_version": 3,
                        "format": "lead-story-v1",
                        "generation": {"provider": "codex-agent"},
                        "images": images,
                    }
                ),
                encoding="utf-8",
            )

            result = optimize_day_images(day_id, root=root)
            stored = json.loads(day_path.read_text(encoding="utf-8"))

            self.assertLessEqual(result["total_bytes"], LEAD_IMAGE_SET_BUDGET)
            self.assertEqual(
                list(stored["images"]),
                ["cover", "visual_1", "visual_2", "visual_3"],
            )
            self.assertTrue(all(asset["path"].endswith(".webp") for asset in stored["images"].values()))
            self.assertEqual(inspect_day_images(day_id, root=root)["reasons"], [])


if __name__ == "__main__":
    unittest.main()
