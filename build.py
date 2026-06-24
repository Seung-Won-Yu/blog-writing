# -*- coding: utf-8 -*-
"""
데일리 다이제스트 — 하루치 상세 페이지 렌더러.
미니멀 에디토리얼 디자인. 공유 assets/site.css · site.js 사용 (index와 동일 시스템).
구성: 뉴스 1 · 꿀팁 1 · 이것저것 1.

usage: python build.py <day.json> [out.html]
"""
import json, sys, html, os

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

def _src(obj):
    if obj.get("url") and obj.get("source"):
        return f'<a class="ssrc" href="{esc(obj["url"])}" target="_blank" rel="noopener">출처 · {esc(obj["source"])} ↗</a>'
    if obj.get("source"):
        return f'<span class="ssrc">출처 · {esc(obj["source"])}</span>'
    return ""

def build_sections(d):
    news, tip, misc = d["news"], d["tip"], d["misc"]
    facts = "".join(f"<li>{esc(strip_check(b))}</li>" for b in news["bullets_kr"])
    steps = "".join(f"<li>{esc(strip_check(s))}</li>" for s in tip["steps_kr"])
    return f'''
      <article class="daysec sec-news">
        <div class="secnum">01</div>
        <span class="seclabel">뉴스</span>
        <h2 class="stitle">{esc(oneline(news["title_kr"]))}</h2>
        <ul class="sfacts">{facts}</ul>
        <div class="stake">{esc(news["why_kr"])}</div><br>
        {_src(news)}
      </article>

      <article class="daysec sec-tip">
        <div class="secnum">02</div>
        <span class="seclabel">꿀팁</span>
        <div class="sectag">#{esc(tip.get("tag","개발"))}</div>
        <h2 class="stitle">{esc(oneline(tip["title_kr"]))}</h2>
        <p class="secbody">{esc(tip["summary_kr"])}</p>
        <ol class="steps">{steps}</ol>
      </article>

      <article class="daysec sec-misc">
        <div class="secnum">03</div>
        <span class="seclabel">이것저것</span>
        <div class="sectag">#{esc(misc.get("tag","잡학"))}</div>
        <h2 class="stitle">{esc(oneline(misc["title_kr"]))}</h2>
        <p class="secbody">{esc(misc["body_kr"])}</p>
        {_src(misc)}
      </article>'''

def render_day(d, back_href=None, asset_prefix="../"):
    a = asset_prefix
    back = (f'<div class="dnav"><a class="backlink" href="{esc(back_href)}">← 전체 보기</a></div>') if back_href else ''
    wd = d.get("weekday", "")
    label = f'{esc(d["date_label"])}' + (f' ({esc(wd)})' if wd else '')
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
  <h1 class="dhead">오늘 <em>알아두면</em> 좋은 것</h1>
  <p class="dsub">뉴스 · 꿀팁 · 이것저것</p>
  <div class="rule"></div>

  <section class="daystack">{build_sections(d)}</section>

  <div class="foot">
    <span class="fbrand">데일리</span> · 알아두면 좋은 것들 · {esc(d["date_label"])}<br>
    뉴스 본문은 LLM 웹검색 자동 수집물입니다. 게시 전 출처 확인을 권장합니다.
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
