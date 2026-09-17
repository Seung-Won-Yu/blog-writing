import json
from pathlib import Path
import tempfile
import unittest

from blog_pipeline.publishing.preview_server import allowed_files, read_allowed


class PreviewServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.day = "2026-09-17"
        self.asset = "docs/tistory/assets/2026-09-17/USB-근거.webp"
        for name in ("docs/preview/tistory-style.css", "docs/preview/2026-09-17.html", self.asset):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"public preview")
        source = self.root / "data/days/2026-09-17.json"
        source.parent.mkdir(parents=True)
        source.write_text(json.dumps({"images": {"cover": {"path": self.asset}}}))

    def test_only_explicit_public_assets_are_served(self):
        allowed = allowed_files(self.root, [self.day])
        self.assertEqual(len(allowed), 3)
        self.assertIsNotNone(read_allowed(allowed, "/preview/2026-09-17.html?qa=1"))
        self.assertIsNotNone(read_allowed(allowed, "/tistory/assets/2026-09-17/USB-%EA%B7%BC%EA%B1%B0.webp"))
        for path in ("/", "/.git/config", "/data/days/2026-09-17.json", "/preview/../.env", "/%2e%2e/.env", "/preview/2026-09-16.html"):
            self.assertIsNone(read_allowed(allowed, path))

    def test_symlink_is_rejected_at_startup(self):
        path = self.root / self.asset
        path.unlink()
        path.symlink_to(self.root / "docs/preview/tistory-style.css")
        with self.assertRaises(ValueError):
            allowed_files(self.root, [self.day])

    def test_symlink_swap_is_rejected_at_read(self):
        allowed = allowed_files(self.root, [self.day])
        path = self.root / self.asset
        path.unlink()
        path.symlink_to(self.root / "docs/preview/tistory-style.css")
        self.assertIsNone(read_allowed(allowed, "/tistory/assets/2026-09-17/USB-근거.webp"))

    def test_asset_cannot_escape_its_draft(self):
        source = self.root / "data/days/2026-09-17.json"
        source.write_text(json.dumps({"images": {"cover": {"path": "docs/preview/tistory-style.css"}}}))
        with self.assertRaises(ValueError):
            allowed_files(self.root, [self.day])
