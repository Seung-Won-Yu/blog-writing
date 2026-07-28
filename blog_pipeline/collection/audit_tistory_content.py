"""Audit public Tistory posts for site-level low-value content risks.

The thresholds in this module are editorial triage heuristics, not Google
AdSense rules. Google does not publish a required word count or post count.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from .collect_news import fetch_url
from .sync_tistory_posts import BLOG_URL, SITEMAP_URL, parse_public_posts


GENERIC_TITLE_TERMS = (
    "완벽 가이드",
    "완벽 정리",
    "완전 정리",
    "완전정리",
    "완전 정복",
    "완전정복",
    "핵심 요약",
    "핵심 정리",
    "총정리",
)
QUESTION_DUMP_PATTERN = re.compile(
    r"(?:시험\s*문제|문제집|객관식\s*\d+\s*문제|문제\s*정리|"
    r"(?:정보처리기사|ADsP|인공지능\s*활용능력).*문제)",
    re.IGNORECASE,
)
QUESTION_ITEM_PATTERN = re.compile(
    r"(?:\[?문제\s*\d+\]?|\bQ\s*\d+\b)",
    re.IGNORECASE,
)
LEGACY_AUTO_DIGEST_PHRASES = (
    "자동 생성 데일리 다이제스트",
    "본문은 핵심 내용 요약과 학습용 문제로 구성",
)
SPACE_PATTERN = re.compile(r"\s+")
TITLE_PATTERN = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
CATEGORY_PATTERN = re.compile(r'categoryLabel":"([^"]*)"')

# Internal review thresholds only. Never present these as AdSense requirements.
THIN_TEXT_REVIEW_CHARS = 1500
LINK_LIST_REVIEW_CHARS = 2000
LINK_LIST_MIN_LINKS = 8
CODE_HEAVY_RATIO = 0.70

RISK_WEIGHTS = {
    "duplicate_title": 4,
    "question_dump": 4,
    "legacy_auto_digest": 4,
    "link_list": 4,
    "thin_text": 3,
    "code_heavy": 3,
    "low_structure": 2,
    "broken_internal_links": 2,
    "generic_summary_title": 1,
    "no_evidence_or_sources": 1,
}


def _clean_text(parts):
    return SPACE_PATTERN.sub(" ", " ".join(parts)).strip()


def normalized_title(value):
    return re.sub(r"[^0-9a-z가-힣]+", "", str(value or "").lower())


class _ArticleParser(HTMLParser):
    """Extract article signals without depending on the active Tistory skin."""

    def __init__(self, *, blog_host):
        super().__init__(convert_charrefs=True)
        self.blog_host = blog_host
        self.article_depth = 0
        self.ignored_depth = 0
        self.code_depth = 0
        self.text_parts = []
        self.code_parts = []
        self.paragraphs = 0
        self.headings = 0
        self.images = 0
        self.tables = 0
        self.external_links = 0
        self.internal_post_ids = []
        self.page_ad_units = 0
        self.found_article = False

    @property
    def in_article(self):
        return self.article_depth > 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attributes = dict(attrs)
        classes = set(str(attributes.get("class") or "").split())
        if "revenue_unit_item" in classes:
            self.page_ad_units += 1
        elif tag == "ins" and "adsbygoogle" in classes:
            self.page_ad_units += 1

        if not self.in_article:
            if tag == "div" and "tt_article_useless_p_margin" in classes:
                self.article_depth = 1
                self.found_article = True
            return

        if tag == "div":
            self.article_depth += 1
        if tag in {"script", "style", "noscript"}:
            self.ignored_depth += 1
            return
        if self.ignored_depth:
            return
        if tag == "p":
            self.paragraphs += 1
        elif tag in {"h2", "h3", "h4"}:
            self.headings += 1
        elif tag == "img":
            self.images += 1
        elif tag == "table":
            self.tables += 1
        elif tag in {"pre", "code"}:
            self.code_depth += 1
        elif tag == "a":
            href = str(attributes.get("href") or "").strip()
            parsed = urlsplit(href)
            host = parsed.netloc.lower().removeprefix("www.")
            if parsed.scheme in {"http", "https"} and host and host != self.blog_host:
                self.external_links += 1
            elif not host or host == self.blog_host:
                match = re.fullmatch(r"/(?:m/)?(\d+)/?", parsed.path or "")
                if match:
                    self.internal_post_ids.append(int(match.group(1)))

    def handle_endtag(self, tag):
        tag = tag.lower()
        if not self.in_article:
            return
        if tag in {"script", "style", "noscript"} and self.ignored_depth:
            self.ignored_depth -= 1
        elif tag in {"pre", "code"} and self.code_depth:
            self.code_depth -= 1
        if tag == "div":
            self.article_depth -= 1

    def handle_data(self, data):
        if not self.in_article or self.ignored_depth:
            return
        value = str(data or "").strip()
        if not value:
            return
        self.text_parts.append(value)
        if self.code_depth:
            self.code_parts.append(value)


def parse_post_html(html_text, *, post_id, url, blog_url=BLOG_URL):
    blog_host = urlsplit(blog_url).netloc.lower().removeprefix("www.")
    parser = _ArticleParser(blog_host=blog_host)
    parser.feed(str(html_text or ""))
    title_match = TITLE_PATTERN.search(str(html_text or ""))
    category_match = CATEGORY_PATTERN.search(str(html_text or ""))
    title = unescape(title_match.group(1)).strip() if title_match else ""
    category = unescape(category_match.group(1)).strip() if category_match else ""
    text = _clean_text(parser.text_parts)
    code = _clean_text(parser.code_parts)
    return {
        "id": int(post_id),
        "url": str(url),
        "title": title,
        "category": category,
        "chars": len(text),
        "paragraphs": parser.paragraphs,
        "headings": parser.headings,
        "images": parser.images,
        "tables": parser.tables,
        "code_chars": len(code),
        "external_links": parser.external_links,
        "internal_post_ids": sorted(set(parser.internal_post_ids)),
        "page_ad_units": parser.page_ad_units,
        "question_items": len(QUESTION_ITEM_PATTERN.findall(text)),
        "legacy_auto_digest": any(
            phrase in text for phrase in LEGACY_AUTO_DIGEST_PHRASES
        ),
        "article_found": parser.found_article,
    }


def editorial_reasons(post):
    reasons = []
    title = str(post.get("title") or "")
    chars = int(post.get("chars") or 0)
    paragraphs = int(post.get("paragraphs") or 0)
    headings = int(post.get("headings") or 0)
    images = int(post.get("images") or 0)
    tables = int(post.get("tables") or 0)
    code_chars = int(post.get("code_chars") or 0)
    links = int(post.get("external_links") or 0)
    question_items = int(post.get("question_items") or 0)

    if chars < THIN_TEXT_REVIEW_CHARS:
        reasons.append("thin_text")
    if paragraphs <= 2 and headings <= 1:
        reasons.append("low_structure")
    if links >= LINK_LIST_MIN_LINKS and chars < LINK_LIST_REVIEW_CHARS:
        reasons.append("link_list")
    if QUESTION_DUMP_PATTERN.search(title) or question_items >= 15:
        reasons.append("question_dump")
    if post.get("legacy_auto_digest"):
        reasons.append("legacy_auto_digest")
    if any(term in title for term in GENERIC_TITLE_TERMS):
        reasons.append("generic_summary_title")
    if (
        chars
        and code_chars / chars >= CODE_HEAVY_RATIO
        and (paragraphs < 10 or (links == 0 and images + tables == 0))
    ):
        reasons.append("code_heavy")
    if images == 0 and tables == 0 and links == 0:
        reasons.append("no_evidence_or_sources")
    return reasons


def audit_posts(posts):
    audited = []
    title_groups = {}
    public_ids = {
        int(post.get("id"))
        for post in posts
        if str(post.get("id") or "").isdigit()
    }
    for post in posts:
        item = dict(post)
        item["reasons"] = editorial_reasons(item)
        item["broken_internal_links"] = sorted(
            post_id
            for post_id in item.get("internal_post_ids", [])
            if post_id not in public_ids
        )
        if item["broken_internal_links"]:
            item["reasons"].append("broken_internal_links")
        key = normalized_title(item.get("title"))
        if key:
            title_groups.setdefault(key, []).append(item)
        audited.append(item)

    for group in title_groups.values():
        if len(group) < 2:
            continue
        for item in group:
            if "duplicate_title" not in item["reasons"]:
                item["reasons"].append("duplicate_title")

    for item in audited:
        score = sum(RISK_WEIGHTS[reason] for reason in item["reasons"])
        item["risk_score"] = score
        if not item.get("article_found"):
            item["risk"] = "error"
        elif score >= 4:
            item["risk"] = "high"
        elif score >= 2:
            item["risk"] = "review"
        else:
            item["risk"] = "low"
    return sorted(audited, key=lambda item: (-item["risk_score"], item["id"]))


def build_report(posts, *, generated_at=None, errors=None):
    current = generated_at or dt.datetime.now(ZoneInfo("Asia/Seoul"))
    audited = audit_posts(posts)
    counts = {
        key: sum(1 for item in audited if item["risk"] == key)
        for key in ("high", "review", "low", "error")
    }
    return {
        "schema_version": 1,
        "generated_at": current.isoformat(timespec="seconds"),
        "policy_note": (
            "위험도는 정리 우선순위를 위한 내부 휴리스틱이며 "
            "Google AdSense의 글자 수·게시물 수 기준이 아니다."
        ),
        "counts": counts,
        "layout": {
            "maximum_ad_units_on_page": max(
                (int(item.get("page_ad_units") or 0) for item in audited),
                default=0,
            ),
            "pages_with_four_or_more_ad_units": sum(
                1 for item in audited if int(item.get("page_ad_units") or 0) >= 4
            ),
            "policy_note": (
                "광고 수는 내부 레이아웃 점검 신호다. Google은 숫자 제한보다 "
                "콘텐츠 방해·콘텐츠 대비 광고 비중·맥락을 판단한다."
            ),
            "pages_with_broken_internal_links": sum(
                1 for item in audited if item.get("broken_internal_links")
            ),
        },
        "posts": audited,
        "errors": list(errors or []),
    }


def render_markdown(report):
    lines = [
        "# Tistory 공개 콘텐츠 품질 감사",
        "",
        f"- 생성: {report['generated_at']}",
        f"- 공개 글: {len(report['posts'])}개",
        (
            "- 분류: 고위험 {high} · 검토 {review} · 낮음 {low} · 오류 {error}"
        ).format(**report["counts"]),
        (
            "- 광고 레이아웃: 페이지당 최대 {maximum_ad_units_on_page}개 · "
            "4개 이상인 글 {pages_with_four_or_more_ad_units}개"
        ).format(**report["layout"]),
        (
            "- 내부 링크: 삭제·비공개 글을 가리키는 페이지 "
            "{pages_with_broken_internal_links}개"
        ).format(**report["layout"]),
        f"- 주의: {report['policy_note']}",
        "",
        "## 고위험·검토 글",
        "",
        "| ID | 위험 | 제목 | 신호 |",
        "|---:|:---:|---|---|",
    ]
    for post in report["posts"]:
        if post["risk"] not in {"high", "review", "error"}:
            continue
        reasons = ", ".join(post["reasons"]) or "article_not_found"
        title = str(post["title"] or "(제목 없음)").replace("|", "\\|")
        lines.append(
            f"| {post['id']} | {post['risk']} | [{title}]({post['url']}) | {reasons} |"
        )
    return "\n".join(lines) + "\n"


def _fetch_posts(public_posts, *, timeout, max_workers):
    results = []
    errors = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_url, post["url"], timeout): post
            for post in public_posts
        }
        for future in as_completed(futures):
            post = futures[future]
            try:
                html_text = future.result()
                results.append(
                    parse_post_html(
                        html_text,
                        post_id=post["id"],
                        url=post["url"],
                    )
                )
            except Exception as exc:  # Network errors must remain visible in report.
                errors.append(
                    {
                        "id": post["id"],
                        "url": post["url"],
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
    return results, errors


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="공개 Tistory 글의 저가치 콘텐츠 위험 신호를 점검합니다."
    )
    parser.add_argument("--sitemap-url", default=SITEMAP_URL)
    parser.add_argument("--output", default="reports/tistory-content-audit.json")
    parser.add_argument(
        "--markdown-output",
        default="reports/tistory-content-audit.md",
    )
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--max-workers", type=int, default=8)
    args = parser.parse_args(argv)

    sitemap = fetch_url(args.sitemap_url, args.timeout)
    public_posts = parse_public_posts(sitemap)
    posts, errors = _fetch_posts(
        public_posts,
        timeout=args.timeout,
        max_workers=max(1, min(args.max_workers, 12)),
    )
    report = build_report(posts, errors=errors)

    output = Path(args.output)
    markdown_output = Path(args.markdown_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(
        "Tistory 품질 감사: 공개 {total} / 고위험 {high} / 검토 {review} / 오류 {error}".format(
            total=len(report["posts"]),
            **report["counts"],
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
