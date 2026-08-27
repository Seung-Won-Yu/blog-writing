"""Canonical identities for daily news, automation, and evergreen guides."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


_DAILY_ID = re.compile(r"^(\d{4}-\d{2}-\d{2})$")
_AUTOMATION_ID = re.compile(r"^(\d{4}-\d{2}-\d{2})-automation$")
_GUIDE_ID = re.compile(r"^(\d{4}-\d{2}-\d{2})-guide$")
_PROJECT_ID = re.compile(r"^(\d{4}-\d{2}-\d{2})-project$")

CATEGORY_TAXONOMY_V2_START = date(2026, 7, 22)
EVERGREEN_DAILY_START = date(2026, 8, 25)
WEEKLY_EDITORIAL_LANES_START = date(2026, 8, 31)
CURIOSITY_EDITORIAL_LANES_START = date(2026, 9, 1)
WEEKLY_GUIDE_SCHEDULE_START = date(2026, 7, 22)
FRIDAY_AUTOMATION_SCHEDULE_START = date(2026, 8, 28)
MANUAL_REVIEW_PUBLICATION_START = date(2026, 8, 28)
LEGACY_CATEGORIES = {
    "daily_news": "데일리IT뉴스",
    "automation_case": "업무자동화",
    "evergreen_guide": "나만의 정리",
    "project_log": "프로젝트·회고",
}
V2_CATEGORIES = {
    "daily_news": "최신 IT·개발 소식",
    "automation_case": "자동화·실험",
    "evergreen_guide": "개발 가이드",
    "project_log": "프로젝트·회고",
}
CURRENT_CATEGORIES = {
    "daily_news": "IT 트렌드 해설",
    "automation_case": "자동화·실험",
    "evergreen_guide": "개발 가이드",
    "project_log": "프로젝트·회고",
}
CURIOSITY_CATEGORY = "궁금한 IT 원리"


@dataclass(frozen=True)
class DraftIdentity:
    draft_id: str
    publish_date: str
    content_type: str
    content_label: str
    source: str


def category_for_content_type(content_type, publish_date=None):
    """Return the category recorded by the taxonomy active on publish day.

    Historical source metadata is immutable even when live Tistory categories
    are renamed later.  The 2026-08-25 redesign therefore starts a new epoch
    instead of retroactively validating July and August drafts against it.
    """
    key = str(content_type or "daily_news").strip()
    if key not in CURRENT_CATEGORIES:
        key = "daily_news"
    if not publish_date:
        return CURRENT_CATEGORIES[key]
    try:
        published = date.fromisoformat(str(publish_date).strip())
    except ValueError:
        return CURRENT_CATEGORIES[key]
    if published < CATEGORY_TAXONOMY_V2_START:
        return LEGACY_CATEGORIES[key]
    if published < EVERGREEN_DAILY_START:
        return V2_CATEGORIES[key]
    if key == "daily_news":
        if (
            published >= CURIOSITY_EDITORIAL_LANES_START
            and published.weekday() in {1, 3}
        ):
            return CURIOSITY_CATEGORY
        if (
            published >= WEEKLY_EDITORIAL_LANES_START
            and published.weekday() == 0
        ):
            return CURRENT_CATEGORIES["evergreen_guide"]
    return CURRENT_CATEGORIES[key]


def content_label_for_daily(publish_date):
    """Keep historical labels stable while switching the recurring lane."""
    published = date.fromisoformat(str(publish_date).strip())
    if (
        published >= CURIOSITY_EDITORIAL_LANES_START
        and published.weekday() in {1, 3}
    ):
        return CURIOSITY_CATEGORY
    if (
        published >= WEEKLY_EDITORIAL_LANES_START
        and published.weekday() == 0
    ):
        return "개발 가이드"
    return "IT 트렌드 해설" if published >= EVERGREEN_DAILY_START else "뉴스 심층글"


def category_for_identity(identity):
    return category_for_content_type(
        identity.content_type,
        identity.publish_date,
    )


def editorial_lane_for_identity(identity):
    """Return the future weekly promise made to a reader for this draft."""
    publish_day = date.fromisoformat(identity.publish_date)
    if (
        identity.content_type == "daily_news"
        and publish_day >= WEEKLY_EDITORIAL_LANES_START
    ):
        lanes = {0: "evergreen_problem", 2: "change_explainer"}
        if publish_day >= CURIOSITY_EDITORIAL_LANES_START:
            lanes.update(
                {
                    1: "curiosity_mechanism",
                    3: "curiosity_myth_history",
                }
            )
        return lanes.get(publish_day.weekday(), "")
    if (
        identity.content_type == "automation_case"
        and publish_day >= FRIDAY_AUTOMATION_SCHEDULE_START
    ):
        return "executed_experiment"
    return ""


def is_regular_automation_day(publish_day):
    """Keep historical Saturday cases valid; use Friday from the new schedule."""
    if publish_day >= FRIDAY_AUTOMATION_SCHEDULE_START:
        return publish_day.weekday() == 4
    return publish_day.weekday() == 5


def publication_mode_for_identity(identity):
    """Return how a completed draft is handed off to the Tistory owner."""
    publish_day = date.fromisoformat(identity.publish_date)
    if (
        publish_day >= MANUAL_REVIEW_PUBLICATION_START
        and identity.content_type in {"daily_news", "automation_case", "project_log"}
    ):
        return "manual_review"
    return "scheduled"


def regular_schedule_for_identity(identity):
    """Return the canonical KST schedule for a recurring draft, if eligible."""
    publish_day = date.fromisoformat(identity.publish_date)
    if identity.content_type == "daily_news":
        regular_days = {0, 2}
        if publish_day >= CURIOSITY_EDITORIAL_LANES_START:
            regular_days.update({1, 3})
        if (
            publish_day >= WEEKLY_EDITORIAL_LANES_START
            and publish_day.weekday() not in regular_days
        ):
            return None
        hour = "09:00:00"
    elif identity.content_type == "automation_case":
        if not is_regular_automation_day(publish_day):
            return None
        hour = (
            "09:00:00"
            if publish_day >= MANUAL_REVIEW_PUBLICATION_START
            else "18:00:00"
        )
    elif identity.content_type == "evergreen_guide":
        if (
            publish_day < WEEKLY_GUIDE_SCHEDULE_START
            or publish_day.weekday() != 2
        ):
            return None
        hour = "18:00:00"
    elif identity.content_type == "project_log":
        if publish_day.weekday() != 5:
            return None
        hour = (
            "09:00:00"
            if publish_day >= MANUAL_REVIEW_PUBLICATION_START
            else "18:00:00"
        )
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
            content_label=content_label_for_daily(publish_date),
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
            if match:
                publish_date = match.group(1)
                identity = DraftIdentity(
                    draft_id=value,
                    publish_date=publish_date,
                    content_type="evergreen_guide",
                    content_label="개발 가이드",
                    source=f"data/guides/{publish_date}.json",
                )
            else:
                match = _PROJECT_ID.fullmatch(value)
                if not match:
                    raise ValueError(f"invalid draft id: {draft_id}")
                publish_date = match.group(1)
                identity = DraftIdentity(
                    draft_id=value,
                    publish_date=publish_date,
                    content_type="project_log",
                    content_label="프로젝트 제작기",
                    source=f"data/project_logs/{publish_date}.json",
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
    if identity.content_type in {
        "automation_case",
        "evergreen_guide",
        "project_log",
    }:
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


def project_draft_id(day_id):
    publish_date = date.fromisoformat(str(day_id)).isoformat()
    return f"{publish_date}-project"
