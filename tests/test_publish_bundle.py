import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class PublishBundleTests(unittest.TestCase):
    def test_stage_includes_every_required_daily_publish_artifact(self):
        from blog_pipeline.publishing.publish_bundle import (
            publish_bundle_tracking_reasons,
            stage_publish_bundle,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(
                ["git", "init", "-q"], cwd=root, check=True
            )
            draft_id = "2026-07-20"
            paths = {
                "source": root / "data" / "days" / f"{draft_id}.json",
                "meta": root / "docs" / "tistory" / f"{draft_id}.json",
                "html": root / "docs" / "tistory" / f"{draft_id}.html",
                "before": root / "docs" / "tistory" / f"{draft_id}-before-ad.html",
                "after": root / "docs" / "tistory" / f"{draft_id}-after-ad.html",
                "adfit": root / "docs" / "tistory" / f"{draft_id}-adfit.html",
                "preview": root / "docs" / "preview" / f"{draft_id}.html",
                "image": root / "docs" / "tistory" / "assets" / draft_id / "대표.webp",
                "copy_page": root / "docs" / "index.html",
                "integration_page": root / "docs" / "integration.html",
            }
            for path in paths.values():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(path.name, encoding="utf-8")
            paths["source"].write_text(
                json.dumps(
                    {
                        "draft_id": draft_id,
                        "publish_date": draft_id,
                        "content_type": "daily_news",
                    }
                ),
                encoding="utf-8",
            )
            paths["meta"].write_text(
                json.dumps(
                    {
                        "source": f"data/days/{draft_id}.json",
                        "html": f"docs/tistory/{draft_id}.html",
                        "before_ad_html": f"docs/tistory/{draft_id}-before-ad.html",
                        "after_ad_html": f"docs/tistory/{draft_id}-after-ad.html",
                        "adfit_html": f"docs/tistory/{draft_id}-adfit.html",
                        "image_assets": [
                            {
                                "path": (
                                    "docs/tistory/assets/"
                                    f"{draft_id}/대표.webp"
                                )
                            },
                            {},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "add", "--", str(paths["source"].relative_to(root))],
                cwd=root,
                check=True,
            )

            before = publish_bundle_tracking_reasons(draft_id, root=root)
            staged = stage_publish_bundle(draft_id, root=root)
            after = publish_bundle_tracking_reasons(draft_id, root=root)
            paths["adfit"].write_text("changed after staging", encoding="utf-8")
            unstaged = publish_bundle_tracking_reasons(draft_id, root=root)
            cached = subprocess.run(
                ["git", "diff", "--cached", "--name-only", "-z"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.split("\0")

        self.assertIn(
            "untracked_publish_bundle:docs/tistory/2026-07-20.json",
            before,
        )
        self.assertEqual(after, [])
        self.assertIn(
            "unstaged_publish_bundle:docs/tistory/2026-07-20-adfit.html",
            unstaged,
        )
        self.assertEqual({item for item in cached if item}, set(staged))
        self.assertEqual(
            {item for item in cached if item},
            {str(path.relative_to(root)) for path in paths.values()},
        )


if __name__ == "__main__":
    unittest.main()
