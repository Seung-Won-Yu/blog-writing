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
    title = " ".join(str(raw.get("title") or "").split())
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
        "source_name": source.get("name") or source.get("id", ""),
        "group": source.get("group", "other"),
        "source_weight": int(source.get("weight", 0)),
        "requires_manual_review": bool(source.get("manual_review", False)),
        "score": 0,
        "score_reasons": [],
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


def score_candidate(candidate, interest_keywords, now=None):
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
        if str(keyword).strip() and str(keyword).casefold() in haystack
    ]
    if matches:
        score += min(2, len(matches))
        reasons.append("관심 키워드")

    if len(candidate.get("title", "")) < 12:
        score -= 1
        reasons.append("짧은 제목")

    candidate["score"] = score
    candidate["score_reasons"] = reasons
    return candidate


def select_candidates(
    candidates,
    max_items=3,
    max_per_source=1,
    preferred_groups=None,
):
    preferred_groups = preferred_groups or []
    ranked = sorted(
        candidates,
        key=lambda item: (item.get("score", 0), item.get("published_at", "")),
        reverse=True,
    )
    selected = []
    source_counts = {}

    def add(item):
        source_id = item.get("source_id", "")
        if source_counts.get(source_id, 0) >= max_per_source:
            return False
        selected.append(item)
        source_counts[source_id] = source_counts.get(source_id, 0) + 1
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
