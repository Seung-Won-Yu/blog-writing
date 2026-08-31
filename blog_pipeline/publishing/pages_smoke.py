"""Verify that GitHub Pages serves the exact handoff page built by CI."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


def _sha256(value):
    return hashlib.sha256(value).hexdigest()


def _cache_busted_url(url, cache_key=""):
    parts = urlsplit(str(url or "").strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("url must be an absolute HTTP(S) URL")
    query = parse_qsl(parts.query, keep_blank_values=True)
    if cache_key:
        query.append(("build", str(cache_key)))
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path or "/", urlencode(query), "")
    )


def _fetch(url, timeout):
    request = Request(
        url,
        headers={
            "User-Agent": "blog-writing-pages-smoke/1.0",
            "Accept": "text/html",
            "Cache-Control": "no-cache",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def verify_public_page(
    *,
    url,
    expected_bytes,
    cache_key="",
    max_attempts=8,
    delay_seconds=5.0,
    timeout_seconds=10.0,
    fetcher=None,
    sleep=None,
):
    """Compare the public page with the CI artifact using bounded retries."""
    if not 1 <= int(max_attempts) <= 12:
        raise ValueError("max_attempts must be between 1 and 12")
    if float(delay_seconds) < 0 or float(timeout_seconds) <= 0:
        raise ValueError("delay and timeout must be positive")
    target = _cache_busted_url(url, cache_key)
    expected_digest = _sha256(bytes(expected_bytes))
    fetcher = fetcher or _fetch
    sleep = sleep or time.sleep
    last_error = ""
    actual_digest = ""

    for attempt in range(1, int(max_attempts) + 1):
        try:
            actual = fetcher(target, float(timeout_seconds))
            actual_digest = _sha256(bytes(actual))
            if actual_digest == expected_digest:
                return {
                    "status": "COMPLETE",
                    "attempts": attempt,
                    "url": target,
                    "expected_sha256": expected_digest,
                    "actual_sha256": actual_digest,
                    "error": "",
                }
            last_error = "public_content_mismatch"
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            last_error = str(error)
        if attempt < int(max_attempts):
            sleep(float(delay_seconds))

    return {
        "status": "REMOTE_PUSHED_VERIFY_PENDING",
        "attempts": int(max_attempts),
        "url": target,
        "expected_sha256": expected_digest,
        "actual_sha256": actual_digest,
        "error": last_error,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="배포된 Pages 발행 도우미가 CI 산출물과 같은지 확인합니다."
    )
    parser.add_argument("--url", required=True)
    parser.add_argument("--expected-file", required=True)
    parser.add_argument("--cache-key", default="")
    parser.add_argument("--max-attempts", type=int, default=8)
    parser.add_argument("--delay-seconds", type=float, default=5.0)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    args = parser.parse_args(argv)
    try:
        expected = Path(args.expected_file).read_bytes()
        result = verify_public_page(
            url=args.url,
            expected_bytes=expected,
            cache_key=args.cache_key,
            max_attempts=args.max_attempts,
            delay_seconds=args.delay_seconds,
            timeout_seconds=args.timeout_seconds,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
