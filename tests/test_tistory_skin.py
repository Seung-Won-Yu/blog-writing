from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
STYLE_PATH = ROOT / "design" / "tistory" / "style.css"
LAYER_PATH = ROOT / "design" / "tistory" / "skin-layer.css"
SKIN_PATH = ROOT / "design" / "tistory" / "skin.html"
COMPONENTS_PATH = ROOT / "design" / "tistory" / "skin-components.html"
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

    def test_home_uses_six_equal_cards_instead_of_a_broken_lead_card(self):
        layer_css = LAYER_PATH.read_text(encoding="utf-8")

        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr));", layer_css)
        self.assertNotIn("> .post-item:first-child {\n  grid-column: 1 / -1;", layer_css)
        self.assertNotIn("> .post-item:first-child a {", layer_css)

    def test_home_starts_with_articles_not_a_marketing_hero(self):
        skin_html = SKIN_PATH.read_text(encoding="utf-8")
        components_html = COMPONENTS_PATH.read_text(encoding="utf-8")
        layer_css = LAYER_PATH.read_text(encoding="utf-8")

        self.assertNotIn('class="dev-hero"', skin_html)
        self.assertNotIn('class="dev-hero"', components_html)
        self.assertNotIn(".dev-hero", layer_css)

    def test_skin_tokens_are_complete_and_semantic(self):
        layer_css = LAYER_PATH.read_text(encoding="utf-8")
        declared = set(re.findall(r"(--sw-[a-z0-9-]+)\s*:", layer_css))
        used = set(re.findall(r"var\((--sw-[a-z0-9-]+)", layer_css))

        self.assertFalse(used - declared, f"undefined skin tokens: {sorted(used - declared)}")
        self.assertIn("--sw-font-body:", layer_css)
        self.assertIn("--sw-surface-tint:", layer_css)
        self.assertIn("--sw-warning:", layer_css)

    def test_article_titles_use_ink_and_accents_stay_supporting(self):
        layer_css = LAYER_PATH.read_text(encoding="utf-8")
        cover_section = layer_css.split("/* 5. Post cover", 1)[1]
        cover = cover_section.split(".post-cover {", 1)[1].split("}", 1)[0]
        cover_overlay = cover_section.split(".post-cover::before {", 1)[1].split("}", 1)[0]
        story_heading = layer_css.split(".daily-digest-post .digest-news-card h3 {", 1)[1].split("}", 1)[0]
        detail_heading = layer_css.split(".daily-digest-post .digest-full-content h4 {", 1)[1].split("}", 1)[0]

        self.assertIn("background: var(--sw-surface-tint) !important;", cover)
        self.assertNotIn("var(--sw-warm)", cover)
        self.assertIn("display: none !important;", cover_overlay)
        self.assertIn("content: none !important;", cover_overlay)
        self.assertIn("color: var(--sw-ink) !important;", story_heading)
        self.assertIn("color: var(--sw-ink) !important;", detail_heading)
        self.assertNotIn("border-left", detail_heading)


if __name__ == "__main__":
    unittest.main()
