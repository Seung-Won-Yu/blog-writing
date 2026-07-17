"""Canonical identities for daily news and Saturday automation drafts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


_DAILY_ID = re.compile(r"^(\d{4}-\d{2}-\d{2})$")
_AUTOMATION_ID = re.compile(r"^(\d{4}-\d{2}-\d{2})-automation$")


@dataclass(frozen=True)
class DraftIdentity:
    draft_id: str
    publish_date: str
    content_type: str
    content_label: str
    source: str


def resolve_draft_identity(draft_id, payload=None):
    """Resolve and validate the only two supported draft namespaces."""
    value = str(draft_id or "").strip()
    match = _DAILY_ID.fullmatch(value)
    if match:
        publish_date = match.group(1)
        identity = DraftIdentity(
            draft_id=value,
            publish_date=publish_date,
            content_type="daily_news",
            content_label="뉴스 심층글",
            source=f"data/days/{publish_date}.json",
        )
    else:
        match = _AUTOMATION_ID.fullmatch(value)
        if not match:
            raise ValueError(f"invalid draft id: {draft_id}")
        publish_date = match.group(1)
        identity = DraftIdentity(
            draft_id=value,
            publish_date=publish_date,
            content_type="automation_case",
            content_label="업무자동화 실험",
            source=f"data/automation_cases/{publish_date}.json",
        )

    date.fromisoformat(identity.publish_date)
    if not isinstance(payload, dict):
        return identity

    expected = {
        "draft_id": identity.draft_id,
        "publish_date": identity.publish_date,
        "content_type": identity.content_type,
        "content_label": identity.content_label,
    }
    if identity.content_type == "automation_case":
        missing = [key for key in expected if not str(payload.get(key) or "").strip()]
        if missing:
            raise ValueError(
                "automation draft identity is incomplete: " + ", ".join(missing)
            )
    for key, expected_value in expected.items():
        actual = str(payload.get(key) or "").strip()
        if actual and actual != expected_value:
            raise ValueError(
                f"draft identity mismatch for {key}: {actual} != {expected_value}"
            )
    return identity


def automation_draft_id(day_id):
    publish_date = date.fromisoformat(str(day_id)).isoformat()
    return f"{publish_date}-automation"
