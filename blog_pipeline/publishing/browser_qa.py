"""Isolated, loopback-only scheduled preview capture; no app panel or login."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from threading import Thread
from urllib.parse import quote, urlsplit

from .draft_identity import resolve_draft_identity
from .preview_server import allowed_files, make_handler


ROOT = Path(__file__).resolve().parents[2]
VIEWPORTS = ((1280, 900), (390, 844))
PAGES = 'https://seung-won-yu.github.io/blog-writing'


def choose_preview(root, draft_id=None):
    """Resolve real exported IDs, never a refresh date or guessed public URL."""
    root = Path(root)
    if draft_id:
        identity = resolve_draft_identity(draft_id)
        if not (root / 'docs/preview' / f'{identity.draft_id}.html').is_file():
            raise ValueError(f'PREVIEW_NOT_FOUND: {identity.draft_id}')
        allowed_files(root, [identity.draft_id])
        return identity.draft_id
    for meta in sorted((root / 'docs/tistory').glob('*.json'), reverse=True):
        try:
            if json.loads(meta.read_text()).get('publish_ready') is not True:
                continue
            return choose_preview(root, meta.stem)
        except (ValueError, OSError, KeyError):
            continue
    raise ValueError('NO_REVIEWED_PREVIEW: export an actual draft first')


def evidence_directory(root, output):
    output = Path(output).resolve()
    if output.is_relative_to(Path(root).resolve()):
        raise ValueError('QA evidence must be outside repository')
    output.mkdir(parents=True, exist_ok=True)
    return output


def validate_navigation(status, expected_title, actual_title):
    if status != 200:
        raise ValueError(f'PREVIEW_HTTP_ERROR: {status}')
    if not expected_title or expected_title.strip() != actual_title.strip():
        raise ValueError('PREVIEW_WRONG_ARTICLE')


def capture_status(reports):
    return 'CAPTURED' if (
        len(reports) == 2
        and {tuple(r.get('viewport', [])) for r in reports} == set(VIEWPORTS)
        and all(r.get('status') == 'METRICS_PASS' for r in reports)
    ) else 'LAYOUT_FAILED'


def request_allowed(url, origin):
    target, expected = urlsplit(url), urlsplit(origin)
    return (
        target.scheme == expected.scheme and target.netloc == expected.netloc
        and (not expected.path or target.path.startswith(expected.path + '/'))
    )


@contextmanager
def preview_host(root, draft_id):
    files = allowed_files(root, [draft_id])
    server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(files))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f'http://127.0.0.1:{server.server_address[1]}', files
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


@contextmanager
def preview_target(root, draft_id, published):
    if published:
        yield PAGES, allowed_files(root, [draft_id])
    else:
        with preview_host(root, draft_id) as target:
            yield target


def capture(root, draft_id, output, published=False):
    # Optional dependency: pure contract tests and Pages builds need no browser.
    from playwright.sync_api import sync_playwright
    from importlib.metadata import version

    root = Path(root).resolve()
    output = evidence_directory(root, output)
    identity = resolve_draft_identity(draft_id)
    source_path = root / identity.source
    source = json.loads(source_path.read_text())
    script_path = root / 'agent/browser-layout-audit.js'
    script = script_path.read_text()
    expected_title = source.get('editorial', {}).get('headline', '')
    reports, screenshots, console = [], [], []
    (output / 'capture.json').write_text(json.dumps({
        'status': 'RUNNING', 'visual_review': 'PENDING', 'draft_id': draft_id,
    }))

    with preview_target(root, draft_id, published) as (origin, files), sync_playwright() as pw:
        paths = set(files.values()) | {source_path, script_path}
        hashes_before = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted(paths)}
        with pw.chromium.launch(headless=True, chromium_sandbox=True) as browser:
            browser_version = browser.version
            for label, (width, height) in zip(('desktop', 'mobile'), VIEWPORTS):
                # Fresh contexts have no user profile, cookies, extensions or sign-in.
                context = browser.new_context(
                    viewport={'width': width, 'height': height},
                    device_scale_factor=1, accept_downloads=False,
                    service_workers='block',
                )
                try:
                    context.route('**/*', lambda route: (
                        route.continue_() if
                        request_allowed(route.request.url, origin)
                        else route.abort()
                    ))
                    if published and label == 'desktop':
                        # Check every selected public artifact, not only index.html.
                        for path, local in files.items():
                            resource = context.request.get(origin + quote(path, safe='/'))
                            if resource.status != 200 or resource.body() != local.read_bytes():
                                raise ValueError(f'PUBLIC_ARTIFACT_MISMATCH: {path}')
                    page = context.new_page()
                    page.set_default_timeout(10000)
                    page.on('console', lambda msg: console.append(
                        {'type': msg.type, 'text': msg.text})
                        if msg.type in {'error', 'warning'} else None)
                    response = page.goto(
                        f'{origin}/preview/{draft_id}.html',
                        wait_until='load', timeout=20000,
                    )
                    validate_navigation(
                        response.status if response else None,
                        expected_title, page.locator('h1').inner_text(),
                    )
                    page.evaluate('document.fonts.ready')
                    # Trigger every lazy image before testing natural dimensions.
                    for img in page.locator('img').all():
                        img.scroll_into_view_if_needed()
                    # These previews have only finite local/public asset loads.
                    # Network readiness avoids Playwright's string-predicate eval,
                    # which older previews correctly forbid through script-src none.
                    page.wait_for_load_state('networkidle', timeout=10000)
                    report = page.evaluate(script)
                    reports.append(report)
                    (output / f'{label}.json').write_text(
                        json.dumps(report, ensure_ascii=False, indent=2) + '\n')
                    page.evaluate('window.scrollTo(0, 0)')
                    for suffix, full in (('top', False), ('full', True)):
                        name = f'{label}-{suffix}.png'
                        page.screenshot(path=str(output / name), full_page=full)
                        screenshots.append({'path': name, 'target': suffix})
                    for kind, selector in (
                        ('image', 'figure img'), ('table', 'table'),
                        ('code', 'pre'), ('heading', 'h2,h3,h4'),
                    ):
                        for index, element in enumerate(page.locator(selector).all(), 1):
                            if not element.is_visible():
                                continue
                            element.scroll_into_view_if_needed()
                            name = f'{label}-{kind}-{index:02}.png'
                            page.screenshot(path=str(output / name))
                            screenshots.append({
                                'path': name,
                                'target': element.get_attribute('alt')
                                if kind == 'image' else element.inner_text()[:180],
                            })
                            if kind in {'table', 'code'}:
                                shifted = element.evaluate('''(el) => {
                                    const box = el.closest('.digest-table-wrap') || el;
                                    if (box.scrollWidth <= box.clientWidth + 2) return false;
                                    box.scrollLeft = box.scrollWidth;
                                    return box.scrollLeft > 0;
                                }''')
                                if shifted:
                                    name = f'{label}-{kind}-{index:02}-right.png'
                                    page.screenshot(path=str(output / name))
                                    screenshots.append({'path': name, 'target': f'{kind} right edge'})
                                    element.evaluate('''(el) => {
                                        (el.closest('.digest-table-wrap') || el).scrollLeft = 0;
                                    }''')
                finally:
                    context.close()

    hashes_after = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(paths)}
    result = {
        'status': capture_status(reports) if hashes_before == hashes_after else 'STALE_INPUTS',
        'visual_review': 'PENDING',
        'draft_id': draft_id, 'captured_at': datetime.now(timezone.utc).isoformat(),
        'tool': f'Playwright {version("playwright")}',
        'browser': f'Chromium {browser_version}', 'isolated': True,
        'network': 'published blog-writing Pages only' if published else 'selected loopback preview only',
        'hashes': hashes_before,
        'metrics': ['desktop.json', 'mobile.json'],
        'screenshots': screenshots, 'console': console,
        'note': 'CAPTURED is not visual approval; inspect captures before publication.',
    }
    (output / 'capture.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--draft-id')
    target.add_argument('--preflight', action='store_true')
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--published', action='store_true',
                        help='Verify already-deployed files and their actual Pages layout')
    args = parser.parse_args(argv)
    if args.published and args.preflight:
        parser.error('--published requires an explicit --draft-id')
    output = None
    try:
        draft_id = choose_preview(ROOT, args.draft_id)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        output = evidence_directory(ROOT, args.output_dir or (
            Path(tempfile.gettempdir()) / 'blog-writing-qa' / draft_id / stamp))
        result = capture(ROOT, draft_id, output, published=args.published)
        print(json.dumps({
            'status': result['status'], 'draft_id': draft_id,
            'visual_review': result['visual_review'], 'evidence_dir': str(output),
            'manifest': str(output / 'capture.json'),
        }, ensure_ascii=False, indent=2))
        return 0 if result['status'] == 'CAPTURED' else 1
    except Exception as exc:
        # Browser startup/runtime failures are explicit nonzero results, not a
        # stale CAPTURED manifest from a preceding attempt in the same directory.
        failure = {'status': 'QA_ENV_BLOCKED', 'visual_review': 'PENDING',
                   'error_type': type(exc).__name__, 'detail': str(exc)}
        if output is not None:
            (output / 'capture.json').write_text(
                json.dumps(failure, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(failure, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
