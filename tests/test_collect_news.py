import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from blog_pipeline.collection.collect_news import (
    build_inbox,
    load_recent_publisher_hosts,
    load_recent_processed_urls,
    parse_feed,
    parse_github_trending,
    parse_html_links,
    render_inbox_html,
)


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


ATOM_WITH_REPLIES = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Prompt injection threats in the wild</title>
    <link rel="replies" href="https://security.example/comments" />
    <link rel="alternate" href="https://security.example/article" />
    <updated>2026-07-12T06:00:00Z</updated>
  </entry>
</feed>
"""


RSS_WITH_GUID_ONLY = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item>
    <title>Agent evaluation field notes</title>
    <guid isPermaLink="true">https://example.com/agent-evaluation</guid>
    <pubDate>Sun, 12 Jul 2026 07:00:00 GMT</pubDate>
  </item>
</channel></rss>
"""


HTML_PAGE = """
<html><body>
  <a href="/magazine/detail/3700/"><span>AI 시대 개발자의 새로운 역할</span></a>
  <a href="/magazine/detail/3701/">클라우드 비용을 줄인 실제 사례</a>
  <a href="/magazine/list/ai/">AI 목록</a>
  <a href="/magazine/detail/3700/">AI 시대 개발자의 새로운 역할</a>
</body></html>
"""

GITHUB_TRENDING_HTML = """
<main>
  <article class="Box-row">
    <h2 class="h3 lh-condensed">
      <a href="/n8n-io/n8n"><span>n8n-io /</span> n8n</a>
    </h2>
    <p class="col-9 color-fg-muted my-1 pr-4">
      Fair-code workflow automation platform with native AI capabilities.
    </p>
    <a href="/n8n-io/n8n/stargazers">stars</a>
  </article>
  <article class="Box-row">
    <h2><a href="/activepieces/activepieces">activepieces / activepieces</a></h2>
    <p class="col-9 color-fg-muted my-1 pr-4">Open source automation tool.</p>
  </article>
  <a href="/features/actions">GitHub Actions</a>
</main>
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

    def test_prefers_atom_alternate_link_over_replies(self):
        items = parse_feed(ATOM_WITH_REPLIES, "https://security.example/feed")

        self.assertEqual(items[0]["url"], "https://security.example/article")

    def test_uses_rss_permalink_guid_when_link_is_missing(self):
        items = parse_feed(RSS_WITH_GUID_ONLY, "https://example.com/feed")

        self.assertEqual(items[0]["url"], "https://example.com/agent-evaluation")


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

    def test_parses_github_trending_repository_names_and_descriptions(self):
        items = parse_github_trending(
            GITHUB_TRENDING_HTML,
            "https://github.com/trending?since=weekly",
        )

        self.assertEqual(
            [item["title"] for item in items],
            ["n8n-io/n8n", "activepieces/activepieces"],
        )
        self.assertEqual(items[0]["url"], "https://github.com/n8n-io/n8n")
        self.assertIn("workflow automation", items[0]["summary"])
        self.assertEqual(items[0]["published_at"], "")


class InboxTests(unittest.TestCase):
    def test_builds_a_five_item_lead_shortlist_instead_of_lane_slots(self):
        sources = []
        feeds = {}
        for index in range(6):
            source_id = f"source-{index}"
            url = f"https://{source_id}.example/feed"
            sources.append(
                {
                    "id": source_id,
                    "name": source_id,
                    "group": "official",
                    "type": "rss",
                    "url": url,
                    "weight": 5,
                    "enabled": True,
                }
            )
            feeds[url] = RSS_XML.replace(
                "GitHub Actions 보안 업데이트",
                f"AI 개발 도구 핵심 변화 {index}",
            ).replace(
                "https://example.com/actions?utm_source=rss",
                f"https://{source_id}.example/article",
            )
        config = {
            "interest_keywords": ["AI", "개발 도구"],
            "audience_lanes": {
                "broad": {"keywords": ["AI"]},
                "practical": {"keywords": ["개발 도구"]},
                "deep": {"keywords": ["보안"]},
            },
            "selection": {
                "mode": "lead_shortlist",
                "max_items": 5,
                "max_per_source": 1,
                "max_per_family": 1,
                "min_lead_score": 0,
            },
            "sources": sources,
        }

        result = build_inbox(
            config,
            fetch_text=lambda url: feeds[url],
            now=NOW,
            day_id="2026-07-12",
        )

        self.assertEqual(len(result["selected"]), 5)
        self.assertEqual(result["lead_shortlist"], result["selected"])
        self.assertTrue(all(item.get("lead_rank") for item in result["selected"]))
        self.assertTrue(all("audience_lane" not in item for item in result["selected"]))

    def test_filters_items_older_than_the_collection_age_limit(self):
        config = {
            "max_age_days": 14,
            "selection": {"max_items": 3, "max_per_source": 1},
            "sources": [
                {
                    "id": "official",
                    "name": "Official",
                    "group": "official",
                    "type": "rss",
                    "url": "https://official.example/feed",
                    "enabled": True,
                }
            ],
        }
        feed = """<rss><channel>
          <item><title>새 보안 업데이트</title><link>https://official.example/new</link><pubDate>Sun, 12 Jul 2026 07:00:00 GMT</pubDate></item>
          <item><title>오래된 보안 업데이트</title><link>https://official.example/old</link><pubDate>Mon, 01 Jun 2026 07:00:00 GMT</pubDate></item>
        </channel></rss>"""

        result = build_inbox(
            config,
            fetch_text=lambda _url: feed,
            now=NOW,
            day_id="2026-07-12",
        )

        self.assertEqual(
            [item["url"] for item in result["candidates"]],
            ["https://official.example/new"],
        )

    def test_excludes_recently_selected_url_from_new_selection(self):
        config = {
            "interest_keywords": ["AI"],
            "selection": {"max_items": 1, "max_per_source": 1},
            "sources": [
                {
                    "id": "news",
                    "name": "News",
                    "group": "official",
                    "type": "rss",
                    "url": "https://news.example/feed",
                    "enabled": True,
                }
            ],
        }
        feed = """<rss><channel>
          <item><title>AI 어제 기사</title><link>https://news.example/old?utm_source=rss</link></item>
          <item><title>AI 오늘 기사</title><link>https://news.example/new</link></item>
        </channel></rss>"""

        result = build_inbox(
            config,
            fetch_text=lambda _url: feed,
            now=NOW,
            day_id="2026-07-13",
            excluded_urls={"https://news.example/old"},
        )

        self.assertEqual([item["url"] for item in result["selected"]], ["https://news.example/new"])
        self.assertEqual(result["selection"]["recently_selected_excluded"], 1)

    def test_excludes_recent_publisher_from_shortlist_but_keeps_candidate_visible(self):
        config = {
            "interest_keywords": ["보안"],
            "selection": {"max_items": 2, "max_per_source": 1},
            "sources": [
                {
                    "id": "cloudflare",
                    "name": "Cloudflare",
                    "group": "official",
                    "type": "rss",
                    "url": "https://blog.cloudflare.com/rss/",
                    "enabled": True,
                },
                {
                    "id": "wordpress",
                    "name": "WordPress",
                    "group": "official",
                    "type": "rss",
                    "url": "https://wordpress.org/news/feed/",
                    "enabled": True,
                },
            ],
        }
        feeds = {
            "https://blog.cloudflare.com/rss/": """<rss><channel><item>
              <title>Cloudflare WAF 보안 업데이트</title>
              <link>https://blog.cloudflare.com/new-waf-rule</link>
            </item></channel></rss>""",
            "https://wordpress.org/news/feed/": """<rss><channel><item>
              <title>WordPress 플러그인 보안 업데이트</title>
              <link>https://wordpress.org/news/security-update</link>
            </item></channel></rss>""",
        }

        result = build_inbox(
            config,
            fetch_text=lambda url: feeds[url],
            now=NOW,
            day_id="2026-07-18",
            excluded_publisher_hosts={"blog.cloudflare.com"},
        )

        self.assertEqual(
            [item["source_id"] for item in result["selected"]],
            ["wordpress"],
        )
        cloudflare = next(
            item for item in result["candidates"] if item["source_id"] == "cloudflare"
        )
        self.assertTrue(cloudflare["recent_publisher"])
        self.assertEqual(result["selection"]["recent_publisher_excluded"], 1)

    def test_loads_only_processed_urls_from_recent_prior_days(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            (output / "2026-07-12.json").write_text(
                json.dumps(
                    {
                        "news": [
                            {"url": "https://news.example/kept?utm_source=rss"},
                        ],
                        "references": [{"url": "https://news.example/not-published"}],
                    }
                ),
                encoding="utf-8",
            )
            (output / "2026-06-28.json").write_text(
                json.dumps({"news": [{"url": "https://news.example/too-old"}]}),
                encoding="utf-8",
            )
            (output / "2026-07-13.json").write_text(
                json.dumps({"news": [{"url": "https://news.example/same-day"}]}),
                encoding="utf-8",
            )

            urls = load_recent_processed_urls(output, "2026-07-13", lookback_days=14)

        self.assertEqual(urls, {"https://news.example/kept"})

    def test_loads_recent_publisher_hosts_for_short_cooldown_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            for day, url in (
                ("2026-07-17", "https://blog.cloudflare.com/cache-update"),
                ("2026-07-16", "https://github.blog/changelog/actions"),
                ("2026-07-14", "https://openai.com/too-old"),
                ("2026-07-18", "https://same-day.example/ignore"),
            ):
                (output / f"{day}.json").write_text(
                    json.dumps({"news": [{"url": url}]}),
                    encoding="utf-8",
                )

            hosts = load_recent_publisher_hosts(
                output,
                "2026-07-18",
                lookback_days=3,
            )

        self.assertEqual(hosts, {"blog.cloudflare.com", "github.blog"})

    def test_review_inbox_is_not_search_indexable(self):
        page = render_inbox_html(
            {"day": "2026-07-13", "generated_at": "", "selected": [], "candidates": [], "errors": []}
        )

        self.assertIn('name="robots" content="noindex,nofollow,noarchive"', page)
        self.assertNotRegex(page, r"[ \t]+\n")

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
