import datetime as dt
import unittest

from collect_news import build_inbox, parse_feed, parse_html_links


RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item>
    <title>GitHub Actions 보안 업데이트</title>
    <link>https://example.com/actions?utm_source=rss</link>
    <description><![CDATA[<p>AI 프롬프트 인젝션 탐지를 추가했습니다.</p>]]></description>
    <pubDate>Sun, 12 Jul 2026 07:00:00 GMT</pubDate>
  </item>
</channel></rss>
"""


ATOM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Efficient AI Agents</title>
    <link href="https://arxiv.org/abs/2607.00001" />
    <summary>New agent benchmark.</summary>
    <updated>2026-07-12T06:00:00Z</updated>
  </entry>
</feed>
"""


HTML_PAGE = """
<html><body>
  <a href="/magazine/detail/3700/"><span>AI 시대 개발자의 새로운 역할</span></a>
  <a href="/magazine/detail/3701/">클라우드 비용을 줄인 실제 사례</a>
  <a href="/magazine/list/ai/">AI 목록</a>
  <a href="/magazine/detail/3700/">AI 시대 개발자의 새로운 역할</a>
</body></html>
"""

NOW = dt.datetime(2026, 7, 12, 9, 0, tzinfo=dt.timezone.utc)


class FeedParserTests(unittest.TestCase):
    def test_parses_rss_item_and_strips_html_summary(self):
        items = parse_feed(RSS_XML, "https://example.com/feed")

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "GitHub Actions 보안 업데이트")
        self.assertEqual(items[0]["summary"], "AI 프롬프트 인젝션 탐지를 추가했습니다.")
        self.assertEqual(items[0]["published_at"], "2026-07-12T07:00:00+00:00")

    def test_parses_atom_entry(self):
        items = parse_feed(ATOM_XML, "https://arxiv.org/")

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["url"], "https://arxiv.org/abs/2607.00001")
        self.assertEqual(items[0]["published_at"], "2026-07-12T06:00:00+00:00")


class HtmlParserTests(unittest.TestCase):
    def test_keeps_matching_article_links_and_removes_duplicates(self):
        source = {
            "url": "https://yozm.example/magazine/list/ai/",
            "link_pattern": r"^/magazine/detail/\d+/$",
        }

        items = parse_html_links(HTML_PAGE, source)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["url"], "https://yozm.example/magazine/detail/3700")
        self.assertEqual(items[0]["title"], "AI 시대 개발자의 새로운 역할")

    def test_skips_long_article_card_copy_instead_of_using_it_as_a_title(self):
        source = {
            "url": "https://yozm.example/magazine/",
            "link_pattern": r"^/magazine/detail/\d+/$",
            "max_title_chars": 120,
        }
        long_card = "본문처럼 긴 카드 문장입니다. " * 12
        html = f"""
          <a href="/magazine/detail/2064/">{long_card}</a>
          <a href="/magazine/detail/3838/">바이브 코딩으로 유료 앱 대체하기</a>
        """

        items = parse_html_links(html, source)

        self.assertEqual([item["title"] for item in items], ["바이브 코딩으로 유료 앱 대체하기"])


class InboxTests(unittest.TestCase):
    def test_builds_diverse_selection_and_records_source_errors(self):
        config = {
            "interest_keywords": ["AI", "GitHub Actions"],
            "selection": {
                "max_items": 3,
                "max_per_source": 1,
                "preferred_groups": ["official", "community", "korean_editorial"],
            },
            "sources": [
                {
                    "id": "official",
                    "name": "Official",
                    "group": "official",
                    "type": "rss",
                    "url": "https://official.example/feed",
                    "weight": 5,
                    "enabled": True,
                },
                {
                    "id": "community",
                    "name": "Community",
                    "group": "community",
                    "type": "rss",
                    "url": "https://community.example/feed",
                    "weight": 3,
                    "enabled": True,
                },
                {
                    "id": "broken",
                    "name": "Broken",
                    "group": "korean_editorial",
                    "type": "rss",
                    "url": "https://broken.example/feed",
                    "weight": 3,
                    "enabled": True,
                },
            ],
        }

        def fetch(url):
            if "broken" in url:
                raise OSError("network down")
            title = "AI 공식 발표" if "official" in url else "GitHub Actions 개발자 반응"
            article_url = "https://official.example/article" if "official" in url else "https://community.example/article"
            return RSS_XML.replace("GitHub Actions 보안 업데이트", title).replace(
                "https://example.com/actions?utm_source=rss", article_url
            )

        result = build_inbox(
            config,
            fetch_text=fetch,
            now=dt.datetime(2026, 7, 12, 9, 0, tzinfo=dt.timezone.utc),
            day_id="2026-07-12",
        )

        self.assertEqual(result["day"], "2026-07-12")
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual([item["group"] for item in result["selected"]], ["official", "community"])
        self.assertEqual(result["errors"][0]["source_id"], "broken")

    def test_uses_html_fallback_when_a_feed_rejects_the_request(self):
        config = {
            "interest_keywords": ["AI", "개발"],
            "selection": {"max_items": 1, "max_per_source": 1},
            "sources": [
                {
                    "id": "yozmit",
                    "name": "요즘IT",
                    "group": "korean_editorial",
                    "type": "rss",
                    "url": "https://yozm.example/feed/",
                    "fallbacks": [
                        {
                            "type": "html",
                            "url": "https://yozm.example/magazine/",
                            "link_pattern": r"^/magazine/detail/\d+/?$",
                        }
                    ],
                    "enabled": True,
                }
            ],
        }
        html = '<a href="/magazine/detail/3834/">AI 개발 도구 직접 써보기</a>'

        def fetch(url):
            if url.endswith("/feed/"):
                raise OSError("HTTP 405")
            return html

        result = build_inbox(config, fetch_text=fetch, now=NOW, day_id="2026-07-12")

        self.assertEqual(result["errors"], [])
        self.assertEqual(result["selected"][0]["source_id"], "yozmit")
        self.assertEqual(result["selected"][0]["title"], "AI 개발 도구 직접 써보기")

    def test_source_title_filter_drops_unrelated_items_from_a_mixed_feed(self):
        config = {
            "interest_keywords": ["AI"],
            "selection": {"max_items": 3, "max_per_source": 1},
            "sources": [
                {
                    "id": "aitimes",
                    "name": "AI타임스",
                    "group": "korean_general",
                    "type": "rss",
                    "url": "https://aitimes.example/rss.xml",
                    "include_title_keywords": ["AI", "챗GPT", "로봇"],
                    "enabled": True,
                }
            ],
        }
        mixed_feed = """<rss><channel>
          <item><title>지역 역사관 착공</title><link>https://aitimes.example/1</link><description>AI 생성 영상</description></item>
          <item><title>챗GPT 무료 이용 기간 연장</title><link>https://aitimes.example/2</link><description>일반 사용자 대상 혜택</description></item>
        </channel></rss>"""

        result = build_inbox(
            config,
            fetch_text=lambda _url: mixed_feed,
            now=NOW,
            day_id="2026-07-12",
        )

        self.assertEqual(
            [item["title"] for item in result["candidates"]],
            ["챗GPT 무료 이용 기간 연장"],
        )

    def test_source_can_keep_rss_metadata_but_omit_copyrighted_summary(self):
        config = {
            "interest_keywords": ["AI"],
            "selection": {"max_items": 1, "max_per_source": 1},
            "sources": [
                {
                    "id": "aitimes",
                    "name": "AI타임스",
                    "group": "korean_general",
                    "type": "rss",
                    "url": "https://aitimes.example/rss.xml",
                    "include_summary": False,
                    "enabled": True,
                }
            ],
        }
        feed = """<rss><channel><item>
          <title>인스타 사진 AI 연동 중단</title>
          <link>https://aitimes.example/1</link>
          <description>기사 본문을 길게 옮긴 RSS 설명</description>
          <pubDate>Sun, 12 Jul 2026 07:00:00 GMT</pubDate>
        </item></channel></rss>"""

        result = build_inbox(config, fetch_text=lambda _url: feed, now=NOW, day_id="2026-07-12")

        self.assertEqual(result["candidates"][0]["title"], "인스타 사진 AI 연동 중단")
        self.assertEqual(result["candidates"][0]["summary"], "")


if __name__ == "__main__":
    unittest.main()
