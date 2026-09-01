import json
import subprocess
import tempfile
import unittest
from pathlib import Path


def write_project_bundle(root, draft_id, *, source_text="public project summary"):
    paths = {
        "source": root / "data" / "project_logs" / f"{draft_id[:10]}.json",
        "meta": root / "docs" / "tistory" / f"{draft_id}.json",
        "html": root / "docs" / "tistory" / f"{draft_id}.html",
        "before": root / "docs" / "tistory" / f"{draft_id}-before-ad.html",
        "after": root / "docs" / "tistory" / f"{draft_id}-after-ad.html",
        "adfit": root / "docs" / "tistory" / f"{draft_id}-adfit.html",
        "preview": root / "docs" / "preview" / f"{draft_id}.html",
        "image": root / "docs" / "tistory" / "assets" / draft_id / "cover.webp",
        "copy_page": root / "docs" / "index.html",
        "integration_page": root / "docs" / "integration.html",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(path.name, encoding="utf-8")
    paths["source"].write_text(source_text, encoding="utf-8")
    paths["meta"].write_text(
        json.dumps(
            {
                "source": str(paths["source"].relative_to(root)),
                "html": str(paths["html"].relative_to(root)),
                "before_ad_html": str(paths["before"].relative_to(root)),
                "after_ad_html": str(paths["after"].relative_to(root)),
                "adfit_html": str(paths["adfit"].relative_to(root)),
                "image_assets": [
                    {"path": str(paths["image"].relative_to(root))}
                ],
            }
        ),
        encoding="utf-8",
    )
    return paths


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

    def test_resume_accepts_only_current_complete_bundle_changes(self):
        from blog_pipeline.publishing.publish_bundle import (
            publish_bundle_resume_reasons,
            required_publish_bundle_paths,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            draft_id = "2026-08-12-guide"
            for relative in required_publish_bundle_paths(draft_id, root=root):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(relative, encoding="utf-8")

            ready = publish_bundle_resume_reasons(draft_id, root=root)
            unexpected = root / "notes.txt"
            unexpected.write_text("user change", encoding="utf-8")
            blocked = publish_bundle_resume_reasons(draft_id, root=root)

        self.assertEqual(ready, [])
        self.assertIn("unexpected_worktree_change:notes.txt", blocked)

    def test_resume_ignores_gitignored_playwright_runtime_artifacts(self):
        from blog_pipeline.publishing.publish_bundle import (
            publish_bundle_resume_reasons,
            required_publish_bundle_paths,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / ".gitignore").write_text(
                "/.playwright-cli/\n", encoding="utf-8"
            )
            subprocess.run(["git", "add", ".gitignore"], cwd=root, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.com",
                    "commit",
                    "-qm",
                    "fixture ignore",
                ],
                cwd=root,
                check=True,
            )
            draft_id = "2026-08-18"
            for relative in required_publish_bundle_paths(draft_id, root=root):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(relative, encoding="utf-8")
            runtime_snapshot = root / ".playwright-cli" / "page.yml"
            runtime_snapshot.parent.mkdir(parents=True, exist_ok=True)
            runtime_snapshot.write_text("runtime snapshot", encoding="utf-8")

            reasons = publish_bundle_resume_reasons(draft_id, root=root)

        self.assertEqual(reasons, [])

    def test_resume_requires_source_change(self):
        from blog_pipeline.publishing.publish_bundle import (
            publish_bundle_resume_reasons,
            required_publish_bundle_paths,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            draft_id = "2026-08-12-guide"
            required = required_publish_bundle_paths(draft_id, root=root)
            for relative in required:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(relative, encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.com",
                    "commit",
                    "-qm",
                    "fixture",
                ],
                cwd=root,
                check=True,
            )
            (root / "docs" / "index.html").write_text("changed", encoding="utf-8")
            reasons = publish_bundle_resume_reasons(draft_id, root=root)

        self.assertIn(
            "source_not_changed:data/guides/2026-08-12.json",
            reasons,
        )

    def test_project_public_safety_accepts_summaries_and_public_sources(self):
        from blog_pipeline.publishing.publish_bundle import (
            project_public_safety_reasons,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            draft_id = "2026-09-05-project"
            paths = write_project_bundle(
                root,
                draft_id,
                source_text=(
                    "실제 테스트를 비식별 집계값으로 요약했다. "
                    "공개 근거: https://www.sec.gov/investor/pubs/"
                ),
            )
            paths["image"].write_bytes(b"RIFF public-safe WEBP metadata")

            reasons = project_public_safety_reasons(draft_id, root=root)

        self.assertEqual(reasons, [])

    def test_project_public_safety_redacts_values_and_scans_image_metadata(self):
        from blog_pipeline.publishing.publish_bundle import (
            project_public_safety_reasons,
        )

        fake_token = "ghp_" + "A" * 32
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            draft_id = "2026-09-05-project"
            paths = write_project_bundle(
                root,
                draft_id,
                source_text=(
                    "/Users/example/private/edgelab/result.json\n"
                    f"access_token={fake_token}\n"
                    "account_id=acct-live-4815\n"
                    "commit_sha=deadbeef"
                ),
            )
            paths["image"].write_bytes(
                b"RIFF metadata /home/trader/private/edgelab/snapshot.png"
            )

            reasons = project_public_safety_reasons(draft_id, root=root)

        self.assertTrue(any(reason.endswith(":absolute_path") for reason in reasons))
        self.assertTrue(any(reason.endswith(":github_token") for reason in reasons))
        self.assertTrue(any(reason.endswith(":assigned_secret") for reason in reasons))
        self.assertTrue(any(reason.endswith(":private_identifier") for reason in reasons))
        self.assertTrue(any(reason.endswith(":private_revision") for reason in reasons))
        self.assertNotIn(fake_token, " ".join(reasons))
        self.assertNotIn("acct-live-4815", " ".join(reasons))

    def test_project_stage_is_blocked_before_git_add_when_private_data_exists(self):
        from blog_pipeline.publishing.publish_bundle import stage_publish_bundle

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            draft_id = "2026-09-05-project"
            write_project_bundle(
                root,
                draft_id,
                source_text="server_ip=203.0.113.77",
            )

            with self.assertRaisesRegex(ValueError, "public-safety"):
                stage_publish_bundle(draft_id, root=root)
            cached = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout

        self.assertEqual(cached, "")


if __name__ == "__main__":
    unittest.main()
