from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
STYLE_PATH = ROOT / "design" / "tistory" / "style.css"
LAYER_PATH = ROOT / "design" / "tistory" / "skin-layer.css"
LAYER_MARKER = "/*\n  won0322.tistory.com · canonical custom layer"


class TistorySkinTests(unittest.TestCase):
    def test_full_css_keeps_base_and_exactly_one_custom_layer(self):
        full_css = STYLE_PATH.read_text(encoding="utf-8")
        layer_css = LAYER_PATH.read_text(encoding="utf-8")

        self.assertIn("CSS CONTENTS:", full_css)
        self.assertEqual(full_css.count(LAYER_MARKER), 1)
        self.assertTrue(full_css.endswith(layer_css))

    def test_mobile_layout_guards_are_present(self):
        layer_css = LAYER_PATH.read_text(encoding="utf-8")

        self.assertIn("#tt-body-page .post-cover", layer_css)
        self.assertIn("position: relative;", layer_css)
        self.assertIn("overflow-x: hidden;", layer_css)
        self.assertIn("#tt-body-index .pagination", layer_css)
        self.assertIn("gap: 22px;", layer_css)


if __name__ == "__main__":
    unittest.main()
