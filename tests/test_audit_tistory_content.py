import datetime as dt
import unittest

from blog_pipeline.collection.audit_tistory_content import (
    audit_posts,
    build_report,
    editorial_reasons,
    parse_post_html,
    render_markdown,
)


def article_html(*, title, category="개발 가이드", body=""):
    return f"""<!doctype html>
<html><head><title>{title}</title></head>
<body>
<script>window.T.entryInfo = {{"categoryLabel":"{category}"}};</script>
<div class="tt_article_useless_p_margin contents_style">{body}</div>
</body></html>"""


class TistoryContentAuditTests(unittest.TestCase):
    def test_parses_article_signals_inside_tistory_body_only(self):
        html = article_html(
            title="직접 실험한 API 재시도",
            body=(
                "<h2>문제</h2><p>같은 요청이 두 번 처리됐다.</p>"
                "<p>재현 절차와 결과를 기록했다.</p>"
                "<pre><code>print('retry')</code></pre>"
                '<img src="/result.webp" alt="결과">'
                "<table><tr><td>1회</td></tr></table>"
                '<a href="https://docs.python.org/3/">공식 문서</a>'
                '<a href="/11">다음 글</a>'
            ),
        )

        post = parse_post_html(
            html,
            post_id=10,
            url="https://won0322.tistory.com/10",
        )

        self.assertEqual(post["title"], "직접 실험한 API 재시도")
        self.assertEqual(post["category"], "개발 가이드")
        self.assertEqual(post["paragraphs"], 2)
        self.assertEqual(post["headings"], 1)
        self.assertEqual(post["images"], 1)
        self.assertEqual(post["tables"], 1)
        self.assertEqual(post["external_links"], 1)
        self.assertEqual(post["internal_post_ids"], [11])
        self.assertEqual(post["page_ad_units"], 0)
        self.assertGreater(post["code_chars"], 0)
        self.assertFalse(post["legacy_auto_digest"])

    def test_flags_question_dump_and_link_list_as_high_risk(self):
        post = {
            "title": "인공지능 활용능력 시험문제 100개",
            "chars": 900,
            "paragraphs": 2,
            "headings": 0,
            "images": 0,
            "tables": 0,
            "code_chars": 0,
            "external_links": 12,
        }

        reasons = editorial_reasons(post)

        self.assertIn("question_dump", reasons)
        self.assertIn("link_list", reasons)
        self.assertIn("thin_text", reasons)

    def test_flags_legacy_automatic_digest(self):
        html = article_html(
            title="[개발 뉴스] 여러 소식 핵심 정리",
            body="<p>자동 생성 데일리 다이제스트</p>"
            "<p>본문은 핵심 내용 요약과 학습용 문제로 구성했습니다.</p>",
        )
        post = parse_post_html(
            html,
            post_id=108,
            url="https://won0322.tistory.com/108",
        )

        audited = audit_posts([post])

        self.assertEqual(audited[0]["risk"], "high")
        self.assertIn("legacy_auto_digest", audited[0]["reasons"])

    def test_explained_code_tutorial_is_not_flagged_for_code_ratio_alone(self):
        post = {
            "title": "Java 배열 문제 풀이",
            "chars": 5000,
            "paragraphs": 20,
            "headings": 10,
            "images": 1,
            "tables": 1,
            "code_chars": 3500,
            "external_links": 5,
        }

        self.assertNotIn("code_heavy", editorial_reasons(post))

    def test_duplicate_normalized_titles_are_high_risk(self):
        base = {
            "category": "프로젝트",
            "chars": 4000,
            "paragraphs": 10,
            "headings": 5,
            "images": 1,
            "tables": 1,
            "code_chars": 0,
            "external_links": 2,
            "article_found": True,
        }
        posts = [
            {**base, "id": 1, "url": "https://example.com/1", "title": "프로젝트 정리"},
            {**base, "id": 2, "url": "https://example.com/2", "title": "프로젝트-정리"},
        ]

        audited = audit_posts(posts)

        self.assertTrue(all(item["risk"] == "high" for item in audited))
        self.assertTrue(all("duplicate_title" in item["reasons"] for item in audited))

    def test_flags_internal_links_to_non_public_posts(self):
        base = {
            "title": "공개 글",
            "category": "가이드",
            "chars": 3000,
            "paragraphs": 10,
            "headings": 5,
            "images": 1,
            "tables": 1,
            "code_chars": 0,
            "external_links": 2,
            "article_found": True,
            "legacy_auto_digest": False,
            "question_items": 0,
        }
        posts = [
            {
                **base,
                "id": 10,
                "url": "https://won0322.tistory.com/10",
                "internal_post_ids": [11, 12],
            },
            {
                **base,
                "id": 11,
                "url": "https://won0322.tistory.com/11",
                "internal_post_ids": [],
            },
        ]

        audited = {item["id"]: item for item in audit_posts(posts)}

        self.assertEqual(audited[10]["broken_internal_links"], [12])
        self.assertIn("broken_internal_links", audited[10]["reasons"])

    def test_report_states_thresholds_are_not_google_rules(self):
        report = build_report(
            [],
            generated_at=dt.datetime(2026, 7, 28, 12, 0, tzinfo=dt.timezone.utc),
        )
        markdown = render_markdown(report)

        self.assertIn("내부 휴리스틱", report["policy_note"])
        self.assertIn("Google AdSense의 글자 수·게시물 수 기준이 아니다", markdown)

    def test_counts_page_level_ad_units_separately_from_content_risk(self):
        html = article_html(
            title="광고 레이아웃 점검",
            body="<p>충분한 본문</p>",
        ).replace(
            "<body>",
            '<body><ins class="adsbygoogle"></ins>'
            '<div class="revenue_unit_item adfit"></div>',
        )
        post = parse_post_html(
            html,
            post_id=20,
            url="https://won0322.tistory.com/20",
        )
        report = build_report([post])

        self.assertEqual(post["page_ad_units"], 2)
        self.assertEqual(report["layout"]["maximum_ad_units_on_page"], 2)


if __name__ == "__main__":
    unittest.main()
