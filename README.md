# Blog News Radar

[![Collect daily news](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/collect-news.yml/badge.svg)](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/collect-news.yml)
[![Collect Saturday automation candidates](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/collect-automation.yml/badge.svg)](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/collect-automation.yml)

`쑥쑥자라나라` 블로그를 위한 AI·IT 심층뉴스 제작 프로젝트입니다. 여러 출처의 새 글을 모아 후보를 정리하고, 매일 핵심뉴스 한 건을 추가 조사해 설명 이미지와 함께 읽을 만한 글로 만듭니다.

- 블로그: [하루 한 시간 나를 Develop!](https://won0322.tistory.com/)
- 뉴스 레이더: [오늘의 수집 결과](https://seung-won-yu.github.io/blog-writing/inbox/)
- 실전글 후보함: [토요일 개발·자동화 레이더](https://seung-won-yu.github.io/blog-writing/automation-inbox/)

## 주요 기능

- RSS·Atom·HTML 출처를 하나의 후보 형식으로 정규화
- 추적 파라미터를 제거한 canonical URL 기반 중복 방지
- 공식 발표·국내외 일반 기술 매체·독립 보안 출처를 함께 탐색
- 14일보다 오래된 기사 제외와 같은 운영사 피드의 중복 선정 제한
- `일상에 닿는 변화`, `바로 쓰는 도구`, `깊이 읽는 기술` 관점으로 후보 분류
- 최신 후보만 유지해 불필요한 원문 데이터 누적 방지
- 최소 3개의 정상 출처·후보 출처가 없으면 직전 정상 후보함을 보존하는 오류 처리
- GitHub Actions를 이용한 정기 수집과 GitHub Pages 결과 확인
- GitHub Trending·공식 릴리스·공식 가이드·요즘IT에서 토요일 개발·자동화 실험 후보를 별도 선정
- 요청형 상시 검색 글을 `개발 가이드`로 분리해 뉴스와 같은 복사·광고·미리보기 흐름으로 제공

## 운영 흐름

```text
07:17 KST · GitHub Actions
  → RSS·Atom·HTML 수집
  → URL·제목 정규화
  → 최근 사용 기사와 중복 확인
  → 출처·신선도·독자 관점 점수 계산
  → 오늘의 추천 후보 5건과 추가 후보 저장
  → GitHub Pages 뉴스 레이더 갱신

09:00 KST · Codex 예약 작업
  → 핵심뉴스 1건 선정·추가 검색
  → 공식 문서와 독립 자료 교차 확인
  → 8~12분 심층글 작성
  → 한국어 설명 도식·표·차트 생성·검수
  → 티스토리 복사용 결과 제작
  → 테스트·GitHub Pages 배포 확인

토요일 11:17 KST · GitHub Actions
  → GitHub Trending·공식 릴리스·공식 가이드 수집
  → 최근 90일 개발·자동화 주제 제외
  → 검색성·문제 해결성·재현성·시각화 가능성 점수 계산
  → 추천 5건과 추가 후보를 개발·자동화 레이더에 저장

토요일 14:00 KST · Codex 실전 개발·자동화 작업
  → 실제 반복 작업·공개 도구·개발/AI 실전 주제 1건 선정
  → 안전한 임시 환경에서 최소 예제 실행
  → 실제 화면·로그와 한국어 설명 도식 제작
  → 뉴스글과 분리된 두 번째 티스토리 초안 생성
  → 테스트·GitHub Pages 배포 확인

요청 시 · 상시 검색형 개발 가이드
  → 기존 글은 주제 출발점으로만 사용
  → 최신 공식 문서와 독립 자료 교차 확인
  → 10~20분 원고와 한국어 설명 이미지 3장 이상 제작
  → `나만의 정리` 카테고리용 최종 HTML·미리보기 제공
```

GitHub Actions의 정기 작업은 뉴스·개발·자동화 후보 수집, 중복 제거, 우선순위 계산까지만 수행하며 저장소 실행·글·이미지를 생성하지 않습니다. 후보 페이지는 주제를 고르는 편집용 레이더입니다. Codex 예약 작업도 티스토리에 자동 발행하지 않으며, 사용자는 배포된 도우미에서 최종 HTML을 복사해 직접 예약합니다.

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
.github/workflows/collect-news.yml   정기 뉴스 수집
.github/workflows/collect-automation.yml 토요일 개발·자동화 후보 수집
agent/DAILY_EDITOR.md                매일 09:00 뉴스 편집 계약
agent/SATURDAY_AUTOMATION.md         토요일 14:00 실전 개발·자동화 계약
blog_pipeline/collection/            수집·정규화·중복 제거·선정
blog_pipeline/publishing/            이미지 최적화·HTML·검사
config/news_sources.json             출처와 선정 규칙
config/automation_sources.json       개발·자동화 출처와 임시 점수 규칙
data/days/                            완성된 일일 글 데이터
data/automation_cases/                토요일 실전 개발·자동화 데이터
data/guides/                          요청형 상시 검색 개발 가이드
docs/inbox/                           최신 뉴스 후보 JSON·페이지
docs/automation-inbox/                최신 개발·자동화 후보 JSON·페이지
docs/tistory/                         티스토리 복사용 결과와 이미지
tests/                                수집 파이프라인 회귀 테스트
```

## 데이터 원칙

- 원뉴스 후보는 `latest` 두 파일만 유지합니다.
- 실제 활용한 기사의 URL은 최근 기록과 비교해 반복 선정을 줄입니다.
- 수집 과정에는 생성형 AI API 키가 필요하지 않습니다.
- 로그인 정보와 외부 서비스 API 키를 저장소에 저장하지 않습니다.

## 이용 안내

이 저장소는 프로젝트 구조와 뉴스 탐색 결과를 공개하기 위한 개인 프로젝트입니다. 별도의 오픈소스 라이선스를 부여하지 않으며, 코드와 콘텐츠의 재사용·재배포에는 작성자의 허락이 필요합니다.
