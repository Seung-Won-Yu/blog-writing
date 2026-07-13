import datetime as dt
import unittest

from news_pipeline import (
    canonicalize_url,
    deduplicate_candidates,
    make_candidate,
    score_candidate,
    select_candidates,
    validate_day_id,
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

    def test_validates_strict_iso_day_ids_for_output_paths(self):
        self.assertEqual(validate_day_id("2026-07-13"), "2026-07-13")
        for invalid in ("../../main", "2026-7-13", "2026-02-30", ""):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    validate_day_id(invalid)


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

    def test_scores_reader_impact_above_a_generic_ai_announcement(self):
        broad = {
            "keywords": ["무료", "요금", "개인정보", "사진", "일자리"],
        }
        practical = {"keywords": ["GitHub", "VS Code", "업데이트", "도구"]}
        deep = {"keywords": ["API", "데이터베이스", "성능", "논문"]}
        generic = make_candidate(
            raw("OpenAI 새 AI 모델 발표", "https://official.example/model"),
            source("official-ai", "official", weight=5),
        )
        reader_impact = make_candidate(
            raw(
                "인스타 사진 AI 활용, 개인정보 반발로 자동 연동 중단",
                "https://news.example/privacy",
            ),
            source("korean-news", "korean_general", weight=3),
        )

        for item in (generic, reader_impact):
            score_candidate(
                item,
                ["AI"],
                now=NOW,
                audience_lanes={
                    "broad": broad,
                    "practical": practical,
                    "deep": deep,
                },
                topic_keywords={"ai": ["AI", "OpenAI"]},
            )

        self.assertGreater(
            reader_impact["lane_scores"]["broad"],
            generic["lane_scores"]["broad"],
        )
        self.assertIn("ai", reader_impact["topic_tags"])


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

    def test_selects_broad_practical_and_deep_lanes_without_research_overload(self):
        items = []

        def candidate(title, source_id, group, score, lanes, topics=()):
            item = make_candidate(
                raw(title, f"https://{source_id}.example/{len(items)}"),
                source(source_id, group, weight=3),
            )
            item["score"] = score
            item["lane_scores"] = lanes
            item["topic_tags"] = list(topics)
            items.append(item)

        candidate(
            "인스타 사진 AI 활용 중단",
            "aitimes",
            "korean_general",
            10,
            {"broad": 5, "practical": 0, "deep": 0},
            ("ai",),
        )
        candidate(
            "GitHub pull request 대시보드 공개",
            "github",
            "official",
            9,
            {"broad": 0, "practical": 5, "deep": 1},
        )
        candidate(
            "Postgres 19 그래프 쿼리 이해하기",
            "geeknews",
            "community",
            7,
            {"broad": 0, "practical": 1, "deep": 5},
        )
        candidate(
            "새 AI 모델 세부 기술 발표",
            "openai",
            "official",
            30,
            {"broad": 0, "practical": 1, "deep": 3},
            ("ai",),
        )
        candidate(
            "VEXAIoT 에이전트 논문",
            "arxiv",
            "research",
            25,
            {"broad": 0, "practical": 0, "deep": 4},
            ("ai",),
        )

        selected = select_candidates(
            items,
            max_items=3,
            max_per_source=1,
            audience_lanes=["broad", "practical", "deep"],
            max_topic_items={"ai": 2},
            max_research_items=1,
        )

        self.assertEqual(
            [item["audience_lane"] for item in selected],
            ["broad", "practical", "deep"],
        )
        self.assertEqual(
            [item["source_id"] for item in selected],
            ["aitimes", "github", "geeknews"],
        )
        self.assertNotIn("arxiv", [item["source_id"] for item in selected])

    def test_never_relaxes_hard_topic_or_research_caps_to_fill_slots(self):
        items = []

        def candidate(title, source_id, group, lanes, topics=()):
            item = make_candidate(
                raw(title, f"https://{source_id}.example/{len(items)}"),
                source(source_id, group, weight=3),
            )
            item["score"] = 20 - len(items)
            item["lane_scores"] = lanes
            item["topic_tags"] = list(topics)
            items.append(item)

        candidate(
            "AI 생활 서비스 변화",
            "general-ai",
            "korean_general",
            {"broad": 5, "practical": 0, "deep": 0},
            ("ai",),
        )
        candidate(
            "AI 개발 도구 업데이트",
            "tool-ai",
            "official",
            {"broad": 0, "practical": 5, "deep": 0},
            ("ai",),
        )
        for index in range(3):
            candidate(
                f"AI 연구 논문 {index}",
                f"arxiv-{index}",
                "research",
                {"broad": 3, "practical": 3, "deep": 5},
                ("ai",),
            )

        selected = select_candidates(
            items,
            max_items=3,
            max_per_source=1,
            audience_lanes=["broad", "practical", "deep"],
            max_topic_items={"ai": 2},
            max_research_items=0,
        )

        self.assertEqual(len(selected), 2)
        self.assertEqual(sum("ai" in item["topic_tags"] for item in selected), 2)
        self.assertFalse(any(item["group"] == "research" for item in selected))

    def test_topic_coherence_does_not_force_unrelated_lane_articles(self):
        items = []

        def candidate(title, source_id, score, lanes, topics=()):
            item = make_candidate(
                raw(title, f"https://{source_id}.example/{len(items)}"),
                source(source_id, "official", weight=3),
            )
            item["score"] = score
            item["lane_scores"] = lanes
            item["topic_tags"] = list(topics)
            items.append(item)

        candidate(
            "인스타 사진 AI 활용 중단",
            "aitimes",
            10,
            {"broad": 5, "practical": 0, "deep": 0},
            ("ai",),
        )
        candidate(
            "GitHub pull request 대시보드 공개",
            "github",
            9,
            {"broad": 0, "practical": 5, "deep": 1},
        )
        candidate(
            "Postgres 19 그래프 쿼리 이해하기",
            "postgres",
            8,
            {"broad": 0, "practical": 1, "deep": 5},
        )

        selected = select_candidates(
            items,
            max_items=3,
            audience_lanes=["broad", "practical", "deep"],
            require_topic_coherence=True,
        )

        self.assertEqual([item["source_id"] for item in selected], ["aitimes"])

    def test_topic_coherence_keeps_related_general_and_developer_angles(self):
        items = []

        def candidate(title, source_id, lanes):
            item = make_candidate(
                raw(title, f"https://{source_id}.example/{len(items)}"),
                source(source_id, "official", weight=3),
            )
            item["score"] = 10 - len(items)
            item["lane_scores"] = lanes
            item["topic_tags"] = ["ai"]
            items.append(item)

        candidate("인스타 사진 AI 활용 중단", "aitimes", {"broad": 5, "practical": 0, "deep": 0})
        candidate("AI 코딩 도구 검증 기능", "tool", {"broad": 0, "practical": 5, "deep": 1})
        candidate("AI 추론 비용의 구조", "deep", {"broad": 0, "practical": 1, "deep": 5})

        selected = select_candidates(
            items,
            max_items=3,
            audience_lanes=["broad", "practical", "deep"],
            max_topic_items={"ai": 3},
            require_topic_coherence=True,
        )

        self.assertEqual(
            [item["audience_lane"] for item in selected],
            ["broad", "practical", "deep"],
        )
        self.assertTrue(all("주제 연결" in item["selection_reason"] for item in selected[1:]))


if __name__ == "__main__":
    unittest.main()
