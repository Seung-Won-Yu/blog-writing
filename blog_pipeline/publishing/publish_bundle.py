"""Stage and verify the complete Git-backed handoff for one draft."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .daily_guard import ROOT
from .draft_identity import resolve_draft_identity


_PROJECT_PRIVATE_PATTERNS = (
    (
        "absolute_path",
        re.compile(
            r"(?i)(?:/Users/[A-Za-z0-9._-]+(?:/[^\s\"'<>\x00]+)+|"
            r"/home/[A-Za-z0-9._-]+(?:/[^\s\"'<>\x00]+)+|"
            r"[A-Z]:\\Users\\[A-Za-z0-9._-]+(?:\\[^\s\"'<>\x00]+)+)"
        ),
    ),
    (
        "private_repository",
        re.compile(
            r"(?i)(?:https?://github\.com/|git@github\.com:|"
            r"ssh://git@github\.com/)[^\s\"'<>]+/edgelab(?:\.git)?(?:\b|/)"
        ),
    ),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "github_token",
        re.compile(
            r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"
        ),
    ),
    ("api_secret", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    (
        "private_key",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
    (
        "jwt",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\."
            r"[A-Za-z0-9_-]{10,}\b"
        ),
    ),
)
_PROJECT_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?:\"|')?(?:api[_-]?key|access[_-]?token|refresh[_-]?token|"
    r"secret|password|passwd|private[_-]?key|cookie)(?:\"|')?"
    r"\s*(?:[:=])\s*(?:\"|')?([^\s,;\"'<>]{12,})"
)
_PROJECT_IDENTIFIER_ASSIGNMENT = re.compile(
    r"(?i)(?:\"|')?(?:account[_-]?(?:id|number)|order[_-]?id|"
    r"position[_-]?id|server[_-]?(?:ip|host)|계좌번호|주문번호)"
    r"(?:\"|')?\s*(?:[:=])\s*(?:\"|')?([^\s,;\"'<>]{4,})"
)
_PROJECT_REVISION_ASSIGNMENT = re.compile(
    r"(?i)(?:\"|')?(?:commit(?:[_-]?(?:sha|hash))?|branch|source_revision)"
    r"(?:\"|')?\s*(?:[:=])\s*(?:\"|')?([^\s,;\"'<>]{4,})"
)
_SAFE_PLACEHOLDER = re.compile(
    r"(?i)^(?:redacted|masked|placeholder|example|sample|none|null|"
    r"your[_-].*|test[_-].*|dummy[_-].*|x{3,}|\*{3,}|\$\{.*\}|\[.*\])$"
)


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


def _project_public_scan_paths(draft_id, root):
    """Return the public project payload plus its reusable editorial source."""
    paths = {
        Path(path)
        for path in required_publish_bundle_paths(draft_id, root=root)
    }
    editorial_root = Path(root) / "editorial" / "edgelab"
    if editorial_root.is_dir():
        paths.update(
            path.relative_to(root)
            for path in editorial_root.rglob("*")
            if path.is_file()
        )
    return sorted(paths, key=lambda path: path.as_posix())


def _project_private_kinds(raw):
    text = raw.decode("utf-8", errors="ignore")
    kinds = {
        kind
        for kind, pattern in _PROJECT_PRIVATE_PATTERNS
        if pattern.search(text)
    }
    for match in _PROJECT_SECRET_ASSIGNMENT.finditer(text):
        if not _SAFE_PLACEHOLDER.fullmatch(match.group(1).strip()):
            kinds.add("assigned_secret")
    for match in _PROJECT_IDENTIFIER_ASSIGNMENT.finditer(text):
        if not _SAFE_PLACEHOLDER.fullmatch(match.group(1).strip()):
            kinds.add("private_identifier")
    for match in _PROJECT_REVISION_ASSIGNMENT.finditer(text):
        if not _SAFE_PLACEHOLDER.fullmatch(match.group(1).strip()):
            kinds.add("private_revision")
    return kinds


def project_public_safety_reasons(draft_id, *, root=ROOT):
    """Fail closed when a project handoff contains private implementation data.

    Reasons deliberately expose only a repository-relative path and a leak kind;
    the matched value must never be copied into logs or the Pages handoff.
    """
    root = Path(root).resolve()
    identity = resolve_draft_identity(draft_id)
    if identity.content_type != "project_log":
        return []

    reasons = []
    for relative in _project_public_scan_paths(identity.draft_id, root):
        path = root / relative
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        for kind in sorted(_project_private_kinds(raw)):
            reasons.append(
                f"private_evidence_leak:{relative.as_posix()}:{kind}"
            )
    return reasons


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
    reasons = project_public_safety_reasons(draft_id, root=root)
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
    safety_reasons = project_public_safety_reasons(draft_id, root=root)
    if safety_reasons:
        raise ValueError(
            "project public-safety check failed: "
            + ", ".join(safety_reasons)
        )
    subprocess.run(["git", "add", "--", *paths], cwd=root, check=True)
    return paths


def publish_bundle_resume_reasons(draft_id, *, root=ROOT):
    """Allow a retry only when every local change belongs to today's bundle."""
    root = Path(root)
    required = set(required_publish_bundle_paths(draft_id, root=root))
    identity = resolve_draft_identity(draft_id)
    try:
        changed = set()
        for command in (
            ["git", "diff", "--name-only", "-z"],
            ["git", "diff", "--cached", "--name-only", "-z"],
            ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        ):
            result = subprocess.run(
                command,
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            changed.update(item for item in result.stdout.split("\0") if item)
    except (OSError, subprocess.CalledProcessError):
        return ["git_resume_check_failed"]

    reasons = project_public_safety_reasons(draft_id, root=root)
    if not changed:
        reasons.append("no_local_publish_bundle")
    if identity.source not in changed:
        reasons.append(f"source_not_changed:{identity.source}")
    for path in sorted(changed - required):
        reasons.append(f"unexpected_worktree_change:{path}")
    for path in sorted(required):
        if not (root / path).is_file():
            reasons.append(f"missing_publish_bundle:{path}")
    return reasons


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
    action.add_argument("--resume-check", action="store_true")
    args = parser.parse_args(argv)
    draft_id = (
        args.draft_id
        or args.day
        or datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
    )
    try:
        staged = stage_publish_bundle(draft_id, root=ROOT) if args.stage else []
        reasons = (
            publish_bundle_resume_reasons(draft_id, root=ROOT)
            if args.resume_check
            else publish_bundle_tracking_reasons(draft_id, root=ROOT)
        )
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
