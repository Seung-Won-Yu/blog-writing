# 데일리 다이제스트 (Daily Digest)

매일 **오늘의 뉴스 + 기초상식(정처기 문제) + IT·개발·기획 용어**를 미니멀 에디토리얼 + 3D 정적 사이트로.
뉴스는 요즘IT(yozm) · GeekNews(news.hada.io)에서 수집. **PC 없이 매일 자동**으로 갱신·배포된다.

🔗 **라이브: https://ihan0316.github.io/ai-weekly-newsroom/**

## 기능
- **오늘의 뉴스**: 클릭 시 외부 이동 대신 **3D 모달**로 크롤한 원문 표시 + **뉴럴 TTS 본문 듣기**(edge-tts) + 대표 이미지
- **기초상식**: 정보처리기사 4지선다 — 보기 클릭 시 정답/오답 즉시 표시
- **IT·개발·기획 용어** 3개/일
- **검색**: 제목·요약·출처 + **본문 전체** 대상, 가중 랭킹 + 매칭 스니펫 (`docs/search.json` 지연 로드)
- **자동 갱신**: 새 빌드 감지 시 강제 새로고침 없이 자동 반영(`build.json` + `<meta site-build>`)
- 데스크톱·모바일 반응형, WCAG AA 대비

## 구조
```
data/days/<YYYY-MM-DD>.json   # 하루치 원천 (news[]/quiz/terms)
build.py                      # render_day(): 하루 상세 HTML
build_site.py                 # 전체 빌드 → docs/ (index 피드 + 날짜별 + search.json + build.json)
assets/site.css, site.js      # 공유 디자인·인터랙션(3D 히어로/틸트/모달/TTS/검색/자동갱신)
fetch_images.py               # 기사 대표 이미지(og:image) → docs/images (증분)
gen_audio.py                  # 뉴럴 TTS MP3(ko-KR-SunHiNeural) → docs/audio (증분)
attach_content.py             # 크롤 본문(_crawled.json) → day json 주입
pipeline_gemini.py            # [무인용] 뉴스선별·본문추출·퀴즈/용어를 Gemini로 + 위 스크립트 호출
.github/workflows/daily.yml   # 매일 09:30 KST 자동 실행 → 커밋 → Pages 배포
```
주의: `assemble_days.py`는 **초기 한 달 일괄 생성용**. 재실행하면 기존 날짜의 퀴즈/용어가 재셔플되니 **운영 중 실행 금지**(하루 추가는 day json 하나만 넣고 `build_site.py`).

## 자동화 (무인 CI/CD)
```
GitHub Actions (cron 09:30 KST)
 → pipeline_gemini.py: Gemini(무료 2.5 Flash)로 뉴스 3선별·본문추출·퀴즈/용어 생성
 → fetch_images / gen_audio / build_site
 → export_tistory.py: 티스토리 편집기에 붙여넣을 HTML 생성
 → github-actions[bot] 커밋 → GitHub Pages 자동 배포
```
- 키: repo secret `GEMINI_API_KEY` (무료). 비용 $0 (Gemini 무료티어·edge-tts·Pages 전부 무료).
- 데이터센터 IP 차단(yozm 403) 우회: `r.jina.ai` 리더 프록시 폴백.
- 수동 실행: `gh workflow run "Daily digest"` 또는 Actions 탭.

## 티스토리 글 발행
티스토리 Open API의 글 작성·수정 기능은 종료되었기 때문에, 이 프로젝트는 자동 발행 대신
**티스토리 편집기용 HTML 생성**까지 자동화한다.

```powershell
python export_tistory.py --latest
```

매일 생성된 글을 실제 티스토리 편집기에 올릴 때는 아래 헬퍼를 쓴다.

```powershell
python prepare_tistory_post.py --latest
python prepare_tistory_post.py --latest --copy body
python prepare_tistory_post.py --latest --copy title --open-editor
```

추천 운영 방식:

1. GitHub Actions가 매일 글 데이터를 생성한다.
2. `prepare_tistory_post.py --latest --copy body --open-editor`로 티스토리 글쓰기 화면을 연다.
3. 출력된 제목·카테고리·태그를 입력하고, HTML 모드에서 복사된 본문을 붙여넣는다.
4. 원문 링크와 정처기 답만 확인한 뒤 발행한다.

생성 위치:
- `docs/tistory/<YYYY-MM-DD>.html`: 티스토리 HTML 모드에 붙여넣을 본문
- `docs/tistory/<YYYY-MM-DD>.json`: 제목과 태그 메타데이터

블로그 카테고리/스킨 적용 자료:
- `tistory/CATEGORY_PLAN.md`: 추천 카테고리 구조와 기존 글 이동 기준
- `tistory/skin-hero-snippet.html`: 스킨 HTML에 넣을 소개 영역
- `tistory/skin-sidebar-profile-snippet.html`: 사이드바 상단 프로필 카드
- `tistory/skin-custom.css`: 현재 티스토리 스킨에 덧붙이는 개발자 뉴스룸 스타일
- `tistory/README.md`: 관리자 화면 적용 순서

완전 자동 발행이 꼭 필요하면 브라우저 자동화로 티스토리 관리자 화면을 조작하는 방식은 가능하지만,
로그인 세션 만료와 UI 변경에 취약하므로 운영 기본값으로는 권장하지 않는다.

## 수동 빌드/배포
```powershell
python build_site.py
git add -A; git commit -m "update"; git push   # Pages 자동 재배포(1~2분)
```

## ⚠ 콘텐츠 정확도
뉴스 본문은 자동 수집·요약물이다. 공개 사이트이므로 큰 수치·민감 내용은 원문 확인 권장(모달에 출처 링크 있음).
