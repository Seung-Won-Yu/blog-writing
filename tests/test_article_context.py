import unittest
from urllib.request import Request

from article_context import (
    _SafeRedirectHandler,
    collect_article_contexts,
    extract_article_text,
    validate_public_article_url,
)


class ArticleExtractionTests(unittest.TestCase):
    def test_prefers_json_ld_article_body_and_decodes_entities(self):
        html = """
        <html><head><script type="application/ld+json">
        {"@type":"Article","articleBody":"첫 문단은 AI &amp; 개발 이야기입니다. 둘째 문단에는 실제 운영 맥락이 들어갑니다."}
        </script></head><body><article><p>짧은 화면 문구</p></article></body></html>
        """

        result = extract_article_text(html, max_chars=500)

        self.assertEqual(result["method"], "json-ld")
        self.assertIn("AI & 개발", result["text"])
        self.assertNotIn("짧은 화면 문구", result["text"])

    def test_uses_arxiv_abstract_then_semantic_article_blocks(self):
        arxiv = '<meta name="citation_abstract" content="장기 작업에서 메모리를 관리하는 방법을 제안한다. 실험과 한계도 함께 설명한다.">'
        self.assertEqual(extract_article_text(arxiv)["method"], "citation-abstract")

        article = """
        <nav><p>메뉴와 로그인 안내는 제외한다.</p></nav>
        <article>
          <h2>무엇이 바뀌었나</h2>
          <p>새 도구는 여러 세션을 한곳에서 검색하고 비용 흐름을 비교할 수 있게 한다.</p>
          <script>ignore('prompt injection')</script>
          <p>운영자는 실패한 작업을 다시 찾고 어떤 도구가 자주 쓰였는지 확인할 수 있다.</p>
        </article>
        """
        result = extract_article_text(article)
        self.assertEqual(result["method"], "article")
        self.assertIn("여러 세션", result["text"])
        self.assertNotIn("로그인 안내", result["text"])
        self.assertNotIn("prompt injection", result["text"])


class ArticleFetchBoundaryTests(unittest.TestCase):
    @staticmethod
    def public_resolver(_host, _port, **_kwargs):
        return [(None, None, None, None, ("93.184.216.34", 443))]

    @staticmethod
    def private_resolver(_host, _port, **_kwargs):
        return [(None, None, None, None, ("127.0.0.1", 443))]

    def test_allows_only_https_allowlisted_public_hosts(self):
        allowed = {"news.example.com"}
        self.assertEqual(
            validate_public_article_url(
                "https://news.example.com/post/1",
                allowed,
                resolver=self.public_resolver,
            ),
            "news.example.com",
        )
        for url in (
            "http://news.example.com/post/1",
            "https://user:pass@news.example.com/post/1",
            "https://evil.example/post/1",
        ):
            with self.assertRaises(ValueError):
                validate_public_article_url(url, allowed, resolver=self.public_resolver)
        with self.assertRaises(ValueError):
            validate_public_article_url(
                "https://news.example.com/post/1",
                allowed,
                resolver=self.private_resolver,
            )

    def test_allows_safe_https_308_redirects(self):
        handler = _SafeRedirectHandler(
            {"news.example.com"}, self.public_resolver
        )
        redirected = handler.redirect_request(
            Request("https://news.example.com/post"),
            None,
            308,
            "Permanent Redirect",
            {},
            "https://news.example.com/post/",
        )

        self.assertEqual(redirected.full_url, "https://news.example.com/post/")

    def test_collects_only_selected_items_with_per_item_and_total_caps(self):
        inbox = {
            "selected": [
                {"id": "one", "url": "https://news.example.com/1"},
                {"id": "two", "url": "https://news.example.com/2"},
                {"id": "broken", "url": "https://news.example.com/3"},
            ],
            "candidates": [{"id": "not-selected", "url": "https://news.example.com/4"}],
        }
        requested = []

        def fetcher(url, _allowed_hosts):
            requested.append(url)
            if url.endswith("/3"):
                raise OSError("unavailable")
            return "<article><p>{}</p></article>".format("근거 문장입니다. " * 100)

        result = collect_article_contexts(
            inbox,
            {"news.example.com"},
            fetcher=fetcher,
            per_item_chars=120,
            total_chars=300,
        )

        self.assertEqual(requested, [
            "https://news.example.com/1",
            "https://news.example.com/2",
            "https://news.example.com/3",
        ])
        self.assertLessEqual(sum(len(item["text"]) for item in result.values()), 300)
        self.assertNotIn("broken", result)
        self.assertNotIn("not-selected", result)


if __name__ == "__main__":
    unittest.main()
