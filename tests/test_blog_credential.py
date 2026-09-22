import subprocess
import unittest
from pathlib import Path


class BlogCredentialTests(unittest.TestCase):
    def test_rejects_unrelated_targets_without_credentials(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/blog-credential'
        base = 'protocol=https\nhost=github.com\npath=Seung-Won-Yu/blog-writing.git\n'
        cases = [
            ('store', base), ('erase', base),
            ('get', base.replace('https', 'http')),
            ('get', base.replace('github.com', 'example.com')),
            ('get', base.replace('blog-writing.git', 'another.git')),
            ('get', base + 'username=yu-reka\n'),
            ('get', 'protocol=https\nhost=github.com\n'),
        ]
        for operation, request in cases:
            with self.subTest(operation=operation, request=request):
                result = subprocess.run(['sh', str(script), operation], input=request+'\n', text=True, capture_output=True)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, '')
