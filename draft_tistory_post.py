# -*- coding: utf-8 -*-
"""
Create or update a Tistory draft from the generated daily digest.

This uses the logged-in Chrome session through cua-driver. It does not publish:
it only saves a draft in Tistory without touching the current editor fields, so
the final review and publish step stays in the browser.

usage:
  python draft_tistory_post.py --today
  python draft_tistory_post.py --day 2026-07-01 --from-pages
  python draft_tistory_post.py --latest
  python draft_tistory_post.py --day 2026-07-01
  python draft_tistory_post.py --latest --dry-run
"""
import argparse
import json
import subprocess
import sys
import time

from export_tistory import DEFAULT_BLOG_URL, DEFAULT_CATEGORY, latest_or_today, read_export, today_day_id, write_post
from pages_to_tistory import DEFAULT_BASE_URL, write_page_post

CHROME_BUNDLE_ID = "com.google.Chrome"


def run_cua(tool, payload):
    result = subprocess.run(
        ["cua-driver", tool, json.dumps(payload, ensure_ascii=False)],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def parse_json_output(output):
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        start = output.find("{")
        end = output.rfind("}")
        if start >= 0 and end >= start:
            return json.loads(output[start : end + 1])
        raise


def parse_page_result(output):
    if "```" in output:
        parts = output.split("```")
        if len(parts) >= 3:
            return parts[1].strip()
    return output.strip()


def execute_js(pid, window_id, javascript):
    output = run_cua(
        "page",
        {
            "pid": pid,
            "window_id": window_id,
            "action": "execute_javascript",
            "javascript": javascript,
        },
    )
    return parse_page_result(output)


def open_manage(blog_url):
    url = blog_url.rstrip("/") + "/manage"
    info = parse_json_output(
        run_cua(
            "launch_app",
            {
                "bundle_id": CHROME_BUNDLE_ID,
                "urls": [url],
            },
        )
    )
    pid = info["pid"]
    window_id = pick_window(info.get("windows") or [])
    return pid, window_id, url


def pick_window(windows):
    candidates = [w for w in windows if "블로그관리" in (w.get("title") or "")]
    if not candidates:
        candidates = [w for w in windows if w.get("title") == "글쓰기"]
    if not candidates:
        candidates = [w for w in windows if w.get("on_current_space") and w.get("is_on_screen")]
    if not candidates:
        candidates = windows
    if not candidates:
        raise SystemExit("Chrome window not found")
    candidates.sort(
        key=lambda w: (
            w.get("title") == "글쓰기",
            "블로그관리" in (w.get("title") or ""),
            w.get("on_current_space", False),
            w.get("is_on_screen", False),
            (w.get("bounds", {}).get("width", 0) * w.get("bounds", {}).get("height", 0)),
        ),
        reverse=True,
    )
    return candidates[0]["window_id"]


def wait_for_manage(pid, window_id, timeout=20):
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        last = execute_js(
            pid,
            window_id,
            """(() => JSON.stringify({
              href: location.href,
              title: document.title,
              ready: document.readyState
            }))()""",
        )
        try:
            data = json.loads(last)
        except json.JSONDecodeError:
            data = {}
        if data.get("ready") == "complete" and "/manage" in data.get("href", ""):
            return data
        time.sleep(0.7)
    raise SystemExit(f"Tistory manage page did not become ready: {last}")


def upload_content_chunks(pid, window_id, content):
    chunks = [content[i : i + 7000] for i in range(0, len(content), 7000)] or [""]
    for index, chunk in enumerate(chunks):
        prefix = "window.__codexDraftContentChunks = []; " if index == 0 else ""
        js = (
            "(() => { "
            + prefix
            + f"window.__codexDraftContentChunks[{index}] = {json.dumps(chunk, ensure_ascii=False)}; "
            + f"return 'chunk {index + 1}/{len(chunks)}'; "
            + "})()"
        )
        execute_js(pid, window_id, js)


def save_draft(pid, window_id, meta, content, category, dry_run):
    upload_content_chunks(pid, window_id, content)
    payload = {
        "title": meta.get("title", ""),
        "category": category or meta.get("category") or DEFAULT_CATEGORY,
        "tags": meta.get("tags") or [],
        "dryRun": dry_run,
    }
    js = f"""
(() => {{
  try {{
    const payload = {json.dumps(payload, ensure_ascii=False)};
    payload.content = (window.__codexDraftContentChunks || []).join("");

    const request = (method, url, body) => {{
      const xhr = new XMLHttpRequest();
      xhr.open(method, url, false);
      xhr.setRequestHeader("Accept", "application/json");
      if (body !== undefined) {{
        xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
      }}
      xhr.send(body === undefined ? null : JSON.stringify(body));
      let data = null;
      try {{ data = JSON.parse(xhr.responseText || "null"); }} catch (e) {{
        data = {{ raw: String(xhr.responseText || "").slice(0, 500) }};
      }}
      return {{ status: xhr.status, ok: xhr.status >= 200 && xhr.status < 300, data }};
    }};

    const flatten = (categories, out = []) => {{
      for (const cat of categories || []) {{
        out.push(cat);
        flatten(cat.children || [], out);
      }}
      return out;
    }};

    const catsResponse = request("GET", "/manage/category.json");
    if (!catsResponse.ok) {{
      return JSON.stringify({{
        ok: false,
        step: "category",
        status: catsResponse.status,
        response: catsResponse.data,
      }});
    }}

    const categories = flatten(catsResponse.data.categories || catsResponse.data.data || []);
    const category = categories.find((cat) =>
      cat.name === payload.category ||
      cat.label === payload.category ||
      String(cat.label || "").endsWith("/" + payload.category)
    );
    const categoryId = category ? category.id : 0;

    const draftsResponse = request("GET", "/manage/drafts");
    const draftRows = draftsResponse.ok
      ? (Array.isArray(draftsResponse.data.data) ? draftsResponse.data.data : [])
      : [];
    const existing = draftRows.find((draft) => draft.title === payload.title);
    const endpoint = existing && existing.sequence
      ? "/manage/drafts/" + existing.sequence
      : "/manage/drafts";

    const body = {{
      title: payload.title,
      content: payload.content,
      tags: payload.tags.join(","),
      categoryId,
      thumbnail: "",
      totalWritingTimeMs: 0,
    }};

    if (payload.dryRun) {{
      return JSON.stringify({{
        ok: true,
        dryRun: true,
        endpoint,
        title: payload.title,
        categoryId,
        categoryName: category ? category.label : null,
        tags: payload.tags,
        contentLength: payload.content.length,
        existingSequence: existing ? existing.sequence : null,
      }});
    }}

    const saveResponse = request("POST", endpoint, body);
    return JSON.stringify({{
      ok: saveResponse.ok,
      status: saveResponse.status,
      endpoint,
      title: payload.title,
      categoryId,
      categoryName: category ? category.label : null,
      tags: payload.tags,
      contentLength: payload.content.length,
      existingSequence: existing ? existing.sequence : null,
      response: saveResponse.data,
    }});
  }} catch (error) {{
    return JSON.stringify({{ ok: false, error: error.message, stack: error.stack }});
  }}
}})()
"""
    return json.loads(execute_js(pid, window_id, js))


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--today", action="store_true", help="draft today's exported day")
    group.add_argument("--latest", action="store_true", help="draft the newest exported day only when it is today")
    group.add_argument("--day", help="draft one YYYY-MM-DD day")
    parser.add_argument("--blog-url", default=DEFAULT_BLOG_URL)
    parser.add_argument(
        "--from-pages",
        action="store_true",
        help="build the Tistory post from the published GitHub Pages day, including images",
    )
    parser.add_argument("--pages-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--category", default=DEFAULT_CATEGORY)
    parser.add_argument("--pid", type=int, help="reuse an existing Chrome pid")
    parser.add_argument("--window-id", type=int, help="reuse an existing Chrome window id")
    parser.add_argument("--dry-run", action="store_true", help="validate payload without saving")
    args = parser.parse_args()

    if args.today:
        day_id = today_day_id()
    elif args.latest:
        day_id = latest_or_today()
    else:
        day_id = args.day
    if args.from_pages:
        write_page_post(day_id, args.pages_url)
    else:
        write_post(day_id)
    meta, content, html_path, _ = read_export(day_id)

    if args.pid and args.window_id:
        pid, window_id, manage_url = args.pid, args.window_id, args.blog_url.rstrip("/") + "/manage"
    else:
        pid, window_id, manage_url = open_manage(args.blog_url)

    wait_for_manage(pid, window_id)
    result = save_draft(pid, window_id, meta, content, args.category, args.dry_run)
    if not result.get("ok"):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit("티스토리 초안 저장 실패")

    print("티스토리 초안 준비 완료")
    print(f"날짜: {day_id}")
    print(f"제목: {result.get('title')}")
    print(f"카테고리: {result.get('categoryName')} ({result.get('categoryId')})")
    print(f"태그: {', '.join(result.get('tags') or [])}")
    print(f"본문 길이: {result.get('contentLength')}")
    print(f"본문 HTML: {html_path}")
    print(f"관리 URL: {manage_url}")
    print(f"글쓰기 URL: {args.blog_url.rstrip('/')}/manage/newpost")
    if args.dry_run:
        print("드라이런: 실제 임시저장은 하지 않음")
        if result.get("existingSequence"):
            print(f"기존 임시저장 감지: {result.get('existingSequence')}")
    elif result.get("existingSequence"):
        print(f"기존 임시저장 업데이트: {result.get('existingSequence')}")
    else:
        draft = (result.get("response") or {}).get("data", {}).get("draft", {})
        sequence = draft.get("sequence") or (result.get("response") or {}).get("draft", {}).get("sequence")
        print(f"새 임시저장 생성: {sequence or '확인 필요'}")


if __name__ == "__main__":
    main()
