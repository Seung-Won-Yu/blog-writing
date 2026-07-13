import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from build_copy_page import json_for_script, load_drafts, render


class CopyPageTests(unittest.TestCase):
    def test_copy_page_hides_legacy_drafts_without_local_source_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tistory = root / "docs" / "tistory"
            days = root / "data" / "days"
            tistory.mkdir(parents=True)
            days.mkdir(parents=True)
            for day in ("2026-07-12", "2026-07-13"):
                (tistory / f"{day}.html").write_text("draft", encoding="utf-8")
                (tistory / f"{day}.json").write_text(
                    json.dumps({"title": day, "source": f"data/days/{day}.json"}),
                    encoding="utf-8",
                )
            (days / "2026-07-13.json").write_text("{}", encoding="utf-8")

            with patch("build_copy_page.ROOT", root), patch(
                "build_copy_page.TISTORY_DIR", tistory
            ):
                drafts = load_drafts()

        self.assertEqual([item["day"] for item in drafts], ["2026-07-13"])

    def test_explains_manual_generation_without_upstream_copy(self):
        html = render([])

        self.assertIn("빠진 날짜 직접 생성", html)
        self.assertIn("날짜를 비우면 오늘", html)
        self.assertIn("Run workflow", html)
        self.assertNotIn("조이한", html)
        self.assertIn('role="status"', html)
        self.assertIn('aria-live="polite"', html)

    def test_draft_buttons_expose_selected_state_and_fetch_recovery(self):
        html = render(
            [
                {
                    "day": "2026-07-13",
                    "title": "오늘의 초안",
                    "title_candidates": [],
                    "category": "데일리IT뉴스",
                    "tags": "AI",
                    "meta_description": "설명",
                    "key_summary": [],
                    "publish_checklist": [],
                    "image_assets": [],
                    "source": "data/days/2026-07-13.json",
                    "source_page": "",
                    "html_path": "tistory/2026-07-13.html",
                    "meta_path": "tistory/2026-07-13.json",
                }
            ]
        )

        self.assertIn('aria-pressed="false"', html)
        self.assertIn('button.setAttribute("aria-pressed"', html)
        self.assertIn("초안을 불러오지 못했습니다", html)
        self.assertIn('<label for="htmlCode"', html)
        self.assertIn('copyText(els.htmlCode.value, "본문 HTML")', html)
        self.assertNotIn('copyText(currentHtml, "본문 HTML")', html)

    def test_selects_named_cover_and_escapes_payload_for_script_context(self):
        unsafe = "뉴스 </script><script>alert(1)</script> & 흐름\u2028다음"
        encoded = json_for_script({"title": unsafe})
        self.assertNotIn("</script>", encoded)
        self.assertNotIn("<script>", encoded)
        self.assertNotIn("\u2028", encoded)
        self.assertIn("\\u003c/script\\u003e", encoded)

        html = render([])
        self.assertIn('asset.kind === "cover"', html)
        self.assertIn('aspect-ratio: 1200 / 630', html)
        self.assertIn("els.coverPreview.alt =", html)
        self.assertIn('asset.kind === "flow"', html)
        self.assertIn('asset.kind.startsWith("story_")', html)
        self.assertIn("본문 1번 이미지 열기", html)

    def test_body_preview_opens_the_actual_draft_next_to_copy_button(self):
        html = render([])

        self.assertIn(
            '<a class="preview-link" id="previewLink" href="#" target="_blank" rel="noopener" aria-disabled="true" tabindex="-1">본문 미리보기</a>',
            html,
        )
        self.assertLess(html.index('id="previewLink"'), html.index('data-copy="html"'))
        self.assertIn('els.previewLink.href = draft.html_path + "?v=" + Date.now();', html)
        self.assertIn('els.previewLink.setAttribute("aria-disabled", "false");', html)
        self.assertIn('els.previewLink.removeAttribute("tabindex");', html)
        self.assertIn('els.previewLink.addEventListener("click"', html)
        self.assertNotIn("previewDialog", html)
        self.assertNotIn("previewFrame", html)
        self.assertNotIn("srcdoc", html)
        self.assertIn(".code-actions {", html)
        self.assertIn(".preview-link {", html)


if __name__ == "__main__":
    unittest.main()
