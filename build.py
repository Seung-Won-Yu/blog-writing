# -*- coding: utf-8 -*-
"""
데일리 다이제스트 — 하루치 상세 페이지 렌더러.
구성: 오늘의 뉴스(소스 수집, 소량) · 기초상식(정처기 문제) · IT/개발/기획 용어.
공유 assets/site.css · site.js 사용.

usage: python build.py <day.json> [out.html]
"""
import json, sys, html, os

KIND_COLORS = {"IT": "#1f6feb", "개발": "#0a8f6b", "기획": "#c2532f"}

def esc(s):
    return html.escape(html.unescape(str(s)))

def strip_check(s):
    s = str(s).lstrip()
    for p in ("✅", "✔️", "✔", "✓", "- ", "* "):
        if s.startswith(p):
            s = s[len(p):].lstrip()
    return s

def oneline(s):
    return " ".join(str(s).split("\n")).strip()

def build_news(news):
    if not news:
        return '<p class="empty">오늘은 수집된 소식이 없습니다.</p>'
    out = []
    for it in news:
        blurb = f'<p class="ni-blurb">{esc(it["blurb_kr"])}</p>' if it.get("blurb_kr") else ""
        title = esc(oneline(it["title_kr"]))
        link = (f'<a href="{esc(it["url"])}" target="_blank" rel="noopener">{title} ↗</a>'
                if it.get("url") else title)
        out.append(f'''
        <li class="newsitem">
          <span class="ni-src">{esc(it.get("source",""))}</span>
          <h3 class="ni-title">{link}</h3>
          {blurb}
        </li>''')
    return f'<ul class="newslist">{"".join(out)}</ul>'

def build_quiz(q):
    letters = "①②③④⑤"
    opts = "".join(
        f'<li class="qopt{" correct" if i == q["answer"] else ""}">'
        f'<span class="ql">{letters[i]}</span> {esc(o)}</li>'
        for i, o in enumerate(q["options"])
    )
    cat = esc(q.get("category", "정보처리기사"))
    ans = letters[q["answer"]]
    return f'''
      <div class="quiz">
        <div class="sectag">#{cat}</div>
        <p class="q-question">{esc(q["question"])}</p>
        <ol class="qopts">{opts}</ol>
        <details class="q-ans">
          <summary>정답 &amp; 해설 보기</summary>
          <p><b>정답: {ans}</b></p>
          <p>{esc(q["explain_kr"])}</p>
        </details>
      </div>'''

def build_terms(terms):
    rows = []
    for t in terms:
        kind = t.get("kind", "IT")
        col = KIND_COLORS.get(kind, "#1f6feb")
        rows.append(f'''
        <li class="termrow">
          <span class="t-kind" style="background:{col}">{esc(kind)}</span>
          <span class="t-term">{esc(t["term"])}</span>
          <span class="t-mean">{esc(t["meaning_kr"])}</span>
        </li>''')
    return f'<ul class="terms">{"".join(rows)}</ul>'

def render_day(d, back_href=None, asset_prefix="../"):
    a = asset_prefix
    back = (f'<div class="dnav"><a class="backlink" href="{esc(back_href)}">← 전체 보기</a></div>') if back_href else ''
    wd = d.get("weekday", "")
    label = f'{esc(d["date_label"])}' + (f' ({esc(wd)})' if wd else '')
    n_news = len(d.get("news", []))
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>데일리 다이제스트 · {esc(d["date_label"])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..600;1,9..144,400..600&family=Hanken+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Noto+Serif+KR:wght@500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{a}assets/site.css">
</head>
<body>
<div class="orbs"><span class="orb o1"></span><span class="orb o2"></span><span class="orb o3"></span></div>
{back}
<main class="reader">
  <div class="kicker">{label} · 데일리 다이제스트</div>
  <h1 class="dhead">오늘 <em>읽을거리</em></h1>
  <p class="dsub">뉴스 · 기초상식(정처기) · IT·개발·기획 용어</p>
  <div class="rule"></div>

  <section class="daystack">
    <article class="daysec sec-news">
      <div class="secnum">01</div>
      <span class="seclabel">오늘의 뉴스</span>
      {build_news(d.get("news", []))}
    </article>

    <article class="daysec sec-quiz">
      <div class="secnum">02</div>
      <span class="seclabel">기초상식 · 정처기</span>
      {build_quiz(d["quiz"])}
    </article>

    <article class="daysec sec-terms">
      <div class="secnum">03</div>
      <span class="seclabel">IT · 개발 · 기획 용어</span>
      {build_terms(d.get("terms", []))}
    </article>
  </section>

  <div class="foot">
    <span class="fbrand">데일리</span> · 읽을거리 · {esc(d["date_label"])}<br>
    뉴스는 yozm.wishket · GeekNews(news.hada.io) · Threads 등에서 수집한 링크입니다. 원문 출처를 확인하세요.
  </div>
</main>
<script src="{a}assets/site.js"></script>
</body></html>'''

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join("data", "days", "sample.json")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join("docs", "day.html")
    with open(src, "r", encoding="utf-8") as f:
        d = json.load(f)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render_day(d, asset_prefix=""))
    print("built:", out)

if __name__ == "__main__":
    main()
