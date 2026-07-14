import unittest

from blog_pipeline.publishing.repair_archived_posts import (
    add_adfit_after_first_section,
    normalize_archived_html,
)


class RepairArchivedPostsTests(unittest.TestCase):
    def test_normalizes_shell_cards_and_learning_sections(self):
        source = """<article style="padding:0"><section class="digest-news-card" style="padding:0">첫째</section><section class="digest-news-card" style="padding:0">둘째</section><section class="digest-quiz">문제</section><section class="digest-terms">용어</section></article>"""

        html = normalize_archived_html(source)

        self.assertIn("max-width:728px !important", html)
        self.assertIn("padding:12px 0 36px !important", html)
        self.assertIn('id="digest-news-1"', html)
        self.assertIn('id="digest-news-2"', html)
        self.assertIn(
            'class="digest-quiz" style="margin:36px 0;padding:22px clamp(18px,4vw,28px)',
            html,
        )
        self.assertIn(
            'class="digest-terms" style="margin:36px 0;padding:22px clamp(18px,4vw,28px)',
            html,
        )

    def test_inserts_one_ad_before_second_story(self):
        source = normalize_archived_html(
            """<article><section class="digest-news-card">첫째</section><section class="digest-news-card">둘째</section></article>"""
        )

        html = add_adfit_after_first_section(source)

        self.assertLess(html.index("첫째"), html.index('data-ad-vendor="adfit"'))
        self.assertLess(html.index('data-ad-vendor="adfit"'), html.index("둘째"))
        self.assertEqual(html.count('data-ad-vendor="adfit"'), 1)

    def test_custom_story_anchor_places_ad_before_entire_second_section(self):
        source = """<article><section><h2>첫 이야기</h2></section><section><figure>이미지</figure><h2>둘째 이야기</h2></section></article>"""

        html = add_adfit_after_first_section(
            source, second_story_heading="둘째 이야기"
        )

        self.assertLess(html.index('data-ad-vendor="adfit"'), html.index("이미지"))


if __name__ == "__main__":
    unittest.main()
