"""Fast-forward the publishing repository with bounded network retries."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from zoneinfo import ZoneInfo


TRANSIENT_NETWORK_MARKERS = (
    "could not resolve host",
    "could not resolve hostname",
    "temporary failure in name resolution",
    "name or service not known",
    "failed to connect",
    "couldn't connect",
    "connection timed out",
    "connection reset",
    "network is unreachable",
    "remote end hung up unexpectedly",
    "the requested url returned error: 502",
    "the requested url returned error: 503",
    "the requested url returned error: 504",
)


def is_transient_network_error(output: str) -> bool:
    """Return True only for errors that can reasonably succeed on retry."""

    lowered = output.lower()
    return any(marker in lowered for marker in TRANSIENT_NETWORK_MARKERS)


def pull_with_retry(
    remote: str = "origin",
    branch: str = "main",
    attempts: int = 3,
    retry_delay: float = 2.0,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    sleeper: Callable[[float], None] | None = None,
    transient_fallback: Callable[[], bool] | None = None,
) -> int:
    """Run a safe fast-forward pull and retry transient network failures."""

    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if retry_delay < 0:
        raise ValueError("retry_delay must not be negative")

    run = runner or subprocess.run
    sleep = sleeper or time.sleep
    command = ["git", "pull", "--ff-only", remote, branch]

    for attempt in range(1, attempts + 1):
        result = run(command, capture_output=True, text=True, check=False)
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        if result.returncode == 0:
            return 0

        combined = f"{result.stdout}\n{result.stderr}"
        transient = is_transient_network_error(combined)
        if attempt == attempts:
            if transient and transient_fallback and transient_fallback():
                print(
                    "LOCAL_CACHE_READY: 원격 DNS 오류가 계속되어 깨끗한 작업 트리의 "
                    "당일 후보함으로 편집을 계속합니다. 커밋 전 원격 동기화는 다시 확인해야 합니다."
                )
                return 0
            return result.returncode
        if not transient:
            return result.returncode

        delay = retry_delay * (2 ** (attempt - 1))
        print(
            f"일시적 네트워크 오류입니다. {delay:g}초 후 "
            f"동기화를 재시도합니다 ({attempt}/{attempts}).",
            file=sys.stderr,
        )
        sleep(delay)

    return 1


def verify_remote_current(
    remote: str = "origin",
    branch: str = "main",
    attempts: int = 3,
    retry_delay: float = 2.0,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    sleeper: Callable[[float], None] | None = None,
) -> int:
    """Fetch without touching the worktree and require local HEAD == remote branch."""

    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if retry_delay < 0:
        raise ValueError("retry_delay must not be negative")

    run = runner or subprocess.run
    sleep = sleeper or time.sleep
    command = ["git", "fetch", "--no-tags", remote, branch]
    for attempt in range(1, attempts + 1):
        result = run(command, capture_output=True, text=True, check=False)
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        if result.returncode == 0:
            break
        combined = f"{result.stdout}\n{result.stderr}"
        if not is_transient_network_error(combined) or attempt == attempts:
            return result.returncode
        delay = retry_delay * (2 ** (attempt - 1))
        print(
            f"일시적 네트워크 오류입니다. {delay:g}초 후 "
            f"원격 확인을 재시도합니다 ({attempt}/{attempts}).",
            file=sys.stderr,
        )
        sleep(delay)

    local = run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    fetched = run(
        ["git", "rev-parse", "FETCH_HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if local.returncode != 0 or fetched.returncode != 0:
        return local.returncode or fetched.returncode or 1
    if local.stdout.strip() != fetched.stdout.strip():
        print(
            "REMOTE_DIVERGED: 로컬 HEAD와 origin/main이 달라 자동 복구를 중단합니다.",
            file=sys.stderr,
        )
        return 1
    print("REMOTE_CURRENT: 로컬 HEAD와 origin/main이 일치합니다.")
    return 0


def local_inbox_fallback_ready(
    repo_root: str | Path,
    day_id: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> bool:
    """Allow drafting from a current cached inbox without risking dirty work."""

    root = Path(repo_root).resolve()
    run = runner or subprocess.run
    status = run(
        ["git", "status", "--porcelain"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if status.returncode != 0 or status.stdout.strip():
        return False

    latest = root / "docs" / "inbox" / "latest.json"
    try:
        inbox = json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return inbox.get("day") == day_id and bool(inbox.get("candidates"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Retry transient GitHub network failures while keeping --ff-only safety."
    )
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--retry-delay", type=float, default=2.0)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--allow-current-inbox", action="store_true")
    parser.add_argument("--verify-current", action="store_true")
    day_group = parser.add_mutually_exclusive_group()
    day_group.add_argument("--today", action="store_true")
    day_group.add_argument("--day")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        day_id = args.day or dt.datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
        if args.verify_current:
            return verify_remote_current(
                remote=args.remote,
                branch=args.branch,
                attempts=args.attempts,
                retry_delay=args.retry_delay,
            )
        fallback = None
        if args.allow_current_inbox:
            fallback = lambda: local_inbox_fallback_ready(args.repo_root, day_id)
        return pull_with_retry(
            remote=args.remote,
            branch=args.branch,
            attempts=args.attempts,
            retry_delay=args.retry_delay,
            transient_fallback=fallback,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
