"""Normalize daily editorial images before they enter Git history."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import re
import shutil
import tempfile
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from PIL import Image, ImageOps

from blog_pipeline.collection.news_pipeline import validate_day_id
from .draft_identity import resolve_draft_identity
from .editorial_format import image_kinds_for_day, is_lead_story
from .editorial_quality import measurement_digest


ROOT = Path(__file__).resolve().parents[2]
IMAGE_SIZE = (1200, 630)
IMAGE_FILE_BUDGET = 256 * 1024
IMAGE_SET_BUDGET = 1024 * 1024
LEAD_IMAGE_SET_BUDGET = 2 * 1024 * 1024
IMAGE_POLICY = "webp-v1"
IMAGE_POLICY_START = dt.date(2026, 7, 16)
IMAGE_CONTENT_POLICY_START = dt.date(2026, 7, 19)
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


def _file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _path_collision_key(path):
    return unicodedata.normalize("NFC", str(Path(path).resolve())).casefold()


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
    source_paths = []
    target_paths = []
    source_digests = []
    for kind in required_image_kinds:
        asset = images.get(kind)
        if not isinstance(asset, dict):
            raise ValueError(f"missing image asset: {kind}")
        source = _draft_asset_path(root, identity.draft_id, asset.get("path"))
        if not source.is_file():
            raise FileNotFoundError(f"missing image file: {source}")
        source_paths.append(source)
        target_paths.append(source.with_suffix(".webp"))
        source_digests.append(_file_sha256(source))
    if (
        len({_path_collision_key(path) for path in source_paths}) != len(source_paths)
        or len({_path_collision_key(path) for path in target_paths}) != len(target_paths)
        or len(set(source_digests)) != len(source_digests)
    ):
        raise ValueError("image source, content, and WebP target must be unique")

    with tempfile.TemporaryDirectory(
        prefix=".image-optimize-", dir=root
    ) as temporary_directory:
        stage_root = Path(temporary_directory)
        staged_outputs = []
        for index, kind in enumerate(required_image_kinds):
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
                digest_path = source
            else:
                staged_target = stage_root / f"{index:02d}-{target.name}"
                result = save_bounded_webp(
                    source_image,
                    staged_target,
                    preserve_full_frame=is_lead_story(day),
                )
                staged_outputs.append((staged_target, target))
                digest_path = staged_target
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
                    "sha256": _file_sha256(digest_path),
                }
            )
            if asset.get("origin") in {"capture", "annotated_capture"}:
                asset["capture_sha256"] = asset["sha256"]
            if asset.get("origin") == "measured_chart":
                visual = day.get("visual") if isinstance(day.get("visual"), dict) else {}
                briefs = visual.get("assets") if isinstance(visual.get("assets"), list) else []
                try:
                    visual_index = int(kind.removeprefix("visual_")) - 1
                    brief = briefs[visual_index]
                except (ValueError, IndexError, TypeError):
                    raise ValueError(f"missing measured chart brief: {kind}")
                asset["measurement_sha256"] = measurement_digest(brief)
            if source != target:
                original_paths.append(source)

        set_budget = LEAD_IMAGE_SET_BUDGET if is_lead_story(day) else IMAGE_SET_BUDGET
        output_digests = [
            str(images[kind].get("sha256") or "") for kind in required_image_kinds
        ]
        if len(set(output_digests)) != len(output_digests):
            raise ValueError("optimized image content must be unique")
        if total_bytes > set_budget:
            raise ValueError(
                f"draft image set exceeds {set_budget} bytes: {total_bytes}"
            )
        generation = day.setdefault("generation", {})
        generation["image_policy"] = IMAGE_POLICY

        backups = []
        created_targets = []
        try:
            for index, (staged_target, target) in enumerate(staged_outputs):
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    backup = stage_root / f"backup-{index:02d}-{target.name}"
                    shutil.copy2(target, backup)
                    backups.append((backup, target))
                else:
                    created_targets.append(target)
                staged_target.replace(target)
            _atomic_write_json(day_path, day)
        except Exception:
            for target in created_targets:
                target.unlink(missing_ok=True)
            for backup, target in reversed(backups):
                shutil.copy2(backup, target)
            day_path.with_name(day_path.name + ".tmp").unlink(missing_ok=True)
            raise
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
    strict_content = dt.date.fromisoformat(identity.publish_date) >= IMAGE_CONTENT_POLICY_START
    raw_generation = day.get("generation")
    generation = raw_generation if isinstance(raw_generation, dict) else {}
    if raw_generation is not None and not isinstance(raw_generation, dict):
        reasons.append("invalid_image_manifest")
    if generation.get("image_policy") != IMAGE_POLICY:
        reasons.append("missing_image_policy")
    images = day.get("images") if isinstance(day.get("images"), dict) else {}
    total_bytes = 0
    inspected_paths = []
    inspected_urls = []
    inspected_digests = []
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
        if strict_content:
            try:
                with Image.open(path) as opened:
                    opened.load()
                    actual_format = opened.format
                    actual_size = opened.size
                    grayscale = opened.convert("L")
                    grayscale_extrema = grayscale.getextrema()
                    grayscale_entropy = grayscale.entropy()
            except (OSError, ValueError):
                reasons.append(f"invalid_image_file:{kind}")
                continue
            if actual_format != "WEBP":
                reasons.append(f"invalid_image_format:{kind}")
            if actual_size != IMAGE_SIZE:
                reasons.append(f"invalid_image_dimensions:{kind}")
            if (
                grayscale_extrema[1] - grayscale_extrema[0] < 12
                or grayscale_entropy < 0.2
            ):
                reasons.append(f"low_information_image:{kind}")
            if (
                str(asset.get("format") or "").casefold() != "webp"
                or _as_int(asset.get("width")) != IMAGE_SIZE[0]
                or _as_int(asset.get("height")) != IMAGE_SIZE[1]
                or _as_int(asset.get("bytes")) != size
            ):
                reasons.append(f"image_metadata_mismatch:{kind}")
            alt = " ".join(str(asset.get("alt") or "").split())
            if len(alt) < 20 or not re.search(r"[가-힣]", alt):
                reasons.append(f"missing_image_alt:{kind}")
            filename = path.name
            if not re.search(r"[가-힣]", filename):
                reasons.append(f"generic_image_filename:{kind}")
            parsed_url = urlsplit(str(asset.get("url") or ""))
            url_filename = Path(unquote(parsed_url.path)).name
            if (
                parsed_url.scheme.lower() not in {"http", "https"}
                or not parsed_url.netloc
                or url_filename != filename
            ):
                reasons.append(f"image_url_mismatch:{kind}")
            actual_digest = _file_sha256(path)
            if str(asset.get("sha256") or "").lower() != actual_digest:
                reasons.append(f"image_digest_mismatch:{kind}")
            inspected_paths.append(_path_collision_key(path))
            inspected_urls.append(
                unicodedata.normalize("NFC", str(asset.get("url") or "")).casefold()
            )
            inspected_digests.append(actual_digest)
    if (
        len(set(inspected_paths)) != len(inspected_paths)
        or len(set(inspected_urls)) != len(inspected_urls)
        or len(set(inspected_digests)) != len(inspected_digests)
    ):
        reasons.append("duplicate_image_asset")
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
        generation = day.get("generation") if isinstance(day.get("generation"), dict) else {}
        if (
            publish_date < IMAGE_POLICY_START
            and generation.get("image_policy") != IMAGE_POLICY
        ):
            continue
        checked += 1
        try:
            result = inspect_draft_images(draft_id, root=root)
        except (
            OSError,
            AttributeError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            OverflowError,
        ):
            result = {
                "day": identity.publish_date,
                "draft_id": identity.draft_id,
                "publish_date": identity.publish_date,
                "total_bytes": 0,
                "reasons": ["invalid_image_manifest"],
            }
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
