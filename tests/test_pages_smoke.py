import unittest

from blog_pipeline.publishing.pages_smoke import verify_public_page


class PagesSmokeTests(unittest.TestCase):
    def test_public_page_completes_when_bytes_match(self):
        result = verify_public_page(
            url="https://example.github.io/blog-writing/",
            expected_bytes=b"handoff",
            cache_key="abc123",
            fetcher=lambda _url, _timeout: b"handoff",
            sleep=lambda _seconds: None,
        )

        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["attempts"], 1)
        self.assertIn("build=abc123", result["url"])
        self.assertEqual(result["expected_sha256"], result["actual_sha256"])

    def test_public_page_retries_until_new_deployment_reaches_the_cdn(self):
        responses = iter([b"old", b"old", b"new"])
        sleeps = []

        result = verify_public_page(
            url="https://example.github.io/blog-writing/",
            expected_bytes=b"new",
            max_attempts=4,
            delay_seconds=0.25,
            fetcher=lambda _url, _timeout: next(responses),
            sleep=sleeps.append,
        )

        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["attempts"], 3)
        self.assertEqual(sleeps, [0.25, 0.25])

    def test_public_page_reports_pending_without_redeploying(self):
        result = verify_public_page(
            url="https://example.github.io/blog-writing/",
            expected_bytes=b"new",
            max_attempts=2,
            delay_seconds=0,
            fetcher=lambda _url, _timeout: b"old",
            sleep=lambda _seconds: None,
        )

        self.assertEqual(result["status"], "REMOTE_PUSHED_VERIFY_PENDING")
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["error"], "public_content_mismatch")

    def test_public_page_rejects_non_http_urls(self):
        with self.assertRaises(ValueError):
            verify_public_page(
                url="file:///tmp/index.html",
                expected_bytes=b"new",
                fetcher=lambda _url, _timeout: b"new",
            )


if __name__ == "__main__":
    unittest.main()
