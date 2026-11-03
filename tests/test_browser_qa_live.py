"""Opt-in real Chromium checks: BLOG_BROWSER_QA_LIVE=1 python -m unittest ..."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from blog_pipeline.publishing.browser_qa import ROOT, capture


@unittest.skipUnless(os.environ.get('BLOG_BROWSER_QA_LIVE') == '1',
                     'explicit isolated-browser integration run only')
class BrowserQaLiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.output.cleanup)
        self.root = Path(self.temp.name).resolve()
        for name in ['agent', 'docs/preview', 'docs/tistory/assets/2026-11-03', 'data/days']:
            (self.root / name).mkdir(parents=True)
        (self.root / 'agent/browser-layout-audit.js').write_text(
            (ROOT / 'agent/browser-layout-audit.js').read_text())
        asset = 'docs/tistory/assets/2026-11-03/fixture.webp'
        Image.new('RGB', (32, 32), 'white').save(self.root / asset)
        (self.root / 'data/days/2026-11-03.json').write_text(json.dumps({
            'editorial': {'headline': 'Strict CSP fixture'},
            'images': {'cover': {'path': asset}},
        }))
        (self.root / 'docs/preview/tistory-style.css').write_text('''
            .daily-digest-post {max-width:700px; margin:auto}
            .digest-table-wrap {overflow-x:auto}
            table {width:100%;table-layout:fixed;border-collapse:collapse}
            caption {text-align:left}
            img {max-width:100%;height:auto}
        ''')
        (self.root / 'docs/preview/2026-11-03.html').write_text('''<!doctype html>
            <meta http-equiv="Content-Security-Policy"
              content="default-src 'none'; script-src 'none'; style-src 'self'; img-src 'self'">
            <link rel="stylesheet" href="tistory-style.css">
            <article class="daily-digest-post"><h1>Strict CSP fixture</h1>
              <figure><img loading="lazy" alt="fixture" src="../tistory/assets/2026-11-03/fixture.webp"></figure>
              <div class="digest-table-wrap"><table><caption>Two columns</caption>
                <thead><tr><th>A</th><th>B</th></tr></thead>
                <tbody><tr><td>left</td><td>right</td></tr></tbody>
              </table></div>
            </article>''')

    def test_strict_csp_capture_needs_no_script_policy_bypass(self):
        result = capture(self.root, '2026-11-03', self.output.name)
        self.assertEqual(result['status'], 'CAPTURED',
                         (Path(self.output.name) / 'desktop.json').read_text())
        self.assertEqual(result['visual_review'], 'PENDING')
        self.assertEqual(len(result['metrics']), 2)

    def test_real_shrunken_table_body_cannot_pass(self):
        css = self.root / 'docs/preview/tistory-style.css'
        css.write_text(css.read_text() + '\ntbody {display:block;width:40%}\n')
        result = capture(self.root, '2026-11-03', self.output.name)
        self.assertEqual(result['status'], 'LAYOUT_FAILED')
        desktop = json.loads((Path(self.output.name) / 'desktop.json').read_text())
        self.assertIn('table_1:inner_width_mismatch', desktop['issues'])
