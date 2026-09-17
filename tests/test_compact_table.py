import unittest
from blog_pipeline.publishing.export_tistory import render_content_blocks


class CompactTableTests(unittest.TestCase):
    def test_two_columns_do_not_inherit_wide_table_minimum(self):
        html = render_content_blocks([{"t": "table", "headers": ["기록", "확인"], "rows": [["완료", "검증"]]}])
        self.assertIn('class="digest-compact-table"', html)
        self.assertNotIn('style=', html)

    def test_three_columns_retain_scrollable_table(self):
        html = render_content_blocks([{"t": "table", "headers": ["가", "나", "다"], "rows": [["1", "2", "3"]]}])
        self.assertIn('class="digest-data-table"', html)
