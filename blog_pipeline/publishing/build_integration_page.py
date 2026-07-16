# -*- coding: utf-8 -*-
"""Build a client-side Tistory HTML assembler for integrated study posts."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from .build_copy_page import esc, json_for_script


ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = ROOT / "data" / "integrated_posts"
OUT_PATH = ROOT / "docs" / "integration.html"
POSTS_PATH = CONTENT_DIR / "posts.json"
IMAGE_MARKER = "<!-- TISTORY_IMAGE_TAG -->"
AD_MARKER = "<!-- ADFIT_TAG -->"


def _schedule_label(value):
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        scheduled = dt.datetime.fromisoformat(text)
    except ValueError:
        return text
    period = "오전" if scheduled.hour < 12 else "오후"
    hour = scheduled.hour % 12 or 12
    return f"{scheduled.year}. {scheduled.month}. {scheduled.day}. {period} {hour}시"


def load_posts(content_dir=CONTENT_DIR):
    """Load integrated posts and reject templates with ambiguous placeholders."""
    content_dir = Path(content_dir)
    metadata_path = content_dir / "posts.json"
    raw_posts = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(raw_posts, list):
        raise ValueError("보강글 메타데이터는 목록이어야 합니다.")

    posts = []
    for raw in raw_posts:
        if not isinstance(raw, dict):
            raise ValueError("보강글 메타데이터 항목이 올바르지 않습니다.")
        slug = str(raw.get("slug") or "").strip()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ValueError(f"보강글 slug가 올바르지 않습니다: {slug}")
        source_path = content_dir / f"{slug}.html"
        if not source_path.is_file():
            raise ValueError(f"보강글 HTML이 없습니다: {source_path}")
        source_html = source_path.read_text(encoding="utf-8")
        if source_html.count(IMAGE_MARKER) != 1 or source_html.count(AD_MARKER) != 1:
            raise ValueError(
                f"{slug}: 이미지·광고 자리표시자는 각각 정확히 1개여야 합니다."
            )
        tags = raw.get("tags") if isinstance(raw.get("tags"), list) else []
        posts.append(
            {
                "slug": slug,
                "title": str(raw.get("title") or slug),
                "category": str(raw.get("category") or ""),
                "tags": ", ".join(str(tag) for tag in tags if str(tag).strip()),
                "scheduled_at": _schedule_label(raw.get("scheduled_at")),
                "source_ids": raw.get("source_ids") or [],
                "delete_urls": raw.get("delete_urls") or [],
                "image_filename": str(raw.get("image_filename") or ""),
                "image_location": str(raw.get("image_location") or ""),
                "image_position": str(raw.get("image_position") or ""),
                "image_alt": str(raw.get("image_alt") or ""),
                "ad_position": str(raw.get("ad_position") or ""),
                "html": source_html,
            }
        )
    return posts


def render(posts):
    payload = json_for_script(posts)
    first_slug = posts[0]["slug"] if posts else ""
    buttons = "\n".join(
        '<button class="post-button" type="button" data-slug="{}" '
        'aria-pressed="false"><span>{}번 글 · {}</span><strong>{}</strong></button>'.format(
            esc(post.get("slug")),
            index,
            esc(post.get("scheduled_at")),
            esc(post.get("title")),
        )
        for index, post in enumerate(posts, start=1)
    )
    empty = '<p class="empty">준비된 보강글이 없습니다.</p>'
    template = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow,noarchive">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src https: data: blob:; object-src 'none'; base-uri 'none'; form-action 'none'">
  <title>티스토리 보강글 발행 도우미</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17211c;
      --muted: #647069;
      --line: #d7ded9;
      --paper: #ffffff;
      --canvas: #f3f4f1;
      --accent: #28745a;
      --accent-dark: #1f5d49;
      --accent-soft: #edf4f0;
      --warm: #f7f4ec;
      --danger: #a33b2b;
    }
    * { box-sizing: border-box; }
    html { background: var(--canvas); }
    body {
      margin: 0;
      color: var(--ink);
      font-family: "Pretendard Variable", "SUIT Variable", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
      line-height: 1.55;
    }
    button, textarea { font: inherit; }
    button:focus-visible, textarea:focus-visible, a:focus-visible, summary:focus-visible {
      outline: 3px solid #91c4b0;
      outline-offset: 2px;
    }
    .sr-only {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }
    .wrap {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 24px 0 52px;
    }
    .masthead {
      padding: 20px 22px 18px;
      border-top: 4px solid var(--accent);
      border-bottom: 1px solid var(--line);
      background: var(--paper);
    }
    .desk-nav {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 16px;
    }
    .desk-nav a {
      display: inline-flex;
      min-height: 36px;
      align-items: center;
      padding: 0 12px;
      border: 1px solid var(--line);
      border-radius: 3px;
      background: #fff;
      color: var(--ink);
      font-size: 13px;
      font-weight: 800;
      text-decoration: none;
    }
    .desk-nav a[aria-current="page"] {
      border-color: var(--accent);
      background: var(--accent);
      color: #fff;
    }
    .eyebrow {
      margin: 0 0 6px;
      color: var(--accent);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: .13em;
    }
    h1 {
      margin: 0;
      font-size: clamp(25px, 3vw, 34px);
      line-height: 1.2;
      letter-spacing: -.035em;
      word-break: keep-all;
    }
    .lead {
      max-width: 760px;
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 14px;
    }
    .steps {
      display: flex;
      flex-wrap: wrap;
      gap: 8px 24px;
      margin: 0 0 16px;
      padding: 13px 18px;
      border-bottom: 1px solid var(--line);
      background: var(--warm);
      color: #46534d;
      font-size: 13px;
      font-weight: 750;
    }
    .steps span::before {
      content: attr(data-step);
      display: inline-grid;
      width: 20px;
      height: 20px;
      margin-right: 6px;
      place-items: center;
      border-radius: 50%;
      background: var(--accent);
      color: #fff;
      font-size: 11px;
    }
    .layout {
      display: grid;
      grid-template-columns: 300px minmax(0, 1fr);
      gap: 16px;
      align-items: start;
      margin-top: 16px;
    }
    .panel {
      border: 1px solid var(--line);
      background: var(--paper);
    }
    .panel-title {
      padding: 12px 15px;
      border-bottom: 1px solid var(--line);
      background: var(--warm);
      font-size: 13px;
      font-weight: 900;
    }
    .post-list { display: grid; gap: 5px; padding: 8px; }
    .post-button {
      width: 100%;
      padding: 13px;
      border: 1px solid transparent;
      border-radius: 4px;
      background: transparent;
      color: var(--ink);
      text-align: left;
      cursor: pointer;
    }
    .post-button:hover, .post-button.is-active {
      border-color: #b9d0c5;
      background: var(--accent-soft);
    }
    .post-button span {
      display: block;
      margin-bottom: 3px;
      color: var(--accent-dark);
      font-size: 11px;
      font-weight: 900;
    }
    .post-button strong {
      display: -webkit-box;
      font-size: 13px;
      line-height: 1.45;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .content { padding: 17px; }
    .publish-fields { display: grid; gap: 1px; margin-bottom: 15px; }
    .field {
      display: grid;
      grid-template-columns: 100px minmax(0, 1fr) auto;
      gap: 10px;
      align-items: center;
      min-height: 46px;
      padding: 8px 10px;
      border-bottom: 1px solid var(--line);
    }
    .field-label { color: var(--muted); font-size: 12px; font-weight: 850; }
    .field-value { min-width: 0; font-size: 14px; overflow-wrap: anywhere; }
    .title-value { font-size: 16px; font-weight: 850; line-height: 1.45; }
    .btn {
      display: inline-flex;
      min-height: 38px;
      align-items: center;
      justify-content: center;
      padding: 0 13px;
      border: 1px solid #9aa8a1;
      border-radius: 3px;
      background: #fff;
      color: var(--ink);
      font-size: 13px;
      font-weight: 850;
      cursor: pointer;
    }
    .btn:hover:not(:disabled) { border-color: var(--accent); background: var(--accent); color: #fff; }
    .btn.primary { border-color: var(--accent); background: var(--accent); color: #fff; }
    .btn.dark { border-color: var(--ink); background: var(--ink); color: #fff; }
    .btn:disabled { cursor: not-allowed; opacity: .42; }
    .builder {
      display: grid;
      gap: 12px;
      margin-bottom: 12px;
    }
    .markup-box {
      min-width: 0;
      padding: 13px;
      border: 1px solid var(--line);
      background: #fbfcfb;
    }
    .step-head { display: flex; gap: 10px; align-items: center; justify-content: space-between; }
    .markup-box h2 { margin: 0; font-size: 17px; }
    .markup-box p { margin: 6px 0 10px; color: var(--muted); font-size: 13px; }
    .step-state {
      display: inline-flex;
      min-height: 28px;
      align-items: center;
      padding: 0 9px;
      border: 1px solid #d6b977;
      border-radius: 999px;
      background: #fff8e8;
      color: #80520b;
      font-size: 12px;
      font-weight: 900;
      white-space: nowrap;
    }
    .step-state[data-complete="true"] { border-color: #9fc8b7; background: #eaf6f1; color: var(--accent-dark); }
    .markup-input {
      display: block;
      width: 100%;
      min-height: 118px;
      padding: 10px 11px;
      border: 1px solid #bfcac4;
      border-radius: 3px;
      background: #fff;
      color: #27332d;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      line-height: 1.5;
      resize: vertical;
    }
    .asset-note {
      margin: 0 0 12px;
      padding: 11px 13px;
      border-left: 4px solid var(--accent);
      background: var(--accent-soft);
      color: #34463d;
      font-size: 13px;
    }
    .asset-note p { margin: 3px 0; overflow-wrap: anywhere; }
    .asset-title { margin: 0 0 10px; color: var(--ink); font-size: 17px; }
    .asset-grid { display: grid; gap: 8px; }
    .asset-row { display: grid; grid-template-columns: 105px minmax(0, 1fr) auto; gap: 10px; align-items: center; }
    .asset-label { color: var(--muted); font-size: 12px; font-weight: 900; }
    .asset-value { min-width: 0; overflow-wrap: anywhere; }
    .file-name { color: var(--accent-dark); font-size: 16px; font-weight: 900; }
    .path-value { padding: 8px 10px; border: 1px solid #cad8d1; background: #fff; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11px; }
    .asset-tip { margin: 10px 0 0 !important; padding-top: 9px; border-top: 1px solid #cfe0d8; }
    .action-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      justify-content: flex-end;
      margin: 12px 0 10px;
    }
    .readiness { margin: 0 auto 0 0; color: #9a5c12; font-size: 12px; font-weight: 850; }
    .readiness[data-ready="true"] { color: var(--accent); }
    .manual-help {
      margin: 0 0 10px;
      padding: 10px 12px;
      border-left: 3px solid #c99b43;
      background: var(--warm);
      color: #46534d;
      font-size: 12px;
    }
    .publish-checklist { margin: 12px 0; padding: 14px 16px; border: 1px solid var(--line); background: #fff; }
    .publish-checklist h2 { margin: 0 0 7px; font-size: 15px; }
    .publish-checklist ol { margin: 0; padding-left: 22px; color: #46534d; font-size: 13px; }
    .publish-checklist li { margin: 4px 0; }
    .final-result[hidden] { display: none; }
    .code-output {
      display: block;
      width: 100%;
      min-height: 480px;
      padding: 14px;
      border: 1px solid #263449;
      border-radius: 3px;
      background: #0b1220;
      color: #dce8f8;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      line-height: 1.58;
      resize: vertical;
      white-space: pre;
    }
    .preview-pane { width: 100%; min-height: 700px; border: 1px solid var(--line); background: #fff; }
    .preview-frame { display: block; width: 100%; min-height: 700px; border: 0; background: #fff; }
    textarea[hidden], .preview-pane[hidden] { display: none; }
    .delete-details { margin-top: 12px; border-top: 1px solid var(--line); padding-top: 11px; }
    .delete-details summary { color: var(--muted); font-size: 12px; font-weight: 850; cursor: pointer; }
    .delete-list { margin: 9px 0 0; padding-left: 20px; font-size: 12px; }
    .delete-list a { color: #0b6fbd; overflow-wrap: anywhere; }
    .status { min-height: 20px; margin-top: 8px; color: var(--accent); font-size: 12px; font-weight: 800; }
    .status[data-kind="error"] { color: var(--danger); }
    .empty { padding: 18px 12px; color: var(--muted); font-size: 13px; }
    @media (max-width: 820px) {
      .wrap { width: min(100% - 20px, 700px); padding-top: 12px; }
      .masthead { padding: 17px; }
      .layout { grid-template-columns: 1fr; }
      .content { padding: 12px; }
      .builder { grid-template-columns: 1fr; }
      .asset-row { grid-template-columns: 1fr auto; }
      .asset-label { grid-column: 1 / -1; }
      .path-value { grid-column: 1 / -1; }
      .field { grid-template-columns: 1fr auto; }
      .field .field-label { grid-column: 1 / -1; }
      .action-row { display: grid; grid-template-columns: 1fr; }
      .action-row .readiness { margin-bottom: 4px; }
      .btn { width: 100%; }
      .code-output { min-height: 380px; }
      .preview-pane, .preview-frame { min-height: 560px; }
    }
    @media (max-width: 380px) {
      .wrap { width: calc(100% - 12px); }
      .steps { display: grid; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <nav class="desk-nav" aria-label="발행 도구">
      <a href="./">데일리 뉴스 발행</a>
      <a href="integration.html" aria-current="page">보강글 발행 도우미</a>
    </nav>
    <header class="masthead">
      <p class="eyebrow">TISTORY PUBLISHING HELPER</p>
      <h1>티스토리 보강글 발행 도우미</h1>
      <p class="lead">위에서부터 차례대로 따라 하면 됩니다. 글을 고르고, 안내된 이미지를 올린 뒤 이미지·광고 태그만 붙여 넣으면 최종 HTML이 완성됩니다.</p>
    </header>
    <div class="steps" aria-label="사용 순서">
      <span data-step="1">발행할 글 선택</span>
      <span data-step="2">안내된 PNG 업로드</span>
      <span data-step="3">이미지·광고 태그 붙여넣기</span>
      <span data-step="4">완성 HTML 복사</span>
    </div>

    <div class="layout">
      <aside class="panel">
        <div class="panel-title">① 발행할 글을 고르세요</div>
        <div class="post-list" id="postList">__BUTTONS__</div>
      </aside>

      <main class="panel">
        <div class="panel-title">② 선택한 글의 발행 준비</div>
        <div class="content">
          <section class="publish-fields" aria-label="발행 정보">
            <div class="field"><span class="field-label">제목</span><span class="field-value title-value" id="title"></span><button class="btn dark" type="button" data-copy="title">복사</button></div>
            <div class="field"><span class="field-label">카테고리</span><span class="field-value" id="category"></span><button class="btn" type="button" data-copy="category">복사</button></div>
            <div class="field"><span class="field-label">태그</span><span class="field-value" id="tags"></span><button class="btn" type="button" data-copy="tags">복사</button></div>
            <div class="field"><span class="field-label">예약 발행</span><span class="field-value" id="scheduledAt"></span><span></span></div>
            <div class="field"><span class="field-label">통합 원문 ID</span><span class="field-value" id="sourceIds"></span><span></span></div>
          </section>

          <section class="asset-note" aria-label="업로드할 이미지 안내">
            <h2 class="asset-title">먼저 이 이미지를 티스토리에 올리세요</h2>
            <div class="asset-grid">
              <div class="asset-row"><span class="asset-label">이미지 파일명</span><span class="asset-value file-name" id="imageFilename"></span><button class="btn" type="button" data-copy="image-name">파일명 복사</button></div>
              <div class="asset-row"><span class="asset-label">파일이 있는 곳</span><code class="asset-value path-value" id="imageLocation"></code><button class="btn" type="button" data-copy="image-path">경로 복사</button></div>
              <div class="asset-row"><span class="asset-label">글에 들어갈 위치</span><span class="asset-value" id="imagePosition"></span><span></span></div>
              <div class="asset-row"><span class="asset-label">이미지 설명</span><span class="asset-value" id="imageAlt"></span><button class="btn" type="button" data-copy="alt">설명 복사</button></div>
              <div class="asset-row"><span class="asset-label">광고가 들어갈 위치</span><span class="asset-value" id="adPosition"></span><span></span></div>
            </div>
            <p class="asset-tip"><strong>작업 방법:</strong> 위 PNG를 티스토리 기본모드에서 업로드하고 광고도 삽입한 뒤, HTML 모드로 바꿔 각각의 태그를 아래 칸에 붙여 넣으세요. 실제 위치는 자동으로 맞춥니다.</p>
          </section>

          <div class="builder">
            <section class="markup-box">
              <div class="step-head"><h2><label for="imageMarkup">③ 이미지 태그 붙여넣기</label></h2><span class="step-state" id="imageStepState" data-complete="false">입력 전</span></div>
              <p>HTML 모드에서 방금 올린 이미지의 <code>&lt;figure&gt;...&lt;/figure&gt;</code> 전체를 복사해 넣으세요.</p>
              <textarea class="markup-input" id="imageMarkup" spellcheck="false" placeholder="여기에 티스토리 이미지 figure 태그를 붙여넣으세요"></textarea>
            </section>
            <section class="markup-box">
              <div class="step-head"><h2><label for="adMarkup">④ AdFit 광고 태그 붙여넣기</label></h2><span class="step-state" id="adStepState" data-complete="false">입력 전</span></div>
              <p>HTML 모드에서 AdFit 광고의 <code>&lt;figure data-ke-type=&quot;revenue&quot;&gt;...&lt;/figure&gt;</code> 전체를 복사해 넣으세요.</p>
              <textarea class="markup-input" id="adMarkup" spellcheck="false" placeholder="여기에 티스토리 AdFit 광고 figure 태그를 붙여넣으세요"></textarea>
            </section>
          </div>

          <div class="action-row">
            <p class="readiness" id="readiness" data-ready="false">이미지·광고 태그를 붙여 주세요.</p>
            <button class="btn primary" type="button" id="buildFinalButton">⑤ 최종 HTML 만들기</button>
            <button class="btn" type="button" id="previewButton" aria-expanded="false" aria-controls="previewPane" disabled>본문 미리보기</button>
            <button class="btn dark" type="button" id="finalCopyButton" data-copy="final" disabled>최종 HTML 복사</button>
          </div>
          <p class="manual-help"><strong>중요:</strong> 완성 코드를 티스토리 HTML 모드에 전체 붙여넣은 뒤 기본모드로 돌아가지 마세요. 예약 저장 확인 후에만 원문 삭제가 가능합니다.</p>
          <section class="final-result" id="finalResult" hidden>
            <section class="publish-checklist" aria-label="마지막 발행 순서">
              <h2>최종 HTML이 완성됐습니다</h2>
              <ol>
                <li><strong>최종 HTML 복사</strong>를 누릅니다.</li>
                <li>티스토리 HTML 모드 본문을 전체 선택하고 붙여 넣습니다.</li>
                <li>기본모드로 돌아가지 않고 제목·카테고리·태그·예약 시간을 입력합니다.</li>
                <li>예약 저장이 확인된 다음에만 아래 원문을 삭제합니다.</li>
              </ol>
            </section>
            <label class="sr-only" for="finalHtml">최종 티스토리 본문 HTML</label>
            <textarea class="code-output" id="finalHtml" spellcheck="false" readonly></textarea>
            <section class="preview-pane" id="previewPane" aria-label="최종 본문 미리보기" hidden>
              <iframe class="preview-frame" id="previewFrame" title="최종 본문 미리보기" sandbox=""></iframe>
            </section>

            <details class="delete-details">
              <summary>예약 저장 확인 후 삭제할 원문 URL</summary>
              <ul class="delete-list" id="deleteList"></ul>
            </details>
          </section>
          <div class="status" id="status" role="status" aria-live="polite"></div>
        </div>
      </main>
    </div>
  </div>

  <script>
    const posts = __PAYLOAD__;
    const firstSlug = __FIRST_SLUG__;
    const imageMarker = "<!-- TISTORY_IMAGE_TAG -->";
    const adMarker = "<!-- ADFIT_TAG -->";
    const bySlug = new Map(posts.map((post) => [post.slug, post]));
    let current = null;
    let sourceHtml = "";
    let currentFinalHtml = "";

    const els = {
      title: document.getElementById("title"),
      category: document.getElementById("category"),
      tags: document.getElementById("tags"),
      scheduledAt: document.getElementById("scheduledAt"),
      sourceIds: document.getElementById("sourceIds"),
      imageFilename: document.getElementById("imageFilename"),
      imageLocation: document.getElementById("imageLocation"),
      imagePosition: document.getElementById("imagePosition"),
      imageAlt: document.getElementById("imageAlt"),
      adPosition: document.getElementById("adPosition"),
      imageMarkup: document.getElementById("imageMarkup"),
      adMarkup: document.getElementById("adMarkup"),
      imageStepState: document.getElementById("imageStepState"),
      adStepState: document.getElementById("adStepState"),
      buildFinalButton: document.getElementById("buildFinalButton"),
      previewButton: document.getElementById("previewButton"),
      previewPane: document.getElementById("previewPane"),
      previewFrame: document.getElementById("previewFrame"),
      finalCopyButton: document.getElementById("finalCopyButton"),
      finalResult: document.getElementById("finalResult"),
      finalHtml: document.getElementById("finalHtml"),
      readiness: document.getElementById("readiness"),
      deleteList: document.getElementById("deleteList"),
      status: document.getElementById("status"),
    };

    function setStatus(text, kind = "success") {
      els.status.textContent = text;
      els.status.dataset.kind = kind;
      if (text && kind !== "error") window.setTimeout(() => {
        if (els.status.textContent === text) els.status.textContent = "";
      }, 2400);
    }

    function parseMarkup(value) {
      return new DOMParser().parseFromString(String(value || ""), "text/html");
    }

    function extractImageMarkup(value) {
      const parsed = parseMarkup(value);
      const figures = Array.from(parsed.querySelectorAll("figure")).filter((figure) => {
        return figure.querySelector("img") && figure.dataset.keType !== "revenue";
      });
      if (figures.length === 1) return figures[0].outerHTML;
      const images = parsed.querySelectorAll("img");
      return figures.length === 0 && images.length === 1 ? images[0].outerHTML : "";
    }

    function applyImageAlt(markup, alt) {
      if (!markup) return "";
      const parsed = parseMarkup(markup);
      const images = parsed.querySelectorAll("img");
      if (images.length !== 1) return "";
      const image = images[0];
      const cleanAlt = String(alt || "").trim();
      if (cleanAlt) {
        image.setAttribute("alt", cleanAlt);
        const holder = image.closest("[data-url]");
        if (holder) holder.setAttribute("data-alt", cleanAlt);
      }
      const figure = image.closest("figure");
      return figure ? figure.outerHTML : image.outerHTML;
    }

    function extractRevenueMarkup(value) {
      const parsed = parseMarkup(value);
      const ads = Array.from(parsed.querySelectorAll('figure[data-ke-type="revenue"]')).filter((figure) => {
        const vendor = String(figure.dataset.adVendor || "").toLowerCase();
        return !vendor || vendor === "adfit";
      });
      return ads.length === 1 ? ads[0].outerHTML : "";
    }

    function isFinalHtmlStructurallyValid(value) {
      if (!value || value.includes(imageMarker) || value.includes(adMarker)) return false;
      const parsed = parseMarkup(value);
      const articles = parsed.querySelectorAll("article");
      const images = parsed.querySelectorAll("article img");
      const ads = parsed.querySelectorAll('article figure[data-ke-type="revenue"]');
      const scripts = parsed.querySelectorAll("script");
      return articles.length === 1 && images.length >= 1 && ads.length === 1 && scripts.length === 0;
    }

    function setPreviewMode(showingPreview) {
      els.previewPane.hidden = !showingPreview;
      els.finalHtml.hidden = showingPreview;
      els.previewButton.setAttribute("aria-expanded", String(showingPreview));
      els.previewButton.textContent = showingPreview ? "HTML 코드 보기" : "본문 미리보기";
    }

    function updateState(message = "") {
      const imageReady = Boolean(extractImageMarkup(els.imageMarkup.value));
      const adReady = Boolean(extractRevenueMarkup(els.adMarkup.value));
      const ready = isFinalHtmlStructurallyValid(currentFinalHtml);
      els.imageStepState.dataset.complete = String(imageReady);
      els.imageStepState.textContent = imageReady ? "확인 완료" : "입력 전";
      els.adStepState.dataset.complete = String(adReady);
      els.adStepState.textContent = adReady ? "확인 완료" : "입력 전";
      els.buildFinalButton.disabled = !(imageReady && adReady);
      els.finalCopyButton.disabled = !ready;
      els.previewButton.disabled = !ready;
      els.finalResult.hidden = !ready;
      els.readiness.dataset.ready = String(ready);
      els.readiness.textContent = message || (
        ready
          ? "최종 HTML 준비 완료 · " + currentFinalHtml.length.toLocaleString() + "자"
          : "이미지·광고 태그를 붙여 주세요."
      );
    }

    function buildFinalHtml(showMessage = true) {
      if (!current || !sourceHtml) return false;
      const imageMarkup = applyImageAlt(extractImageMarkup(els.imageMarkup.value), current.image_alt);
      const adMarkup = extractRevenueMarkup(els.adMarkup.value);
      if (!imageMarkup || !adMarkup) {
        currentFinalHtml = "";
        els.finalHtml.value = sourceHtml;
        els.previewFrame.removeAttribute("srcdoc");
        setPreviewMode(false);
        const missing = !imageMarkup && !adMarkup
          ? "이미지·AdFit 태그를 확인해 주세요."
          : (!imageMarkup ? "이미지 태그 1개를 찾지 못했습니다." : "AdFit 태그 1개를 찾지 못했습니다.");
        updateState(missing);
        if (showMessage) setStatus(missing, "error");
        return false;
      }
      currentFinalHtml = sourceHtml.replace(imageMarker, imageMarkup)
        .replace(adMarker, adMarkup);
      if (!isFinalHtmlStructurallyValid(currentFinalHtml)) {
        currentFinalHtml = "";
        els.finalHtml.value = sourceHtml;
        updateState("최종 본문 구조를 확인하지 못했습니다.");
        if (showMessage) setStatus("최종 본문 구조 검사 실패 · 복사하지 않았습니다.", "error");
        return false;
      }
      els.imageMarkup.value = imageMarkup;
      els.adMarkup.value = adMarkup;
      els.finalHtml.value = currentFinalHtml;
      els.previewFrame.srcdoc = currentFinalHtml;
      window.localStorage.setItem("tistory-integration-adfit", adMarkup);
      window.localStorage.setItem("tistory-integration-image-" + current.slug, imageMarkup);
      updateState();
      if (showMessage) setStatus("최종 HTML 생성 완료");
      return true;
    }

    function renderDeleteLinks(urls) {
      els.deleteList.replaceChildren();
      (urls || []).forEach((url) => {
        const item = document.createElement("li");
        const link = document.createElement("a");
        link.href = url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = url;
        item.appendChild(link);
        els.deleteList.appendChild(item);
      });
    }

    function selectPost(slug) {
      const post = bySlug.get(slug);
      if (!post) return;
      current = post;
      sourceHtml = post.html || "";
      currentFinalHtml = "";
      document.querySelectorAll(".post-button").forEach((button) => {
        const selected = button.dataset.slug === slug;
        button.classList.toggle("is-active", selected);
        button.setAttribute("aria-pressed", String(selected));
      });
      els.title.textContent = post.title || "";
      els.category.textContent = post.category || "";
      els.tags.textContent = post.tags || "";
      els.scheduledAt.textContent = post.scheduled_at || "";
      els.sourceIds.textContent = (post.source_ids || []).join(", ");
      els.imageFilename.textContent = post.image_filename || "";
      els.imageLocation.textContent = post.image_location || "";
      els.imagePosition.textContent = post.image_position || "";
      els.imageAlt.textContent = post.image_alt || "";
      els.adPosition.textContent = post.ad_position || "";
      els.imageMarkup.value = window.localStorage.getItem("tistory-integration-image-" + slug) || "";
      els.adMarkup.value = window.localStorage.getItem("tistory-integration-adfit") || "";
      els.finalHtml.value = sourceHtml;
      els.previewFrame.removeAttribute("srcdoc");
      setPreviewMode(false);
      renderDeleteLinks(post.delete_urls);
      buildFinalHtml(false);
      setStatus(post.title + " 불러옴");
    }

    async function copyText(text, label) {
      if (!text) {
        setStatus("복사할 내용이 없습니다.", "error");
        return false;
      }
      let copied = false;
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text);
          copied = true;
        }
      } catch (error) {
        copied = false;
      }
      if (!copied) {
        const helper = document.createElement("textarea");
        helper.value = text;
        helper.setAttribute("readonly", "");
        helper.style.position = "fixed";
        helper.style.left = "-9999px";
        helper.style.top = "0";
        document.body.appendChild(helper);
        helper.focus();
        helper.select();
        helper.setSelectionRange(0, helper.value.length);
        copied = document.execCommand("copy");
        helper.remove();
      }
      if (!copied) {
        setStatus("복사 실패 · 코드 창에서 직접 복사해 주세요.", "error");
        return false;
      }
      setStatus(label + " 복사 완료");
      return true;
    }

    function rebuildAfterInput() {
      currentFinalHtml = "";
      setPreviewMode(false);
      buildFinalHtml(false);
    }

    els.imageMarkup.addEventListener("input", () => {
      rebuildAfterInput();
    });
    els.adMarkup.addEventListener("input", () => {
      rebuildAfterInput();
    });
    els.buildFinalButton.addEventListener("click", () => buildFinalHtml(true));
    els.previewButton.addEventListener("click", () => {
      const showingPreview = els.previewButton.getAttribute("aria-expanded") !== "true";
      setPreviewMode(showingPreview);
    });
    document.getElementById("postList").addEventListener("click", (event) => {
      const button = event.target.closest(".post-button");
      if (button) selectPost(button.dataset.slug);
    });
    document.addEventListener("click", (event) => {
      const button = event.target.closest("[data-copy]");
      if (!button || !current) return;
      if (button.dataset.copy === "title") copyText(current.title, "제목");
      if (button.dataset.copy === "category") copyText(current.category, "카테고리");
      if (button.dataset.copy === "tags") copyText(current.tags, "태그");
      if (button.dataset.copy === "image-name") copyText(current.image_filename, "이미지 파일명");
      if (button.dataset.copy === "image-path") copyText(current.image_location, "이미지 경로");
      if (button.dataset.copy === "alt") copyText(current.image_alt, "이미지 대체 문구");
      if (button.dataset.copy === "final") {
        if (!isFinalHtmlStructurallyValid(currentFinalHtml)) {
          setStatus("이미지·광고가 포함된 최종 HTML이 아닙니다.", "error");
          return;
        }
        copyText(currentFinalHtml, "최종 HTML");
      }
    });

    if (firstSlug) selectPost(firstSlug);
  </script>
</body>
</html>
"""
    return (
        template.replace("__BUTTONS__", buttons or empty)
        .replace("__PAYLOAD__", payload)
        .replace("__FIRST_SLUG__", json_for_script(first_slug))
    )


def write_page(posts=None, output_path=OUT_PATH):
    if posts is None:
        posts = load_posts()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render(posts), encoding="utf-8")
    return output_path


def main():
    output = write_page()
    print(f"built: {output}")


if __name__ == "__main__":
    main()
