# -*- coding: utf-8 -*-
"""Build a small GitHub Pages UI for copying Tistory draft HTML."""
import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT / "docs"
TISTORY_DIR = DOCS_DIR / "tistory"
OUT_PATH = DOCS_DIR / "index.html"
WORKFLOW_URL = "https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/tistory-draft.yml"


def esc(value):
    return html.escape(str(value or ""), quote=True)


def load_drafts():
    drafts = []
    for meta_path in sorted(TISTORY_DIR.glob("*.json"), reverse=True):
        html_path = meta_path.with_suffix(".html")
        if not html_path.exists():
            continue
        with meta_path.open("r", encoding="utf-8") as f:
            meta = json.load(f)
        day = meta_path.stem
        drafts.append(
            {
                "day": day,
                "title": meta.get("title") or day,
                "title_candidates": meta.get("title_candidates") or [],
                "category": meta.get("category") or "",
                "tags": ", ".join(meta.get("tags") or []),
                "meta_description": meta.get("meta_description") or "",
                "key_summary": meta.get("key_summary") or [],
                "publish_checklist": meta.get("publish_checklist") or [],
                "image_assets": meta.get("image_assets") or [],
                "source_page": meta.get("source_page") or "",
                "html_path": f"tistory/{day}.html",
                "meta_path": f"tistory/{day}.json",
            }
        )
    return drafts


def render(drafts):
    payload = json.dumps(drafts, ensure_ascii=False)
    latest = drafts[0]["day"] if drafts else ""
    buttons = "\n".join(
        f'<button class="draft-btn" type="button" data-day="{esc(item["day"])}">'
        f'<span>{esc(item["day"])}</span><small>{esc(item["title"])}</small></button>'
        for item in drafts
    )
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>티스토리 블로그 초안 복사</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #111827;
      --muted: #64748b;
      --line: #dbe5ee;
      --soft: #f8fafc;
      --accent: #0f9b8e;
      --accent-weak: #e8f7f4;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: #f5f7fb;
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
      line-height: 1.6;
    }}
    .wrap {{
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 34px 0 54px;
    }}
    header {{
      margin-bottom: 24px;
      padding: 26px 28px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: linear-gradient(135deg, #ffffff 0%, #f1faf8 64%, #fff7ed 100%);
      box-shadow: 0 16px 42px rgba(15, 23, 42, 0.07);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 30px;
      line-height: 1.25;
      letter-spacing: 0;
    }}
    .lead {{
      margin: 0;
      color: var(--muted);
      font-size: 15px;
    }}
    .header-row {{
      display: flex;
      gap: 16px;
      align-items: center;
      justify-content: space-between;
    }}
    .header-copy {{
      min-width: 0;
    }}
    .action-btn {{
      display: inline-flex;
      min-height: 42px;
      flex: 0 0 auto;
      align-items: center;
      justify-content: center;
      padding: 0 16px;
      border-radius: 12px;
      background: #111827;
      color: #ffffff;
      font-size: 14px;
      font-weight: 850;
      text-decoration: none;
      white-space: nowrap;
    }}
    .action-btn:hover {{
      background: #0f9b8e;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 310px minmax(0, 1fr);
      gap: 18px;
      align-items: start;
    }}
    .panel {{
      border: 1px solid var(--line);
      border-radius: 16px;
      background: #ffffff;
      box-shadow: 0 12px 34px rgba(15, 23, 42, 0.06);
      overflow: hidden;
    }}
    .side-head, .main-head {{
      padding: 16px 18px;
      border-bottom: 1px solid var(--line);
      background: var(--soft);
      font-weight: 850;
    }}
    .drafts {{
      display: grid;
      gap: 8px;
      padding: 12px;
    }}
    .draft-btn {{
      width: 100%;
      padding: 12px 13px;
      border: 1px solid transparent;
      border-radius: 12px;
      background: #ffffff;
      color: var(--ink);
      text-align: left;
      cursor: pointer;
    }}
    .draft-btn:hover, .draft-btn.is-active {{
      border-color: #9ad9d0;
      background: var(--accent-weak);
    }}
    .draft-btn span {{
      display: block;
      font-weight: 850;
    }}
    .draft-btn small {{
      display: -webkit-box;
      margin-top: 4px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}
    .content {{
      padding: 18px;
    }}
    .meta-grid {{
      display: grid;
      gap: 10px;
      margin-bottom: 16px;
    }}
    .field {{
      display: grid;
      grid-template-columns: 84px minmax(0, 1fr) auto;
      gap: 10px;
      align-items: center;
      padding: 11px 12px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #ffffff;
    }}
    .label {{
      color: var(--muted);
      font-size: 13px;
      font-weight: 800;
    }}
    .value {{
      min-width: 0;
      overflow: hidden;
      color: #243044;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .value.long {{
      white-space: normal;
    }}
    .assist-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin: 0 0 18px;
    }}
    .assist-card {{
      min-width: 0;
      padding: 15px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
    }}
    .assist-card h2 {{
      margin: 0 0 10px;
      color: #18212f;
      font-size: 15px;
      line-height: 1.35;
    }}
    .assist-card ul {{
      display: grid;
      gap: 8px;
      margin: 0 0 12px;
      padding-left: 18px;
      color: #334155;
      font-size: 14px;
    }}
    .assist-card li {{
      padding-left: 2px;
    }}
    .assist-card p {{
      margin: 0 0 12px;
      color: #334155;
      font-size: 14px;
    }}
    .image-card {{
      display: grid;
      grid-template-columns: 180px minmax(0, 1fr);
      gap: 14px;
      align-items: start;
      margin: 0 0 18px;
      padding: 15px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #ffffff;
    }}
    .cover-preview {{
      width: 100%;
      aspect-ratio: 16 / 9;
      object-fit: cover;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--soft);
    }}
    .image-info {{
      min-width: 0;
    }}
    .image-info h2 {{
      margin: 0 0 6px;
      color: #18212f;
      font-size: 15px;
      line-height: 1.35;
    }}
    .image-info p {{
      margin: 0 0 10px;
      color: #334155;
      font-size: 14px;
    }}
    .image-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .download-link {{
      display: inline-flex;
      min-height: 36px;
      align-items: center;
      justify-content: center;
      padding: 0 12px;
      border-radius: 10px;
      background: #0f9b8e;
      color: #ffffff;
      font-size: 13px;
      font-weight: 850;
      text-decoration: none;
    }}
    .image-list {{
      margin: 10px 0 0;
      padding-left: 18px;
      color: var(--muted);
      font-size: 13px;
    }}
    .image-list a {{
      color: #0f766e;
      text-decoration: none;
    }}
    button.copy {{
      min-height: 36px;
      padding: 0 12px;
      border: 0;
      border-radius: 10px;
      background: #111827;
      color: #ffffff;
      font-weight: 850;
      cursor: pointer;
    }}
    button.copy.secondary {{
      background: #0f9b8e;
    }}
    .code-head {{
      display: flex;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
      margin: 18px 0 10px;
    }}
    .code-head h2 {{
      margin: 0;
      font-size: 18px;
    }}
    textarea {{
      display: block;
      width: 100%;
      min-height: 560px;
      padding: 16px;
      border: 1px solid #cfdbe7;
      border-radius: 14px;
      background: #0b1220;
      color: #dce8f8;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
      font-size: 13px;
      line-height: 1.62;
      resize: vertical;
      white-space: pre;
    }}
    .status {{
      min-height: 22px;
      margin-top: 10px;
      color: var(--accent);
      font-size: 13px;
      font-weight: 800;
    }}
    .empty {{
      padding: 28px;
      color: var(--muted);
    }}
    @media (max-width: 820px) {{
      .layout {{ grid-template-columns: 1fr; }}
      .header-row {{ align-items: stretch; flex-direction: column; }}
      .action-btn {{ width: 100%; }}
      .assist-grid {{ grid-template-columns: 1fr; }}
      .image-card {{ grid-template-columns: 1fr; }}
      .field {{ grid-template-columns: 1fr; }}
      button.copy {{ width: 100%; }}
      .download-link {{ width: 100%; }}
      textarea {{ min-height: 430px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="header-row">
        <div class="header-copy">
          <h1>티스토리 블로그 초안 복사</h1>
          <p class="lead">조이한 데일리 뉴스룸에서 가져온 글을 티스토리 HTML 모드에 바로 붙여넣을 수 있게 보여줍니다.</p>
        </div>
        <a class="action-btn" href="{esc(WORKFLOW_URL)}" target="_blank" rel="noopener" title="GitHub Actions에서 Run workflow를 누르면 오늘 초안을 생성하고 복사 페이지 배포까지 실행합니다.">초안 수동 생성/배포</a>
      </div>
    </header>

    <div class="layout">
      <aside class="panel">
        <div class="side-head">초안 목록</div>
        <div class="drafts" id="drafts">{buttons or '<p class="empty">아직 생성된 초안이 없습니다.</p>'}</div>
      </aside>

      <main class="panel">
        <div class="main-head">붙여넣기 정보</div>
        <div class="content" id="content">
          <div class="meta-grid">
            <div class="field"><span class="label">제목</span><span class="value" id="title"></span><button class="copy" type="button" data-copy="title">복사</button></div>
            <div class="field"><span class="label">카테고리</span><span class="value" id="category"></span><button class="copy" type="button" data-copy="category">복사</button></div>
            <div class="field"><span class="label">태그</span><span class="value" id="tags"></span><button class="copy" type="button" data-copy="tags">복사</button></div>
            <div class="field"><span class="label">첫 문단/메타</span><span class="value long" id="metaDescription"></span><button class="copy" type="button" data-copy="meta">복사</button></div>
            <div class="field"><span class="label">원본</span><span class="value" id="source"></span><button class="copy" type="button" data-copy="source">복사</button></div>
          </div>

          <section class="image-card" id="imageCard" hidden>
            <img class="cover-preview" id="coverPreview" alt="대표 이미지 미리보기" loading="lazy">
            <div class="image-info">
              <h2>대표 이미지</h2>
              <p id="coverTitle"></p>
              <div class="image-actions">
                <a class="download-link" id="coverDownload" href="#" download>대표 이미지 다운로드</a>
                <button class="copy" type="button" data-copy="coverUrl">이미지 URL 복사</button>
              </div>
              <ul class="image-list" id="imageList"></ul>
            </div>
          </section>

          <div class="assist-grid">
            <section class="assist-card">
              <h2>검색형 제목 후보</h2>
              <ul id="titleCandidates"></ul>
              <button class="copy" type="button" data-copy="titles">제목 후보 복사</button>
            </section>
            <section class="assist-card">
              <h2>오늘의 핵심 요약</h2>
              <ul id="keySummary"></ul>
              <button class="copy" type="button" data-copy="summary">요약 복사</button>
            </section>
            <section class="assist-card">
              <h2>발행 체크리스트</h2>
              <ul id="publishChecklist"></ul>
              <button class="copy" type="button" data-copy="checklist">체크리스트 복사</button>
            </section>
            <section class="assist-card">
              <h2>운영 메모</h2>
              <p>제목은 후보 중 하나를 골라 티스토리 제목칸에 넣고, 본문은 HTML 모드에서 붙여넣으면 됩니다.</p>
              <button class="copy" type="button" data-copy="allMeta">운영 정보 전체 복사</button>
            </section>
          </div>

          <div class="code-head">
            <h2>본문 HTML 코드</h2>
            <button class="copy secondary" type="button" data-copy="html">본문 HTML 복사</button>
          </div>
          <textarea id="htmlCode" spellcheck="false"></textarea>
          <div class="status" id="status"></div>
        </div>
      </main>
    </div>
  </div>

  <script>
    const drafts = {payload};
    const latest = {json.dumps(latest, ensure_ascii=False)};
    let current = null;
    let currentHtml = "";
    const byDay = new Map(drafts.map((item) => [item.day, item]));

    const els = {{
      title: document.getElementById("title"),
      category: document.getElementById("category"),
      tags: document.getElementById("tags"),
      metaDescription: document.getElementById("metaDescription"),
      source: document.getElementById("source"),
      titleCandidates: document.getElementById("titleCandidates"),
      keySummary: document.getElementById("keySummary"),
      publishChecklist: document.getElementById("publishChecklist"),
      imageCard: document.getElementById("imageCard"),
      coverPreview: document.getElementById("coverPreview"),
      coverTitle: document.getElementById("coverTitle"),
      coverDownload: document.getElementById("coverDownload"),
      imageList: document.getElementById("imageList"),
      htmlCode: document.getElementById("htmlCode"),
      status: document.getElementById("status"),
    }};

    function setStatus(text) {{
      els.status.textContent = text;
      if (text) setTimeout(() => {{ if (els.status.textContent === text) els.status.textContent = ""; }}, 1800);
    }}

    function renderList(target, rows) {{
      target.innerHTML = "";
      (rows || []).forEach((text) => {{
        const li = document.createElement("li");
        li.textContent = text;
        target.appendChild(li);
      }});
    }}

    function numbered(rows) {{
      return (rows || []).map((text, index) => `${{index + 1}}. ${{text}}`).join("\\n");
    }}

    function operatingMemo() {{
      if (!current) return "";
      return [
        "[제목 후보]",
        numbered(current.title_candidates),
        "",
        "[첫 문단/메타 설명]",
        current.meta_description || "",
        "",
        "[핵심 요약]",
        numbered(current.key_summary),
        "",
        "[발행 체크리스트]",
        numbered(current.publish_checklist),
      ].join("\\n");
    }}

    function filenameFromUrl(url) {{
      try {{
        const pathname = new URL(url).pathname;
        return pathname.split("/").filter(Boolean).pop() || "cover-image.png";
      }} catch (error) {{
        return "cover-image.png";
      }}
    }}

    function renderImageAssets(assets) {{
      const cover = (assets || [])[0];
      els.imageList.innerHTML = "";
      if (!cover || !cover.url) {{
        els.imageCard.hidden = true;
        els.coverPreview.removeAttribute("src");
        return;
      }}

      els.imageCard.hidden = false;
      els.coverPreview.src = cover.url;
      els.coverTitle.textContent = cover.title || "오늘 글 대표 이미지";
      els.coverDownload.href = cover.url;
      els.coverDownload.download = `${{current.day}}-${{filenameFromUrl(cover.url)}}`;

      (assets || []).forEach((asset, index) => {{
        if (!asset.url) return;
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.href = asset.url;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = `${{index + 1}}번 이미지 열기`;
        li.appendChild(a);
        els.imageList.appendChild(li);
      }});
    }}

    async function selectDraft(day) {{
      const draft = byDay.get(day);
      if (!draft) return;
      current = draft;
      document.querySelectorAll(".draft-btn").forEach((button) => {{
        button.classList.toggle("is-active", button.dataset.day === day);
      }});
      els.title.textContent = draft.title || "";
      els.category.textContent = draft.category || "";
      els.tags.textContent = draft.tags || "";
      els.metaDescription.textContent = draft.meta_description || "";
      els.source.textContent = draft.source_page || "";
      renderList(els.titleCandidates, draft.title_candidates);
      renderList(els.keySummary, draft.key_summary);
      renderList(els.publishChecklist, draft.publish_checklist);
      renderImageAssets(draft.image_assets);
      els.htmlCode.value = "불러오는 중...";
      const response = await fetch(draft.html_path + "?v=" + Date.now());
      currentHtml = await response.text();
      els.htmlCode.value = currentHtml;
      setStatus(day + " 초안을 불러왔습니다.");
    }}

    async function copyText(text, label) {{
      if (!text) return;
      try {{
        await navigator.clipboard.writeText(text);
      }} catch (error) {{
        els.htmlCode.focus();
        els.htmlCode.select();
        document.execCommand("copy");
      }}
      setStatus(label + " 복사 완료");
    }}

    document.getElementById("drafts").addEventListener("click", (event) => {{
      const button = event.target.closest(".draft-btn");
      if (button) selectDraft(button.dataset.day);
    }});

    document.addEventListener("click", (event) => {{
      const button = event.target.closest("[data-copy]");
      if (!button || !current) return;
      const type = button.dataset.copy;
      if (type === "html") copyText(currentHtml, "본문 HTML");
      if (type === "title") copyText(current.title, "제목");
      if (type === "titles") copyText(numbered(current.title_candidates), "제목 후보");
      if (type === "category") copyText(current.category, "카테고리");
      if (type === "tags") copyText(current.tags, "태그");
      if (type === "meta") copyText(current.meta_description, "메타 설명");
      if (type === "summary") copyText(numbered(current.key_summary), "핵심 요약");
      if (type === "checklist") copyText(numbered(current.publish_checklist), "체크리스트");
      if (type === "allMeta") copyText(operatingMemo(), "운영 정보");
      if (type === "coverUrl") copyText((current.image_assets || [])[0]?.url, "대표 이미지 URL");
      if (type === "source") copyText(current.source_page, "원본 링크");
    }});

    if (latest) selectDraft(latest);
  </script>
</body>
</html>
"""


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    TISTORY_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(render(load_drafts()), encoding="utf-8")
    print(f"built: {OUT_PATH}")


if __name__ == "__main__":
    main()
