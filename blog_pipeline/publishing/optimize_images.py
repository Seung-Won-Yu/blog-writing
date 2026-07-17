"""Normalize daily editorial images before they enter Git history."""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from PIL import Image, ImageOps

from blog_pipeline.collection.news_pipeline import validate_day_id
from .draft_identity import resolve_draft_identity
from .editorial_format import image_kinds_for_day, is_lead_story


ROOT = Path(__file__).resolve().parents[2]
IMAGE_SIZE = (1200, 630)
IMAGE_FILE_BUDGET = 256 * 1024
IMAGE_SET_BUDGET = 1024 * 1024
LEAD_IMAGE_SET_BUDGET = 2 * 1024 * 1024
IMAGE_POLICY = "webp-v1"
IMAGE_POLICY_START = dt.date(2026, 7, 16)
QUALITY_STEPS = tuple(range(82, 9, -4))


def _atomic_write_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _safe_asset_path(root, value):
    root = Path(root).resolve()
    path = (root / str(value or "")).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"asset path escapes repository: {value}") from exc
    return path


def _draft_asset_path(root, draft_id, value):
    path = _safe_asset_path(root, value)
    expected = (
        Path(root).resolve()
        / "docs"
        / "tistory"
        / "assets"
        / str(draft_id)
    ).resolve()
    try:
        path.relative_to(expected)
    except ValueError as exc:
        raise ValueError(
            f"image is outside draft asset namespace {draft_id}: {value}"
        ) from exc
    return path


def _webp_url(value):
    parts = urlsplit(str(value or ""))
    path = str(Path(parts.path).with_suffix(".webp"))
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def save_bounded_webp(
    image,
    target,
    max_bytes=IMAGE_FILE_BUDGET,
    *,
    preserve_full_frame=False,
):
    """Write one 1200x630 WebP within the configured byte budget."""
    source = image.convert("RGB")
    if preserve_full_frame:
        contained = ImageOps.contain(
            source, IMAGE_SIZE, method=Image.Resampling.LANCZOS
        )
        normalized = Image.new("RGB", IMAGE_SIZE, "#fcfbf7")
        normalized.paste(
            contained,
            ((IMAGE_SIZE[0] - contained.width) // 2, (IMAGE_SIZE[1] - contained.height) // 2),
        )
    else:
        normalized = ImageOps.fit(
            source, IMAGE_SIZE, method=Image.Resampling.LANCZOS
        )
    payload = None
    selected_quality = None
    for quality in QUALITY_STEPS:
        buffer = io.BytesIO()
        normalized.save(buffer, "WEBP", quality=quality, method=6)
        candidate = buffer.getvalue()
        if len(candidate) <= max_bytes:
            payload = candidate
            selected_quality = quality
            break
    if payload is None:
        raise ValueError(
            f"image cannot fit {max_bytes} byte budget at {IMAGE_SIZE[0]}x{IMAGE_SIZE[1]}"
        )

    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(target)
    return {"bytes": len(payload), "quality": selected_quality}


def optimize_draft_images(draft_id, *, root=ROOT, preserve_sources=False):
    """Convert one daily or Saturday draft image set to bounded WebP files."""
    identity = resolve_draft_identity(draft_id)
    root = Path(root).resolve()
    day_path = root / identity.source
    if not day_path.is_file():
        raise FileNotFoundError(f"draft not found: {day_path}")
    day = json.loads(day_path.read_text(encoding="utf-8"))
    resolve_draft_identity(identity.draft_id, day)
    images = day.get("images")
    if not isinstance(images, dict):
        raise ValueError("day images must be an object")

    original_paths = []
    total_bytes = 0
    required_image_kinds = image_kinds_for_day(day)
    for kind in required_image_kinds:
        asset = images.get(kind)
        if not isinstance(asset, dict):
            raise ValueError(f"missing image asset: {kind}")
        source = _draft_asset_path(
            root, identity.draft_id, asset.get("path")
        )
        if not source.is_file():
            raise FileNotFoundError(f"missing image file: {source}")
        target = source.with_suffix(".webp")
        with Image.open(source) as opened:
            opened.load()
            is_compliant = (
                source == target
                and opened.format == "WEBP"
                and opened.size == IMAGE_SIZE
                and source.stat().st_size <= IMAGE_FILE_BUDGET
                and day.get("generation", {}).get("image_policy") == IMAGE_POLICY
            )
            source_image = None if is_compliant else opened.copy()
        if is_compliant:
            result = {
                "bytes": source.stat().st_size,
                "quality": asset.get("quality"),
            }
        else:
            result = save_bounded_webp(
                source_image,
                target,
                preserve_full_frame=is_lead_story(day),
            )
        total_bytes += result["bytes"]
        asset.update(
            {
                "path": target.relative_to(root).as_posix(),
                "url": _webp_url(asset.get("url")),
                "width": IMAGE_SIZE[0],
                "height": IMAGE_SIZE[1],
                "format": "webp",
                "bytes": result["bytes"],
                "quality": result["quality"],
            }
        )
        if source != target:
            original_paths.append(source)

    set_budget = LEAD_IMAGE_SET_BUDGET if is_lead_story(day) else IMAGE_SET_BUDGET
    if total_bytes > set_budget:
        raise ValueError(
            f"draft image set exceeds {set_budget} bytes: {total_bytes}"
        )
    generation = day.setdefault("generation", {})
    generation["image_policy"] = IMAGE_POLICY
    _atomic_write_json(day_path, day)
    if not preserve_sources:
        for path in original_paths:
            path.unlink(missing_ok=True)
    return {
        "day": identity.publish_date,
        "draft_id": identity.draft_id,
        "publish_date": identity.publish_date,
        "total_bytes": total_bytes,
        "images": images,
    }


def optimize_day_images(day_id, *, root=ROOT, preserve_sources=False):
    """Backward-compatible strict daily image optimizer."""
    day_id = validate_day_id(day_id)
    return optimize_draft_images(
        day_id, root=root, preserve_sources=preserve_sources
    )


def inspect_draft_images(draft_id, *, root=ROOT):
    """Check one draft image policy using committed paths and file sizes."""
    identity = resolve_draft_identity(draft_id)
    root = Path(root).resolve()
    day_path = root / identity.source
    day = json.loads(day_path.read_text(encoding="utf-8"))
    resolve_draft_identity(identity.draft_id, day)
    reasons = []
    if day.get("generation", {}).get("image_policy") != IMAGE_POLICY:
        reasons.append("missing_image_policy")
    images = day.get("images") if isinstance(day.get("images"), dict) else {}
    total_bytes = 0
    for kind in image_kinds_for_day(day):
        asset = images.get(kind)
        if not isinstance(asset, dict):
            reasons.append(f"missing_image:{kind}")
            continue
        try:
            path = _draft_asset_path(
                root, identity.draft_id, asset.get("path")
            )
        except ValueError:
            reasons.append(f"foreign_image_path:{kind}")
            continue
        if path.suffix.lower() != ".webp":
            reasons.append(f"non_webp_image:{kind}")
        if not path.is_file():
            reasons.append(f"missing_image_file:{kind}")
            continue
        size = path.stat().st_size
        total_bytes += size
        if size > IMAGE_FILE_BUDGET:
            reasons.append(f"oversized_image:{kind}")
    set_budget = LEAD_IMAGE_SET_BUDGET if is_lead_story(day) else IMAGE_SET_BUDGET
    if total_bytes > set_budget:
        reasons.append("oversized_image_set")
    return {
        "day": identity.publish_date,
        "draft_id": identity.draft_id,
        "publish_date": identity.publish_date,
        "total_bytes": total_bytes,
        "reasons": list(dict.fromkeys(reasons)),
    }


def inspect_day_images(day_id, *, root=ROOT):
    """Backward-compatible strict daily image inspection."""
    day_id = validate_day_id(day_id)
    return inspect_draft_images(day_id, root=root)


def _check_all(root):
    failures = []
    checked = 0
    roots = (
        (Path(root) / "data" / "days", False),
        (Path(root) / "data" / "automation_cases", True),
    )
    sources = []
    for source_root, is_automation in roots:
        sources.extend(
            (path, f"{path.stem}-automation" if is_automation else path.stem)
            for path in source_root.glob("*.json")
        )
    for path, draft_id in sorted(sources, key=lambda item: item[1]):
        try:
            day = json.loads(path.read_text(encoding="utf-8"))
            identity = resolve_draft_identity(draft_id, day)
            publish_date = dt.date.fromisoformat(identity.publish_date)
        except (OSError, TypeError, ValueError):
            failures.append(
                {
                    "day": path.stem,
                    "draft_id": draft_id,
                    "total_bytes": 0,
                    "reasons": ["invalid_draft_json"],
                }
            )
            continue
        if (
            publish_date < IMAGE_POLICY_START
            and day.get("generation", {}).get("image_policy") != IMAGE_POLICY
        ):
            continue
        checked += 1
        result = inspect_draft_images(draft_id, root=root)
        if result["reasons"]:
            failures.append(result)
    return {"checked": checked, "failures": failures}


def main(argv=None):
    parser = argparse.ArgumentParser(description="데일리 이미지를 WebP로 최적화합니다.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--today", action="store_true")
    group.add_argument("--day")
    group.add_argument("--draft-id")
    group.add_argument("--check-all", action="store_true")
    parser.add_argument("--preserve-sources", action="store_true")
    args = parser.parse_args(argv)

    if args.check_all:
        result = _check_all(ROOT)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result["failures"] else 0
    draft_id = (
        dt.datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
        if args.today
        else (args.draft_id or args.day)
    )
    result = optimize_draft_images(
        draft_id, root=ROOT, preserve_sources=args.preserve_sources
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
