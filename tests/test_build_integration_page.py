import json
import re
import tempfile
import unittest
from pathlib import Path

from blog_pipeline.publishing.build_integration_page import (
    load_posts,
    render,
    write_page,
)


class IntegrationPageTests(unittest.TestCase):
    def test_loads_copy_ready_posts_and_requires_one_image_and_ad_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = root / "integrated_posts"
            content.mkdir()
            (content / "sample.html").write_text(
                '<style>.sample { color: black; }</style><article class="sample">'
                '<!-- TISTORY_IMAGE_TAG --><p>본문</p><!-- ADFIT_TAG --></article>',
                encoding="utf-8",
            )
            (content / "posts.json").write_text(
                json.dumps(
                    [
                        {
                            "slug": "sample",
                            "title": "Java 예제 통합",
                            "category": "Java 기초",
                            "tags": ["Java", "예제"],
                            "scheduled_at": "2026-07-17T09:00:00+09:00",
                            "source_ids": [1, 2],
                            "delete_urls": [
                                "https://won0322.tistory.com/1",
                                "https://won0322.tistory.com/2",
                            ],
                            "image_filename": "sample.png",
                            "image_location": "~/티스토리-업로드/1번-샘플.png",
                            "image_position": "도입부 다음, 목차 앞",
                            "image_alt": "Java 예제 설명 이미지",
                            "ad_position": "본문 약 40%",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            posts = load_posts(content)

        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["slug"], "sample")
        self.assertEqual(posts[0]["tags"], "Java, 예제")
        self.assertEqual(posts[0]["image_location"], "~/티스토리-업로드/1번-샘플.png")
        self.assertEqual(posts[0]["image_position"], "도입부 다음, 목차 앞")
        self.assertIn("<!-- TISTORY_IMAGE_TAG -->", posts[0]["html"])
        self.assertIn("<!-- ADFIT_TAG -->", posts[0]["html"])

    def test_rejects_source_with_missing_or_duplicate_placeholders(self):
        with tempfile.TemporaryDirectory() as directory:
            content = Path(directory)
            (content / "broken.html").write_text(
                "<!-- TISTORY_IMAGE_TAG --><!-- TISTORY_IMAGE_TAG -->",
                encoding="utf-8",
            )
            (content / "posts.json").write_text(
                json.dumps([{"slug": "broken", "title": "깨진 글"}]),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "자리표시자"):
                load_posts(content)

    def test_renders_one_step_image_and_adfit_html_assembler(self):
        page = render(
            [
                {
                    "slug": "sample",
                    "title": "Java 예제 통합",
                    "category": "자격증·공부 아카이브 / Java 기초",
                    "tags": "Java, 예제",
                    "scheduled_at": "2026-07-17 오전 9시",
                    "source_ids": [1, 2],
                    "delete_urls": ["https://won0322.tistory.com/1"],
                    "image_filename": "sample.png",
                    "image_location": "~/티스토리-업로드/1번-샘플.png",
                    "image_position": "도입부 다음, 목차 앞",
                    "image_alt": "Java 예제 설명 이미지",
                    "ad_position": "본문 약 40%",
                    "html": "<style></style><article><!-- TISTORY_IMAGE_TAG --><!-- ADFIT_TAG --></article>",
                }
            ]
        )

        self.assertIn("티스토리 보강글 발행 도우미", page)
        self.assertIn("위에서부터 차례대로", page)
        self.assertIn('href="./"', page)
        self.assertIn('id="imageLocation"', page)
        self.assertIn('id="imagePosition"', page)
        self.assertIn('data-copy="image-path"', page)
        self.assertIn('id="imageStepState"', page)
        self.assertIn('id="adStepState"', page)
        self.assertIn('id="finalResult" hidden', page)
        self.assertIn('els.finalResult.hidden = !ready;', page)
        self.assertIn('id="imageMarkup"', page)
        self.assertIn('id="adMarkup"', page)
        self.assertIn('id="buildFinalButton"', page)
        self.assertIn('id="finalHtml" spellcheck="false" readonly', page)
        self.assertIn("function extractImageMarkup(value)", page)
        self.assertIn("function applyImageAlt(markup, alt)", page)
        self.assertIn("function extractRevenueMarkup(value)", page)
        self.assertIn("function buildFinalHtml(showMessage = true)", page)
        self.assertIn("function isFinalHtmlStructurallyValid(value)", page)
        self.assertIn('sourceHtml.replace(imageMarker, imageMarkup)', page)
        self.assertIn(
            "applyImageAlt(extractImageMarkup(els.imageMarkup.value), current.image_alt)",
            page,
        )
        self.assertIn('.replace(adMarker, adMarkup)', page)
        self.assertIn('els.previewFrame.srcdoc = currentFinalHtml;', page)
        self.assertIn('sandbox=""', page)
        self.assertIn('els.imageMarkup.addEventListener("input"', page)
        self.assertIn('buildFinalHtml(false);', page)
        self.assertIn('data-copy="final" disabled', page)
        self.assertIn('document.execCommand("copy")', page)
        self.assertIn("기본모드로 돌아가지 마세요", page)
        self.assertIn("예약 저장 확인 후에만 원문 삭제", page)
        self.assertIn('copyText(current.image_location, "이미지 경로")', page)

    def test_real_posts_use_korean_image_names_and_explain_image_location(self):
        posts = load_posts()

        self.assertTrue(posts)
        self.assertTrue(all(re.search(r"[가-힣]", post["image_filename"]) for post in posts))
        self.assertTrue(all(post["image_location"] for post in posts))
        self.assertTrue(all(post["image_position"] for post in posts))

    def test_escapes_post_html_inside_script_payload(self):
        page = render(
            [
                {
                    "slug": "unsafe",
                    "title": "</script><script>alert(1)</script>",
                    "html": "<!-- TISTORY_IMAGE_TAG --><!-- ADFIT_TAG -->",
                }
            ]
        )

        self.assertNotIn("</script><script>alert(1)</script>", page)
        self.assertIn("\\u003c/script\\u003e", page)

    def test_writes_public_integration_page(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "integration.html"
            write_page([], output)

            page = output.read_text(encoding="utf-8")

        self.assertIn('<html lang="ko">', page)
        self.assertIn("티스토리 보강글 발행 도우미", page)


if __name__ == "__main__":
    unittest.main()
