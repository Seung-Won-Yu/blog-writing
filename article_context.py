"""Fetch bounded article context for the model without persisting source text."""

import ipaddress
import json
import re
import socket
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


DEFAULT_MAX_BYTES = 786_432
DEFAULT_PER_ITEM_CHARS = 1_800
DEFAULT_TOTAL_CHARS = 5_400


def _plain(value):
    return " ".join(unescape(str(value or "")).split())


def _trim(value, max_chars):
    text = _plain(value)
    if len(text) <= max_chars:
        return text, False
    cutoff = max(
        text.rfind(". ", 0, max_chars),
        text.rfind("다. ", 0, max_chars),
        text.rfind("요. ", 0, max_chars),
    )
    if cutoff < max_chars // 2:
        cutoff = max_chars - 1
    else:
        cutoff += 1
    return text[:cutoff].rstrip() + "…", True


class _ArticleParser(HTMLParser):
    BLOCK_TAGS = {"p", "li", "blockquote", "h2", "h3"}
    PRIMARY_TAGS = {"article", "main"}
    IGNORED_TAGS = {"script", "style", "nav", "footer", "header", "form", "svg", "noscript"}
    VOID_TAGS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.primary_depth = 0
        self.ignored_depth = 0
        self.active_block = None
        self.block_parts = []
        self.block_primary = False
        self.blocks = []
        self.json_ld_parts = None
        self.json_ld = []
        self.meta = {}

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attributes = {str(key).lower(): value for key, value in attrs}
        if tag == "script" and "ld+json" in str(attributes.get("type", "")).lower():
            self.json_ld_parts = []
            return
        if self.ignored_depth:
            if tag not in self.VOID_TAGS:
                self.ignored_depth += 1
            return
        if tag in self.IGNORED_TAGS:
            self.ignored_depth = 1
            return
        if tag in self.PRIMARY_TAGS:
            self.primary_depth += 1
        if tag == "meta":
            name = str(attributes.get("name") or attributes.get("property") or "").lower()
            content = _plain(attributes.get("content"))
            if name and content:
                self.meta[name] = content
        if tag in self.BLOCK_TAGS and self.active_block is None:
            self.active_block = tag
            self.block_parts = []
            self.block_primary = self.primary_depth > 0

    def handle_data(self, data):
        if self.json_ld_parts is not None:
            self.json_ld_parts.append(data)
        elif not self.ignored_depth and self.active_block:
            self.block_parts.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "script" and self.json_ld_parts is not None:
            self.json_ld.append("".join(self.json_ld_parts))
            self.json_ld_parts = None
            return
        if self.ignored_depth:
            self.ignored_depth -= 1
            return
        if tag == self.active_block:
            text = _plain(" ".join(self.block_parts))
            if text:
                self.blocks.append((self.block_primary, text))
            self.active_block = None
            self.block_parts = []
        if tag in self.PRIMARY_TAGS and self.primary_depth:
            self.primary_depth -= 1


def _find_article_body(value):
    if isinstance(value, dict):
        body = value.get("articleBody")
        if isinstance(body, str) and _plain(body):
            return _plain(body)
        for child in value.values():
            found = _find_article_body(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_article_body(child)
            if found:
                return found
    return ""


def extract_article_text(html_text, max_chars=DEFAULT_PER_ITEM_CHARS):
    parser = _ArticleParser()
    parser.feed(str(html_text or ""))
    parser.close()

    for raw_json in parser.json_ld:
        try:
            body = _find_article_body(json.loads(raw_json))
        except (TypeError, ValueError):
            continue
        if body:
            text, truncated = _trim(body, max_chars)
            return {"text": text, "method": "json-ld", "truncated": truncated}

    abstract = parser.meta.get("citation_abstract", "")
    if abstract:
        text, truncated = _trim(abstract, max_chars)
        return {"text": text, "method": "citation-abstract", "truncated": truncated}

    primary = [text for is_primary, text in parser.blocks if is_primary]
    rows = primary or [text for _is_primary, text in parser.blocks]
    rows = [row for row in rows if len(row) >= 12]
    deduplicated = []
    for row in rows:
        if row not in deduplicated:
            deduplicated.append(row)
    if deduplicated:
        text, truncated = _trim("\n".join(deduplicated), max_chars)
        return {"text": text, "method": "article", "truncated": truncated}

    description = parser.meta.get("og:description") or parser.meta.get("description") or ""
    text, truncated = _trim(description, max_chars)
    return {"text": text, "method": "meta-description", "truncated": truncated}


def validate_public_article_url(url, allowed_hosts, resolver=socket.getaddrinfo):
    parts = urlsplit(str(url or ""))
    if parts.scheme.lower() != "https":
        raise ValueError("기사 본문은 HTTPS 주소만 허용합니다.")
    if parts.username or parts.password:
        raise ValueError("사용자 정보가 포함된 기사 주소는 허용하지 않습니다.")
    hostname = (parts.hostname or "").lower().rstrip(".")
    allowed = {str(host).lower().rstrip(".") for host in allowed_hosts or []}
    if not hostname or hostname not in allowed:
        raise ValueError("허용되지 않은 기사 호스트입니다.")
    try:
        port = parts.port or 443
    except ValueError as exc:
        raise ValueError("기사 주소의 포트가 올바르지 않습니다.") from exc
    if port != 443:
        raise ValueError("기본 HTTPS 포트만 허용합니다.")

    addresses = resolver(hostname, port, type=socket.SOCK_STREAM)
    if not addresses:
        raise ValueError("기사 호스트를 확인할 수 없습니다.")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ValueError("공개 인터넷 주소가 아닌 기사 호스트입니다.")
    return hostname


class _SafeRedirectHandler(HTTPRedirectHandler):
    # Python 3.9's handler does not dispatch HTTP 308 by default.
    http_error_308 = HTTPRedirectHandler.http_error_302

    def __init__(self, allowed_hosts, resolver):
        super().__init__()
        self.allowed_hosts = allowed_hosts
        self.resolver = resolver
        self.redirect_count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.redirect_count += 1
        if self.redirect_count > 3:
            raise ValueError("기사 리다이렉트가 너무 많습니다.")
        validate_public_article_url(newurl, self.allowed_hosts, resolver=self.resolver)
        if code == 308:
            if req.get_method() not in {"GET", "HEAD"}:
                raise ValueError("지원하지 않는 기사 리다이렉트입니다.")
            redirected_headers = {
                key: value
                for key, value in req.headers.items()
                if key.lower() not in {"content-length", "content-type"}
            }
            return Request(
                newurl.replace(" ", "%20"),
                headers=redirected_headers,
                origin_req_host=req.origin_req_host,
                unverifiable=True,
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_article(
    url,
    allowed_hosts,
    timeout=8,
    max_bytes=DEFAULT_MAX_BYTES,
    resolver=socket.getaddrinfo,
    opener=None,
):
    validate_public_article_url(url, allowed_hosts, resolver=resolver)
    request = Request(
        url,
        headers={
            "User-Agent": "blog-writing-context/2.0",
            "Accept": "text/html,application/xhtml+xml;q=0.9",
        },
    )
    if opener is None:
        opener = build_opener(_SafeRedirectHandler(allowed_hosts, resolver)).open
    with opener(request, timeout=timeout) as response:
        final_url = response.geturl() if hasattr(response, "geturl") else url
        validate_public_article_url(final_url, allowed_hosts, resolver=resolver)
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError("HTML 기사가 아닙니다.")
        payload = response.read(max_bytes + 1)
        if len(payload) > max_bytes:
            raise ValueError("기사 본문이 허용 크기를 초과했습니다.")
        charset = response.headers.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def collect_article_contexts(
    inbox,
    allowed_hosts,
    fetcher=None,
    per_item_chars=DEFAULT_PER_ITEM_CHARS,
    total_chars=DEFAULT_TOTAL_CHARS,
):
    fetcher = fetcher or fetch_article
    remaining = max(0, int(total_chars))
    contexts = {}
    for item in (inbox.get("selected") or [])[:3]:
        if remaining <= 0:
            break
        try:
            html_text = fetcher(item.get("url", ""), allowed_hosts)
            extracted = extract_article_text(
                html_text, max_chars=min(int(per_item_chars), remaining)
            )
        except Exception:
            continue
        text = extracted.get("text", "")
        if not text:
            continue
        key = item.get("id") or item.get("url")
        contexts[key] = extracted
        remaining -= len(text)
    return contexts
