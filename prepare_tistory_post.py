# -*- coding: utf-8 -*-
"""
Prepare a generated daily digest for Tistory posting.

The official Tistory Open API publishing endpoints are no longer available, so
this helper makes the human-in-the-loop step fast: export the latest post,
print its metadata, optionally copy one field to the clipboard, and optionally
open the Tistory editor.

usage:
  python prepare_tistory_post.py --today
  python prepare_tistory_post.py --latest
  python prepare_tistory_post.py --latest --copy body
  python prepare_tistory_post.py --latest --copy title --open-editor
  python prepare_tistory_post.py --day 2026-07-01 --copy tags
"""
import argparse
import json
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

from export_tistory import OUT_DIR, latest_or_today, today_day_id, write_post

DEFAULT_BLOG_URL = "https://won0322.tistory.com"


def read_export(day_id):
    html_path = OUT_DIR / f"{day_id}.html"
    meta_path = OUT_DIR / f"{day_id}.json"

    if not html_path.exists() or not meta_path.exists():
        write_post(day_id)

    with meta_path.open("r", encoding="utf-8") as f:
        meta = json.load(f)
    body = html_path.read_text(encoding="utf-8")
    return meta, body, html_path, meta_path


def clipboard_command():
    if sys.platform == "darwin" and shutil.which("pbcopy"):
        return ["pbcopy"]
    if shutil.which("wl-copy"):
        return ["wl-copy"]
    if shutil.which("xclip"):
        return ["xclip", "-selection", "clipboard"]
    return None


def copy_to_clipboard(value):
    cmd = clipboard_command()
    if not cmd:
        raise SystemExit("clipboard command not found: install pbcopy, wl-copy, or xclip")
    subprocess.run(cmd, input=value, text=True, check=True)


def selected_value(kind, meta, body):
    tags = ", ".join(meta.get("tags") or [])
    values = {
        "title": meta.get("title", ""),
        "category": meta.get("category", ""),
        "tags": tags,
        "body": body,
        "summary": (
            f"제목: {meta.get('title', '')}\n"
            f"카테고리: {meta.get('category', '')}\n"
            f"태그: {tags}\n"
        ),
    }
    return values[kind]


def editor_url(blog_url):
    return blog_url.rstrip("/") + "/manage/newpost"


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--today", action="store_true", help="prepare today's exported day")
    group.add_argument("--latest", action="store_true", help="prepare the newest exported day only when it is today")
    group.add_argument("--day", help="prepare one YYYY-MM-DD day")
    parser.add_argument(
        "--copy",
        choices=["none", "title", "category", "tags", "body", "summary"],
        default="none",
        help="copy one value to the system clipboard",
    )
    parser.add_argument(
        "--open-editor",
        action="store_true",
        help="open the Tistory new post editor in the default browser",
    )
    parser.add_argument("--blog-url", default=DEFAULT_BLOG_URL)
    args = parser.parse_args()

    if args.today:
        day_id = today_day_id()
    elif args.latest:
        day_id = latest_or_today()
    else:
        day_id = args.day
    meta, body, html_path, meta_path = read_export(day_id)
    tags = ", ".join(meta.get("tags") or [])

    if args.copy != "none":
        copy_to_clipboard(selected_value(args.copy, meta, body))

    url = editor_url(args.blog_url)
    if args.open_editor:
        webbrowser.open(url)

    print("티스토리 글 준비 완료")
    print(f"날짜: {day_id}")
    print(f"제목: {meta.get('title', '')}")
    print(f"카테고리: {meta.get('category', '')}")
    print(f"태그: {tags}")
    print(f"본문 HTML: {html_path}")
    print(f"메타데이터: {meta_path}")
    print(f"글쓰기 URL: {url}")
    if args.copy != "none":
        print(f"클립보드 복사: {args.copy}")
    print()
    print("다음 단계")
    print("1. 글쓰기 URL을 연다.")
    print("2. 위 제목, 카테고리, 태그를 입력한다.")
    print("3. 에디터를 HTML 모드로 바꾼다.")
    print("4. 본문 HTML을 붙여넣고 빠르게 검토한 뒤 발행한다.")


if __name__ == "__main__":
    main()
