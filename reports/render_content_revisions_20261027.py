"""Render the eight reviewed existing-post replacements, with bounded local QA."""
from __future__ import annotations

import argparse
from html import escape
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blog_pipeline.publishing.preview_server import make_handler

SOURCE = ROOT / "reports/content-revisions-2026-10-27.json"
QA = Path("/tmp/blog-writing-qa/2026-10-27-revisions")
STYLE = """
.sw-revision-20261027{max-width:860px;margin:0 auto;color:#202923;font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;font-size:18px;line-height:1.85;word-break:keep-all;overflow-wrap:anywhere}
.sw-revision-20261027 *{box-sizing:border-box}
.sw-revision-20261027 p{margin:0 0 1.15em}
.sw-revision-20261027 .rev-date{font-size:13px;color:#647168}
.sw-revision-20261027 .rev-lead{font-size:20px;line-height:1.8}
.sw-revision-20261027 h2{margin:2.2em 0 .85em;font-size:1.35em;line-height:1.45;border-bottom:1px solid #cdd7d1;padding-bottom:.5em;color:#183d30}
.sw-revision-20261027 .rev-table{margin:1.5em 0;overflow-x:auto;-webkit-overflow-scrolling:touch}
.sw-revision-20261027 table{border-collapse:collapse;width:100%;font-size:16px;line-height:1.7}
.sw-revision-20261027 th,.sw-revision-20261027 td{padding:12px 13px;text-align:left;vertical-align:top;border:1px solid #d4ddd7;min-width:110px}
.sw-revision-20261027 th{background:#eff5f1;color:#244536}
.sw-revision-20261027 li{margin:.55em 0}
.sw-revision-20261027 pre{white-space:pre-wrap;background:#f3f6f4;border-left:3px solid #2c7357;padding:18px;font-size:16px;line-height:1.8;overflow-wrap:anywhere}
.sw-revision-20261027 a{color:#1c654a;text-decoration:underline;text-underline-offset:3px}
.sw-revision-20261027 .rev-refs{border-top:1px solid #cdd7d1;margin-top:2.5em;padding-top:.5em;font-size:16px}
@media(max-width:600px){.sw-revision-20261027{font-size:17px;line-height:1.85}.sw-revision-20261027 .rev-lead{font-size:19px}.sw-revision-20261027 th,.sw-revision-20261027 td{min-width:100px;padding:10px}}
""".strip()


def paragraphs(values):
    return "\n".join(f"<p>{escape(value)}</p>" for value in values)


def ad_for(post):
    legacy = ROOT / "docs/tistory" / f"{post['original_date']}-adfit.html"
    markers = re.findall(
        r'<figure\b[^>]*(?:ad-wp|data-ke-type="revenue")[^>]*>.*?</figure>',
        legacy.read_text(encoding="utf-8"), re.S,
    )
    if len(markers) != 1:
        raise ValueError(f"Expected one existing body ad marker: {post['id']}")
    return markers[0]


def fragment(post):
    parts = [f"<style>{STYLE}</style>",
             f'<article class="sw-revision-20261027" data-revision-post="{post["id"]}">',
             '<p class="rev-date">2026. 10. 27 내용 확인·보완</p>',
             f'<p class="rev-lead">{escape(post["lead"])}</p>']
    for index, section in enumerate(post["sections"]):
        parts += [f'<section><h2>{escape(section["heading"])}</h2>',
                  paragraphs(section.get("paragraphs", []))]
        table = section.get("table")
        if table:
            headers = "".join(f'<th scope="col">{escape(v)}</th>' for v in table["headers"])
            rows = "".join("<tr>" + "".join(f"<td>{escape(v)}</td>" for v in row) + "</tr>" for row in table["rows"])
            parts.append(f'<div class="rev-table" role="region" aria-label="{escape(section["heading"])} 비교표" tabindex="0"><table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table></div>')
        if section.get("steps"):
            parts.append("<ol>" + "".join(f"<li>{escape(v)}</li>" for v in section["steps"]) + "</ol>")
        if section.get("prompt"):
            parts.append(f'<pre>{escape(section["prompt"])}</pre>')
        parts += [paragraphs(section.get("paragraphs_after", [])), "</section>"]
        if index == 1:
            parts.append(ad_for(post))
    parts += ['<section class="rev-refs"><h2>참고한 자료</h2><ul>']
    for label, url in post["references"]:
        parts.append(f'<li><a href="{escape(url)}" target="_blank" rel="noopener noreferrer">{escape(label)}</a></li>')
    parts.append("</ul></section>")
    if post.get("related"):
        parts.append('<section><h2>이어서 읽기</h2><ul>')
        for label, url in post["related"]:
            parts.append(f'<li><a href="{escape(url)}">{escape(label)}</a></li>')
        parts.append("</ul></section>")
    parts.append("</article>")
    return "\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--export-review", action="store_true", help="Export visually reviewed replacements to the public handoff folder")
    args = parser.parse_args()
    posts = json.loads(SOURCE.read_text(encoding="utf-8"))["posts"]
    if {post["id"] for post in posts} != {110,111,112,114,117,119,120,124}:
        raise ValueError("Unexpected replacement targets")
    QA.mkdir(parents=True, exist_ok=True)
    review = ROOT / "docs/revisions/2026-10-27"
    if args.export_review:
        review.mkdir(parents=True, exist_ok=True)
    allowed = {}
    for post in posts:
        content = fragment(post)
        path = ROOT / "reports" / f'tistory-{post["id"]}-revision-2026-10-27.html'
        path.write_text(content, encoding="utf-8")
        page = QA / f'{post["id"]}.html'
        preview = content.replace(ad_for(post), '<div style="margin:36px 0;border:1px dashed #a4b4a9;padding:18px;font-size:14px;color:#65776c">기존 본문 중간 광고 위치</div>')
        page.write_text(f'<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive"><title>{escape(post["title"])}</title><body style="margin:0;padding:24px 20px;background:white"><header style="max-width:860px;margin:0 auto 32px;font-family:sans-serif"><h1 style="font-size:30px;line-height:1.4">{escape(post["title"])}</h1></header>{preview}</body></html>', encoding="utf-8")
        allowed[f'/{post["id"]}.html'] = page.resolve()
        if args.export_review:
            (review / page.name).write_bytes(page.read_bytes())
            (review / f'{post["id"]}.txt').write_text(content, encoding="utf-8")
            allowed[f'/{post["id"]}.txt'] = (review / f'{post["id"]}.txt').resolve()
        print(f'Rendered /{post["id"]}: {path.name}', flush=True)
    if args.export_review:
        links = "".join(
            f'<li><p><strong>/{p["id"]} · {escape(p["title"])}</strong></p>'
            f'<a href="{p["id"]}.html">수정 본문 읽기</a> · '
            f'<a href="{p["id"]}.txt">교체용 HTML</a> · '
            f'<a href="https://won0322.tistory.com/{p["id"]}">수정 반영된 공개 글</a></li>'
            for p in posts
        )
        (review / "index.html").write_text(
            '<!doctype html><html lang="ko"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta name="robots" content="noindex,nofollow,noarchive">'
            '<title>10월 27일 기존 글 수정본 8편</title>'
            '<style>body{max-width:860px;margin:40px auto;padding:0 20px;color:#24352c;font:17px/1.8 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif}h1{font-size:30px;line-height:1.4;word-break:keep-all}li{border-bottom:1px solid #d6dfd9;padding:12px 0 25px}a{color:#176347;text-underline-offset:3px}.state{border-left:4px solid #337355;background:#eff6f1;padding:14px 18px}ul{padding-left:22px}</style>'
            '<h1>10월 27일 기존 글 수정본 8편</h1>'
            '<p class="state">티스토리 8편 본문 교체·공개 반영 확인 완료 · 2026. 10. 27</p>'
            '<p>기존 글의 주소와 발행일을 유지하는 교체용 원고입니다. 무관한 뉴스·시험 문제·용어를 덜고 제목의 질문에 집중했습니다. 광고 설정은 변경하지 않았으며 기존 중간 광고 태그 1개를 유지했습니다.</p>'
            '<p>8편 모두 기존 URL에 저장한 뒤 제목·전체 본문·출처·발행일을 대조하고, 실제 공개 화면을 데스크톱 1280px·모바일 390px에서 확인했습니다. 이 페이지는 교체 원고의 보관용이며 AdSense 승인 판정은 아닙니다.</p>'
            '<ul>' + links + '</ul><p><a href="../../">기존 발행 도우미로 돌아가기</a></p></html>',
            encoding="utf-8",
        )
        allowed["/index.html"] = (review / "index.html").resolve()
    if args.serve:
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(allowed))
        for route in allowed:
            print(f'Preview ready: http://127.0.0.1:{server.server_port}{route}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == "__main__":
    main()
