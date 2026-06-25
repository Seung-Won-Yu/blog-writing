# -*- coding: utf-8 -*-
"""
크롤한 본문(data/_crawled.json)을 각 day JSON의 news 항목에 content로 주입.
입력: data/_crawled.json = {"results":[{"url","ok","blocks":[{t,text}]}]}
"""
import json, glob, os, html
HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    crawled = json.load(open(os.path.join(HERE, "data", "_crawled.json"), encoding="utf-8"))
    results = crawled.get("results", crawled if isinstance(crawled, list) else [])
    m = {}
    for r in results:
        if r.get("ok") and r.get("blocks"):
            blocks = [{"t": ("h" if b.get("t") == "h" else "p"), "text": html.unescape(b.get("text", ""))}
                      for b in r["blocks"] if b.get("text")]
            if blocks:
                m[r["url"].strip()] = blocks
    filled = 0; total = 0
    for f in glob.glob(os.path.join(HERE, "data", "days", "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        changed = False
        for it in d.get("news", []):
            total += 1
            u = it.get("url", "").strip()
            if u in m:
                it["content"] = m[u]; filled += 1; changed = True
            else:
                it.setdefault("content", [])
        if changed:
            json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"content attached: {filled}/{total} news items, sources_with_body={len(m)}")

if __name__ == "__main__":
    main()
