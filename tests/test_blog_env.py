from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class BlogEnvTests(unittest.TestCase):
    def test_repository_venv_has_priority_even_from_another_cwd(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            script = scripts / "blog-env"
            shutil.copyfile(Path(__file__).resolve().parents[1] / "scripts/blog-env", script)
            binary = root / ".venv/bin/python3"
            binary.parent.mkdir(parents=True)
            binary.write_text('#!/bin/sh\nprintf "repository-python"\n')
            binary.chmod(0o700)
            result = subprocess.run(["sh", str(script), "python3"], cwd="/tmp", text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "repository-python")
