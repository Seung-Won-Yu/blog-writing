import datetime as dt
import unittest

from news_pipeline import (
    canonicalize_url,
    deduplicate_candidates,
    make_candidate,
    score_candidate,
    select_candidates,
)


NOW = dt.datetime(2026, 7, 12, 9, 0, tzinfo=dt.timezone.utc)


def source(source_id, group, weight=3, manual_review=False):
    return {
        "id": source_id,
        "name": source_id,
        "group": group,
        "weight": weight,
        "manual_review": manual_review,
    }


def raw(title, url, published_at="2026-07-12T07:00:00+00:00", summary=""):
    return {
        "title": title,
        "url": url,
        "published_at": published_at,
        "summary": summary,
    }


class CanonicalUrlTests(unittest.TestCase):
    def test_removes_tracking_parameters_and_fragments(self):
        value = canonicalize_url(
            "HTTPS://Example.com/news/item/?utm_source=rss&ref=home&id=7#section"
        )

        self.assertEqual(value, "https://example.com/news/item?id=7")


class DeduplicationTests(unittest.TestCase):
    def test_deduplicates_same_canonical_url(self):
        first = make_candidate(
            raw("OpenAI 새 모델 발표", "https://example.com/post?utm_source=rss"),
            source("official-a", "official", weight=5),
        )
        second = make_candidate(
            raw("OpenAI 새 모델 발표", "https://example.com/post#top"),
            source("community-a", "community"),
        )

        result = deduplicate_candidates([first, second])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_id"], "official-a")

    def test_deduplicates_nearly_identical_titles(self):
        first = make_candidate(
            raw("OpenAI GPT-5.6 출시: 개발자 핵심 변화", "https://a.example/1"),
            source("official-a", "official", weight=5),
        )
        second = make_candidate(
            raw("OpenAI GPT 5.6 출시, 개발자 핵심 변화", "https://b.example/2"),
            source("community-a", "community"),
        )

        result = deduplicate_candidates([first, second])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_id"], "official-a")


class RankingTests(unittest.TestCase):
    def test_official_recent_keyword_item_scores_higher(self):
        official = make_candidate(
            raw("GitHub Actions AI 보안 기능 출시", "https://official.example/1"),
            source("official-a", "official", weight=5),
        )
        old_community = make_candidate(
            raw(
                "일반 개발 이야기",
                "https://community.example/1",
                published_at="2026-06-20T07:00:00+00:00",
            ),
            source("community-a", "community", weight=2),
        )

        score_candidate(official, ["AI", "GitHub Actions"], now=NOW)
        score_candidate(old_community, ["AI", "GitHub Actions"], now=NOW)

        self.assertGreater(official["score"], old_community["score"])
        self.assertIn("관심 키워드", official["score_reasons"])
        self.assertIn("48시간 이내", official["score_reasons"])

    def test_manual_review_flag_is_preserved(self):
        item = make_candidate(
            raw("현업 AI 트렌드", "https://yozm.example/1"),
            source("yozmit", "korean_editorial", manual_review=True),
        )

        self.assertTrue(item["requires_manual_review"])


class SelectionTests(unittest.TestCase):
    def test_prefers_group_diversity_and_limits_one_per_source(self):
        items = []
        for title, url, source_config, score in [
            ("공식 발표 A", "https://official.example/a", source("official-a", "official", 5), 10),
            ("공식 발표 B", "https://official.example/b", source("official-a", "official", 5), 9),
            ("개발자 반응", "https://community.example/a", source("community-a", "community", 3), 8),
            ("국내 현업 관점", "https://yozm.example/a", source("yozmit", "korean_editorial", 3, True), 7),
            ("AI 논문", "https://arxiv.example/a", source("arxiv", "research", 4, True), 6),
        ]:
            item = make_candidate(raw(title, url), source_config)
            item["score"] = score
            items.append(item)

        selected = select_candidates(
            items,
            max_items=3,
            max_per_source=1,
            preferred_groups=["official", "community", "korean_editorial", "research"],
        )

        self.assertEqual(
            [item["group"] for item in selected],
            ["official", "community", "korean_editorial"],
        )
        self.assertEqual(len({item["source_id"] for item in selected}), 3)


if __name__ == "__main__":
    unittest.main()
