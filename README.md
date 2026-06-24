# 데일리 다이제스트 (Daily Digest)

매일 **AI·테크 뉴스 1 + 실무 꿀팁 1 + 이것저것(업무 무관 흥미) 1**을
미니멀 에디토리얼 + 3D 정적 사이트로 보여준다. 모바일 반응형.

🔗 **라이브: https://ihan0316.github.io/ai-weekly-newsroom/**

## 구조

```
ai-weekly-news/
├─ build.py          # day JSON 1건 → 하루 상세 HTML 렌더러 (render_day)
├─ build_site.py     # 전체 사이트 빌드 (index 피드 + 모든 날) → docs/
├─ assets/
│  ├─ site.css       # 공유 디자인 시스템 (index·상세 단일 소스, 반응형 포함)
│  └─ site.js        # 3D 히어로(Three.js) + 카드 틸트(터치 제외) + reduced-motion 가드
├─ data/days/        # 날짜별 데이터 (예: 2026-06-24.json)
├─ docs/             # 빌드 결과 = GitHub Pages 서빙 대상 (main /docs)
└─ README.md
```

## 하루치 데이터 스키마 (data/days/YYYY-MM-DD.json)

```jsonc
{
  "date_label": "2026. 6. 24", "weekday": "수",
  "news": { "title_kr", "bullets_kr[3-4]", "why_kr", "source", "url" },
  "tip":  { "title_kr", "summary_kr", "steps_kr[2-4]", "tag" },
  "misc": { "title_kr", "body_kr", "tag", "source?", "url?" }
}
```

## 디자인 / 반응형

- 타입: Fraunces(라틴 세리프) · Noto Serif KR(한글 헤드) · Hanken Grotesk(본문) · JetBrains Mono(라벨)
- 색: 본(bone) + 잉크 + 테라코타. 섹션 구분색(뉴스=테라코타 / 꿀팁=그린 / 이것저것=블루)
- 3D: Three.js 회전 다면체 히어로, 데스크톱 카드 포인터 틸트, 플로팅 오브
- 모바일: nav 축약, 카드 1열, 큰 번호↔제목 겹침 방지, 터치 틸트 비활성, 가로 스크롤 없음

## 빌드 & 배포

```powershell
python build_site.py          # docs/ 생성
git add -A; git commit -m "Update daily"; git push   # Pages 자동 재배포(1~2분)
```

## 콘텐츠 파이프라인 (매일)

```
[1] Claude 워크플로우: 그날 AI/테크 뉴스 웹검색 + 꿀팁 + 이것저것 → data/days/<날짜>.json
[2] python build_site.py → docs/
[3] git push → Pages 자동 재배포
```

새 날 추가 = `data/days/`에 JSON 하나 넣고 [2][3] 반복. 코드 변경 0.

## ⚠ 콘텐츠 정확도

뉴스 본문은 LLM 웹검색 자동 수집물이다. **게시 전 출처 링크로 사실 확인 권장**
(특히 인수·금액 등 큰 숫자). 자동 파이프라인에도 1차 게시 전 사람 검수 1회를 권장.
