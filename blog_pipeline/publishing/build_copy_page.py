# -*- coding: utf-8 -*-
"""Build a small GitHub Pages UI for copying Tistory draft HTML."""
import html
import json
from datetime import datetime
from pathlib import Path

from .draft_identity import resolve_draft_identity
from .editorial_quality import PUBLISH_GATE_START
from .export_tistory import TISTORY_ADFIT_MARKER, safe_http_url


ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs"
TISTORY_DIR = DOCS_DIR / "tistory"
PREVIEW_DIR = DOCS_DIR / "preview"
OUT_PATH = DOCS_DIR / "index.html"
SKIN_CSS_PATH = ROOT / "design" / "tistory" / "style.css"
EDITOR_GUIDE_URL = (
    "https://github.com/Seung-Won-Yu/blog-writing/blob/main/agent/DAILY_EDITOR.md"
)


def esc(value):
    return html.escape(str(value or ""), quote=True)


def json_for_script(value):
    """Encode JSON so untrusted feed text cannot close the script element."""
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def is_allowed_source(source):
    path = Path(str(source or ""))
    if path.is_absolute() or ".." in path.parts:
        return False
    if path.parts[:2] not in {
        ("data", "days"),
        ("data", "automation_cases"),
        ("data", "guides"),
    }:
        return False
    return len(path.parts) == 3 and path.suffix == ".json" and (ROOT / path).is_file()


def scheduled_label(value, *, publication_mode="scheduled"):
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        scheduled = datetime.fromisoformat(text)
    except ValueError:
        return text
    weekdays = "월화수목금토일"
    label = (
        f"{scheduled.year}. {scheduled.month}. {scheduled.day}. "
        f"({weekdays[scheduled.weekday()]}) {scheduled:%H:%M}"
    )
    return f"즉시 발행 · {label}" if publication_mode == "manual_extra" else label


def safe_image_assets(values):
    assets = []
    for item in values if isinstance(values, list) else []:
        if not isinstance(item, dict):
            continue
        url = safe_http_url(item.get("url"))
        if not url:
            continue
        assets.append({**item, "url": url})
    return assets


def load_drafts():
    drafts = []
    for meta_path in sorted(TISTORY_DIR.glob("*.json"), reverse=True):
        html_path = meta_path.with_suffix(".html")
        if not html_path.exists():
            continue
        with meta_path.open("r", encoding="utf-8") as f:
            meta = json.load(f)
        source = str(meta.get("source") or "")
        file_draft_id = meta_path.stem
        draft_id = str(meta.get("draft_id") or file_draft_id)
        if draft_id != file_draft_id:
            continue
        try:
            identity = resolve_draft_identity(draft_id, meta)
        except ValueError:
            continue
        if source != identity.source or not is_allowed_source(source):
            continue
        publish_date = identity.publish_date
        content_type = identity.content_type
        content_label = identity.content_label
        scheduled_at = str(meta.get("scheduled_at") or "")
        publication_mode = str(meta.get("publication_mode") or "scheduled")
        drafts.append(
            {
                "day": draft_id,
                "draft_id": draft_id,
                "publish_date": publish_date,
                "content_type": content_type,
                "content_label": content_label,
                "publication_mode": publication_mode,
                "scheduled_at": scheduled_at,
                "scheduled_label": scheduled_label(
                    scheduled_at, publication_mode=publication_mode
                ),
                "title": meta.get("title") or draft_id,
                "title_candidates": meta.get("title_candidates") or [],
                "category": meta.get("category") or "",
                "tags": ", ".join(meta.get("tags") or []),
                "meta_description": meta.get("meta_description") or "",
                "key_summary": meta.get("key_summary") or [],
                "publish_checklist": meta.get("publish_checklist") or [],
                "image_assets": safe_image_assets(meta.get("image_assets")),
                "generation_provider": meta.get("generation_provider") or "unknown",
                "publish_ready": bool(meta.get("publish_ready")),
                "quality_reasons": list(meta.get("quality_reasons") or []),
                "source": source,
                "source_page": meta.get("source_page") or "",
                "html_path": f"tistory/{draft_id}.html",
                "before_ad_html_path": f"tistory/{draft_id}-before-ad.html",
                "after_ad_html_path": f"tistory/{draft_id}-after-ad.html",
                "adfit_html_path": f"tistory/{draft_id}-adfit.html",
                "preview_path": f"preview/{draft_id}.html",
                "meta_path": f"tistory/{draft_id}.json",
            }
        )
    return sorted(
        drafts,
        key=lambda item: (
            item["publish_date"],
            item["scheduled_at"],
            item["draft_id"],
        ),
        reverse=True,
    )


def apply_guard_results(drafts, *, root=ROOT):
    """Make the copy UI fail closed when a future full guard is partial."""
    from . import daily_guard

    checked = []
    for original in drafts:
        draft = dict(original)
        try:
            publish_date = datetime.fromisoformat(
                str(draft.get("publish_date") or "")
            ).date()
        except ValueError:
            draft["publish_ready"] = False
            draft["quality_reasons"] = ["invalid_publish_date"]
            checked.append(draft)
            continue
        if publish_date >= PUBLISH_GATE_START and draft.get("publish_ready"):
            identity = resolve_draft_identity(draft.get("draft_id"), draft)
            result = daily_guard.inspect_draft_state(
                identity.draft_id,
                root=root,
                window_days=(
                    90 if identity.content_type == "automation_case" else 60
                ),
            )
            draft["quality_reasons"] = list(result.get("reasons") or [])
            draft["publish_ready"] = result.get("status") == "COMPLETE"
        checked.append(draft)
    return checked


def render_preview_page(draft, fragment):
    """Render the canonical standalone preview bound to one final fragment."""
    preview_fragment = str(fragment or "").replace(
        "https://seung-won-yu.github.io/blog-writing/tistory/assets/",
        "../tistory/assets/",
    )
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow,noarchive">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'none'; img-src 'self' https: data:; style-src 'self' 'unsafe-inline'; font-src data:; base-uri 'none'; form-action 'none'">
  <title>{esc(draft.get("title"))} · 본문 미리보기</title>
  <link rel="stylesheet" href="tistory-style.css">
  <style>
    html {{ background: #f5f7f9; }}
    body.preview-page {{ min-height: 100vh; margin: 0; overflow-wrap: anywhere; }}
    .preview-page #container .content-wrap {{ max-width: none; }}
    .preview-page #content {{
      float: none;
      width: min(740px, 100%);
      margin: 0 auto;
      padding-bottom: 56px;
    }}
    .preview-page img {{ max-width: 100%; height: auto; }}
  </style>
</head>
<body id="tt-body-page" class="layout-aside-right paging-number preview-page">
<div id="wrap">
  <section id="container">
    <div class="content-wrap">
      <article id="content">
        <div class="inner">
          <div class="post-cover">
            <div class="inner">
              <span class="category">{esc(draft.get("category") or "본문 미리보기")}</span>
              <h1>{esc(draft.get("title"))}</h1>
              <span class="meta"><span class="date">{esc(draft.get("publish_date"))} · {esc(draft.get("content_label"))}</span></span>
            </div>
          </div>
          <div class="entry-content" id="article-view">
            <div class="tt_article_useless_p_margin contents_style">
  {preview_fragment}
            </div>
          </div>
        </div>
      </article>
    </div>
  </section>
</div>
</body>
</html>
"""


def write_preview_pages(drafts):
    """Write UTF-8 standalone previews without changing copy-ready fragments."""
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    skin_css = SKIN_CSS_PATH.read_text(encoding="utf-8")
    (PREVIEW_DIR / "tistory-style.css").write_text(skin_css, encoding="utf-8")
    for draft in drafts:
        draft_id = str(draft.get("draft_id") or draft.get("day") or "")
        if not draft_id:
            raise ValueError("draft requires draft_id or day")
        adfit_path = TISTORY_DIR / f"{draft_id}-adfit.html"
        fragment_path = (
            adfit_path if adfit_path.is_file() else TISTORY_DIR / f"{draft_id}.html"
        )
        fragment = fragment_path.read_text(encoding="utf-8")
        page = render_preview_page(draft, fragment)
        (PREVIEW_DIR / f"{draft_id}.html").write_text(page, encoding="utf-8")


def render_draft_buttons(drafts):
    groups = []
    for draft in drafts:
        publish_date = str(draft.get("publish_date") or draft.get("day") or "")
        if not groups or groups[-1][0] != publish_date:
            groups.append((publish_date, []))
        groups[-1][1].append(draft)
    rendered = []
    for publish_date, items in groups:
        rendered.append(
            f'<section class="draft-group"><p class="draft-group-title">'
            f'{esc(publish_date)} · {len(items)}건</p>'
        )
        for item in items:
            draft_id = str(item.get("draft_id") or item.get("day") or "")
            rendered.append(
                f'<button class="draft-btn" type="button" '
                f'data-draft-id="{esc(draft_id)}" aria-pressed="false">'
                f'<span><b>{esc(item.get("content_label") or "뉴스 심층글")}</b>'
                f'<em>{esc(item.get("scheduled_label"))}</em></span>'
                f'<small>{esc(item.get("title"))}</small></button>'
            )
        rendered.append("</section>")
    return "\n".join(rendered)


def render(drafts):
    payload = json_for_script(drafts)
    latest = str((drafts[0].get("draft_id") or drafts[0].get("day") or "")) if drafts else ""
    buttons = render_draft_buttons(drafts)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow,noarchive">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%2328745a'/%3E%3Cpath d='M18 18h28v8H26v20h-8z' fill='white'/%3E%3C/svg%3E">
  <title>티스토리 발행 준비</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17211c;
      --muted: #66716b;
      --line: #d8dedb;
      --paper: #ffffff;
      --canvas: #f3f4f1;
      --accent: #28745a;
      --accent-soft: #edf4f0;
      --warm: #f7f4ec;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--canvas);
      color: var(--ink);
      font-family: "Pretendard Variable", "SUIT Variable", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
      line-height: 1.55;
    }}
    button, textarea {{ font: inherit; }}
    .sr-only {{
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }}
    button:focus-visible, textarea:focus-visible, a:focus-visible {{
      outline: 3px solid #91c4b0;
      outline-offset: 2px;
    }}
    .wrap {{
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 30px 0 52px;
    }}
    .masthead {{
      margin-bottom: 16px;
      padding: 22px 24px;
      border-top: 4px solid var(--accent);
      border-bottom: 1px solid var(--line);
      background: var(--paper);
    }}
    .desk-nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 12px;
    }}
    .desk-nav a {{
      display: inline-flex;
      min-height: 36px;
      align-items: center;
      padding: 0 12px;
      border: 1px solid var(--line);
      border-radius: 3px;
      background: var(--paper);
      color: var(--ink);
      font-size: 13px;
      font-weight: 800;
      text-decoration: none;
    }}
    .desk-nav a[aria-current="page"] {{
      border-color: var(--accent);
      background: var(--accent);
      color: #fff;
    }}
    .eyebrow {{
      margin: 0 0 7px;
      color: var(--accent);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: .14em;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(25px, 3vw, 34px);
      line-height: 1.2;
      letter-spacing: -.035em;
    }}
    .lead {{
      margin: 9px 0 0;
      color: var(--muted);
      font-size: 14px;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 240px minmax(0, 1fr);
      gap: 16px;
      align-items: start;
    }}
    .panel {{
      border: 1px solid var(--line);
      background: var(--paper);
    }}
    .panel-title {{
      padding: 13px 16px;
      border-bottom: 1px solid var(--line);
      background: var(--warm);
      font-size: 13px;
      font-weight: 900;
    }}
    .drafts {{
      display: grid;
      gap: 4px;
      padding: 8px;
    }}
    .draft-group + .draft-group {{
      margin-top: 5px;
      padding-top: 7px;
      border-top: 1px solid var(--line);
    }}
    .draft-group-title {{
      margin: 0;
      padding: 5px 10px 3px;
      color: var(--muted);
      font-size: 11px;
      font-weight: 900;
    }}
    .draft-btn {{
      width: 100%;
      padding: 10px 11px;
      border: 1px solid transparent;
      border-radius: 4px;
      background: transparent;
      color: var(--ink);
      text-align: left;
      cursor: pointer;
    }}
    .draft-btn:hover, .draft-btn.is-active {{
      border-color: #b9d0c5;
      background: var(--accent-soft);
    }}
    .draft-btn span {{
      display: flex;
      gap: 6px;
      align-items: center;
      justify-content: space-between;
      font-size: 13px;
      font-weight: 900;
    }}
    .draft-btn span b {{ font-weight: 900; }}
    .draft-btn span em {{
      color: var(--accent);
      font-size: 10px;
      font-style: normal;
      white-space: nowrap;
    }}
    .draft-btn small {{
      display: -webkit-box;
      margin-top: 3px;
      color: var(--muted);
      font-size: 11px;
      line-height: 1.4;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}
    .content {{ padding: 18px; }}
    .publish-fields {{
      display: grid;
      gap: 8px;
      margin-bottom: 14px;
    }}
    .field {{
      display: grid;
      grid-template-columns: 92px minmax(0, 1fr) auto;
      gap: 10px;
      align-items: center;
      min-height: 48px;
      padding: 9px 11px;
      border-bottom: 1px solid var(--line);
    }}
    .label {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 850;
    }}
    .value {{
      min-width: 0;
      color: #27332d;
      font-size: 14px;
      overflow-wrap: anywhere;
    }}
    .title-value {{
      font-size: 16px;
      font-weight: 850;
      line-height: 1.45;
    }}
    .image-card {{
      display: grid;
      grid-template-columns: 170px minmax(0, 1fr);
      gap: 14px;
      align-items: center;
      margin: 0 0 16px;
      padding: 12px;
      border: 1px solid var(--line);
      background: #fbfcfb;
    }}
    .cover-preview {{
      display: block;
      width: 100%;
      aspect-ratio: 1200 / 630;
      object-fit: cover;
      border: 1px solid var(--line);
      background: var(--warm);
    }}
    .image-info h2 {{
      margin: 0 0 5px;
      font-size: 14px;
    }}
    .image-info p {{
      margin: 0 0 10px;
      color: var(--muted);
      font-size: 12px;
    }}
    .ad-builder {{
      margin: 0 0 14px;
      padding: 14px;
      border: 1px solid var(--line);
      border-left: 4px solid var(--accent);
      background: #fbfcfb;
    }}
    .ad-builder-head {{
      display: flex;
      gap: 12px;
      align-items: end;
      justify-content: space-between;
      margin-bottom: 8px;
    }}
    .ad-builder h2 {{
      margin: 0;
      font-size: 15px;
    }}
    .ad-builder p {{
      margin: 3px 0 0;
      color: var(--muted);
      font-size: 12px;
    }}
    .ad-input {{
      display: block;
      width: 100%;
      min-height: 88px;
      padding: 10px 11px;
      border: 1px solid #bfcac4;
      border-radius: 3px;
      background: #ffffff;
      color: #27332d;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      line-height: 1.5;
      resize: vertical;
    }}
    .action-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      justify-content: flex-end;
      margin: 12px 0 10px;
    }}
    .btn, .download-link {{
      display: inline-flex;
      min-height: 38px;
      align-items: center;
      justify-content: center;
      padding: 0 13px;
      border: 1px solid #9aa8a1;
      border-radius: 3px;
      background: #ffffff;
      color: var(--ink);
      font-size: 13px;
      font-weight: 850;
      text-decoration: none;
      cursor: pointer;
    }}
    .btn.primary {{
      border-color: var(--accent);
      background: var(--accent);
      color: #ffffff;
    }}
    .btn.dark {{
      border-color: #17211c;
      background: #17211c;
      color: #ffffff;
    }}
    .btn:hover:not(:disabled), .download-link:hover {{
      border-color: var(--accent);
      background: var(--accent);
      color: #ffffff;
    }}
    .btn:disabled {{
      cursor: not-allowed;
      opacity: .42;
    }}
    .review-gate {{
      margin: 0 auto 8px 0;
      color: #9a5c12;
      font-size: 12px;
      font-weight: 850;
    }}
    .review-gate[data-ready="true"] {{ color: var(--accent); }}
    .manual-help {{
      margin: 0 0 10px;
      padding: 10px 12px;
      border-left: 3px solid #c99b43;
      background: var(--warm);
      color: #46534d;
      font-size: 12px;
    }}
    .code-output {{
      display: block;
      width: 100%;
      min-height: 440px;
      padding: 15px;
      border: 1px solid #263449;
      border-radius: 3px;
      background: #0b1220;
      color: #dce8f8;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      line-height: 1.6;
      resize: vertical;
      white-space: pre;
    }}
    .preview-pane {{
      width: 100%;
      min-height: 700px;
      border: 1px solid var(--line);
      background: #ffffff;
      overflow: hidden;
    }}
    .preview-frame {{
      display: block;
      width: 100%;
      height: min(82vh, 1040px);
      min-height: 700px;
      border: 0;
      background: #ffffff;
    }}
    textarea[hidden], .preview-pane[hidden] {{ display: none; }}
    .status {{
      min-height: 20px;
      margin-top: 8px;
      color: var(--accent);
      font-size: 12px;
      font-weight: 800;
    }}
    .status[data-kind="error"] {{ color: #a33b2b; }}
    .empty {{
      padding: 22px 14px;
      color: var(--muted);
      font-size: 13px;
    }}
    @media (max-width: 760px) {{
      .wrap {{ width: min(100% - 20px, 680px); padding-top: 14px; }}
      .masthead {{ padding: 18px; }}
      .layout {{ grid-template-columns: 1fr; }}
      .content {{ padding: 12px; }}
      .field {{ grid-template-columns: 1fr auto; }}
      .field .label {{ grid-column: 1 / -1; }}
      .image-card {{ grid-template-columns: 1fr; }}
      .ad-builder-head {{ align-items: stretch; flex-direction: column; }}
      .action-row {{ display: grid; grid-template-columns: 1fr; }}
      .btn, .download-link {{ width: 100%; }}
      .code-output {{ min-height: 360px; }}
      .preview-pane, .preview-frame {{ min-height: 560px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <nav class="desk-nav" aria-label="발행 도구">
      <a href="./" aria-current="page">데일리 뉴스 발행</a>
      <a href="integration.html">보강글 HTML 조립</a>
    </nav>
    <header class="masthead">
      <p class="eyebrow">DAILY PUBLISH DESK</p>
      <h1>오늘 글 발행 준비</h1>
      <p class="lead">매일 09:00 Codex Terra / Medium 뉴스 심층글과 토요일 14:00 업무자동화 실험글의 발행 준비물을 확인합니다.</p>
    </header>

    <div class="layout">
      <aside class="panel">
        <div class="panel-title">초안 날짜</div>
        <div class="drafts" id="drafts">{buttons or '<p class="empty">아직 생성된 초안이 없습니다.</p>'}</div>
      </aside>

      <main class="panel">
        <div class="panel-title">티스토리 붙여넣기</div>
        <div class="content">
          <section class="publish-fields" aria-label="발행 정보">
            <div class="field"><span class="label">추천 제목</span><span class="value title-value" id="title"></span><button class="btn dark" type="button" data-copy="title">복사</button></div>
            <div class="field"><span class="label">카테고리</span><span class="value" id="category"></span><button class="btn" type="button" data-copy="category">복사</button></div>
            <div class="field"><span class="label">태그</span><span class="value" id="tags"></span><button class="btn" type="button" data-copy="tags">복사</button></div>
            <div class="field"><span class="label">발행 방식</span><span class="value" id="schedule"></span><button class="btn" type="button" data-copy="schedule">복사</button></div>
          </section>

          <section class="image-card" id="imageCard" hidden>
            <img class="cover-preview" id="coverPreview" alt="대표 이미지 미리보기" loading="lazy">
            <div class="image-info">
              <h2>대표 이미지</h2>
              <p id="coverTitle"></p>
              <a class="download-link" id="coverDownload" href="#" download>대표 이미지 다운로드</a>
            </div>
          </section>

          <section class="ad-builder">
            <div class="ad-builder-head">
              <div>
                <h2><label for="adMarkup">광고 HTML 태그</label></h2>
                <p>티스토리 광고 넣기로 만든 태그를 붙이면 첫 핵심 설명이 끝난 35~45% 위치에 정확히 한 번 들어갑니다.</p>
              </div>
              <button class="btn primary" type="button" id="buildFinalButton" disabled>최종 HTML 만들기</button>
            </div>
            <textarea class="ad-input" id="adMarkup" spellcheck="false"></textarea>
          </section>

          <div class="action-row">
            <p class="review-gate" id="reviewGateStatus" data-ready="false">초안을 선택해 주세요.</p>
            <button class="btn" type="button" id="previewButton" aria-expanded="false" aria-controls="previewPane" disabled>본문 미리보기</button>
            <button class="btn dark" type="button" id="finalCopyButton" data-copy="final" disabled>최종 HTML 복사</button>
          </div>
          <div class="status" id="status" role="status" aria-live="polite"></div>
          <p class="manual-help"><strong>붙여넣기:</strong> 최종 HTML을 티스토리 HTML 모드에 한 번 붙여넣고 기본모드로 다시 전환하지 마세요.</p>
          <label class="sr-only" for="htmlCode">최종 블로그 본문 HTML</label>
          <textarea class="code-output" id="htmlCode" spellcheck="false" readonly></textarea>
          <section class="preview-pane" id="previewPane" aria-label="블로그 본문 미리보기" hidden>
            <iframe class="preview-frame" id="previewFrame" title="블로그 본문 미리보기" sandbox="allow-same-origin" referrerpolicy="no-referrer"></iframe>
          </section>
        </div>
      </main>
    </div>
  </div>

  <script>
    const drafts = {payload};
    const latest = {json_for_script(latest)};
    const defaultAdMarkup = {json_for_script(TISTORY_ADFIT_MARKER)};
    const revenueMarkerPattern = /<figure\\b(?=[^>]*data-ke-type=["']revenue["'])[^>]*><\\/figure>/gi;
    let current = null;
    let currentPreviewPath = "";
    let currentBaseHtml = "";
    let currentAdfitHtml = "";
    let currentFinalHtml = "";
    let selectionRevision = 0;
    const byId = new Map(drafts.map((item) => [item.draft_id, item]));

    const els = {{
      title: document.getElementById("title"),
      category: document.getElementById("category"),
      tags: document.getElementById("tags"),
      schedule: document.getElementById("schedule"),
      imageCard: document.getElementById("imageCard"),
      coverPreview: document.getElementById("coverPreview"),
      coverTitle: document.getElementById("coverTitle"),
      coverDownload: document.getElementById("coverDownload"),
      adMarkup: document.getElementById("adMarkup"),
      buildFinalButton: document.getElementById("buildFinalButton"),
      finalCopyButton: document.getElementById("finalCopyButton"),
      htmlCode: document.getElementById("htmlCode"),
      status: document.getElementById("status"),
      previewButton: document.getElementById("previewButton"),
      previewPane: document.getElementById("previewPane"),
      previewFrame: document.getElementById("previewFrame"),
      reviewGateStatus: document.getElementById("reviewGateStatus"),
    }};

    function setStatus(text, kind = "success") {{
      els.status.textContent = text;
      els.status.dataset.kind = kind;
      if (text && kind !== "error") setTimeout(() => {{
        if (els.status.textContent === text) els.status.textContent = "";
      }}, 2200);
    }}

    function isDraftCopyReady() {{
      return Boolean(current && current.publish_ready && currentBaseHtml && currentAdfitHtml);
    }}

    function reviewGateMessage() {{
      if (!current) return "초안을 선택해 주세요.";
      if (!current.publish_ready) {{
        const reasons = (current.quality_reasons || []).join(", ");
        return "발행 보류 · " + (reasons || "품질 검사를 통과한 초안이 아닙니다.");
      }}
      if (!currentFinalHtml) return "광고 태그 확인 후 최종 HTML을 만들어 주세요.";
      return "최종 HTML 준비 완료 · " + currentFinalHtml.length.toLocaleString() + "자";
    }}

    function updateCopyState() {{
      const ready = isDraftCopyReady();
      els.buildFinalButton.disabled = !ready;
      els.finalCopyButton.disabled = !ready || !currentFinalHtml;
      els.reviewGateStatus.textContent = reviewGateMessage();
      els.reviewGateStatus.dataset.ready = String(Boolean(ready && currentFinalHtml));
    }}

    function selectCoverAsset(assets) {{
      const validAssets = (assets || []).filter(
        (asset) => asset && safeImageUrl(asset.url)
      );
      return validAssets.find((asset) => asset.kind === "cover") || validAssets[0];
    }}

    function safeImageUrl(value) {{
      try {{
        const url = new URL(value, window.location.href);
        return ["http:", "https:"].includes(url.protocol) ? url.href : "";
      }} catch (error) {{
        return "";
      }}
    }}

    function filenameFromUrl(url) {{
      try {{
        const pathname = new URL(url).pathname;
        return pathname.split("/").filter(Boolean).pop() || "cover-image.png";
      }} catch (error) {{
        return "cover-image.png";
      }}
    }}

    function renderCover(assets) {{
      const cover = selectCoverAsset(assets);
      if (!cover) {{
        els.imageCard.hidden = true;
        els.coverPreview.removeAttribute("src");
        return;
      }}
      const coverUrl = safeImageUrl(cover.url);
      if (!coverUrl) {{
        els.imageCard.hidden = true;
        return;
      }}
      els.imageCard.hidden = false;
      els.coverPreview.src = coverUrl;
      els.coverPreview.alt = cover.alt || "대표 이미지 미리보기";
      els.coverTitle.textContent = cover.title || "오늘 글 대표 이미지";
      els.coverDownload.href = coverUrl;
      els.coverDownload.download = current.draft_id + "-" + filenameFromUrl(coverUrl);
    }}

    function extractRevenueMarkup(value) {{
      const matches = String(value || "").match(revenueMarkerPattern) || [];
      return matches.length === 1 ? matches[0] : "";
    }}

    function isFinalHtmlStructurallyValid(value) {{
      if (!value || value.length < 1000) return false;
      const parsed = new DOMParser().parseFromString(value, "text/html");
      const articles = parsed.querySelectorAll(".daily-digest-post");
      const news = parsed.querySelectorAll(".digest-news-card");
      const ads = parsed.querySelectorAll('[data-ad-vendor="adfit"]');
      const nextSection = parsed.querySelector(".digest-lead-continuation") || news[1];
      if (articles.length !== 1 || news.length < 1 || ads.length !== 1 || !nextSection) return false;
      const firstBeforeAd = Boolean(news[0].compareDocumentPosition(ads[0]) & 4);
      const adBeforeNext = Boolean(ads[0].compareDocumentPosition(nextSection) & 4);
      return firstBeforeAd && adBeforeNext;
    }}

    function buildFinalHtml(showMessage = true) {{
      if (!isDraftCopyReady()) {{
        if (showMessage) setStatus(reviewGateMessage(), "error");
        return false;
      }}
      const markup = extractRevenueMarkup(els.adMarkup.value);
      if (!markup) {{
        currentFinalHtml = "";
        els.htmlCode.value = currentAdfitHtml;
        updateCopyState();
        if (showMessage) setStatus("AdFit 광고 태그 1개를 찾을 수 없습니다.", "error");
        return false;
      }}
      const markers = currentAdfitHtml.match(revenueMarkerPattern) || [];
      if (markers.length !== 1) {{
        currentFinalHtml = "";
        updateCopyState();
        if (showMessage) setStatus("광고 위치가 1개인지 확인할 수 없습니다.", "error");
        return false;
      }}
      currentFinalHtml = currentAdfitHtml.replace(revenueMarkerPattern, markup);
      if (!isFinalHtmlStructurallyValid(currentFinalHtml)) {{
        currentFinalHtml = "";
        els.htmlCode.value = currentAdfitHtml;
        updateCopyState();
        if (showMessage) setStatus("최종 본문 구조 검사에 실패했습니다. 복사하지 않았습니다.", "error");
        return false;
      }}
      els.adMarkup.value = markup;
      els.htmlCode.value = currentFinalHtml;
      window.localStorage.setItem("tistory-ad-markup", markup);
      updateCopyState();
      if (showMessage) setStatus("최종 HTML 생성 완료");
      return true;
    }}

    function setPreviewMode(showingPreview) {{
      els.previewPane.hidden = !showingPreview;
      els.htmlCode.hidden = showingPreview;
      els.previewButton.setAttribute("aria-expanded", String(showingPreview));
      els.previewButton.textContent = showingPreview ? "HTML 코드 보기" : "본문 미리보기";
    }}

    async function selectDraft(draftId) {{
      const draft = byId.get(draftId);
      if (!draft) return;
      const revision = ++selectionRevision;
      current = draft;
      document.querySelectorAll(".draft-btn").forEach((button) => {{
        const selected = button.dataset.draftId === draftId;
        button.classList.toggle("is-active", selected);
        button.setAttribute("aria-pressed", String(selected));
      }});
      els.title.textContent = draft.title || "";
      els.category.textContent = draft.category || "";
      els.tags.textContent = draft.tags || "";
      els.schedule.textContent = draft.scheduled_label || draft.scheduled_at || "직접 지정";
      renderCover(draft.image_assets);
      currentBaseHtml = "";
      currentAdfitHtml = "";
      currentFinalHtml = "";
      setPreviewMode(false);
      els.previewButton.disabled = true;
      els.previewFrame.removeAttribute("src");
      currentPreviewPath = "";
      els.htmlCode.value = "불러오는 중...";
      updateCopyState();
      try {{
        const cacheBust = "?v=" + Date.now();
        const responses = await Promise.all([
          fetch(draft.html_path + cacheBust),
          fetch(draft.adfit_html_path + cacheBust),
        ]);
        if (!responses[0].ok || !responses[1].ok) throw new Error("HTML fetch failed");
        const bodies = await Promise.all([responses[0].text(), responses[1].text()]);
        if (revision !== selectionRevision) return;
        currentBaseHtml = bodies[0];
        currentAdfitHtml = bodies[1];
        currentPreviewPath = draft.preview_path + "?v=" + Date.now();
        els.previewButton.disabled = false;
        buildFinalHtml(false);
        els.previewFrame.setAttribute("src", currentPreviewPath);
        setPreviewMode(true);
        updateCopyState();
        setStatus(draft.publish_date + " · " + draft.content_label + " 초안을 불러왔습니다.");
      }} catch (error) {{
        if (revision !== selectionRevision) return;
        currentBaseHtml = "";
        currentAdfitHtml = "";
        currentFinalHtml = "";
        updateCopyState();
        els.htmlCode.value = "초안을 불러오지 못했습니다.";
        setStatus("초안을 불러오지 못했습니다. 잠시 뒤 새로고침해 주세요.", "error");
      }}
    }}

    async function copyText(text, label) {{
      if (!text) {{
        setStatus("복사할 내용이 없습니다.", "error");
        return false;
      }}
      let copied = false;
      try {{
        if (navigator.clipboard && window.isSecureContext) {{
          await navigator.clipboard.writeText(text);
          copied = true;
        }}
      }} catch (error) {{
        copied = false;
      }}
      if (!copied) {{
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
      }}
      if (!copied) {{
        setStatus("복사에 실패했습니다. HTML 코드 보기에서 전체 코드를 직접 복사해 주세요.", "error");
        return false;
      }}
      setStatus(label + " 복사 완료 · " + text.length.toLocaleString() + "자");
      return true;
    }}

    els.adMarkup.value = window.localStorage.getItem("tistory-ad-markup") || defaultAdMarkup;

    els.adMarkup.addEventListener("input", () => {{
      currentFinalHtml = "";
      if (currentAdfitHtml) els.htmlCode.value = currentAdfitHtml;
      updateCopyState();
      setStatus("광고 태그 변경됨 · 최종 HTML 만들기를 눌러 주세요.");
    }});

    els.buildFinalButton.addEventListener("click", () => buildFinalHtml(true));

    els.previewButton.addEventListener("click", () => {{
      const showingPreview = els.previewButton.getAttribute("aria-expanded") !== "true";
      if (showingPreview && !els.previewFrame.hasAttribute("src")) {{
        els.previewFrame.setAttribute("src", currentPreviewPath);
      }}
      setPreviewMode(showingPreview);
    }});

    document.getElementById("drafts").addEventListener("click", (event) => {{
      const button = event.target.closest(".draft-btn");
      if (button) selectDraft(button.dataset.draftId);
    }});

    document.addEventListener("click", (event) => {{
      const button = event.target.closest("[data-copy]");
      if (!button || !current) return;
      const type = button.dataset.copy;
      if (type === "final") {{
        if (!isDraftCopyReady() || !isFinalHtmlStructurallyValid(currentFinalHtml)) {{
          setStatus("전체 본문 구조가 확인되지 않아 복사하지 않았습니다.", "error");
          return;
        }}
        copyText(currentFinalHtml, "최종 HTML");
      }}
      if (type === "title") copyText(current.title, "추천 제목");
      if (type === "category") copyText(current.category, "카테고리");
      if (type === "tags") copyText(current.tags, "태그");
      if (type === "schedule") copyText(current.scheduled_label || current.scheduled_at, "발행 설정");
    }});

    if (latest) selectDraft(latest);
  </script>
</body>
</html>
"""

def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    TISTORY_DIR.mkdir(parents=True, exist_ok=True)
    drafts = load_drafts()
    write_preview_pages(drafts)
    drafts = apply_guard_results(drafts, root=ROOT)
    OUT_PATH.write_text(render(drafts), encoding="utf-8")
    print(f"built: {OUT_PATH}")


if __name__ == "__main__":
    main()
