"""Pure normalization, deduplication, ranking, and selection logic."""

import datetime as dt
import hashlib
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "referrer",
    "source",
}

COHERENCE_STOP_TOKENS = {
    "ai",
    "개발",
    "개발자",
    "기능",
    "관련",
    "발표",
    "방법",
    "새",
    "새로운",
    "업데이트",
    "위한",
    "이유",
    "이해하기",
    "출시",
    "공개",
    "the",
    "and",
    "for",
    "with",
}


def validate_day_id(value):
    """Return a strict YYYY-MM-DD value that is safe to use in output paths."""
    text = str(value or "").strip()
    try:
        parsed = dt.date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다.") from exc
    if parsed.isoformat() != text:
        raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다.")
    return text


def canonicalize_url(url):
    value = str(url or "").strip()
    if not value:
        return ""

    parts = urlsplit(value)
    scheme = parts.scheme.lower() or "https"
    host = parts.netloc.lower()
    if scheme not in {"http", "https"} or not host:
        return ""
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/":
        path = path.rstrip("/")

    query = []
    for key, item_value in parse_qsl(parts.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered.startswith("utm_") or lowered in TRACKING_PARAMS:
            continue
        query.append((key, item_value))
    query.sort()

    return urlunsplit((scheme, host, path, urlencode(query), ""))


def normalize_title(title):
    value = unicodedata.normalize("NFKC", str(title or "")).casefold()
    value = re.sub(r"[^0-9a-z가-힣]+", " ", value)
    return " ".join(value.split())


def _title_similarity(left, right):
    left_tokens = set(normalize_title(left).split())
    right_tokens = set(normalize_title(right).split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _coherence_tokens(item):
    return {
        token
        for token in normalize_title(item.get("title", "")).split()
        if len(token) >= 2 and token not in COHERENCE_STOP_TOKENS
    }


def _is_topic_coherent(anchor, candidate):
    anchor_topics = set(anchor.get("topic_tags") or [])
    candidate_topics = set(candidate.get("topic_tags") or [])
    if anchor_topics & candidate_topics:
        return True
    return bool(_coherence_tokens(anchor) & _coherence_tokens(candidate))


def _parse_datetime(value):
    if isinstance(value, dt.datetime):
        parsed = value
    else:
        text = str(value or "").strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = dt.datetime.fromisoformat(text)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def make_candidate(raw, source):
    canonical_url = canonicalize_url(raw.get("url"))
    title = " ".join(str(raw.get("title") or "").split())[:300]
    summary = " ".join(str(raw.get("summary") or "").split())
    published = _parse_datetime(raw.get("published_at"))
    identifier = hashlib.sha256(
        (canonical_url or normalize_title(title)).encode("utf-8")
    ).hexdigest()[:12]

    return {
        "id": identifier,
        "title": title,
        "normalized_title": normalize_title(title),
        "url": canonical_url,
        "published_at": published.isoformat() if published else "",
        "summary": summary,
        "source_id": source.get("id", ""),
        "source_family": source.get("source_family") or source.get("id", ""),
        "source_name": source.get("name") or source.get("id", ""),
        "group": source.get("group", "other"),
        "source_weight": int(source.get("weight", 0)),
        "lane_bias": dict(source.get("lane_bias") or {}),
        "requires_manual_review": bool(source.get("manual_review", False)),
        "score": 0,
        "score_reasons": [],
        "lane_scores": {},
        "topic_tags": [],
    }


def deduplicate_candidates(candidates, title_threshold=0.78):
    ranked = sorted(
        candidates,
        key=lambda item: (
            int(item.get("source_weight", 0)),
            len(item.get("summary", "")),
        ),
        reverse=True,
    )
    kept = []
    seen_urls = set()

    for item in ranked:
        url = item.get("url", "")
        if url and url in seen_urls:
            continue
        if any(
            _title_similarity(item.get("title"), existing.get("title"))
            >= title_threshold
            for existing in kept
        ):
            continue
        kept.append(item)
        if url:
            seen_urls.add(url)

    return kept


def _keyword_matches(normalized, keyword):
    keyword = str(keyword or "").strip().casefold()
    if not keyword:
        return False
    if keyword.isascii():
        pattern = r"(?<![a-z0-9]){}(?![a-z0-9])".format(re.escape(keyword))
        return re.search(pattern, normalized) is not None
    return keyword in normalized


def score_candidate(
    candidate,
    interest_keywords,
    now=None,
    audience_lanes=None,
    topic_keywords=None,
):
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    now = now.astimezone(dt.timezone.utc)

    score = int(candidate.get("source_weight", 0))
    reasons = [f"출처 가중치 {score}"]

    group = candidate.get("group")
    if group == "official":
        score += 2
        reasons.append("공식 출처")
    elif group == "research":
        score += 1
        reasons.append("연구 출처")

    published = _parse_datetime(candidate.get("published_at"))
    if published:
        age_hours = max(0.0, (now - published).total_seconds() / 3600)
        if age_hours <= 48:
            score += 3
            reasons.append("48시간 이내")
        elif age_hours <= 168:
            score += 1
            reasons.append("7일 이내")

    haystack = f"{candidate.get('title', '')} {candidate.get('summary', '')}".casefold()
    matches = [
        keyword
        for keyword in interest_keywords or []
        if _keyword_matches(haystack, keyword)
    ]
    if matches:
        score += min(2, len(matches))
        reasons.append("관심 키워드")

    if len(candidate.get("title", "")) < 12:
        score -= 1
        reasons.append("짧은 제목")

    lane_scores = {}
    lane_bias = candidate.get("lane_bias") or {}
    for lane, lane_config in (audience_lanes or {}).items():
        if isinstance(lane_config, dict):
            keywords = lane_config.get("keywords", [])
        else:
            keywords = lane_config or []
        lane_matches = [
            keyword for keyword in keywords if _keyword_matches(haystack, keyword)
        ]
        bias = int(lane_bias.get(lane, 0))
        lane_scores[lane] = min(5, len(lane_matches)) + bias

    topic_tags = []
    for topic, keywords in (topic_keywords or {}).items():
        if any(_keyword_matches(haystack, keyword) for keyword in keywords or []):
            topic_tags.append(topic)

    candidate["score"] = score
    candidate["score_reasons"] = reasons
    candidate["lane_scores"] = lane_scores
    candidate["topic_tags"] = topic_tags
    return candidate


def score_lead_candidate(candidate):
    """Add an explainable score used only to build the five-story shortlist."""
    lanes = candidate.get("lane_scores") or {}
    reasons = set(candidate.get("score_reasons") or [])
    group = candidate.get("group")
    breakdown = {
        "reader_relevance": min(5, max((int(value) for value in lanes.values()), default=0)),
        "actionability": min(5, int(lanes.get("practical", 0))),
        "explanatory_depth": min(5, int(lanes.get("deep", 0))),
        "evidence": {
            "official": 5,
            "research": 4,
            "korean_editorial": 3,
            "community": 3,
            "korean_general": 2,
        }.get(group, 2),
        "freshness": 5 if "48시간 이내" in reasons else 3 if "7일 이내" in reasons else 1,
    }
    candidate["lead_score_breakdown"] = breakdown
    candidate["lead_score"] = sum(breakdown.values())
    return candidate


def select_lead_shortlist(
    candidates,
    max_items=5,
    max_per_source=1,
    max_per_family=1,
):
    """Return the strongest diverse stories for the 09:00 editorial review."""
    ranked = sorted(
        candidates,
        key=lambda item: (
            int(item.get("lead_score", 0)),
            int(item.get("score", 0)),
            item.get("published_at", ""),
        ),
        reverse=True,
    )
    selected = []
    source_counts = {}
    family_counts = {}
    for item in ranked:
        source_id = item.get("source_id", "")
        family = item.get("source_family") or source_id
        if source_counts.get(source_id, 0) >= int(max_per_source):
            continue
        if max_per_family is not None and family_counts.get(family, 0) >= int(max_per_family):
            continue
        selected.append(item)
        source_counts[source_id] = source_counts.get(source_id, 0) + 1
        family_counts[family] = family_counts.get(family, 0) + 1
        if len(selected) >= int(max_items):
            break
    for rank, item in enumerate(selected, 1):
        item["lead_rank"] = rank
        item["selection_reason"] = "핵심뉴스 후보 {} · 점수 {}".format(
            rank, item.get("lead_score", 0)
        )
    return selected


def select_candidates(
    candidates,
    max_items=3,
    max_per_source=1,
    max_per_family=None,
    preferred_groups=None,
    audience_lanes=None,
    max_topic_items=None,
    max_research_items=1,
    require_topic_coherence=False,
):
    preferred_groups = preferred_groups or []
    ranked = sorted(
        candidates,
        key=lambda item: (item.get("score", 0), item.get("published_at", "")),
        reverse=True,
    )
    selected = []
    source_counts = {}
    family_counts = {}

    def family_key(item):
        return item.get("source_family") or item.get("source_id", "")

    def family_is_full(item):
        if max_per_family is None:
            return False
        return family_counts.get(family_key(item), 0) >= int(max_per_family)

    def record_source(item):
        source_id = item.get("source_id", "")
        source_counts[source_id] = source_counts.get(source_id, 0) + 1
        family = family_key(item)
        family_counts[family] = family_counts.get(family, 0) + 1

    if audience_lanes:
        topic_limits = max_topic_items or {}
        topic_counts = {}
        research_count = 0

        def can_add(item, *, source_limit=True):
            source_id = item.get("source_id", "")
            if source_limit and source_counts.get(source_id, 0) >= max_per_source:
                return False
            if family_is_full(item):
                return False
            for topic in item.get("topic_tags", []):
                limit = topic_limits.get(topic)
                if limit is not None and topic_counts.get(topic, 0) >= int(limit):
                    return False
            if (
                max_research_items is not None
                and item.get("group") == "research"
                and research_count >= int(max_research_items)
            ):
                return False
            return True

        def add_for_lane(item, lane):
            nonlocal research_count
            is_followup = bool(selected)
            selected.append(item)
            record_source(item)
            for topic in item.get("topic_tags", []):
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            if item.get("group") == "research":
                research_count += 1
            item["audience_lane"] = lane
            lane_score = int((item.get("lane_scores") or {}).get(lane, 0))
            reason = f"{lane} 독자 적합도 {lane_score}"
            if require_topic_coherence and is_followup:
                reason += " · 주제 연결"
            item["selection_reason"] = reason
            return True

        for lane in list(audience_lanes)[:max_items]:
            lane_ranked = sorted(
                (item for item in ranked if item not in selected),
                key=lambda item: (
                    int((item.get("lane_scores") or {}).get(lane, 0)),
                    item.get("score", 0),
                    item.get("published_at", ""),
                ),
                reverse=True,
            )
            passes = (
                # First keep all diversity limits. A positive lane match is ideal.
                (True, True),
                # If a lane has no direct keyword match, use the best diverse item.
                (False, True),
                # The source cap is soft; topic and research caps stay hard.
                (True, False),
                (False, False),
            )
            for positive_only, source_limit in passes:
                chosen = next(
                    (
                        item
                        for item in lane_ranked
                        if (
                            not positive_only
                            or int((item.get("lane_scores") or {}).get(lane, 0)) > 0
                        )
                        and can_add(item, source_limit=source_limit)
                        and (
                            not require_topic_coherence
                            or not selected
                            or _is_topic_coherent(selected[0], item)
                        )
                    ),
                    None,
                )
                if chosen is not None:
                    add_for_lane(chosen, lane)
                    break

        for item in ranked:
            if len(selected) >= max_items:
                break
            if (
                item not in selected
                and can_add(item)
                and (
                    not require_topic_coherence
                    or not selected
                    or _is_topic_coherent(selected[0], item)
                )
            ):
                add_for_lane(item, "additional")
        return selected

    def add(item):
        source_id = item.get("source_id", "")
        if source_counts.get(source_id, 0) >= max_per_source or family_is_full(item):
            return False
        selected.append(item)
        record_source(item)
        return True

    for group in preferred_groups:
        if len(selected) >= max_items:
            break
        for item in ranked:
            if item in selected or item.get("group") != group:
                continue
            if add(item):
                break

    for item in ranked:
        if len(selected) >= max_items:
            break
        if item not in selected:
            add(item)

    return selected
