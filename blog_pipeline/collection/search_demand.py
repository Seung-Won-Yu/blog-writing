"""Read observed Search Console queries before choosing editorial topics.

Snapshots contain query totals only. They never imply a query-page join,
market search volume, or permission to create a competing article.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
POLICY_START = dt.date(2026, 10, 29)
PROPERTY = "https://won0322.tistory.com/"
MAX_AGE_DAYS = 30


def load_snapshot(reference, *, root=ROOT):
    path = Path(str(reference))
    if (
        len(path.parts) != 3
        or path.parts[:2] != ("data", "search_demand")
        or path.suffix != ".json"
        or path.is_absolute()
    ):
        raise ValueError("Invalid search demand snapshot path")
    dt.date.fromisoformat(path.stem)
    resolved = (Path(root) / path).resolve()
    if not resolved.is_relative_to(Path(root).resolve()):
        raise ValueError("Search demand snapshot leaves repository")
    return json.loads(resolved.read_text(encoding="utf-8"))


def observed_queries(snapshot, day):
    """Validate observation scope, equal periods, dates and real query metrics."""
    if (
        snapshot.get("source") != "Google Search Console"
        or snapshot.get("property") != PROPERTY
        or snapshot.get("metric_scope") != "query"
        or snapshot.get("search_type") != "web"
    ):
        raise ValueError("Expected this site's observed web-search query totals")
    observed = dt.datetime.fromisoformat(snapshot["observed_at"].replace("Z", "+00:00"))
    if observed.tzinfo is None:
        raise ValueError("Observation needs a timezone")
    observed_day = observed.astimezone(ZoneInfo("Asia/Seoul")).date()
    current = snapshot["current_period"]
    previous = snapshot["previous_period"]
    start, end = (dt.date.fromisoformat(current[k]) for k in ("start", "end"))
    old_start, old_end = (dt.date.fromisoformat(previous[k]) for k in ("start", "end"))
    if (
        start > end or old_start > old_end
        or end - start != old_end - old_start
        or old_end >= start or end > observed_day
        or not 0 <= (day - observed_day).days <= MAX_AGE_DAYS
        or not 0 <= (day - end).days <= MAX_AGE_DAYS
    ):
        raise ValueError("Search observation is stale, future-dated or not comparable")
    rows = snapshot.get("queries")
    if not isinstance(rows, list):
        raise ValueError("Missing observed query rows")
    result, seen = [], set()
    metrics = ("current_clicks", "previous_clicks", "current_impressions", "previous_impressions")
    for row in rows:
        query = " ".join(str(row.get("query") or "").split())
        if not query or query.casefold() in seen:
            raise ValueError("Empty or duplicate observed query")
        seen.add(query.casefold())
        if any(type(row.get(k)) is not int or row[k] < 0 for k in metrics):
            raise ValueError("Query metrics must be observed nonnegative integers")
        if any(row[f"{p}_clicks"] > row[f"{p}_impressions"] for p in ("current", "previous")):
            raise ValueError("Clicks cannot exceed impressions")
        if query.casefold().startswith("site:") or not row["current_impressions"]:
            continue
        result.append({"query": query, **{k: row[k] for k in metrics}})
    return sorted(result, key=lambda r: (r["current_clicks"], r["current_impressions"]), reverse=True)


def demand_report(snapshot, day):
    rows = observed_queries(snapshot, day)
    observed = dt.datetime.fromisoformat(snapshot["observed_at"].replace("Z", "+00:00"))
    return {
        "status": "READY" if rows else "NO_OBSERVED_QUERIES",
        "observed_at": snapshot["observed_at"],
        "current_period": snapshot["current_period"],
        "metric_scope": "query",
        "refresh_due": (day - observed.astimezone(ZoneInfo("Asia/Seoul")).date()).days >= 7,
        "queries": rows[:20],
        "selection_rule": "실제 검색 의도를 먼저 읽고 기존 글과 대조한다. 같은 답은 기존 URL 개선, 별도 질문만 새 글로 선정한다. 수집기 점수로 이 순서를 바꾸지 않는다.",
        "limits": "표시된 검색어 일부의 사이트 내 합계다. 검색량·페이지별 검색어 성과·성장 보장이 아니다. 관련 없는 기술 발표에 검색어를 붙이지 않는다.",
    }


def source_demand_reasons(source, identity, *, root=ROOT):
    """New weekday articles must cite a fresh archived query, not a hypothesis."""
    day = dt.date.fromisoformat(identity.publish_date)
    if day < POLICY_START or identity.content_type not in {"daily_news", "automation_case"}:
        return []
    editorial = source.get("editorial")
    if not isinstance(editorial, dict) or not isinstance(editorial.get("search_demand"), dict):
        return ["quality_observed_search_demand"]
    evidence = editorial["search_demand"]
    try:
        rows = observed_queries(load_snapshot(evidence.get("snapshot"), root=root), day)
        match = next((r for r in rows if r["query"] == evidence.get("query")), None)
        if (
            not match
            or evidence.get("relation") not in {"same_intent", "distinct_followup"}
            or len(str(evidence.get("intent_gap") or "").strip()) < 20
            or not isinstance(evidence.get("existing_page_urls"), list)
        ):
            return ["quality_observed_search_demand"]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return ["quality_observed_search_demand"]
    return []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot")
    dates = parser.add_mutually_exclusive_group()
    dates.add_argument("--today", action="store_true")
    dates.add_argument("--day", type=dt.date.fromisoformat)
    args = parser.parse_args(argv)
    day = args.day or dt.datetime.now(ZoneInfo("Asia/Seoul")).date()
    try:
        reference = args.snapshot
        if not reference:
            reference = json.loads((ROOT / "config/content_growth_trial.json").read_text())["demand_snapshot"]
        report = demand_report(load_snapshot(reference), day)
        report["snapshot"] = reference
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        report = {"status": "REFRESH_REQUIRED", "reason": str(exc), "queries": []}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
