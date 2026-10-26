"""Render a measured result table, never an invented terminal screenshot."""
import json
import os
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
CODE = """const raw='2026-10-26';
const parsed=new Date(raw), midnight=new Date(2026,9,26);
console.log(JSON.stringify({node:process.version,tz:process.env.TZ,
parsedISO:parsed.toISOString(),localDay:parsed.getDate(),
midnightISO:midnight.toISOString(),slice:midnight.toISOString().slice(0,10),
roundTrip:JSON.parse(JSON.stringify({date:raw})).date}));"""


def main():
    results = []
    for zone in ("Asia/Seoul", "America/Los_Angeles"):
        output = subprocess.check_output(
            ["node", "-e", CODE], env={**os.environ, "TZ": zone}, text=True
        )
        results.append(json.loads(output))
    assert [r["localDay"] for r in results] == [26, 25]
    assert [r["slice"] for r in results] == ["2026-10-25", "2026-10-26"]
    assert all(r["roundTrip"] == "2026-10-26" for r in results)
    record = {"code": CODE, "results": results, "synthetic_input": True}
    (Path(__file__).parent / "2026-10-26-results.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    font = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    canvas = Image.new("RGB", (1200, 900), "#fffdf7")
    draw = ImageDraw.Draw(canvas)
    ink, blue, coral, muted = "#142d4a", "#1265c2", "#bf483a", "#526172"

    def text(x, y, value, size=40, color=ink, bold=False):
        face = ImageFont.truetype(font, size, index=6 if bold else 2)
        draw.text((x, y), value, font=face, fill=color)

    text(60, 45, "같은 입력, 두 시간대의 실제 결과", 52, bold=True)
    text(60, 115, f"입력 2026-10-26 · Node {results[0]['node']}", 32, muted)
    draw.line((60, 180, 1140, 180), fill="#cdd7df", width=2)
    for x, label, result in zip((60, 650), ("서울", "로스앤젤레스"), results):
        text(x, 215, label, 44, blue, True)
        text(x, 280, "getDate()의 현지 날짜", 32, muted)
        text(x, 325, str(result["localDay"]), 104, blue if result["localDay"] == 26 else coral, True)
        text(x, 465, "현지 자정 → UTC 날짜", 32, muted)
        text(x, 515, result["slice"], 46, coral if result["slice"].endswith("25") else blue, True)
    draw.line((600, 210, 600, 600), fill="#d8e0e7", width=2)
    draw.line((60, 640, 1140, 640), fill="#cdd7df", width=2)
    text(60, 680, "문자열 그대로 왕복하면 두 곳 모두", 38, ink, True)
    text(60, 735, "2026-10-26", 64, blue, True)
    text(60, 840, "실제 Node 출력 요약 · 브라우저·DB 왕복 검증은 아님", 29, muted)
    target = ROOT / "docs/tistory/assets/2026-10-26/JavaScript-두시간대-실측결과-v2.png"
    canvas.save(target)
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
