#!/usr/bin/env python3
"""Restore a minimal review inbox from a legacy exported Tistory HTML draft."""

import argparse
import datetime as dt
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from news_pipeline import normalize_title


CARD_PATTERN = re.compile(
    r"<section\b[^>]*digest-news-card[^>]*>(.*?)</section>",
    re.IGNORECASE | re.DOTALL,
)
TAG_PATTERN = re.compile(r"<[^>]+>")
SPACE_PATTERN = re.compile(r"\s+")
DAY_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


def _text(fragment):
    plain = TAG_PATTERN.sub(" ", fragment or "")
    return SPACE_PATTERN.sub(" ", html.unescape(plain)).strip()


def _match_text(pattern, fragment):
    match = re.search(pattern, fragment, re.IGNORECASE | re.DOTALL)
    return _text(match.group(1)) if match else ""


def _source_id(source_name):
    lowered = source_name.casefold()
    if "geek" in lowered:
        return "geeknews"
    if "ai타임스" in lowered or "aitimes" in lowered:
        return "aitimes"
    if "github" in lowered:
        return "github"
    if "openai" in lowered:
        return "openai"
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "legacy-source"


def _group(source_id):
    if source_id == "geeknews":
        return "community"
    if source_id in {"github", "openai"}:
        return "official"
    if source_id == "aitimes":
        return "korean_general"
    return "legacy"


def _restore_cards(source_html, day):
    lanes = ("broad", "practical", "deep")
    restored = []
    for index, card in enumerate(CARD_PATTERN.findall(source_html)):
        title = _match_text(r"<h3\b[^>]*>(.*?)</h3>", card)
        source_name = _match_text(
            r"<p\b[^>]*digest-source[^>]*>(.*?)</p>", card
        )
        source_name = re.sub(r"^\d+\.\s*", "", source_name).strip()

        source_url = ""
        for href, label in re.findall(
            r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
            card,
            re.IGNORECASE | re.DOTALL,
        ):
            if "원문" in _text(label):
                candidate_url = html.unescape(href).strip()
                parsed_url = urlparse(candidate_url)
                if parsed_url.scheme in {"http", "https"} and parsed_url.netloc:
                    source_url = candidate_url
                break

        paragraphs = []
        for attributes, body in re.findall(
            r"<p\b([^>]*)>(.*?)</p>", card, re.IGNORECASE | re.DOTALL
        ):
            if "digest-source" in attributes:
                continue
            paragraph = _text(body)
            if paragraph:
                paragraphs.append(paragraph)
        summary = " ".join(paragraphs)[:1200]

        if not title or not source_url:
            continue
        lane = lanes[index % len(lanes)]
        source_id = _source_id(source_name)
        restored.append(
            {
                "id": hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:12],
                "title": title,
                "normalized_title": normalize_title(title),
                "url": source_url,
                "published_at": "{}T00:00:00+09:00".format(day),
                "summary": summary,
                "source_id": source_id,
                "source_name": source_name or "과거 글 원문",
                "group": _group(source_id),
                "source_weight": 1,
                "lane_bias": {lane: 1},
                "requires_manual_review": True,
                "score": 1,
                "score_reasons": ["과거 발행 글에서 복원"],
                "lane_scores": {lane: 1},
                "topic_tags": [],
                "audience_lane": lane,
                "selection_reason": "과거 발행 글의 원문과 주제를 유지해 보강",
            }
        )
    return restored[:3]


def restore_review_inbox(day, html_path, output_path):
    if not DAY_PATTERN.fullmatch(day):
        raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다.")
    html_path = Path(html_path)
    output_path = Path(output_path)
    restored = _restore_cards(html_path.read_text(encoding="utf-8"), day)
    if not restored:
        raise ValueError("복원할 뉴스 카드와 원문 링크를 찾지 못했습니다.")

    inbox = {
        "schema_version": 1,
        "day": day,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "review_required": True,
        "selection": {
            "max_items": 3,
            "max_per_source": 3,
            "audience_lanes": ["broad", "practical", "deep"],
            "require_topic_coherence": False,
            "restored_from_legacy_html": str(html_path),
        },
        "candidates": restored,
        "selected": restored,
        "errors": [],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(inbox, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return inbox


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="과거 티스토리 HTML에서 뉴스 후보함을 복원합니다."
    )
    parser.add_argument("--day", required=True, help="복원할 날짜 (YYYY-MM-DD)")
    parser.add_argument("--html", help="기존 티스토리 HTML 경로")
    parser.add_argument("--output", help="후보함 JSON 출력 경로")
    args = parser.parse_args(argv)

    html_path = args.html or "docs/tistory/{}.html".format(args.day)
    output_path = args.output or "docs/inbox/{}.json".format(args.day)
    restore_review_inbox(args.day, html_path, output_path)
    print("restored: {}".format(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
