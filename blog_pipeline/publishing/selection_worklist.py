"""Build a complete query-first review list; lexical hints are not query-page metrics."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

from ..collection.search_demand import ROOT, load_snapshot, demand_report

GENERIC = {"사용법", "설치", "방법", "오류", "기록", "보는", "선택", "차이", "대체", "하기"}


def compact(value):
    return re.sub(r"[^a-z0-9가-힣]", "", str(value).casefold())


def worklist(plan, day, *, root=ROOT):
    report = demand_report(load_snapshot(plan["demand_snapshot"], root=root), day)
    queued = {i["draft_id"]: i for i in plan.get("refresh_queue", [])}
    sources = []
    for folder in ("days", "automation_cases", "guides"):
        for path in sorted((Path(root) / "data" / folder).glob("*.json")):
            data = json.loads(path.read_text())
            identity = data.get("draft_id")
            title = data.get("editorial", {}).get("headline") or data.get("title", "")
            if not identity or not title:
                continue
            fields = [title, data.get("primary_query", ""), *data.get("tags", [])]
            sources.append((identity, title, path.relative_to(root).as_posix(), [compact(f) for f in fields]))
    for row in report["queries"]:
        terms = [compact(t) for t in re.findall(r"[a-z0-9]{3,}|[가-힣]{2,}", row["query"].casefold()) if t not in GENERIC]
        hints = []
        for identity, title, path, fields in sources:
            score = sum(min(len(t), 10) for t in terms if any(t in f for f in fields))
            if len(compact(row["query"])) >= 4 and any(compact(row["query"]) in f for f in fields):
                score += 20
            if not score:
                continue
            entry = queued.get(identity, {})
            hints.append({"draft_id": identity, "source": path, "title": title,
                          "page_url": entry.get("page_url"), "queue_status": entry.get("status"),
                          "refresh_eligible": entry.get("status") != "ready_for_review", "lexical_score": score})
        row["source_hints"] = sorted(hints, key=lambda h: (-h["lexical_score"], h["draft_id"]))[:3]
    report.update({"status": "REVIEW_REQUIRED", "snapshot": plan["demand_snapshot"]})
    report["protected_handoffs"] = [i["source"] for i in plan.get("refresh_queue", []) if i.get("status") == "ready_for_review"]
    report["limits"] = "보존한 유효 검색어 전체다. 어휘 힌트는 의미·공개 URL·검색어별 페이지 성과의 증거가 아니다. URL은 실제 공개 본문으로 확인한다."
    report["next_action"] = "검수 대기본을 제외하고 다음 검색어/별도 후속 과제를 조사한다. 공개 조회 실패 시 public_article을 사용한다. 후보를 선택하거나 --check-review가 EXHAUSTED를 반환하기 전에 종료하지 않는다."
    return report


def review_result(report, review):
    """A selected gap can stop discovery; an empty selection needs full coverage + research."""
    if review.get("snapshot") != report["snapshot"]:
        return {"status": "RESEARCH_REQUIRED", "reason": "snapshot_mismatch"}
    actual = {r["query"] for r in report["queries"]}
    covered = set()
    allowed = {"already_answered", "pending_handoff", "unrelated", "source_unavailable", "gap_confirmed"}
    for item in review.get("reviews", []):
        queries = set(item.get("queries", []))
        if not queries or not queries <= actual or item.get("decision") not in allowed or len(item.get("reason", "").strip()) < 20:
            return {"status": "RESEARCH_REQUIRED", "reason": "invalid_review"}
        covered.update(queries)
        if item["decision"] == "gap_confirmed":
            from .public_article import validate_url
            try:
                if item.get("action", "refresh_existing") == "new_article":
                    if not isinstance(item.get("existing_page_urls"), list) or len(item.get("distinct_outcome", "")) < 20:
                        raise ValueError("distinct task required")
                    for url in item["existing_page_urls"]:
                        validate_url(url)
                else:
                    validate_url(item.get("page_url", ""))
            except ValueError:
                return {"status": "RESEARCH_REQUIRED", "reason": "public_url_required"}
            if not item.get("source") or not item.get("public_evidence") or not item.get("official_evidence"):
                return {"status": "RESEARCH_REQUIRED", "reason": "gap_evidence_required"}
            blocked = set(report.get("protected_handoffs", []))
            if item["source"] in blocked:
                return {"status": "RESEARCH_REQUIRED", "reason": "pending_handoff_protected"}
            return {"status": "SELECTED", "target": item}
    missing = sorted(actual - covered)
    research = review.get("direct_research", [])
    if missing or len({r.get("url") for r in research if r.get("url", "").startswith("https://") and len(r.get("finding", "")) >= 20}) < 3:
        return {"status": "RESEARCH_REQUIRED", "unreviewed_queries": missing, "reason": "full_review_and_three_research_sources_required"}
    return {"status": "EXHAUSTED", "reviewed_queries": len(covered), "note": "편집 검토 기록이며 품질/배포 완료가 아니다."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", action="store_true")
    parser.add_argument("--day", type=dt.date.fromisoformat)
    parser.add_argument("--check-review", type=Path)
    args = parser.parse_args(argv)
    day = args.day or dt.datetime.now(ZoneInfo("Asia/Seoul")).date()
    try:
        plan = json.loads((ROOT / "config/content_growth_trial.json").read_text())
        report = worklist(plan, day)
        if args.check_review:
            report = review_result(report, json.loads(args.check_review.read_text()))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report = {"status": "RESEARCH_REQUIRED", "reason": str(exc)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "RESEARCH_REQUIRED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
