from pathlib import Path
import re
import unittest
from blog_pipeline.publishing.export_tistory import render_content_blocks


ROOT = Path(__file__).resolve().parents[1]


def table_declarations(class_name, suffix=""):
    """Read rules for the actual class emitted by the HTML exporter."""
    css = (ROOT / "design/tistory/skin-layer.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    target = f".daily-digest-post .{class_name}{suffix}"
    declarations = {}
    for selectors, block in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if target not in {" ".join(s.split()) for s in selectors.split(",")}:
            continue
        for declaration in block.split(";"):
            prop, separator, value = declaration.partition(":")
            if separator:
                declarations[prop.strip()] = " ".join(value.split())
    return declarations


class CompactTableTests(unittest.TestCase):
    def test_two_columns_do_not_inherit_wide_table_minimum(self):
        html = render_content_blocks([{"t": "table", "headers": ["기록", "확인"], "rows": [["완료", "검증"]]}])
        self.assertIn('class="digest-compact-table"', html)
        self.assertNotIn('style=', html)

    def test_three_columns_retain_scrollable_table(self):
        html = render_content_blocks([{"t": "table", "headers": ["가", "나", "다"], "rows": [["1", "2", "3"]]}])
        self.assertIn('class="digest-data-table"', html)

    def test_exported_table_classes_have_real_layout_rules_in_the_skin(self):
        for columns, minimum in ((2, "0 !important"), (3, "560px !important")):
            with self.subTest(columns=columns):
                html = render_content_blocks([{
                    "t": "table", "headers": ["항목"] * columns,
                    "rows": [["확인"] * columns], "caption": "확인표",
                }])
                class_name = re.search(r'<table class="([^"]+)"', html).group(1)
                rules = table_declarations(class_name)
                # display:block makes the outer border fill the article while
                # the native row groups shrink to their text width (post /252).
                self.assertEqual(rules.get("display"), "table !important")
                self.assertEqual(rules.get("width"), "100% !important")
                self.assertEqual(rules.get("min-width"), minimum)
                self.assertEqual(table_declarations(class_name, " caption").get("text-align"), "left !important")

    def test_two_column_table_keeps_columns_inside_the_mobile_reading_width(self):
        rules = table_declarations("digest-compact-table")
        self.assertEqual(rules.get("table-layout"), "fixed !important")
