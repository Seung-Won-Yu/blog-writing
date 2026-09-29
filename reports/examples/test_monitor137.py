import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

spec = importlib.util.spec_from_file_location("monitor137", Path(__file__).with_name("monitor137.py"))
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.html, self.state = self.root / "demo.html", self.root / "state.json"

    def run_monitor(self, markup, *, url=None):
        self.html.write_text(markup, encoding="utf-8")
        args = ["monitor.py", url or str(self.html), "--state", str(self.state)]
        if url is None:
            args.append("--html-file")
        output = io.StringIO()
        with patch.object(sys, "argv", args), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = monitor.main()
        return code, output.getvalue()

    def test_three_normal_states(self):
        first = '<div id="watch-target"><p>마감</p><p>0명</p></div>'
        self.assertEqual(self.run_monitor(first), (0, "BASELINE\n"))
        self.assertEqual(self.run_monitor(first), (0, "UNCHANGED\n"))
        code, out = self.run_monitor(first.replace("마감", "신청 가능").replace("0명", "12명"))
        self.assertEqual(code, 0)
        self.assertIn("CHANGED\n알림 대상", out)
        self.assertIn("+12명", out)

    def test_errors_preserve_baseline(self):
        self.run_monitor('<div id="watch-target">기준</div>')
        original = self.state.read_bytes()
        for markup in ["<p>대상 없음</p>", '<div id="watch-target"></div>',
                       '<div id="watch-target">A</div><div id="watch-target">B</div>',
                       '<div id="watch-target"><p>A</div>', "A" * (monitor.LIMIT + 1)]:
            with self.subTest(markup=markup[:40]):
                self.assertEqual(self.run_monitor(markup)[0], 2)
                self.assertEqual(self.state.read_bytes(), original)

    def test_script_style_and_outside_text_ignored(self):
        markup = '<p>밖1</p><div id="watch-target"><span>마감</span><br><p>0명</p><script>x=1</script><style>x{}</style></div>'
        self.run_monitor(markup)
        changed = markup.replace("밖1", "밖2").replace("x=1", "x=2")
        self.assertEqual(self.run_monitor(changed), (0, "UNCHANGED\n"))

    def test_bad_state_is_not_reset(self):
        self.run_monitor('<div id="watch-target">기준</div>')
        self.state.write_text('{"broken":', encoding="utf-8")
        original = self.state.read_bytes()
        self.assertEqual(self.run_monitor('<div id="watch-target">새값</div>')[0], 2)
        self.assertEqual(self.state.read_bytes(), original)

    def test_network_failure_preserves_state(self):
        self.run_monitor('<div id="watch-target">기준</div>')
        original = self.state.read_bytes()
        with patch.object(monitor, "urlopen", side_effect=URLError("test offline")):
            self.assertEqual(self.run_monitor("", url="https://example.com/apply")[0], 2)
        self.assertEqual(self.state.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
