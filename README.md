# Blog Editorial Pipeline

## 현재 운영: 새 글 3편 + 기존 글 개선 2회

2026-10-12부터 월·수·금은 새 글, 화·목은 기존 공개 글 개선을 09:00 KST에 시작합니다.
AI와 디지털 도구를 쉽게 활용하고 막히는 문제를 해결하는 글에 집중합니다.
검색 반응·독자 질문·실제 사용 근거로 주제를 고르며 8.5 자동 점수를 성장이나
AdSense 승인으로 해석하지 않습니다. 첫 개선 큐는 im-not-ai(`/197`), 시크릿 모드(`/221`),
WMIC(`/209`)이며 기존 URL과 원고 날짜를 유지합니다. 티스토리 발행·본문 교체는 사용자가 합니다.

[6주 운영 계약](agent/CONTENT_GROWTH_TRIAL.md)과 [계획·성과 기준·개선 큐](config/content_growth_trial.json)를
기준으로 2026-11-23에 성과를 점검합니다. 자동으로 이전 편성에 되돌아가지는 않습니다.

```bash
sh scripts/blog-env python3 -m blog_pipeline.publishing.growth_plan --today
```

이 명령은 당일 `new_article`, `refresh_existing`, `off`와 개선 대상을 읽기 전용으로 확인합니다.
원리·원리툰과 과거 프로젝트 계약은 기존 글 검증 및 별도 요청용으로 보존합니다.

## 로컬 제작·검수 실행 환경

Git·Python 명령은 저장소 루트에서 `sh scripts/blog-env ...`로 실행합니다.
래퍼는 저장소 전용 `.venv`와 macOS Homebrew 도구를 우선하며 시스템 Xcode 설정은 바꾸지 않습니다.
새 환경은 `python3 -m venv .venv`와 `.venv/bin/python3 -m pip install -r requirements-images.txt`로
이미지 의존성을 준비하고, 제작 전에 `sh scripts/blog-env python3 -c 'import PIL'`로 확인합니다.

허용된 로컬 검수 환경에서는 다음 명령으로 지정한 글의 HTML·이미지·CSS만 제공합니다.

```bash
sh scripts/blog-env python3 -m blog_pipeline.publishing.preview_server --draft-id 2026-09-17
```

서버가 출력한 `Preview ready:` 주소를 인앱 브라우저에서 확인한 뒤 서버를 종료합니다.
빈 로컬 포트를 자동으로 선택하므로 다른 프로젝트 서버의 포트를 비울 필요가 없습니다.
저장소 전체나 비공개 원고는 제공하지 않으며, 이전 보안 거절을 해제하는 명령이 아닙니다.
자세한 승인·검수·초안 보존 구분은 [화면 검수 계약](agent/BROWSER_QA.md)을 따릅니다.

예약은 한국시간 09:00에 월·수, 화·목, 금요일의 독립 작업으로 시작합니다.
토요일 주식 앱 제작기 예약은 2026-10-12에 종료했으며, 기존 글과 자료만 보존합니다.
삭제된 채팅이 아니라 저장소 계약과 날짜별 산출물을 읽습니다. QA가 막히면 공개자료 기반
텍스트만 `.local-drafts/`에 보존하고, 화면 검수를 통과한 완성본만 GitHub Pages 발행 도우미에 배포합니다.
티스토리 최종 발행은 사용자 담당입니다. 앱의 `missing source rollout` 오류는 작업 시작 이전의
대화 이력 문제이므로 이 저장소의 검증 통과와 별도로 앱 진단이 필요합니다.

[![Collect Monday Wednesday news candidates](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/collect-news.yml/badge.svg)](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/collect-news.yml)
[![Collect Friday developer insight candidates](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/collect-automation.yml/badge.svg)](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/collect-automation.yml)

`쑥쑥자라나라` 블로그를 위한 실전 IT 콘텐츠 제작 프로젝트입니다. 월요일은 오래 검색되는 문제 해결, 수요일은 실제 변화에 따른 확인·대응, 금요일은 AI·개발 도구의 구체적인 활용·선택을 다룹니다. 화·목은 기존 글의 독자 질문·실행 안내·실제 근거를 보완합니다.

모든 글은 같은 모바일 레이아웃·이미지 규격·광고 위치·출처 표기·발행 도우미를 공유하지만, 독자와 전개를 하나의 만능 템플릿으로 통일하지 않습니다. [요일별 독자 약속](agent/WEEKLY_READER_PROMISES.md)에 따라 월요일은 문제 해결, 수요일은 변화 대응, 금요일은 도구 활용·판단을 제공합니다. 화·목 개선본은 실행 요일과 관계없이 원래 글의 독자 경로를 유지합니다. 원리·오해 검증·토요일 프로젝트 규칙은 기존 발행본 검증 및 별도 요청용으로 남깁니다.

[월~금 파이프라인 운영 계약](agent/WEEKLY_PIPELINE.md)은 월·수·금 06:30 후보 수집, 월~금 09:00 글 제작 시작, 10시 전후 사용자 수동 발행이라는 경계를 고정합니다. 월요일과 수요일은 같은 후보 원천을 보더라도 점수 가중치와 최소 통과선을 다르게 적용하고, 화·목·금은 각 역할에 맞는 별도 입력과 선정표를 사용합니다. 화·목의 직접 선정 점수와 하드 게이트는 원고의 `editorial.selection_evaluation`에 남아 품질 가드가 합계까지 다시 확인합니다. 과거 토요일 묶음의 비공개 정보 검사는 이력 검증용으로 유지합니다.

[요일별 이미지 약속](agent/WEEKLY_VISUAL_PROMISES.md)은 크기·진위·대체 텍스트 같은 공통 품질은 유지하면서 이미지가 하는 일을 분리합니다. 월요일은 진단과 복구, 화요일은 고정 남성 캐릭터 `하루`가 이끄는 4컷 IT 원리툰, 수요일은 변경 전후와 행동, 목요일은 오해와 근거, 금요일은 공식 근거와 도구 선택을 시각화합니다. 기사 고유 주제어와 이미지가 가르칠 한 문장을 브리프·캡션·대체 텍스트·제작 프롬프트까지 연결해 역할 태그만 붙인 엉뚱한 이미지는 차단합니다. 하루의 외형만 브랜드 자산으로 잠그고 다른 요일의 색상·그림체와 각 장면의 구도는 최근 글과 겹치지 않게 순환합니다.

- 블로그: [하루 한 시간 나를 Develop!](https://won0322.tistory.com/)
- 월·수 후보 레이더: [요일별 수집 결과](https://seung-won-yu.github.io/blog-writing/inbox/)
- 개발·AI 후보함: [금요일 개발자 인사이트 레이더](https://seung-won-yu.github.io/blog-writing/automation-inbox/)
- 종료된 토요일 프로젝트 연재 기록: [모의투자부터 시작한 주식 앱 제작기](editorial/edgelab/README.md)
- 화·목 지식글 아이디어: [궁금한 IT 원리 아이디어 뱅크](editorial/curiosity/IDEA_BANK.md)

## 주요 기능

- RSS·Atom·HTML 출처를 하나의 후보 형식으로 정규화
- 추적 파라미터를 제거한 canonical URL 기반 중복 방지
- 공식 발표·국내외 일반 기술 매체·독립 보안 출처를 함께 탐색
- 최대 30일 후보를 수집하되 최종 글의 핵심 단서는 최근 7일 자료로 제한
- `일상에 닿는 변화`, `바로 쓰는 도구`, `깊이 읽는 기술` 관점으로 후보 분류
- 최신 후보만 유지해 불필요한 원문 데이터 누적 방지
- 최소 3개의 정상 출처·후보 출처가 없으면 직전 정상 후보함을 보존하는 오류 처리
- 후보함과 별도 `status.json`으로 대상 날짜·요일 역할·신선도·실패 사유를 09시 편집기에 전달
- GitHub Actions를 이용한 정기 수집과 GitHub Pages 결과 확인
- GitHub Trending·공식 문서·공개 저장소·연구·요즘IT에서 금요일 개발·AI 인사이트 후보를 별도 선정
- 월요일 문제 해결·수요일 변화 해설을 서로 다른 점수와 카테고리로 선정
- 수요일은 최근 7일 자료라도 실제 업데이트·출시·장애·유출 변화 신호가 없으면 제외
- 화요일 작동 원리·목요일 기술 오해와 역사를 `궁금한 IT 원리`로 분리하고 365일 중복 방지
- 2026-09-02 이후 모든 새 정규 글에 요일별 `editorial.reader_path`를 강제하고 독자 이해도·공개 가독성 8.5 미만 발행 차단
- Pages 배포 뒤 공개 발행 도우미와 CI 산출물의 SHA-256 일치 여부 제한 재확인

## 운영 흐름

```text
월·수 06:30 KST · GitHub Actions
  → RSS·Atom·HTML 수집
  → URL·제목 정규화
  → 최근 사용 기사와 중복 확인
  → 출처·신선도·장기 문제 해결성·검색 수요 점수 계산
  → 월요일은 지속성·재사용성, 수요일은 변화·독자 영향에 가중치
  → 기존 검색 유입 글과 충돌하는 후보 제외
  → 오늘의 추천 후보 5건과 추가 후보 저장
  → 저장소 후보함과 상태 기록 갱신(Pages는 완성 원고 변경 때만 배포)

  ※ GitHub 예약 실행 지연을 고려해 09:00 편집보다 150분 먼저 예약합니다.
     당일 후보함이 없거나 오래됐으면 편집 작업이 로컬 수집을 한 번 실행합니다.
     `inbox_guard`는 마지막 정상 후보함과 이번 실패 상태를 구분해 오래된 후보 사용을 막습니다.

월·수 09:00 KST · Codex 예약 작업
  → 월요일은 오래 검색되는 문제 해결 1건 선정
  → 수요일은 최근 변화가 기존 흐름에 미치는 영향 1건 선정
  → 공식 문서와 독립 자료 교차 확인
  → 8~12분 심층글 작성
  → 한국어 설명 도식·표·차트 생성·검수
  → 티스토리 복사용 결과 제작
  → 테스트·GitHub Pages 배포 확인

화·목 09:00 KST · Codex 기존 글 개선
  → 성장 계획의 미완료 기존 URL·원고 ID 선택
  → 실제 검색 반응과 공개 본문의 공백 확인
  → 원래 답·실행 증거를 보존하며 이해도·실행 안내·링크 보완
  → 유효한 이미지 재사용, 낡은 화면이나 설명 공백만 교체
  → 기존 ID로 원고·번들·실화면 QA 검증
  → 교체용 표시와 대상 URL을 포함해 Pages 도우미에 인계
  → 당일 신규 원고 생성·티스토리 자동 저장 없음

금요일 06:30 KST · GitHub Actions
  → GitHub Trending·공식 문서·공개 저장소·연구 후보 수집
  → 최근 180일 금요일 주제 제외
  → 검색 지속성·개발자 관련성·출처 신뢰도·새 분석·궁금증 점수 계산
  → 추천 5건과 추가 후보를 개발·AI 인사이트 레이더에 저장

금요일 09:00 KST · Codex 개발·AI 인사이트 편집
  → GitHub·공식 문서·Agent Skills·AI 개발 도구 질문 1건 선정
  → 공식·원출처 포함 3개 이상 교차 확인
  → 생태계 지도·공식 문서 해설·근거 기반 비교·커리어 분석 중 하나로 구성
  → 도구 비교·실습 글만 같은 조건에서 직접 실행
  → 주석 캡처·실측 차트와 한국어 설명 시각물 제작
  → 월·수 글과 분리된 금요일 티스토리 초안 생성
  → 테스트·GitHub Pages 배포 확인

월~금 · 사용자 최종 검수 후 직접 발행
  → Codex가 09:00부터 조사·집필·이미지·검증·도우미 제작을 수행
  → 티스토리 도우미에서 사용자가 제목·본문·이미지를 다시 확인
  → 품질 완료 시 10시 전후 사용자가 직접 붙여넣고 발행 또는 예약
  → 10시는 자동 발행 시각이나 품질을 낮추는 마감이 아님

```

월·수·금 신규 역할과 기존 카테고리는 유지합니다. 화·목 개선본은 원래 글의 역할·카테고리·날짜를 지킵니다. 이번 전환으로 티스토리 카테고리를 일괄 변경하거나 기존 글을 삭제하지 않습니다.

GitHub Actions의 정기 작업은 뉴스·개발·자동화 후보 수집, 중복 제거, 우선순위 계산까지만 수행하며 저장소 실행·글·이미지를 생성하지 않습니다. 후보 페이지는 주제를 고르는 편집용 레이더입니다. Codex 예약 작업도 티스토리에 자동 발행하지 않으며, 사용자는 배포된 도우미에서 최종 HTML을 복사해 직접 발행합니다. 미래 정규 초안의 `publication_mode: manual_review`와 09:00 `scheduled_at`은 Codex 제작 시작 기준이며 티스토리 예약 시각이 아닙니다.

검증된 결과의 GitHub 전송은 `blog_pipeline.publishing.repository_sync`가 담당합니다. 활성 09:00 Codex 예약은 로컬 가드와 단일 커밋이 끝난 뒤 `origin/main` 한 곳만 이 명령으로 전송하도록 외부 쓰기 범위를 명시하며, 원시 push·강제 push·rebase·reset은 허용하지 않습니다. 전송 subprocess는 예약 환경의 `GH_TOKEN`·`GITHUB_TOKEN` 덮어쓰기를 제거해 저장된 Git credential helper를 사용하고, DNS가 막힌 샌드박스의 `gh auth status`만으로 토큰 만료를 단정하지 않습니다. 과거 토요일 묶음의 비공개 증거 유출 검사도 이력 검증용으로 유지합니다. DNS·연결 실패·timeout·HTTP 5xx만 최대 5회 재시도하며 백오프 대기 합계는 45초입니다. 정리된 환경의 실제 push가 반환한 인증·권한·non-fast-forward 오류만 즉시 중단합니다. 최종 실패 시 로컬 커밋을 보존하므로 다음 예약 실행에서 이어서 전송할 수 있습니다.

월·수·금 첫 후보가 탈락하면 해당 수집기를 한 번 다시 돌리고 공식 문서·원출처·독립 자료에서 질문을 더 찾습니다. 화·목은 기존 글의 공백을 추가 조사하며 개선 큐가 비어도 새 글로 빈도를 채우지 않습니다. 근거와 실제 검수가 부족하면 미완료 범위를 기록합니다.

## 콘텐츠 성장 원칙

현재는 신규 제작과 기존 글 개선을 다음처럼 연결합니다.

- 월요일 문제 해결: 특정 독자가 반복해서 겪는 사용·설정·개발 문제를 해결 순서와 확인 결과까지 설명
- 화·목 기존 글 개선: 검색 반응이 있는 답을 보존하면서 부족한 이해·실행·확인 안내를 보강
- 수요일 IT 트렌드 해설: 최근 변화가 기존 사용·개발 흐름에서 바꾸는 조건과 지금 확인할 행동을 설명
- 금요일 AI·개발 도구: 구체적인 작업에서 도구·스킬·문서를 어떻게 활용하고 선택할지 실제 근거로 설명

토요일 주식 앱 제작기는 정규 편성에서 종료했습니다. 공개된 글과 원고·이미지는 보존하지만 새 회차를 예약 생성하지 않습니다.

새 글은 한 역할에 분명히 속해야 하며, 같은 축의 공개 글 2개 이상과 연결합니다. 검색량만 기대한 낯선 주제를 넓게 다루거나 뉴스 원문을 바꿔 말하는 글은 만들지 않습니다. 제목은 핵심 검색어와 얻는 답을 함께 담고, 태그는 기술·문제·기능·사용 상황을 구체적으로 나타냅니다. 도입은 독자가 겪는 장면·방치했을 때의 손해·글에서 얻을 결과·답할 질문을 연결합니다. 원문에 없던 비교·실행 증거·실패 조건·재사용 산출물 중 하나가 없으면 발행 준비를 통과하지 않습니다.

대표 이미지는 포괄적인 AI·노트북 장면 대신 글 고유의 실제 대상·질감·사용 흔적을 한 장면에 두고, 본문 이미지는 흐름·비교·실제 증거를 설명합니다. 이미지 alt와 파일명에도 실제 주제를 기록해 이미지 검색과 접근성을 함께 챙깁니다.

월·수 글은 100점 편집 점수에서 75점 이상이면서 반복 검색 질문·공식 근거·원문에 없던 기여·기존 글 비중복을 모두 만족해야 합니다. 화·목 지식글도 75점 이상이면서 12개월 지속 질문·공식 문서나 표준·쉬운 원리 설명·최근 365일 비중복을 모두 만족해야 합니다. 금요일 글은 개발자 관련성·공식 또는 원출처 3개 이상·새 지도나 비교 기준·최근 180일 비중복을 모두 만족해야 하며 실행이 필요한 주장만 직접 검증합니다. 기준을 통과하지 못한 날은 `NO_PUBLISH_QUALITY`로 보류하며, 발행 횟수를 채우려고 글을 만들지 않습니다.

운영 판단은 하루 수익이나 새 글 직후의 순간 유입이 아니라 최근 28일과 이전 28일을 같은 길이로 비교합니다.

- Search Console: 노출, 클릭, 검색어, 색인된 주요 글
- Tistory: 검색 유입 비중, 인기 글, 신규 글에서 이전 글로 이어지는 흐름
- AdFit: 요청, 유효 노출, 클릭률, eCPM, 예상 적립금

검색 노출은 늘지만 클릭이 없으면 제목을 점검하고, 클릭은 있지만 글 이동이 없으면 도입과 내부 링크를 점검합니다. 이전 28일보다 노출·클릭이 30% 이상 줄면 새 글로 덮지 않고 기존 글의 검색 의도·사실·예제·내부 링크를 먼저 보강합니다. 광고 eCPM만 떨어졌다면 광고를 추가하지 않고 최소 2주 추세를 봅니다.

Search Console에서 같은 길이의 두 기간을 `검색어 × 페이지` 단위로 준비한 뒤 예시 CSV의 열 이름에 맞추면 기존 글 성장 큐를 만들 수 있습니다.

```bash
python3 -m blog_pipeline.collection.analyze_search_performance \
  --input /path/to/search-performance.csv
```

입력 예시는 `config/search_performance.example.csv`입니다. 결과는 `config/search_opportunities.json`과 `reports/search-refresh-queue.md`에 저장됩니다. `protect_existing`, `refresh_existing`, `retitle_existing`, `merge_existing` 대상과 충돌하는 새 글은 제외하며 30일 지난 성과는 최신 점수에 쓰지 않습니다. 현재 보호 큐의 수치는 페이지 합계이고 `query`는 편집용 주제 힌트입니다. 정확한 검색어×페이지 CSV와 합쳐 가짜 관측값을 만들지 않습니다. CSV 재분석이 보호 큐를 대체하므로 재분석 뒤 현재 계획의 기존 글 보호 대상도 대조합니다. 이 분류는 Google 순위 공식이 아닌 내부 휴리스틱입니다.

2026-10-28부터 예약 편집은 [실제 검색어 선정 계약](agent/SEARCH_DEMAND.md)을
우선합니다. `sh scripts/blog-env python3 -m blog_pipeline.collection.search_demand --today`로
관측한 검색어·클릭·노출을 먼저 읽고 기존 글과 다른 질문인지 대조한 뒤 수집기에서
근거를 찾습니다. `data/search_demand/`의 날짜별 관측은 검색어 합계이며 위의 페이지
보호 큐와 수치를 합치지 않습니다. 2026-10-29 이후 신규 원고는 보존된 실제 검색어와
`editorial.search_demand`가 일치해야 가드를 통과합니다. 별도 질문이 없으면 기존 글을
개선하고 새 글 수를 채우기 위한 가설 기사는 만들지 않습니다.

## 직접 실행

Python 3.12를 권장합니다.

```bash
python3 -m blog_pipeline.collection.collect_news --today
python3 -m blog_pipeline.collection.collect_automation --today
```

결과는 다음 두 파일에 최신본으로 저장됩니다.

```text
docs/inbox/latest.json
docs/inbox/index.html
docs/automation-inbox/latest.json
docs/automation-inbox/index.html
```

수집 관련 테스트만 실행하려면 다음 명령을 사용합니다.

```bash
python3 -m unittest \
  tests.test_collect_news \
  tests.test_news_pipeline \
  tests.test_review_inbox
```

## 출처와 선정 기준

출처와 키워드, 독자 관점별 규칙은 [`config/news_sources.json`](config/news_sources.json)에서 관리합니다. 현재 다음 범주의 출처를 함께 확인합니다.

- AI·IT 전문 매체
- 개발자 커뮤니티
- OpenAI·GitHub·Cloudflare·Google·Mozilla·Microsoft 공식 피드
- Google Workspace·GitHub Engineering·Hugging Face 기술 블로그
- ITWorld Korea·The Verge 일반 기술 매체와 Krebs on Security 독립 보안 출처
- 기술 연구 피드

원문 제목과 링크는 외부 입력으로 취급합니다. 후보 페이지를 만들 때 HTML 이스케이프를 적용하고, 페이지에는 검색 제외 메타데이터를 사용합니다.

## 프로젝트 구조

```text
.github/workflows/collect-news.yml   월·수 실전 IT 후보 수집
.github/workflows/collect-automation.yml 금요일 개발·자동화 후보 수집
agent/DAILY_EDITOR.md                월·수 09:00 실전 IT 아티클 편집·발행 준비 계약
agent/CURIOSITY_EDITOR.md            화·목 09:00 궁금한 IT 원리 편집·발행 준비 계약
agent/SATURDAY_AUTOMATION.md         금요일 09:00 실전 개발·자동화 계약(파일명은 기존 작업 호환용)
agent/PROJECT_SERIES.md              종료된 토요일 주식 앱 제작기 편집 계약 기록
agent/WEEKLY_PIPELINE.md             06:30 수집·09:00 제작·요일별 선정·수동 발행 경계
agent/WEEKLY_READER_PROMISES.md      공통 디자인과 월~금 독자·전개 계약(토요일은 기록)
agent/WEEKLY_VISUAL_PROMISES.md      공통 이미지 품질과 월~금 시각 역할 계약(토요일은 기록)
agent/READER_QUALITY_LOOP.md         활성 월~금 글의 8.5 미달 자동 재편집 계약
agent/DEVELOPMENT_GUIDE.md           일시중지된 수요일 개발 가이드의 호환·기록용 계약
editorial/curiosity/characters/      화요일 원리툰의 하루 v1 기준 시트·캐릭터 바이블
blog_pipeline/collection/            수집·정규화·중복 제거·선정
blog_pipeline/collection/inbox_guard.py 수집 날짜·역할·신선도 인계 검사
blog_pipeline/publishing/            이미지 최적화·HTML·검사
blog_pipeline/publishing/skin_contract.py 프로젝트 글·이미지·공통 스킨 계약 검사
blog_pipeline/publishing/pages_smoke.py 공개 Pages와 CI 발행 도우미 일치 검사
config/news_sources.json             출처와 선정 규칙
config/automation_sources.json       개발·자동화 출처와 임시 점수 규칙
data/days/                            완성된 월~목 실전·지식 IT 글 데이터
data/automation_cases/                금요일 실전 개발·자동화 데이터
data/project_logs/                    종료된 토요일 주식 앱 제작기 데이터
data/project_logs/published/          이미 공개한 프로젝트 글 구조화 기록
editorial/edgelab/                    종료된 연재 계획과 기존 원고
editorial/curiosity/                  화·목 장기 지식글 아이디어 뱅크
data/guides/                          기존 개발 가이드 발행 기록
docs/inbox/                           최신 월·수 실전 IT 후보 JSON·페이지
docs/automation-inbox/                최신 개발·자동화 후보 JSON·페이지
docs/tistory/                         티스토리 복사용 결과와 이미지
tests/                                수집 파이프라인 회귀 테스트
```

## 데이터 원칙

- 수집 후보는 `latest` JSON·페이지 두 파일만 유지합니다.
- 실제 활용한 기사의 URL은 최근 기록과 비교해 반복 선정을 줄입니다.
- 수집 과정에는 생성형 AI API 키가 필요하지 않습니다.
- 로그인 정보와 외부 서비스 API 키를 저장소에 저장하지 않습니다.

## 이용 안내

이 저장소는 프로젝트 구조와 뉴스 탐색 결과를 공개하기 위한 개인 프로젝트입니다. 별도의 오픈소스 라이선스를 부여하지 않으며, 코드와 콘텐츠의 재사용·재배포에는 작성자의 허락이 필요합니다.
