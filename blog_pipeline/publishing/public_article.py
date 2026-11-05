"""Read this blog's public article HTML without app panels, login, cookies or JS."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ..collection.search_demand import ROOT

MAX_BYTES = 3_000_000
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
BLOCK = {"p", "div", "h1", "h2", "h3", "li", "tr", "td", "th", "section", "blockquote", "pre", "br"}


def validate_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "won0322.tistory.com" or not re.fullmatch(r"/[0-9]+/?", parsed.path) or parsed.query or parsed.fragment:
        raise ValueError("Only an exact public numeric article URL on won0322.tistory.com is allowed")
    return url


class PublicRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        if newurl.rstrip("/") != req.full_url.rstrip("/"):
            raise ValueError("PUBLIC_ARTICLE_MISMATCH: redirect changed article")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.chunks, self.title = [], [], []
        self.depth = None
        self.done = False
        self.canonical = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical = attrs.get("href")
        if not self.done and self.depth is None and {"tt_article_useless_p_margin", "contents_style"} & set(attrs.get("class", "").split()):
            self.depth = len(self.stack)
        if self.depth is not None and tag in BLOCK:
            self.chunks.append("\n")
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag not in self.stack:
            return
        while self.stack:
            if self.stack.pop() == tag:
                break
        if self.depth is not None:
            if tag in BLOCK:
                self.chunks.append("\n")
            if len(self.stack) <= self.depth:
                self.depth, self.done = None, True

    def handle_data(self, value):
        if self.stack and self.stack[-1] == "title":
            self.title.append(value)
        if self.depth is not None and not {"script", "style", "noscript", "iframe", "form"} & set(self.stack):
            self.chunks.append(value)


def parse_article(html, url):
    parser = ArticleParser()
    parser.feed(html)
    text = "\n".join(" ".join(line.split()) for line in "".join(parser.chunks).splitlines() if line.strip())
    if not parser.done or len(text) < 100:
        raise ValueError("PUBLIC_BODY_NOT_FOUND: login, error page or unsupported template")
    if parser.canonical and parser.canonical.rstrip("/") != url.rstrip("/"):
        raise ValueError("PUBLIC_ARTICLE_MISMATCH")
    return {"title": " ".join(parser.title).strip(), "text": text}


def fetch_article(url):
    validate_url(url)
    # No cookie handler, browser profile, authorization header, or JavaScript.
    opener = build_opener(PublicRedirects())
    req = Request(url, headers={"User-Agent": "BlogWritingPublicReview/1.0", "Accept": "text/html"})
    with opener.open(req, timeout=20) as response:
        validate_url(response.url)
        if response.status != 200 or response.headers.get_content_type() != "text/html":
            raise ValueError("Expected public HTML HTTP 200")
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError("Public HTML exceeds size limit")
        article = parse_article(body.decode(response.headers.get_content_charset() or "utf-8"), response.url)
    return {"status": "READ", "url": url, "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "method": "unauthenticated_public_https", "html_sha256": hashlib.sha256(body).hexdigest(),
            "text_sha256": hashlib.sha256(article["text"].encode()).hexdigest(), **article}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.resolve().is_relative_to(ROOT.resolve()):
        parser.error("Keep raw public evidence outside the repository (for example /tmp/blog-writing-qa/DATE/)")
    try:
        result = fetch_article(args.url)
    except (OSError, ValueError, UnicodeError) as exc:
        result = {"status": "READ_UNAVAILABLE", "url": args.url, "reason": str(exc)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "text"}, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "READ" else 1


if __name__ == "__main__":
    raise SystemExit(main())
