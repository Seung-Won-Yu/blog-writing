import copy
import unittest
from types import SimpleNamespace
from blog_pipeline.publishing.reader_value import reader_value_reasons


class ReaderValueTests(unittest.TestCase):
    def setUp(self):
        self.identity = SimpleNamespace(publish_date='2026-09-29')
        self.source = {'editorial': {'value_review': {
            'primary_reader': '일반 독자', 'reader_question': '언제 쓰는가',
            'source_gap': '설정과 센서의 차이', 'selection_reason': '기존 글에 없는 비교',
            'contributions': [{'basis': 'documented', 'excerpt': '센서가 정상이어도 앱의 설정 때문에 회전하지 않을 수 있습니다.',
                'limit_excerpt': '기기별 임계값을 직접 측정한 결과는 아닙니다.', 'source_urls': ['https://example.com/docs']}]}},
            'news': [{'references': [{'url': 'https://example.com/docs'}], 'content': [
                {'t': 'p', 'text': '센서가 정상이어도 앱의 설정 때문에 회전하지 않을 수 있습니다.'},
                {'t': 'p', 'text': '기기별 임계값을 직접 측정한 결과는 아닙니다.'}]}]}

    def test_documented_explanation_does_not_require_fake_experiment(self):
        self.assertEqual(reader_value_reasons(self.source, self.identity), [])

    def test_metadata_alone_or_unlisted_source_fails(self):
        for field, value in [('excerpt', '본문에 존재하지 않는 기여를 메타데이터에만 적습니다.'),
                             ('source_urls', ['https://unknown.example/']),
                             ('basis', 'observed'), ('basis', 'inference')]:
            source = copy.deepcopy(self.source)
            source['editorial']['value_review']['contributions'][0][field] = value
            self.assertIn('quality_value_review', reader_value_reasons(source, self.identity))

    def test_legacy_is_not_retroactively_blocked(self):
        self.assertEqual(reader_value_reasons({}, SimpleNamespace(publish_date='2026-09-28')), [])

    def test_missing_review_fails_for_new_drafts(self):
        self.assertIn('quality_value_review', reader_value_reasons({}, self.identity))

    def test_common_authoring_gate_includes_value_review(self):
        import json
        from pathlib import Path
        from blog_pipeline.publishing.draft_identity import resolve_draft_identity
        from blog_pipeline.publishing.editorial_quality import source_authoring_reasons
        source = json.loads((Path(__file__).resolve().parents[1] / 'data/days/2026-09-22.json').read_text())
        identity = resolve_draft_identity('2026-09-29')
        self.assertIn('quality_value_review', source_authoring_reasons(source, identity))
