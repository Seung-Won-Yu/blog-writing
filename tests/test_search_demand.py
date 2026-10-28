import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest

from blog_pipeline.collection.search_demand import (
    demand_report, load_snapshot, observed_queries, source_demand_reasons,
)
from blog_pipeline.publishing.draft_identity import resolve_draft_identity
from blog_pipeline.publishing.editorial_quality import _reference_reasons


def snapshot():
    return {
        "source": "Google Search Console", "property": "https://won0322.tistory.com/",
        "observed_at": "2026-10-28T09:00:00+09:00", "search_type": "web",
        "metric_scope": "query",
        "current_period": {"start": "2026-09-28", "end": "2026-10-25"},
        "previous_period": {"start": "2026-08-31", "end": "2026-09-27"},
        "queries": [
            {"query": "im-not-ai 사용법", "current_clicks": 2, "previous_clicks": 5,
             "current_impressions": 77, "previous_impressions": 88},
            {"query": "gpt 도구 선택", "current_clicks": 0, "previous_clicks": 0,
             "current_impressions": 100, "previous_impressions": 0},
        ],
    }


class SearchDemandTests(unittest.TestCase):
    def setUp(self):
        self.day = dt.date(2026, 10, 30)

    def test_actual_clicked_queries_lead_impression_only_queries(self):
        rows = observed_queries(snapshot(), self.day)
        self.assertEqual(rows[0]["query"], "im-not-ai 사용법")
        self.assertNotIn("page_url", rows[0])

    def test_query_scope_cannot_be_replaced_with_page_totals(self):
        data = snapshot(); data["metric_scope"] = "page"
        with self.assertRaises(ValueError):
            observed_queries(data, self.day)

    def test_stale_future_and_unmatched_periods_are_rejected(self):
        for observed, end in (("2026-08-28T09:00:00+09:00", "2026-10-25"),
                              ("2026-11-01T09:00:00+09:00", "2026-10-25"),
                              ("2026-10-28T09:00:00+09:00", "2026-10-24")):
            with self.subTest(observed=observed, end=end):
                data = snapshot(); data["observed_at"] = observed
                data["current_period"]["end"] = end
                with self.assertRaises(ValueError):
                    observed_queries(data, self.day)
        # Merely updating observed_at cannot make old reporting periods fresh.
        with self.assertRaises(ValueError):
            data = snapshot(); data["observed_at"] = "2026-12-01T09:00:00+09:00"
            observed_queries(data, dt.date(2026, 12, 1))

    def test_invalid_or_duplicate_metrics_are_not_silently_used(self):
        for metric in (-1, "77", True):
            data = snapshot(); data["queries"][0]["current_impressions"] = metric
            with self.assertRaises(ValueError):
                observed_queries(data, self.day)
        data = snapshot(); data["queries"].append(copy.deepcopy(data["queries"][0]))
        with self.assertRaises(ValueError):
            observed_queries(data, self.day)

    def test_navigation_and_no_current_impressions_are_not_demand(self):
        data = snapshot()
        data["queries"][0]["query"] = "site:won0322.tistory.com"
        data["queries"][1]["current_impressions"] = 0
        self.assertEqual(demand_report(data, self.day)["status"], "NO_OBSERVED_QUERIES")

    def test_refresh_reminder_does_not_discard_a_usable_cache(self):
        report = demand_report(snapshot(), dt.date(2026, 11, 4))
        self.assertEqual(report["status"], "READY")
        self.assertTrue(report["refresh_due"])

    def test_future_article_must_reference_a_real_archived_query(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = "data/search_demand/2026-10-28.json"
            path = root / reference; path.parent.mkdir(parents=True)
            path.write_text(json.dumps(snapshot()))
            source = {"editorial": {"search_demand": {
                "snapshot": reference, "query": "im-not-ai 사용법",
                "relation": "distinct_followup", "existing_page_urls": [],
                "intent_gap": "기존 설치 안내와 다른 실행 결과 해석 문제인지 실제 본문을 대조한다.",
            }}}
            identity = resolve_draft_identity("2026-10-30-automation")
            self.assertEqual(source_demand_reasons(source, identity, root=root), [])
            source["editorial"]["search_demand"]["query"] = "invented popular query"
            self.assertEqual(source_demand_reasons(source, identity, root=root),
                             ["quality_observed_search_demand"])
            self.assertEqual(source_demand_reasons({}, identity, root=root),
                             ["quality_observed_search_demand"])

    def test_archive_path_and_historical_articles_are_protected(self):
        for reference in ("/etc/passwd", "data/search_demand/../secret.json", "config/search_opportunities.json"):
            with self.assertRaises(ValueError):
                load_snapshot(reference)
        self.assertEqual(source_demand_reasons({}, resolve_draft_identity("2026-10-28")), [])


class OfficialReferenceComparisonTests(unittest.TestCase):
    def source(self):
        return {
            "editorial": {"original_value": {"proof_method": "document_comparison"}},
            "news": [{"title_kr": "비교", "source": "공식 문서", "published_at": "2026-10-23T00:00:00Z",
                      "url": "https://developers.cloudflare.com/change", "blurb_kr": "차이를 확인한다",
                      "references": [
                          {"title": "빌드", "url": "https://developers.cloudflare.com/build", "kind": "official", "publisher": "Cloudflare"},
                          {"title": "변경", "url": "https://developers.cloudflare.com/change", "kind": "official", "publisher": "Cloudflare"},
                          {"title": "설치", "url": "https://docs.npmjs.com/cli", "kind": "official", "publisher": "npm"},
                      ]}],
        }

    def test_cross_vendor_manual_comparison_keeps_official_labels(self):
        self.assertEqual(_reference_reasons(self.source()), [])

    def test_same_vendor_subdomains_or_unsupported_proof_are_not_an_exception(self):
        data = self.source()
        data["news"][0]["references"][2]["url"] = "https://docs.cloudflare.com/npm"
        self.assertEqual(_reference_reasons(data), ["quality_reference_mix"])
        data = self.source(); data["editorial"]["original_value"]["proof_method"] = "hands_on_test"
        self.assertEqual(_reference_reasons(data), ["quality_reference_mix"])


if __name__ == "__main__":
    unittest.main()
