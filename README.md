# Blog Editorial Pipeline

[![Collect Monday Wednesday news candidates](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/collect-news.yml/badge.svg)](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/collect-news.yml)
[![Collect Friday automation candidates](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/collect-automation.yml/badge.svg)](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/collect-automation.yml)

`쑥쑥자라나라` 블로그를 위한 실전 IT 콘텐츠 제작 프로젝트입니다. 월요일은 오래 검색되는 문제 해결 가이드, 화·목요일은 일상 기술의 원리와 오해를 푸는 지식글, 수요일은 최신 변화의 영향 해설, 금요일은 직접 실행한 자동화 실험으로 나누어 만듭니다.

- 블로그: [하루 한 시간 나를 Develop!](https://won0322.tistory.com/)
- 월·수 후보 레이더: [요일별 수집 결과](https://seung-won-yu.github.io/blog-writing/inbox/)
- 실전글 후보함: [금요일 개발·자동화 레이더](https://seung-won-yu.github.io/blog-writing/automation-inbox/)
- 토요일 프로젝트 연재: [모의투자부터 시작한 주식 앱 제작기](editorial/edgelab/README.md)
- 화·목 지식글 아이디어: [궁금한 IT 원리 아이디어 뱅크](editorial/curiosity/IDEA_BANK.md)

## 주요 기능

- RSS·Atom·HTML 출처를 하나의 후보 형식으로 정규화
- 추적 파라미터를 제거한 canonical URL 기반 중복 방지
- 공식 발표·국내외 일반 기술 매체·독립 보안 출처를 함께 탐색
- 최대 30일 후보를 수집하되 최종 글의 핵심 단서는 최근 7일 자료로 제한
- `일상에 닿는 변화`, `바로 쓰는 도구`, `깊이 읽는 기술` 관점으로 후보 분류
- 최신 후보만 유지해 불필요한 원문 데이터 누적 방지
- 최소 3개의 정상 출처·후보 출처가 없으면 직전 정상 후보함을 보존하는 오류 처리
- GitHub Actions를 이용한 정기 수집과 GitHub Pages 결과 확인
- GitHub Trending·공식 릴리스·공식 가이드·요즘IT에서 금요일 개발·자동화 실험 후보를 별도 선정
- 월요일 문제 해결·수요일 변화 해설을 서로 다른 점수와 카테고리로 선정
- 화요일 작동 원리·목요일 기술 오해와 역사를 `궁금한 IT 원리`로 분리하고 365일 중복 방지

## 운영 흐름

```text
월·수 07:17 KST · GitHub Actions
  → RSS·Atom·HTML 수집
  → URL·제목 정규화
  → 최근 사용 기사와 중복 확인
  → 출처·신선도·장기 문제 해결성·검색 수요 점수 계산
  → 월요일은 지속성·재사용성, 수요일은 변화·독자 영향에 가중치
  → 기존 검색 유입 글과 충돌하는 후보 제외
  → 오늘의 추천 후보 5건과 추가 후보 저장
  → GitHub Pages 뉴스 레이더 갱신

  ※ GitHub 예약 실행 지연을 고려해 09:00 편집보다 103분 먼저 예약합니다.
     당일 후보함이 없거나 오래됐으면 편집 작업이 로컬 수집을 한 번 실행합니다.

월·수 09:00 KST · Codex 예약 작업
  → 월요일은 오래 검색되는 문제 해결 1건 선정
  → 수요일은 최근 변화가 기존 흐름에 미치는 영향 1건 선정
  → 공식 문서와 독립 자료 교차 확인
  → 8~12분 심층글 작성
  → 한국어 설명 도식·표·차트 생성·검수
  → 티스토리 복사용 결과 제작
  → 테스트·GitHub Pages 배포 확인

화·목 09:00 KST · Codex 궁금한 IT 원리 편집
  → 화요일은 일상 기술이 작동하는 원리 하나 선정
  → 목요일은 널리 퍼진 기술 오해 또는 역사적 선택 하나 선정
  → 공식 문서·표준·원 논문과 독립 자료 교차 확인
  → 12개월 뒤에도 읽을 수 있는 6~12분 지식글 작성
  → 대표 장면과 원리·오해 경계를 설명하는 본문 이미지 제작
  → 75점 미만·근거 부족·최근 365일 중복이면 발행 보류
  → 티스토리 도우미·테스트·GitHub Pages 배포 확인

금요일 07:17 KST · GitHub Actions
  → GitHub Trending·공식 릴리스·공식 가이드 수집
  → 최근 90일 개발·자동화 주제 제외
  → 검색성·문제 해결성·재현성·시각화 가능성 점수 계산
  → 추천 5건과 추가 후보를 개발·자동화 레이더에 저장

금요일 14:00 KST · Codex 실전 개발·자동화 작업
  → 실제 반복 작업·공개 도구·개발/AI 실전 주제 1건 선정
  → 안전한 임시 환경에서 최소 예제 실행
  → 실제 화면·로그와 한국어 설명 도식 제작
  → 월·수 글과 분리된 금요일 티스토리 초안 생성
  → 테스트·GitHub Pages 배포 확인

토요일 10:00 KST · Codex 주식 앱 제작기 편집
  → 개발 순서와 분리된 40편 이야기 지도에서 다음 회차 선택
  → 비공개 edgelab 저장소의 실제 코드·테스트·커밋·모의투자 증거 확인
  → 공개 공식 문서·논문으로 근거 보강
  → 앞 글의 질문을 이어받아 기획·실험·판정 흐름으로 집필
  → 원고·이미지·티스토리 도우미 HTML·검증·Pages 배포

토요일 18:00 KST · 주식 앱 제작기 수동 예약 발행
  → 티스토리 도우미에서 HTML을 복사해 사용자가 직접 예약

```

별도 수요일 개발 가이드 예약은 일시중지했습니다. 대신 월요일 09:00 글이 오래 검색되는 `개발 가이드`, 수요일 09:00 글이 최근 변화의 `IT 트렌드 해설`을 담당합니다. 화·목 지식글은 뉴스 후보함과 분리해 공개 자료를 직접 조사합니다. 티스토리에서는 `실전 IT`를 큰 묶음으로만 쓰고 실제 글은 `IT 트렌드 해설`, `궁금한 IT 원리`, `개발 가이드`, `자동화·실험`, `프로젝트·회고`에 배치합니다.

GitHub Actions의 정기 작업은 뉴스·개발·자동화 후보 수집, 중복 제거, 우선순위 계산까지만 수행하며 저장소 실행·글·이미지를 생성하지 않습니다. 후보 페이지는 주제를 고르는 편집용 레이더입니다. Codex 예약 작업도 티스토리에 자동 발행하지 않으며, 사용자는 배포된 도우미에서 최종 HTML을 복사해 직접 예약합니다.

## 콘텐츠 성장 원칙

블로그는 다섯 역할을 함께 키웁니다.

- 월요일 개발 가이드: Java·Spring·PostgreSQL·API·보안·운영처럼 반복 검색되는 문제를 원리·실패 조건·재사용 판단표까지 설명
- 화·목 궁금한 IT 원리: 비개발자도 겪는 기술의 작동 원리·오해·역사를 공식 근거와 쉬운 그림으로 설명
- 수요일 IT 트렌드 해설: 최근 변화가 기존 사용·개발 흐름에서 바꾸는 조건과 지금 확인할 행동을 설명
- 금요일 자동화·실험: 직접 실행한 반복 업무와 공개 도구의 실패·수정·결과 기록
- 토요일 프로젝트 연재: 1편은 공개 완료했고, 2편부터 `edgelab` 주식 앱의 실제 구현·실험·서버 모의투자를 매주 이어가는 제작기

새 글은 한 역할에 분명히 속해야 하며, 같은 축의 공개 글 2개 이상과 연결합니다. 검색량만 기대한 낯선 주제를 넓게 다루거나 뉴스 원문을 바꿔 말하는 글은 만들지 않습니다. 제목은 핵심 검색어와 얻는 답을 함께 담고, 태그는 기술·문제·기능·사용 상황을 구체적으로 나타냅니다. 도입은 독자가 겪는 장면·방치했을 때의 손해·글에서 얻을 결과·답할 질문을 연결합니다. 원문에 없던 비교·실행 증거·실패 조건·재사용 산출물 중 하나가 없으면 발행 준비를 통과하지 않습니다.

대표 이미지는 포괄적인 AI·노트북 장면 대신 글 고유의 실제 대상·질감·사용 흔적을 한 장면에 두고, 본문 이미지는 흐름·비교·실제 증거를 설명합니다. 이미지 alt와 파일명에도 실제 주제를 기록해 이미지 검색과 접근성을 함께 챙깁니다.

월·수 글은 100점 편집 점수에서 75점 이상이면서 반복 검색 질문·공식 근거·원문에 없던 기여·기존 글 비중복을 모두 만족해야 합니다. 화·목 지식글도 75점 이상이면서 12개월 지속 질문·공식 문서나 표준·쉬운 원리 설명·최근 365일 비중복을 모두 만족해야 합니다. 금요일 글은 직접 실행 가능한 작은 실험·재현 증거·독자가 가져갈 산출물·최근 90일 비중복을 모두 만족해야 합니다. 토요일 주식 앱 제작기는 독자 질문·실제 구현 또는 모의투자 증거·채택/수정/기각 결론·다음 회차 질문을 모두 갖춰야 합니다. 기준을 통과하지 못한 회차는 오류가 아니라 `NO_PUBLISH_QUALITY`로 보류하며, 발행 횟수를 채우려고 글을 만들지 않습니다.

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

입력 예시는 `config/search_performance.example.csv`입니다. 결과는 `config/search_opportunities.json`과 `reports/search-refresh-queue.md`에 저장됩니다. `refresh_existing`, `retitle_existing`, `merge_existing` 대상은 새 글 후보에서 제외하며, 30일이 지난 성과 파일은 수집기가 자동으로 무시합니다. 이 분류 기준은 Google 순위 공식이 아니라 검토 순서를 정하는 내부 운영 휴리스틱입니다.

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
agent/SATURDAY_AUTOMATION.md         금요일 14:00 실전 개발·자동화 계약(파일명은 기존 작업 호환용)
agent/PROJECT_SERIES.md              토요일 10:00 주식 앱 제작기 편집 계약
agent/DEVELOPMENT_GUIDE.md           일시중지된 수요일 개발 가이드의 호환·기록용 계약
blog_pipeline/collection/            수집·정규화·중복 제거·선정
blog_pipeline/publishing/            이미지 최적화·HTML·검사
config/news_sources.json             출처와 선정 규칙
config/automation_sources.json       개발·자동화 출처와 임시 점수 규칙
data/days/                            완성된 월~목 실전·지식 IT 글 데이터
data/automation_cases/                금요일 실전 개발·자동화 데이터
data/project_logs/                    토요일 주식 앱 제작기 데이터
data/project_logs/published/          이미 공개한 프로젝트 글 구조화 기록
editorial/edgelab/                    40편 연재 지도와 원고
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
