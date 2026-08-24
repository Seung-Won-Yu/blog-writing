import datetime as dt
import tempfile
import unittest
from pathlib import Path

from blog_pipeline.collection.analyze_search_performance import (
    analyze_rows,
    build_report,
    load_csv_rows,
    render_markdown,
)


class SearchPerformanceAnalysisTests(unittest.TestCase):
    def test_prioritizes_refresh_when_impressions_drop_materially(self):
        opportunities = analyze_rows(
            [
                {
                    "query": "spring transaction rollback",
                    "page_url": "https://won0322.tistory.com/150",
                    "current_impressions": 40,
                    "current_clicks": 2,
                    "previous_impressions": 100,
                    "previous_clicks": 8,
                }
            ]
        )

        self.assertEqual(opportunities[0]["action"], "refresh_existing")
        self.assertEqual(opportunities[0]["impression_change_pct"], -60.0)
        self.assertEqual(opportunities[0]["click_change_pct"], -75.0)

    def test_recommends_retitle_for_visible_page_with_no_clicks(self):
        opportunities = analyze_rows(
            [
                {
                    "query": "github copilot limit",
                    "page_url": "https://won0322.tistory.com/145",
                    "current_impressions": 45,
                    "current_clicks": 0,
                    "previous_impressions": 15,
                    "previous_clicks": 0,
                }
            ]
        )

        self.assertEqual(opportunities[0]["action"], "retitle_existing")
        self.assertIn("클릭 0", opportunities[0]["reason"])

    def test_omits_healthy_or_low_volume_rows(self):
        opportunities = analyze_rows(
            [
                {
                    "query": "healthy query",
                    "page_url": "https://won0322.tistory.com/151",
                    "current_impressions": 100,
                    "current_clicks": 12,
                    "previous_impressions": 90,
                    "previous_clicks": 10,
                },
                {
                    "query": "tiny query",
                    "page_url": "https://won0322.tistory.com/152",
                    "current_impressions": 3,
                    "current_clicks": 0,
                    "previous_impressions": 2,
                    "previous_clicks": 0,
                },
            ]
        )

        self.assertEqual(opportunities, [])

    def test_detects_two_pages_competing_for_the_same_query(self):
        opportunities = analyze_rows(
            [
                {
                    "query": "java array example",
                    "page_url": "https://won0322.tistory.com/71",
                    "current_impressions": 30,
                    "current_clicks": 2,
                    "previous_impressions": 25,
                    "previous_clicks": 2,
                },
                {
                    "query": "java array example",
                    "page_url": "https://won0322.tistory.com/72",
                    "current_impressions": 25,
                    "current_clicks": 1,
                    "previous_impressions": 20,
                    "previous_clicks": 1,
                },
            ]
        )

        self.assertEqual(len(opportunities), 1)
        self.assertEqual(opportunities[0]["action"], "merge_existing")
        self.assertEqual(
            opportunities[0]["page_url"], "https://won0322.tistory.com/71"
        )
        self.assertEqual(len(opportunities[0]["competing_pages"]), 2)

    def test_loads_korean_csv_headers_and_builds_dated_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "performance.csv"
            path.write_text(
                "검색어,페이지,최근 노출,최근 클릭,이전 노출,이전 클릭\n"
                "postgresql backup,https://won0322.tistory.com/160,30,0,10,0\n",
                encoding="utf-8-sig",
            )

            rows = load_csv_rows(path)
            report = build_report(
                rows,
                updated_at=dt.datetime(
                    2026, 8, 24, 18, 0, tzinfo=dt.timezone(dt.timedelta(hours=9))
                ),
            )

        self.assertEqual(report["schema_version"], 2)
        self.assertEqual(report["updated_at"], "2026-08-24T18:00:00+09:00")
        self.assertEqual(report["opportunities"][0]["action"], "retitle_existing")
        self.assertIn("내부 운영 휴리스틱", report["policy_note"])
        markdown = render_markdown(report)
        self.assertIn("기존 글 성장 큐", markdown)
        self.assertIn("postgresql backup", markdown)
        self.assertIn("retitle_existing", markdown)


if __name__ == "__main__":
    unittest.main()
