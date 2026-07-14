import json
import tempfile
import unittest
from pathlib import Path

from blog_pipeline.legacy.restore_review_inbox import restore_review_inbox


LEGACY_HTML = """
<section class="digest-news-card">
  <p class="digest-source">1. GeekNews</p>
  <h3>Ghostty와 Zig 오픈소스 유지보수</h3>
  <p>도구를 만든 배경과 장기 유지보수 기준을 설명합니다.</p>
  <p class="digest-source-link"><a href="https://news.hada.io/topic?id=1">원문 보기</a></p>
</section>
<section class="digest-news-card">
  <p class="digest-source">2. AI타임스</p>
  <h3>AI 서비스가 일상에 미치는 변화</h3>
  <p>사용자가 확인해야 할 개인정보와 선택권을 짚습니다.</p>
  <p class="digest-source-link"><a href="https://www.aitimes.com/news/articleView.html?idxno=2">원문 보기</a></p>
</section>
"""


class RestoreReviewInboxTests(unittest.TestCase):
    def test_restores_selected_sources_from_legacy_tistory_html(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            html_path = root / "legacy.html"
            output_path = root / "inbox.json"
            html_path.write_text(LEGACY_HTML, encoding="utf-8")

            inbox = restore_review_inbox("2026-07-11", html_path, output_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(inbox, written)
        self.assertEqual(inbox["day"], "2026-07-11")
        self.assertTrue(inbox["review_required"])
        self.assertEqual(len(inbox["selected"]), 2)
        self.assertEqual(
            inbox["selected"][0]["title"],
            "Ghostty와 Zig 오픈소스 유지보수",
        )
        self.assertEqual(
            inbox["selected"][0]["url"], "https://news.hada.io/topic?id=1"
        )
        self.assertEqual(inbox["selected"][0]["source_name"], "GeekNews")
        self.assertIn("장기 유지보수", inbox["selected"][0]["summary"])
        self.assertEqual(inbox["candidates"], inbox["selected"])

    def test_rejects_legacy_html_without_reusable_source_cards(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            html_path = root / "legacy.html"
            html_path.write_text("<p>원문 링크가 없는 글</p>", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "복원할 뉴스 카드"):
                restore_review_inbox(
                    "2026-07-11", html_path, root / "inbox.json"
                )

    def test_rejects_non_http_source_links_from_legacy_html(self):
        unsafe_html = LEGACY_HTML.replace(
            "https://news.hada.io/topic?id=1", "javascript:alert(1)"
        ).replace(
            "https://www.aitimes.com/news/articleView.html?idxno=2",
            "data:text/html,unsafe",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            html_path = root / "legacy.html"
            html_path.write_text(unsafe_html, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "복원할 뉴스 카드"):
                restore_review_inbox(
                    "2026-07-11", html_path, root / "inbox.json"
                )


if __name__ == "__main__":
    unittest.main()
