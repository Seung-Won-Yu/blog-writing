"""Retry only transient Git push failures and preserve actionable failures."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path


class PushStatus(str, Enum):
    PUSHED = "PUSHED"
    TRANSIENT_FAILURE = "TRANSIENT_FAILURE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class PushResult:
    status: PushStatus
    attempts: int
    returncode: int
    stdout: str = ""
    stderr: str = ""

    def as_json(self):
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


_TRANSIENT_MARKERS = (
    "could not resolve host",
    "temporary failure in name resolution",
    "name or service not known",
    "failed to connect",
    "connection timed out",
    "operation timed out",
    "connection reset by peer",
    "remote end hung up unexpectedly",
    "the remote end hung up unexpectedly",
    "tls connection was non-properly terminated",
)
_NON_RETRYABLE_MARKERS = (
    "authentication failed",
    "permission denied",
    "permission to ",
    "repository not found",
    "non-fast-forward",
    "fetch first",
    "protected branch",
)
_GITHUB_TOKEN_OVERRIDE_VARIABLES = ("GH_TOKEN", "GITHUB_TOKEN")


def is_transient_git_error(message):
    """Return True only for DNS, connection, timeout, or HTTP 5xx failures."""
    normalized = str(message or "").lower()
    if any(marker in normalized for marker in _NON_RETRYABLE_MARKERS):
        return False
    if any(marker in normalized for marker in _TRANSIENT_MARKERS):
        return True
    return bool(re.search(r"(?:http[^\n]*|error:\s*)5\d\d\b", normalized))


def _git_push_environment(environ=None):
    """Prefer the configured Git credential helper over injected token overrides."""
    environment = dict(os.environ if environ is None else environ)
    for variable in _GITHUB_TOKEN_OVERRIDE_VARIABLES:
        environment.pop(variable, None)
    return environment


def _run_git_push(command, cwd):
    return subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=_git_push_environment(),
    )


def push_with_retry(
    *,
    remote="origin",
    refspec="main",
    max_attempts=5,
    base_delay=3.0,
    cwd=None,
    runner=None,
    sleep=None,
):
    """Push with exponential backoff, stopping immediately on actionable errors."""
    if not 1 <= int(max_attempts) <= 5:
        raise ValueError("max_attempts must be between 1 and 5")
    if float(base_delay) < 0:
        raise ValueError("base_delay must be non-negative")

    command = ["git", "push", str(remote), str(refspec)]
    runner = runner or _run_git_push
    sleep = sleep or time.sleep
    cwd = Path(cwd or Path.cwd())
    last_result = None

    for attempt in range(1, int(max_attempts) + 1):
        try:
            last_result = runner(command, cwd)
        except OSError as error:
            last_result = subprocess.CompletedProcess(
                args=command,
                returncode=127,
                stdout="",
                stderr=str(error),
            )

        stdout = str(last_result.stdout or "")
        stderr = str(last_result.stderr or "")
        if last_result.returncode == 0:
            return PushResult(
                PushStatus.PUSHED,
                attempt,
                last_result.returncode,
                stdout,
                stderr,
            )

        if not is_transient_git_error(f"{stdout}\n{stderr}"):
            return PushResult(
                PushStatus.BLOCKED,
                attempt,
                last_result.returncode,
                stdout,
                stderr,
            )

        if attempt < int(max_attempts):
            sleep(float(base_delay) * (2 ** (attempt - 1)))

    return PushResult(
        PushStatus.TRANSIENT_FAILURE,
        int(max_attempts),
        last_result.returncode,
        str(last_result.stdout or ""),
        str(last_result.stderr or ""),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Push a verified commit with bounded transient-network retries."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    push_parser = subparsers.add_parser("push")
    push_parser.add_argument("--remote", default="origin")
    push_parser.add_argument("--ref", dest="refspec", default="main")
    push_parser.add_argument("--max-attempts", type=int, default=5)
    push_parser.add_argument("--base-delay", type=float, default=3.0)
    args = parser.parse_args(argv)

    result = push_with_retry(
        remote=args.remote,
        refspec=args.refspec,
        max_attempts=args.max_attempts,
        base_delay=args.base_delay,
    )
    print(json.dumps(result.as_json(), ensure_ascii=False, indent=2))
    return 0 if result.status == PushStatus.PUSHED else 1


if __name__ == "__main__":
    raise SystemExit(main())
