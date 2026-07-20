"""Stage and verify the complete Git-backed handoff for one draft."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .daily_guard import ROOT
from .draft_identity import resolve_draft_identity


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return {}


def _safe_relative_path(value, root):
    root = Path(root).resolve()
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text)
    if path.is_absolute():
        return None
    try:
        relative = (root / path).resolve().relative_to(root)
    except ValueError:
        return None
    return relative if relative != Path(".") else None


def required_publish_bundle_paths(draft_id, *, root=ROOT):
    """Return every repository path required by the copy-and-preview handoff."""
    root = Path(root)
    identity = resolve_draft_identity(draft_id)
    meta_relative = Path("docs") / "tistory" / f"{identity.draft_id}.json"
    meta = _read_json(root / meta_relative)
    defaults = {
        "source": identity.source,
        "html": f"docs/tistory/{identity.draft_id}.html",
        "before_ad_html": f"docs/tistory/{identity.draft_id}-before-ad.html",
        "after_ad_html": f"docs/tistory/{identity.draft_id}-after-ad.html",
        "adfit_html": f"docs/tistory/{identity.draft_id}-adfit.html",
    }
    values = [
        defaults["source"],
        str(meta_relative),
        *(meta.get(key) or fallback for key, fallback in defaults.items() if key != "source"),
        f"docs/preview/{identity.draft_id}.html",
        "docs/index.html",
        "docs/integration.html",
    ]
    values.extend(
        asset.get("path")
        for asset in meta.get("image_assets", [])
        if isinstance(asset, dict)
    )

    paths = []
    seen = set()
    for value in values:
        relative = _safe_relative_path(value, root)
        if relative is None:
            continue
        text = relative.as_posix()
        if text not in seen:
            seen.add(text)
            paths.append(text)
    return paths


def _git_paths(root, *args, paths):
    result = subprocess.run(
        ["git", *args, "-z", "--", *paths],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return {item for item in result.stdout.split("\0") if item}


def publish_bundle_tracking_reasons(draft_id, *, root=ROOT):
    """Reject missing, untracked, or unstaged files in a publish bundle."""
    root = Path(root)
    paths = required_publish_bundle_paths(draft_id, root=root)
    reasons = []
    missing = {path for path in paths if not (root / path).is_file()}
    for path in sorted(missing):
        reasons.append(f"missing_publish_bundle:{path}")
    if not paths:
        return ["empty_publish_bundle"]
    try:
        tracked = _git_paths(root, "ls-files", "--cached", paths=paths)
        unstaged = _git_paths(root, "diff", "--name-only", paths=paths)
    except (OSError, subprocess.CalledProcessError):
        return [*reasons, "git_publish_bundle_check_failed"]
    for path in paths:
        if path not in missing and path not in tracked:
            reasons.append(f"untracked_publish_bundle:{path}")
        elif path in unstaged:
            reasons.append(f"unstaged_publish_bundle:{path}")
    return reasons


def stage_publish_bundle(draft_id, *, root=ROOT):
    """Stage only the files that form the current draft's public handoff."""
    root = Path(root)
    paths = required_publish_bundle_paths(draft_id, root=root)
    missing = [path for path in paths if not (root / path).is_file()]
    if missing:
        raise FileNotFoundError(
            "publish bundle is incomplete: " + ", ".join(sorted(missing))
        )
    subprocess.run(["git", "add", "--", *paths], cwd=root, check=True)
    return paths


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage or verify one complete Tistory publish bundle."
    )
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--today", action="store_true")
    target.add_argument("--day")
    target.add_argument("--draft-id")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--stage", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    draft_id = (
        args.draft_id
        or args.day
        or datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
    )
    try:
        staged = stage_publish_bundle(draft_id, root=ROOT) if args.stage else []
        reasons = publish_bundle_tracking_reasons(draft_id, root=ROOT)
    except (FileNotFoundError, OSError, subprocess.CalledProcessError, ValueError) as error:
        staged = []
        reasons = [str(error)]
    result = {
        "draft_id": resolve_draft_identity(draft_id).draft_id,
        "status": "READY" if not reasons else "PARTIAL",
        "staged": staged,
        "reasons": reasons,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if reasons else 0


if __name__ == "__main__":
    raise SystemExit(main())
