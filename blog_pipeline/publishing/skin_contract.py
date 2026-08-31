"""Validate the shared Tistory skin and project-article markup contract."""

from __future__ import annotations

import hashlib
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKIN_CONTRACT_VERSION = "project-reader-v1"
REQUIRED_PROJECT_SKIN_RULES = (
    ".daily-digest-post .digest-project-aid {",
    ".daily-digest-post .digest-project-aid > h2 {",
    ".daily-digest-post .digest-project-glossary {",
    ".daily-digest-post .digest-project-glossary div {",
    ".daily-digest-post .digest-project-glossary dt {",
    ".daily-digest-post .digest-project-glossary dd {",
)


def _read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def _sha256_text(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def inspect_skin_contract(root=ROOT):
    """Require the canonical skin, custom layer, and preview copy to agree."""
    root = Path(root)
    style = _read_text(root / "design" / "tistory" / "style.css")
    layer = _read_text(root / "design" / "tistory" / "skin-layer.css")
    preview = _read_text(root / "docs" / "preview" / "tistory-style.css")
    reasons = []

    if not style or not layer or not preview:
        reasons.append("missing_skin_css")
    if style and layer and not style.endswith(layer):
        reasons.append("invalid_skin_layer")
    if style and any(rule not in style for rule in REQUIRED_PROJECT_SKIN_RULES):
        reasons.append("missing_project_skin_contract")
    if layer and any(rule not in layer for rule in REQUIRED_PROJECT_SKIN_RULES):
        reasons.append("missing_project_skin_contract")
    if style and preview and style != preview:
        reasons.append("stale_preview_skin_css")

    reasons = list(dict.fromkeys(reasons))
    return {
        "version": SKIN_CONTRACT_VERSION,
        "status": "COMPLETE" if not reasons else "PARTIAL",
        "reasons": reasons,
        "sha256": _sha256_text(style) if style else "",
    }


class _ProjectMarkupParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.project_aids = 0
        self.project_glossaries = 0
        self.images = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        classes = set(str(values.get("class") or "").split())
        if "digest-project-aid" in classes:
            self.project_aids += 1
        if "digest-project-glossary" in classes:
            self.project_glossaries += 1
        if tag == "img":
            self.images.append(values)

    def handle_data(self, data):
        text = str(data or "").strip()
        if text:
            self.text.append(text)


def inspect_project_html_contract(body_html, image_assets):
    """Fail closed when a project draft loses its reader aids or image roles."""
    parser = _ProjectMarkupParser()
    try:
        parser.feed(str(body_html or ""))
    except (TypeError, ValueError):
        return {
            "status": "PARTIAL",
            "reasons": ["invalid_project_markup"],
        }

    reasons = []
    visible_text = " ".join(parser.text)
    if (
        parser.project_aids != 1
        or parser.project_glossaries != 1
        or "30초 요약" not in visible_text
        or "먼저 알아둘 말" not in visible_text
    ):
        reasons.append("project_reader_aid_markup")

    assets = [item for item in image_assets or [] if isinstance(item, dict)]
    expected_urls = [str(item.get("url") or "").strip() for item in assets]
    expected_urls = [url for url in expected_urls if url]
    images = parser.images
    actual_urls = [str(item.get("src") or "").strip() for item in images]
    cover_images = [
        item
        for item in images
        if "digest-cover-image" in str(item.get("class") or "").split()
    ]
    content_images = [
        item
        for item in images
        if "digest-content-image" in str(item.get("class") or "").split()
    ]

    if len(cover_images) != 1 or cover_images[0].get("loading") != "eager":
        reasons.append("project_image_loading_contract")
    if len(content_images) != max(0, len(expected_urls) - 1) or any(
        item.get("loading") != "lazy" for item in content_images
    ):
        reasons.append("project_image_loading_contract")
    if any(
        not str(item.get("alt") or "").strip()
        or not str(item.get("width") or "").isdigit()
        or not str(item.get("height") or "").isdigit()
        for item in cover_images + content_images
    ):
        reasons.append("project_image_accessibility_contract")
    if expected_urls != actual_urls or len(set(actual_urls)) != len(actual_urls):
        reasons.append("project_image_url_mismatch")

    reasons = list(dict.fromkeys(reasons))
    return {
        "status": "COMPLETE" if not reasons else "PARTIAL",
        "reasons": reasons,
    }
