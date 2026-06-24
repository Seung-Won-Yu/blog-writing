# 주간 AI 뉴스룸 (Weekly AI Newsroom)

매주 가장 중요한 AI 뉴스 3가지 + 실전 영어 표현 + 개발자 은어를
**미니멀 에디토리얼 + 3D** 정적 사이트로 자동 생성한다.

🔗 **라이브: https://ihan0316.github.io/ai-weekly-newsroom/**

## 구조

```
ai-weekly-news/
├─ build.py          # digest 1건 → 상세(호) HTML 렌더러
├─ build_site.py     # 전체 사이트 빌드 (index + 모든 호) → docs/
├─ assets/
│  ├─ site.css       # 공유 디자인 시스템 (index·상세 단일 소스)
│  └─ site.js        # 3D 히어로(Three.js) + 카드 포인터 틸트
├─ data/issues/      # 주차별 데이터 (예: 2026-w26.json) — 워크플로우 산출물
├─ docs/             # 빌드 결과 = GitHub Pages 서빙 대상 (main /docs)
└─ README.md
```

## 디자인

- **타입**: Fraunces(라틴 세리프) · Noto Serif KR(한글 헤드) · Hanken Grotesk(본문) · JetBrains Mono(용어)
- **색**: 본(bone) + 잉크 + 테라코타 단일 악센트
- **3D**: Three.js 회전 다면체 히어로, CSS 포인터 틸트, 플로팅 오브, 썸네일 3D 구 (reduced-motion 가드)
- index ↔ 상세가 `assets/site.css` 한 파일을 공유 → 완전 일관

## 빌드 & 배포

```powershell
# 사이트 빌드 (docs/ 생성)
python build_site.py

# 변경 푸시 → GitHub Pages 자동 재배포(1~2분)
git add -A; git commit -m "Update issues"; git push
```

## 주간 파이프라인

```
[1] 뉴스 수집·큐레이션 (Claude 워크플로우)
      └ 5각 병렬 웹검색 → 상위 3개 선별 + 한글 다이제스트 → data/issues/<week>.json
[2] python build_site.py   → docs/
[3] git push               → Pages 자동 재배포
```

새 주차 추가 = `data/issues/`에 JSON 한 개 넣고 [2][3]만 반복. 코드 변경 0.

## 데이터 스키마

`news[3]`(제목/날짜/말풍선/체크리스트/별요약/출처url) · `english_expressions[10]` ·
`dev_slang[5]` · `mini_practice` · `summary_kr[3]` · `memo`.

## ⚠ 콘텐츠 정확도

뉴스 본문은 LLM 웹검색 자동 수집물이다. **게시 전 출처 링크로 사실 확인 권장**
(특히 인수·금액 등 큰 숫자). 자동 파이프라인에도 1차 게시 전 사람 검수 1회를 권장.
