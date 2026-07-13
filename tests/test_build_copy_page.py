import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from build_copy_page import json_for_script, load_drafts, render, write_preview_pages


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
                    "preview_path": "preview/2026-07-13.html",
                    "meta_path": "tistory/2026-07-13.json",
                    "generation_provider": "gemini",
                    "publish_ready": True,
                }
            ]
        )

        self.assertIn('aria-pressed="false"', html)
        self.assertIn('button.setAttribute("aria-pressed"', html)
        self.assertIn("초안을 불러오지 못했습니다", html)
        self.assertIn('<label for="htmlCode"', html)
        self.assertIn('copyText(buildReviewedHtml(), "본문 HTML")', html)
        self.assertNotIn('copyText(currentHtml, "본문 HTML")', html)

    def test_allows_publish_ready_copy_without_required_manual_review(self):
        html = render([])

        self.assertIn('id="editorNote"', html)
        self.assertIn('id="verificationNote"', html)
        self.assertNotIn('id="sourceChecked"', html)
        self.assertIn('id="relatedUrl"', html)
        self.assertIn('id="htmlCopyButton"', html)
        self.assertIn('data-copy="html" disabled', html)
        self.assertIn('<textarea id="htmlCode" spellcheck="false" readonly>', html)
        self.assertNotIn("검수 완료 후 HTML 코드가 표시됩니다.", html)
        self.assertIn("function escapeHtml(value)", html)
        self.assertIn("function buildAuthorNoteHtml()", html)
        self.assertIn('class="digest-author-note"', html)
        self.assertIn("function isDraftCopyReady()", html)
        self.assertNotIn("editorNote.length >= 40", html)
        self.assertNotIn("verificationNote.length >= 40", html)
        self.assertNotIn("Boolean(els.sourceChecked.checked)", html)
        self.assertIn("current.publish_ready", html)
        self.assertIn("currentBaseHtml", html)
        self.assertIn("바로 복사 가능", html)
        self.assertIn("메모는 선택", html)
        self.assertIn("발행 보류", html)

    def test_loads_generation_readiness_from_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tistory = root / "docs" / "tistory"
            days = root / "data" / "days"
            tistory.mkdir(parents=True)
            days.mkdir(parents=True)
            (tistory / "2026-07-13.html").write_text("draft", encoding="utf-8")
            (tistory / "2026-07-13.json").write_text(
                json.dumps(
                    {
                        "title": "오늘의 초안",
                        "source": "data/days/2026-07-13.json",
                        "generation_provider": "gemini",
                        "publish_ready": True,
                    }
                ),
                encoding="utf-8",
            )
            (days / "2026-07-13.json").write_text("{}", encoding="utf-8")

            with patch("build_copy_page.ROOT", root), patch(
                "build_copy_page.TISTORY_DIR", tistory
            ):
                draft = load_drafts()[0]

        self.assertEqual(draft["generation_provider"], "gemini")
        self.assertTrue(draft["publish_ready"])

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

    def test_body_preview_toggles_inline_next_to_copy_button(self):
        html = render([])

        self.assertIn(
            '<button class="copy preview-toggle" type="button" id="previewButton" aria-expanded="false" aria-controls="previewPane" disabled>본문 미리보기</button>',
            html,
        )
        self.assertLess(html.index('id="previewButton"'), html.index('data-copy="html"'))
        self.assertIn(
            '<section class="preview-pane" id="previewPane" aria-label="블로그 본문 미리보기" hidden>',
            html,
        )
        self.assertIn(
            '<iframe class="preview-frame" id="previewFrame" title="블로그 본문 미리보기" sandbox="allow-same-origin" referrerpolicy="no-referrer"></iframe>',
            html,
        )
        self.assertIn('currentPreviewPath = draft.preview_path + "?v=" + Date.now();', html)
        self.assertIn('els.previewFrame.setAttribute("src", currentPreviewPath);', html)
        self.assertIn('showingPreview && !els.previewFrame.hasAttribute("src")', html)
        self.assertIn('els.previewButton.addEventListener("click"', html)
        self.assertIn('els.previewFrame.addEventListener("load"', html)
        self.assertIn("updatePreviewNote", html)
        self.assertIn('els.previewPane.hidden = !showingPreview;', html)
        self.assertIn('els.htmlCode.hidden = showingPreview;', html)
        self.assertIn('els.previewButton.textContent = showingPreview', html)
        self.assertIn('els.previewButton.setAttribute("aria-expanded"', html)
        self.assertNotIn("previewDialog", html)
        self.assertNotIn("showModal", html)
        self.assertIn(".code-actions {", html)
        self.assertIn(".preview-pane {", html)
        self.assertIn("textarea[hidden], .preview-pane[hidden] { display: none; }", html)

    def test_writes_a_utf8_script_blocked_standalone_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tistory = root / "tistory"
            preview = root / "preview"
            tistory.mkdir()
            (tistory / "2026-07-13.html").write_text(
                '<article><h2>한글 제목</h2><script>alert("x")</script></article>',
                encoding="utf-8",
            )
            drafts = [
                {
                    "day": "2026-07-13",
                    "title": "한글 제목",
                    "html_path": "tistory/2026-07-13.html",
                    "preview_path": "preview/2026-07-13.html",
                }
            ]

            with patch("build_copy_page.TISTORY_DIR", tistory), patch(
                "build_copy_page.PREVIEW_DIR", preview
            ):
                write_preview_pages(drafts)

            page = (preview / "2026-07-13.html").read_text(encoding="utf-8")

        self.assertIn('<meta charset="utf-8">', page)
        self.assertIn('Content-Security-Policy', page)
        self.assertIn("script-src 'none'", page)
        self.assertIn("한글 제목 · 본문 미리보기", page)
        self.assertIn("<article><h2>한글 제목</h2>", page)


if __name__ == "__main__":
    unittest.main()
