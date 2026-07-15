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


ROOT = Path(__file__).resolve().parents[2]
IMAGE_SIZE = (1200, 630)
IMAGE_FILE_BUDGET = 256 * 1024
IMAGE_SET_BUDGET = 1024 * 1024
IMAGE_POLICY = "webp-v1"
IMAGE_POLICY_START = dt.date(2026, 7, 16)
REQUIRED_IMAGE_KINDS = ("cover", "story_1", "story_2", "story_3")
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


def _webp_url(value):
    parts = urlsplit(str(value or ""))
    path = str(Path(parts.path).with_suffix(".webp"))
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def save_bounded_webp(image, target, max_bytes=IMAGE_FILE_BUDGET):
    """Write one 1200x630 WebP within the configured byte budget."""
    normalized = ImageOps.fit(
        image.convert("RGB"), IMAGE_SIZE, method=Image.Resampling.LANCZOS
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


def optimize_day_images(day_id, *, root=ROOT, preserve_sources=False):
    """Convert the referenced daily image set to bounded WebP files."""
    day_id = validate_day_id(day_id)
    root = Path(root).resolve()
    day_path = root / "data" / "days" / f"{day_id}.json"
    if not day_path.is_file():
        raise FileNotFoundError(f"day not found: {day_path}")
    day = json.loads(day_path.read_text(encoding="utf-8"))
    images = day.get("images")
    if not isinstance(images, dict):
        raise ValueError("day images must be an object")

    original_paths = []
    total_bytes = 0
    for kind in REQUIRED_IMAGE_KINDS:
        asset = images.get(kind)
        if not isinstance(asset, dict):
            raise ValueError(f"missing image asset: {kind}")
        source = _safe_asset_path(root, asset.get("path"))
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
            result = save_bounded_webp(source_image, target)
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

    if total_bytes > IMAGE_SET_BUDGET:
        raise ValueError(
            f"daily image set exceeds {IMAGE_SET_BUDGET} bytes: {total_bytes}"
        )
    generation = day.setdefault("generation", {})
    generation["image_policy"] = IMAGE_POLICY
    _atomic_write_json(day_path, day)
    if not preserve_sources:
        for path in original_paths:
            path.unlink(missing_ok=True)
    return {"day": day_id, "total_bytes": total_bytes, "images": images}


def inspect_day_images(day_id, *, root=ROOT):
    """Check the image policy using only committed paths and file sizes."""
    day_id = validate_day_id(day_id)
    root = Path(root).resolve()
    day_path = root / "data" / "days" / f"{day_id}.json"
    day = json.loads(day_path.read_text(encoding="utf-8"))
    reasons = []
    if day.get("generation", {}).get("image_policy") != IMAGE_POLICY:
        reasons.append("missing_image_policy")
    images = day.get("images") if isinstance(day.get("images"), dict) else {}
    total_bytes = 0
    for kind in REQUIRED_IMAGE_KINDS:
        asset = images.get(kind)
        if not isinstance(asset, dict):
            reasons.append(f"missing_image:{kind}")
            continue
        try:
            path = _safe_asset_path(root, asset.get("path"))
        except ValueError:
            reasons.append(f"unsafe_image_path:{kind}")
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
    if total_bytes > IMAGE_SET_BUDGET:
        reasons.append("oversized_image_set")
    return {
        "day": day_id,
        "total_bytes": total_bytes,
        "reasons": list(dict.fromkeys(reasons)),
    }


def _check_all(root):
    failures = []
    checked = 0
    for path in sorted((Path(root) / "data" / "days").glob("*.json")):
        try:
            day = json.loads(path.read_text(encoding="utf-8"))
            file_day = dt.date.fromisoformat(validate_day_id(path.stem))
        except (OSError, TypeError, ValueError):
            failures.append(
                {"day": path.stem, "total_bytes": 0, "reasons": ["invalid_day_json"]}
            )
            continue
        if (
            file_day < IMAGE_POLICY_START
            and day.get("generation", {}).get("image_policy") != IMAGE_POLICY
        ):
            continue
        checked += 1
        result = inspect_day_images(path.stem, root=root)
        if result["reasons"]:
            failures.append(result)
    return {"checked": checked, "failures": failures}


def main(argv=None):
    parser = argparse.ArgumentParser(description="데일리 이미지를 WebP로 최적화합니다.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--today", action="store_true")
    group.add_argument("--day")
    group.add_argument("--check-all", action="store_true")
    parser.add_argument("--preserve-sources", action="store_true")
    args = parser.parse_args(argv)

    if args.check_all:
        result = _check_all(ROOT)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result["failures"] else 0
    day_id = (
        dt.datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
        if args.today
        else args.day
    )
    result = optimize_day_images(
        day_id, root=ROOT, preserve_sources=args.preserve_sources
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
