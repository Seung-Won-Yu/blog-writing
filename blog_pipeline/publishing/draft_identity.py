"""Canonical identities for daily news, automation, and evergreen guides."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


_DAILY_ID = re.compile(r"^(\d{4}-\d{2}-\d{2})$")
_AUTOMATION_ID = re.compile(r"^(\d{4}-\d{2}-\d{2})-automation$")
_GUIDE_ID = re.compile(r"^(\d{4}-\d{2}-\d{2})-guide$")

CATEGORY_TAXONOMY_V2_START = date(2026, 7, 22)
WEEKLY_GUIDE_SCHEDULE_START = date(2026, 7, 22)
LEGACY_CATEGORIES = {
    "daily_news": "데일리IT뉴스",
    "automation_case": "업무자동화",
    "evergreen_guide": "나만의 정리",
}
CURRENT_CATEGORIES = {
    "daily_news": "최신 IT·개발 소식",
    "automation_case": "자동화·실험",
    "evergreen_guide": "개발 가이드",
}


@dataclass(frozen=True)
class DraftIdentity:
    draft_id: str
    publish_date: str
    content_type: str
    content_label: str
    source: str


def category_for_content_type(content_type, publish_date=None):
    """Return the Tistory leaf category for a draft and taxonomy date."""
    key = str(content_type or "daily_news").strip()
    if key not in CURRENT_CATEGORIES:
        key = "daily_news"
    category_map = CURRENT_CATEGORIES
    if publish_date:
        try:
            published = date.fromisoformat(str(publish_date).strip())
        except ValueError:
            published = CATEGORY_TAXONOMY_V2_START
        if published < CATEGORY_TAXONOMY_V2_START:
            category_map = LEGACY_CATEGORIES
    return category_map[key]


def category_for_identity(identity):
    return category_for_content_type(
        identity.content_type,
        identity.publish_date,
    )


def regular_schedule_for_identity(identity):
    """Return the canonical KST schedule for a recurring draft, if eligible."""
    publish_day = date.fromisoformat(identity.publish_date)
    if identity.content_type == "daily_news":
        hour = "09:00:00"
    elif identity.content_type == "automation_case":
        if publish_day.weekday() != 5:
            return None
        hour = "18:00:00"
    elif identity.content_type == "evergreen_guide":
        if (
            publish_day < WEEKLY_GUIDE_SCHEDULE_START
            or publish_day.weekday() != 2
        ):
            return None
        hour = "18:00:00"
    else:
        return None
    return f"{identity.publish_date}T{hour}+09:00"


def resolve_draft_identity(draft_id, payload=None):
    """Resolve and validate every supported draft namespace."""
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
        if match:
            publish_date = match.group(1)
            identity = DraftIdentity(
                draft_id=value,
                publish_date=publish_date,
                content_type="automation_case",
                content_label="업무자동화 실험",
                source=f"data/automation_cases/{publish_date}.json",
            )
        else:
            match = _GUIDE_ID.fullmatch(value)
            if not match:
                raise ValueError(f"invalid draft id: {draft_id}")
            publish_date = match.group(1)
            identity = DraftIdentity(
                draft_id=value,
                publish_date=publish_date,
                content_type="evergreen_guide",
                content_label="개발 가이드",
                source=f"data/guides/{publish_date}.json",
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
    if identity.content_type in {"automation_case", "evergreen_guide"}:
        missing = [key for key in expected if not str(payload.get(key) or "").strip()]
        if missing:
            raise ValueError(
                f"{identity.content_type} draft identity is incomplete: "
                + ", ".join(missing)
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


def guide_draft_id(day_id):
    publish_date = date.fromisoformat(str(day_id)).isoformat()
    return f"{publish_date}-guide"
