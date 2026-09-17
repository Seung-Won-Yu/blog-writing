"""Loopback-only, read-only preview of explicitly selected public draft files."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .draft_identity import resolve_draft_identity

ROOT = Path(__file__).resolve().parents[2]


def allowed_files(root, draft_ids):
    root = Path(root).resolve()
    docs = root / "docs"
    allowed = {}

    def add(path):
        resolved = path.resolve(strict=True)
        if resolved != path or not resolved.is_file():
            raise ValueError("preview must not follow symlinks")
        relative = resolved.relative_to(docs)
        allowed["/" + relative.as_posix()] = resolved

    add(docs / "preview/tistory-style.css")
    for draft_id in draft_ids:
        identity = resolve_draft_identity(draft_id)
        add(docs / "preview" / f"{identity.draft_id}.html")
        source = json.loads((root / identity.source).read_text(encoding="utf-8"))
        for asset in source.get("images", {}).values():
            path = root / str(asset.get("path", ""))
            path.resolve().relative_to(docs / "tistory/assets" / identity.draft_id)
            if path.suffix.lower() != ".webp":
                raise ValueError("preview images must be reviewed WebP assets")
            add(path)
    return allowed


def read_allowed(allowed, request_path):
    path = allowed.get(unquote(urlsplit(request_path).path))
    if path is None or path.resolve() != path or not path.is_file():
        return None
    return path.read_bytes(), mimetypes.guess_type(str(path))[0] or "application/octet-stream"


def make_handler(allowed):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            result = read_allowed(allowed, self.path)
            if result is None:
                self.send_error(404)
                return
            data, content_type = result
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; img-src 'self'; style-src 'self' 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft-id", action="append", required=True)
    args = parser.parse_args()
    allowed = allowed_files(ROOT, args.draft_id)
    # Host and port are intentionally not configurable: no LAN/public serving.
    server = ThreadingHTTPServer(("127.0.0.1", 8765), make_handler(allowed))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
