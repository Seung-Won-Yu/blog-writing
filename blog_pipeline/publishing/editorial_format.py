"""Shared rules for legacy digests and the single-story deep format."""

from __future__ import annotations

import re


LEAD_STORY_FORMAT = "lead-story-v1"
LEGACY_IMAGE_KINDS = ("cover", "story_1", "story_2", "story_3")
_VISUAL_KIND = re.compile(r"^visual_(\d+)$")


def is_lead_story(day):
    return isinstance(day, dict) and day.get("format") == LEAD_STORY_FORMAT


def lead_visual_kinds(images):
    if not isinstance(images, dict):
        return []
    numbered = []
    for kind in images:
        match = _VISUAL_KIND.fullmatch(str(kind))
        if match:
            numbered.append((int(match.group(1)), str(kind)))
    return [kind for _, kind in sorted(numbered)]


def image_kinds_for_day(day):
    if not is_lead_story(day):
        return list(LEGACY_IMAGE_KINDS)
    images = day.get("images") if isinstance(day.get("images"), dict) else {}
    return ["cover", *lead_visual_kinds(images)]
