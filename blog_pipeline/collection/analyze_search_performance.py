"""Turn Search Console period comparisons into a conservative refresh queue.

The thresholds are internal editorial heuristics, not Google ranking rules.
Input rows must contain one query-page pair and metrics for two equal periods.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo


HEADER_ALIASES = {
    "query": ("query", "검색어", "상위 검색어"),
    "page_url": ("page_url", "page", "페이지", "상위 페이지"),
    "current_impressions": (
        "current_impressions",
        "최근 노출",
        "현재 노출",
    ),
    "current_clicks": ("current_clicks", "최근 클릭", "현재 클릭"),
    "previous_impressions": (
        "previous_impressions",
        "이전 노출",
    ),
    "previous_clicks": ("previous_clicks", "이전 클릭"),
    "current_position": ("current_position", "최근 순위", "현재 순위"),
    "previous_position": ("previous_position", "이전 순위"),
}
REQUIRED_FIELDS = {
    "query",
    "page_url",
    "current_impressions",
    "current_clicks",
    "previous_impressions",
    "previous_clicks",
}
ACTION_PRIORITY = {
    "merge_existing": 3,
    "refresh_existing": 2,
    "retitle_existing": 1,
}


def _number(value):
    text = str(value or "").strip().replace(",", "").replace("%", "")
    if not text:
        return 0.0
    try:
        return max(0.0, float(text))
    except ValueError:
        return 0.0


def _change_pct(current, previous):
    if previous <= 0:
        return None
    return round((current - previous) / previous * 100, 1)


def _valid_page_url(value):
    text = str(value or "").strip()
    parsed = urlsplit(text)
    return text if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def _normalized_row(row):
    query = " ".join(str(row.get("query") or "").split())
    page_url = _valid_page_url(row.get("page_url"))
    if not query or not page_url:
        return None
    return {
        "query": query,
        "page_url": page_url,
        "current_impressions": _number(row.get("current_impressions")),
        "current_clicks": _number(row.get("current_clicks")),
        "previous_impressions": _number(row.get("previous_impressions")),
        "previous_clicks": _number(row.get("previous_clicks")),
        "current_position": _number(row.get("current_position")),
        "previous_position": _number(row.get("previous_position")),
    }


def _opportunity(row, action, reason, priority_score, **extra):
    current_impressions = row["current_impressions"]
    current_clicks = row["current_clicks"]
    previous_impressions = row["previous_impressions"]
    previous_clicks = row["previous_clicks"]
    return {
        "query": row["query"],
        "page_url": row["page_url"],
        "impressions": round(current_impressions),
        "clicks": round(current_clicks),
        "previous_impressions": round(previous_impressions),
        "previous_clicks": round(previous_clicks),
        "impression_change_pct": _change_pct(
            current_impressions, previous_impressions
        ),
        "click_change_pct": _change_pct(current_clicks, previous_clicks),
        "current_position": row["current_position"] or None,
        "previous_position": row["previous_position"] or None,
        "action": action,
        "reason": reason,
        "priority_score": round(priority_score, 1),
        "status": "review",
        **extra,
    }


def analyze_rows(rows, *, min_impressions=20, drop_ratio=0.30):
    """Return only material refresh, title, or cannibalization opportunities."""
    normalized = [item for row in rows if (item := _normalized_row(row))]
    by_query = {}
    for row in normalized:
        by_query.setdefault(row["query"].casefold(), []).append(row)

    opportunities = []
    for query_rows in by_query.values():
        unique_pages = {row["page_url"] for row in query_rows}
        total_impressions = sum(row["current_impressions"] for row in query_rows)
        if len(unique_pages) >= 2 and total_impressions >= min_impressions:
            canonical = max(
                query_rows,
                key=lambda row: (
                    row["current_clicks"],
                    row["current_impressions"],
                ),
            )
            aggregate = dict(canonical)
            for metric in (
                "current_impressions",
                "current_clicks",
                "previous_impressions",
                "previous_clicks",
            ):
                aggregate[metric] = sum(row[metric] for row in query_rows)
            opportunities.append(
                _opportunity(
                    aggregate,
                    "merge_existing",
                    "같은 검색어에 여러 공개 글이 노출되어 대표 글 통합 검토가 필요함",
                    100 + total_impressions,
                    competing_pages=sorted(unique_pages),
                )
            )
            continue

        row = query_rows[0]
        impression_loss = max(
            0, row["previous_impressions"] - row["current_impressions"]
        )
        click_loss = max(0, row["previous_clicks"] - row["current_clicks"])
        impression_drop = (
            row["previous_impressions"] >= min_impressions
            and row["current_impressions"]
            <= row["previous_impressions"] * (1 - drop_ratio)
        )
        click_drop = (
            row["previous_clicks"] >= 3
            and row["current_clicks"]
            <= row["previous_clicks"] * (1 - drop_ratio)
        )
        if impression_drop or click_drop:
            opportunities.append(
                _opportunity(
                    row,
                    "refresh_existing",
                    "동일 기간 비교에서 노출 또는 클릭이 30% 이상 감소함",
                    impression_loss + click_loss * 10,
                )
            )
        elif (
            row["current_impressions"] >= min_impressions
            and row["current_clicks"] == 0
        ):
            opportunities.append(
                _opportunity(
                    row,
                    "retitle_existing",
                    "노출은 발생하지만 클릭 0으로 제목·검색 의도 일치 검토가 필요함",
                    row["current_impressions"],
                )
            )

    return sorted(
        opportunities,
        key=lambda item: (
            ACTION_PRIORITY[item["action"]],
            item["priority_score"],
        ),
        reverse=True,
    )


def load_csv_rows(path):
    """Load the documented comparison CSV with English or Korean headers."""
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = {str(field or "").strip().casefold(): field for field in reader.fieldnames or []}
        mapping = {}
        for canonical, aliases in HEADER_ALIASES.items():
            match = next(
                (fields[alias.casefold()] for alias in aliases if alias.casefold() in fields),
                None,
            )
            if match:
                mapping[canonical] = match
        missing = sorted(REQUIRED_FIELDS - mapping.keys())
        if missing:
            raise ValueError("검색 성과 CSV 필드 누락: {}".format(", ".join(missing)))
        return [
            {canonical: row.get(source, "") for canonical, source in mapping.items()}
            for row in reader
        ]


def build_report(rows, *, updated_at=None, min_impressions=20, drop_ratio=0.30):
    current = updated_at or dt.datetime.now(ZoneInfo("Asia/Seoul"))
    if current.tzinfo is None:
        current = current.replace(tzinfo=ZoneInfo("Asia/Seoul"))
    return {
        "schema_version": 2,
        "updated_at": current.isoformat(timespec="seconds"),
        "source": "Google Search Console equal-period comparison",
        "policy_note": (
            "이 결과는 Google 순위 기준이 아니라 기존 글 보강 순서를 정하는 "
            "내부 운영 휴리스틱이다. 삭제나 새 글 생성을 자동 결정하지 않는다."
        ),
        "thresholds": {
            "min_impressions": min_impressions,
            "drop_ratio": drop_ratio,
        },
        "opportunities": analyze_rows(
            rows,
            min_impressions=min_impressions,
            drop_ratio=drop_ratio,
        ),
    }


def render_markdown(report):
    lines = [
        "# 기존 글 성장 큐",
        "",
        f"- 갱신: {report['updated_at']}",
        f"- 검토 대상: {len(report['opportunities'])}건",
        f"- 주의: {report['policy_note']}",
        "",
        "| 우선 | 검색어 | 조치 | 최근/이전 노출 | 최근/이전 클릭 | 대상 글 |",
        "|---:|---|---|---:|---:|---|",
    ]
    for item in report["opportunities"]:
        query = str(item["query"]).replace("|", "\\|")
        url = item["page_url"]
        lines.append(
            "| {priority} | {query} | {action} | {impressions}/{previous_impressions} "
            "| {clicks}/{previous_clicks} | [열기]({url}) |".format(
                priority=item["priority_score"],
                query=query,
                action=item["action"],
                impressions=item["impressions"],
                previous_impressions=item["previous_impressions"],
                clicks=item["clicks"],
                previous_clicks=item["previous_clicks"],
                url=url,
            )
        )
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Search Console 동일 기간 비교 CSV로 기존 글 보강 큐를 만듭니다."
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="config/search_opportunities.json")
    parser.add_argument(
        "--markdown-output",
        default="reports/search-refresh-queue.md",
    )
    parser.add_argument("--min-impressions", type=int, default=20)
    parser.add_argument("--drop-ratio", type=float, default=0.30)
    args = parser.parse_args(argv)

    report = build_report(
        load_csv_rows(args.input),
        min_impressions=max(1, args.min_impressions),
        drop_ratio=min(0.90, max(0.10, args.drop_ratio)),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_output = Path(args.markdown_output)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(
        "검색 성과 보강 큐: {}건 ({}, {})".format(
            len(report["opportunities"]), output, markdown_output
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
