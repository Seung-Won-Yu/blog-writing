"""Collect and rank public sources for the Saturday automation experiment."""

import argparse
import datetime as dt
import json
import re
from collections import Counter
from html import escape
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from .collect_news import build_inbox, fetch_url
from .news_pipeline import canonicalize_url, normalize_title, validate_day_id


AUTOMATION_TOPIC_STOP_WORDS = {
    "ai",
    "automation",
    "github",
    "guide",
    "how",
    "test",
    "to",
    "workflow",
    "설정",
    "사용법",
    "자동화",
    "테스트",
    "워크플로",
}
PRODUCT_HOST_FINGERPRINTS = {
    "blog.n8n.io": "product:n8n",
    "n8n.io": "product:n8n",
}


def _keyword_matches(text, keyword):
    normalized = str(text or "").casefold()
    keyword = str(keyword or "").strip().casefold()
    if not keyword:
        return False
    if keyword.isascii():
        return re.search(
            r"(?<![a-z0-9]){}(?![a-z0-9])".format(re.escape(keyword)),
            normalized,
        ) is not None
    return keyword in normalized


def _criterion_score(text, spec, bias=0):
    weight = max(0, int(spec.get("weight", 0)))
    target = max(1, int(spec.get("target_matches", 2)))
    matches = [
        str(keyword)
        for keyword in spec.get("keywords", [])
        if _keyword_matches(text, keyword)
    ]
    signal_score = round(weight * min(len(matches), target) / target)
    return min(weight, max(0, int(bias)) + signal_score), matches


def score_automation_candidate(candidate, criteria, source=None):
    """Attach the five Saturday editorial criterion scores to a candidate."""
    source = source or {}
    text = "{} {}".format(candidate.get("title", ""), candidate.get("summary", ""))
    biases = source.get("criteria_bias") or {}
    scores = {}
    reasons = []

    for key, spec in criteria.items():
        value, _ = _criterion_score(text, spec, biases.get(key, 0))
        scores[key] = value
        if value:
            label = str(spec.get("label") or key)
            reasons.append("{} {}/{}".format(label, value, int(spec.get("weight", 0))))

    candidate["provisional_score"] = sum(scores.values())
    candidate["score"] = candidate["provisional_score"]
    candidate["score_breakdown"] = scores
    candidate["score_reasons"] = reasons
    candidate["experiment_type"] = str(
        source.get("experiment_type") or "직접 실행 실험기"
    )
    candidate["verification_hint"] = str(source.get("verification_hint") or "")
    candidate["verification_status"] = "metadata_only"
    candidate["execution_status"] = "not_run"
    return candidate


def _prepare_candidate(candidate, source):
    prefix = str(source.get("candidate_prefix") or "").strip()
    title = str(candidate.get("title") or "").strip()
    if prefix and not title.casefold().startswith(prefix.casefold()):
        candidate["title"] = "{} {}".format(prefix, title)
    candidate["repository"] = str(source.get("repository") or "")
    if source.get("type") == "github_trending":
        candidate["repository"] = str(candidate.get("title") or "")
    candidate["source_kind"] = str(source.get("source_kind") or source.get("type") or "")
    summary_limit = max(0, int(source.get("max_summary_chars", 1200)))
    if summary_limit:
        candidate["summary"] = str(candidate.get("summary") or "")[:summary_limit]
    return candidate


def select_automation_candidates(candidates, selection):
    selected = []
    source_counts = Counter()
    family_counts = Counter()
    max_items = max(0, int(selection.get("max_items", 8)))
    max_per_source = max(1, int(selection.get("max_per_source", 2)))
    family_limit = selection.get("max_per_family", 2)
    max_per_family = None if family_limit is None else max(1, int(family_limit))
    minimum = int(selection.get("min_score", 0))

    def can_add(candidate):
        if int(candidate.get("provisional_score", 0)) < minimum:
            return False
        source_id = candidate.get("source_id", "")
        family = candidate.get("source_family") or source_id
        if source_counts[source_id] >= max_per_source:
            return False
        if max_per_family is not None and family_counts[family] >= max_per_family:
            return False
        return candidate not in selected

    def add(candidate):
        if len(selected) >= max_items or not can_add(candidate):
            return False
        source_id = candidate.get("source_id", "")
        family = candidate.get("source_family") or source_id
        selected.append(candidate)
        source_counts[source_id] += 1
        family_counts[family] += 1
        return True

    for source_kind in selection.get("preferred_source_kinds", []):
        match = next(
            (
                candidate
                for candidate in candidates
                if candidate.get("source_kind") == source_kind and can_add(candidate)
            ),
            None,
        )
        if match is not None:
            add(match)
        if len(selected) >= max_items:
            break

    for candidate in candidates:
        if len(selected) >= max_items:
            break
        add(candidate)
    selected.sort(key=lambda item: int(item.get("provisional_score", 0)), reverse=True)
    return selected


def build_automation_inbox(
    config,
    fetch_text,
    now=None,
    day_id=None,
    excluded_urls=None,
    excluded_fingerprints=None,
    excluded_queries=None,
):
    """Collect public candidates and rank them for a reproducible experiment."""
    now = now or dt.datetime.now(dt.timezone.utc)
    base_config = dict(config)
    base_config["selection"] = {
        "max_items": 10000,
        "max_per_source": 10000,
        "max_per_family": None,
    }
    base = build_inbox(
        base_config,
        fetch_text=fetch_text,
        now=now,
        day_id=day_id,
    )
    source_by_id = {
        str(source.get("id") or ""): source for source in config.get("sources", [])
    }
    criteria = config.get("criteria") or {}
    candidates = []
    for candidate in base.get("candidates", []):
        source = source_by_id.get(candidate.get("source_id", ""), {})
        _prepare_candidate(candidate, source)
        score_automation_candidate(candidate, criteria, source)
        candidates.append(candidate)

    candidates.sort(
        key=lambda item: (
            int(item.get("provisional_score", 0)),
            item.get("published_at", ""),
        ),
        reverse=True,
    )
    canonical_excluded = set()
    for url in excluded_urls or set():
        canonical_url = canonicalize_url(url)
        if canonical_url:
            canonical_excluded.add(canonical_url)
    excluded_fingerprints = set(excluded_fingerprints or set())
    excluded_queries = set(excluded_queries or set())
    eligible = []
    for candidate in candidates:
        recent_match = ""
        if candidate.get("url") in canonical_excluded:
            recent_match = "same_url"
        else:
            fingerprint = _automation_source_fingerprint(
                candidate.get("url"),
                candidate.get("repository"),
            )
            if fingerprint and fingerprint in excluded_fingerprints:
                recent_match = (
                    "same_repository"
                    if fingerprint.startswith("repo:")
                    else "same_source_family"
                )
            elif _matches_recent_primary_query(candidate, excluded_queries):
                recent_match = "similar_primary_query"
        candidate["recent_match"] = recent_match
        candidate["recently_used"] = bool(recent_match)
        if not candidate["recently_used"]:
            eligible.append(candidate)

    selection = dict(config.get("selection") or {})
    selection["recently_selected_excluded"] = len(candidates) - len(eligible)
    selected = select_automation_candidates(eligible, selection)
    selected_ids = {item.get("id") for item in selected}
    candidate_limit = max(
        len(selected),
        max(0, int(selection.get("max_candidates", 25))),
    )
    visible_candidates = [
        candidate for candidate in candidates if candidate.get("id") in selected_ids
    ]
    visible_ids = {candidate.get("id") for candidate in visible_candidates}
    for candidate in candidates:
        if len(visible_candidates) >= candidate_limit:
            break
        if candidate.get("id") in visible_ids:
            continue
        visible_candidates.append(candidate)
        visible_ids.add(candidate.get("id"))
    visible_candidates.sort(
        key=lambda item: int(item.get("provisional_score", 0)), reverse=True
    )
    compact_candidates = [_compact_candidate(item) for item in visible_candidates]
    compact_by_id = {item.get("id"): item for item in compact_candidates}
    compact_selected = []
    for rank, item in enumerate(selected, start=1):
        compact = dict(compact_by_id[item.get("id")])
        compact["rank"] = rank
        compact_selected.append(compact)
    public_criteria = {
        key: {
            "label": str(spec.get("label") or key),
            "weight": int(spec.get("weight", 0)),
        }
        for key, spec in criteria.items()
    }
    return {
        "schema_version": 1,
        "lane": "saturday_automation",
        "content_type": "automation_candidates",
        "execution_status": "not_run",
        "day": base.get("day", day_id or ""),
        "generated_at": base.get("generated_at", ""),
        "review_required": True,
        "criteria": public_criteria,
        "selection": selection,
        "candidates": compact_candidates,
        "selected": compact_selected,
        "errors": base.get("errors", []),
    }


def _compact_candidate(candidate):
    keys = (
        "id",
        "title",
        "url",
        "published_at",
        "summary",
        "source_id",
        "source_family",
        "source_name",
        "group",
        "source_kind",
        "repository",
        "provisional_score",
        "score_breakdown",
        "score_reasons",
        "experiment_type",
        "verification_hint",
        "verification_status",
        "execution_status",
        "recently_used",
        "recent_match",
        "requires_manual_review",
    )
    return {key: candidate[key] for key in keys if key in candidate}


def _automation_source_fingerprint(url, repository=""):
    repository = str(repository or "").strip().strip("/").casefold()
    if repository.count("/") == 1:
        return "repo:{}".format(repository)

    canonical_url = canonicalize_url(url)
    if not canonical_url:
        return ""
    parts = urlsplit(canonical_url)
    host = parts.netloc.casefold().removeprefix("www.")
    segments = [segment.casefold() for segment in parts.path.split("/") if segment]
    if host == "github.com" and len(segments) >= 2:
        return "repo:{}/{}".format(segments[0], segments[1])
    return PRODUCT_HOST_FINGERPRINTS.get(host, "")


def _topic_tokens(value):
    return {
        token
        for token in normalize_title(value).split()
        if len(token) >= 2 and token not in AUTOMATION_TOPIC_STOP_WORDS
    }


def _matches_recent_primary_query(candidate, queries):
    candidate_tokens = _topic_tokens(
        "{} {}".format(candidate.get("title", ""), candidate.get("summary", ""))
    )
    if len(candidate_tokens) < 2:
        return False
    for query in queries:
        query_tokens = _topic_tokens(query)
        if len(query_tokens) < 2:
            continue
        overlap = candidate_tokens & query_tokens
        if len(overlap) >= 2 and len(overlap) / len(query_tokens) >= 2 / 3:
            return True
    return False


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return None


def load_recent_automation_history(
    cases_dir,
    day_id,
    lookback_days=90,
    publish_meta_dir=None,
):
    """Load dedupe fingerprints from publish-ready Saturday automation cases."""
    target_day = dt.date.fromisoformat(validate_day_id(day_id))
    cases = Path(cases_dir)
    metadata = (
        Path(publish_meta_dir)
        if publish_meta_dir is not None
        else cases.parent.parent / "docs" / "tistory"
    )
    history = {"urls": set(), "fingerprints": set(), "queries": set()}

    for days_ago in range(1, max(0, int(lookback_days)) + 1):
        prior_day = target_day - dt.timedelta(days=days_ago)
        prior_id = prior_day.isoformat()
        draft_id = "{}-automation".format(prior_id)
        payload = _read_json(cases / "{}.json".format(prior_id))
        meta = _read_json(metadata / "{}.json".format(draft_id))
        if not isinstance(payload, dict) or not isinstance(meta, dict):
            continue
        expected_source = "data/automation_cases/{}.json".format(prior_id)
        if (
            payload.get("draft_id") != draft_id
            or payload.get("publish_date") != prior_id
            or payload.get("content_type") != "automation_case"
            or meta.get("draft_id") != draft_id
            or meta.get("content_type") != "automation_case"
            or meta.get("source") != expected_source
            or not meta.get("publish_ready")
        ):
            continue

        primary_query = str(payload.get("primary_query") or "").strip()
        if primary_query:
            history["queries"].add(primary_query)
        for item in payload.get("news", []):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title_kr") or "").strip()
            if title:
                history["queries"].add(title)
            url = canonicalize_url(item.get("url"))
            if not url:
                continue
            history["urls"].add(url)
            fingerprint = _automation_source_fingerprint(url)
            if fingerprint:
                history["fingerprints"].add(fingerprint)
    return history


def load_recent_automation_urls(
    cases_dir,
    day_id,
    lookback_days=90,
    publish_meta_dir=None,
):
    return load_recent_automation_history(
        cases_dir,
        day_id,
        lookback_days=lookback_days,
        publish_meta_dir=publish_meta_dir,
    )["urls"]


def _criteria_html(item, criteria):
    scores = item.get("score_breakdown") or {}
    return "".join(
        '<span class="criterion">{} {}/{}</span>'.format(
            escape(str(spec.get("label") or key)),
            int(scores.get(key, 0)),
            int(spec.get("weight", 0)),
        )
        for key, spec in criteria.items()
    )


def _candidate_card(item, criteria, featured=False):
    title = escape(str(item.get("title") or ""))
    url = escape(str(item.get("url") or ""), quote=True)
    summary = escape(str(item.get("summary") or ""))
    source = escape(str(item.get("source_name") or ""))
    experiment_type = escape(str(item.get("experiment_type") or ""))
    repository = escape(str(item.get("repository") or ""))
    score = int(item.get("provisional_score", 0))
    reasons = " · ".join(
        escape(str(reason)) for reason in item.get("score_reasons", [])
    )
    summary_html = '<p class="summary">{}</p>'.format(summary) if summary else ""
    repository_html = (
        '<span class="repository">{}</span>'.format(repository) if repository else ""
    )
    return """
      <article class="{card_class}">
        <div class="meta"><span class="type">{experiment_type}</span><span>{source}</span>{repository_html}<b>임시 점수 {score}</b></div>
        <h3><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></h3>
        {summary_html}
        <div class="criteria">{criteria_html}</div>
        <p class="reasons">{reasons}</p>
        <p class="notice">README·라이선스·권한을 확인하고 임시 환경에서 실행하기 전까지 검증 완료로 보지 않습니다.</p>
      </article>""".format(
        card_class="card featured" if featured else "card",
        experiment_type=experiment_type,
        source=source,
        repository_html=repository_html,
        score=score,
        url=url,
        title=title,
        summary_html=summary_html,
        criteria_html=_criteria_html(item, criteria),
        reasons=reasons,
    )


def render_automation_inbox_html(inbox):
    """Render a noindex review page; all source text remains untrusted."""
    criteria = inbox.get("criteria") or {}
    selected = inbox.get("selected") or []
    selected_ids = {item.get("id") for item in selected}
    remaining = [
        item
        for item in inbox.get("candidates", [])
        if item.get("id") not in selected_ids and not item.get("recently_used")
    ]
    selected_html = "".join(
        _candidate_card(item, criteria, featured=True) for item in selected
    ) or '<p class="empty">추천 후보가 없습니다. 수집 상태를 확인하세요.</p>'
    remaining_html = "".join(
        _candidate_card(item, criteria) for item in remaining
    ) or '<p class="empty">추가 후보가 없습니다.</p>'
    errors = "".join(
        "<li><b>{}</b> — {}</li>".format(
            escape(str(error.get("source_id") or "")),
            escape(str(error.get("message") or "")),
        )
        for error in inbox.get("errors", [])
    ) or "<li>모든 출처를 정상적으로 확인했습니다.</li>"
    day = escape(str(inbox.get("day") or ""))
    generated_at = escape(str(inbox.get("generated_at") or ""))
    return """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow,noarchive">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
  <title>{day} 토요일 자동화 후보함</title>
  <style>
    :root {{ --ink:#17211c; --muted:#647069; --line:#dce4df; --paper:#fff; --wash:#f3f6f4; --accent:#176848; --amber:#a76512; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; color:var(--ink); background:var(--wash); font:15px/1.65 -apple-system,BlinkMacSystemFont,"Noto Sans KR",sans-serif; }}
    main {{ width:min(920px,calc(100% - 32px)); margin:auto; padding:52px 0 80px; }}
    h1 {{ margin:4px 0 10px; font-size:clamp(30px,6vw,46px); letter-spacing:-.05em; }}
    h2 {{ margin:42px 0 14px; font-size:21px; }}
    h3 {{ margin:12px 0 6px; font-size:20px; line-height:1.4; letter-spacing:-.025em; }}
    a {{ color:inherit; text-decoration-thickness:1px; text-underline-offset:4px; }}
    .eyebrow,.intro,.generated,.summary,.reasons,.notice,.empty,.errors {{ color:var(--muted); }}
    .eyebrow,.type {{ color:var(--accent); font-weight:800; }}
    .generated {{ font-size:12px; }}
    .intro {{ max-width:720px; }}
    .grid {{ display:grid; gap:14px; }}
    .card {{ padding:21px 23px; background:var(--paper); border:1px solid var(--line); border-radius:14px; }}
    .featured {{ border-left:5px solid var(--accent); }}
    .meta,.criteria {{ display:flex; flex-wrap:wrap; gap:7px 11px; align-items:center; font-size:12px; }}
    .repository {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
    .summary,.reasons,.notice {{ margin:7px 0 0; }}
    .criteria {{ margin-top:13px; }}
    .criterion {{ padding:3px 8px; border:1px solid var(--line); border-radius:999px; background:#f8faf9; }}
    .notice {{ padding-top:9px; border-top:1px dashed var(--line); color:var(--amber); font-size:12px; }}
    .errors {{ padding:16px 20px 16px 38px; background:#fff; border:1px solid var(--line); border-radius:12px; }}
    footer {{ margin-top:42px; padding-top:18px; border-top:1px solid var(--line); color:var(--muted); font-size:13px; }}
  </style>
</head>
<body>
<main>
  <header>
    <p class="eyebrow">SATURDAY AUTOMATION RADAR</p>
    <p class="generated">{day} · 생성 {generated_at}</p>
    <h1>토요일 자동화 후보함</h1>
    <p class="intro">GitHub Trending, 공개 릴리스와 공식 변경 내역에서 실험 후보만 모았습니다. 점수는 메타데이터 기반 임시 점수이며 실제 실행 결과가 아닙니다.</p>
  </header>
  <section><h2>우선 검토할 후보 {selected_count}건</h2><div class="grid">{selected_html}</div></section>
  <section><h2>추가 후보 {remaining_count}건</h2><div class="grid">{remaining_html}</div></section>
  <section><h2>수집 상태</h2><ul class="errors">{errors}</ul></section>
  <footer>후보함은 글이 아닙니다. 14:00 Codex 작업이 공식 문서·버전·권한을 확인하고 안전한 임시 환경에서 직접 검증한 뒤 한 건만 집필합니다.</footer>
</main>
</body>
</html>
""".format(
        day=day,
        generated_at=generated_at,
        selected_count=len(selected),
        selected_html=selected_html,
        remaining_count=len(remaining),
        remaining_html=remaining_html,
        errors=errors,
    )


def write_automation_inbox(inbox, output_dir):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    validate_day_id(inbox["day"])
    latest_json = output / "latest.json"
    index_html = output / "index.html"
    payload = dict(inbox)

    if latest_json.exists():
        try:
            previous = json.loads(latest_json.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            previous = None
        if previous:
            old = {key: value for key, value in previous.items() if key != "generated_at"}
            new = {key: value for key, value in payload.items() if key != "generated_at"}
            if old == new:
                payload["generated_at"] = previous.get("generated_at", "")

    latest_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    index_html.write_text(render_automation_inbox_html(payload), encoding="utf-8")
    return {"json": str(latest_json), "html": str(index_html)}


def main(argv=None):
    parser = argparse.ArgumentParser(description="토요일 자동화 실험 후보함을 생성합니다.")
    day_group = parser.add_mutually_exclusive_group()
    day_group.add_argument("--today", action="store_true", help="한국 시간 기준 오늘")
    day_group.add_argument("--day", help="후보함 날짜 (YYYY-MM-DD)")
    parser.add_argument("--config", default="config/automation_sources.json")
    parser.add_argument("--output-dir", default="docs/automation-inbox")
    parser.add_argument("--automation-cases-dir", default="data/automation_cases")
    parser.add_argument("--publish-meta-dir", default="docs/tistory")
    args = parser.parse_args(argv)

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    now = dt.datetime.now(ZoneInfo("Asia/Seoul"))
    try:
        day_id = validate_day_id(args.day or now.date().isoformat())
    except ValueError as exc:
        parser.error(str(exc))
    lookback = int(config.get("selection", {}).get("exclude_recent_days", 90))
    history = load_recent_automation_history(
        args.automation_cases_dir,
        day_id,
        lookback_days=lookback,
        publish_meta_dir=args.publish_meta_dir,
    )
    inbox = build_automation_inbox(
        config,
        fetch_text=fetch_url,
        now=now,
        day_id=day_id,
        excluded_urls=history["urls"],
        excluded_fingerprints=history["fingerprints"],
        excluded_queries=history["queries"],
    )
    paths = write_automation_inbox(inbox, args.output_dir)
    print(
        "자동화 후보함 생성: 추천 {}건 / 전체 {}건 / 오류 {}건\n{}".format(
            len(inbox["selected"]),
            len(inbox["candidates"]),
            len(inbox["errors"]),
            paths["html"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
