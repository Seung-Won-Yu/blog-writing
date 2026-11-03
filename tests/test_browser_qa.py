import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
import io
from unittest.mock import patch

from blog_pipeline.publishing.browser_qa import (
    choose_preview, evidence_directory, capture_status, validate_navigation, main,
    request_allowed,
)


class BrowserQaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def draft(self, draft_id):
        for name, content in {
            f'data/days/{draft_id}.json': json.dumps({'images': {}}),
            f'docs/tistory/{draft_id}.json': json.dumps({'publish_ready': True}),
            f'docs/preview/{draft_id}.html': '<article>actual preview</article>',
            'docs/preview/tistory-style.css': 'article {}',
        }.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

    def test_preflight_chooses_existing_id_not_latest_refresh_date(self):
        self.draft('2026-08-20')
        self.draft('2026-10-28')
        plan = self.root / 'config/content_growth_trial.json'
        plan.parent.mkdir()
        plan.write_text(json.dumps({'refresh_queue': [
            {'draft_id': '2026-08-20', 'refreshed_on': '2026-11-03'}
        ]}))
        self.assertEqual(choose_preview(self.root), '2026-10-28')

    def test_missing_calendar_url_is_rejected_before_browser_launch(self):
        self.draft('2026-08-20')
        with self.assertRaisesRegex(ValueError, 'PREVIEW_NOT_FOUND'):
            choose_preview(self.root, '2026-10-30')

    def test_preflight_skips_unready_or_missing_previews(self):
        self.draft('2026-10-27')
        self.draft('2026-10-28')
        (self.root / 'docs/tistory/2026-10-28.json').write_text(
            json.dumps({'publish_ready': False}))
        self.assertEqual(choose_preview(self.root), '2026-10-27')
        (self.root / 'docs/preview/2026-10-27.html').unlink()
        with self.assertRaisesRegex(ValueError, 'NO_REVIEWED_PREVIEW'):
            choose_preview(self.root)

    def test_http_error_or_wrong_article_is_not_a_browser_success(self):
        for status, expected, actual in [(404, 'Title', '404'), (200, 'Title', 'Other')]:
            with self.subTest(status=status):
                with self.assertRaises(ValueError):
                    validate_navigation(status, expected, actual)
        validate_navigation(200, 'Title', 'Title')

    def test_two_metrics_passes_are_capture_not_visual_approval(self):
        passed = {'status': 'METRICS_PASS', 'viewport': [1280, 900]}
        mobile = {'status': 'METRICS_PASS', 'viewport': [390, 844]}
        self.assertEqual(capture_status([passed, mobile]), 'CAPTURED')
        for reports in ([passed], [passed, passed],
                        [passed, dict(mobile, status='IMAGES_PENDING')],
                        [passed, dict(mobile, status='METRICS_FAIL')]):
            self.assertEqual(capture_status(reports), 'LAYOUT_FAILED')

    def test_evidence_cannot_dirty_repository(self):
        with self.assertRaisesRegex(ValueError, 'outside repository'):
            evidence_directory(self.root, self.root / 'reports/screenshots')
        with tempfile.TemporaryDirectory() as output:
            self.assertEqual(evidence_directory(self.root, output), Path(output).resolve())

    def test_network_cannot_leave_selected_preview_origin(self):
        self.assertTrue(request_allowed('http://127.0.0.1:54321/preview/one.html',
                                        'http://127.0.0.1:54321'))
        self.assertFalse(request_allowed('http://127.0.0.1:8765/.env',
                                         'http://127.0.0.1:54321'))
        origin = 'https://seung-won-yu.github.io/blog-writing'
        self.assertTrue(request_allowed(origin + '/preview/one.html', origin))
        for url in ('https://example.com/collect',
                    'https://seung-won-yu.github.io/other-project/private',
                    'https://seung-won-yu.github.io/blog-writing-evil/collect',
                    'http://seung-won-yu.github.io/blog-writing/x'):
            self.assertFalse(request_allowed(url, origin))

    def test_browser_failure_replaces_previous_pass_and_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as output:
            manifest = Path(output) / 'capture.json'
            manifest.write_text(json.dumps({'status': 'CAPTURED'}))
            stdout = io.StringIO()
            with patch('blog_pipeline.publishing.browser_qa.choose_preview',
                       return_value='2026-08-20'), \
                 patch('blog_pipeline.publishing.browser_qa.capture',
                       side_effect=RuntimeError('browser crashed')), \
                 redirect_stdout(stdout):
                self.assertEqual(main(['--preflight', '--output-dir', output]), 2)
            self.assertEqual(json.loads(manifest.read_text())['status'], 'QA_ENV_BLOCKED')
            self.assertIn('browser crashed', stdout.getvalue())


if __name__ == '__main__':
    unittest.main()
