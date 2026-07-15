# Blog News Radar

[![Collect daily news](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/collect-news.yml/badge.svg)](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/collect-news.yml)

`쑥쑥자라나라` 블로그를 위한 AI·IT 뉴스 탐색 프로젝트입니다. 여러 출처의 새 글을 모으고, 중복을 정리한 뒤 독자 관점에 따라 읽어볼 후보를 선별합니다.

- 블로그: [하루 한 시간 나를 Develop!](https://won0322.tistory.com/)
- 뉴스 레이더: [오늘의 수집 결과](https://seung-won-yu.github.io/blog-writing/inbox/)

## 주요 기능

- RSS·Atom·HTML 출처를 하나의 후보 형식으로 정규화
- 추적 파라미터를 제거한 canonical URL 기반 중복 방지
- 공식 발표·개발 커뮤니티·국내 기술 매체를 함께 탐색
- `일상에 닿는 변화`, `바로 쓰는 도구`, `깊이 읽는 기술` 관점으로 후보 분류
- 최신 후보만 유지해 불필요한 원문 데이터 누적 방지
- 한 출처의 장애가 전체 수집을 막지 않는 독립 오류 처리
- GitHub Actions를 이용한 정기 수집과 GitHub Pages 결과 확인

## 수집 흐름

```text
GitHub Actions
  → RSS·Atom·HTML 수집
  → URL·제목 정규화
  → 최근 사용 기사와 중복 확인
  → 출처·신선도·독자 관점 점수 계산
  → 오늘의 추천 후보 3건과 추가 후보 저장
  → GitHub Pages 뉴스 레이더 갱신
```

수집기는 글을 자동 발행하지 않습니다. 후보 페이지는 원문 확인을 돕는 편집용 레이더이며, 각 기사에 대한 사실 확인과 해석은 별도 과정으로 남겨둡니다.

## 직접 실행

Python 3.12를 권장합니다.

```bash
python3 -m blog_pipeline.collection.collect_news --today
```

결과는 다음 두 파일에 최신본으로 저장됩니다.

```text
docs/inbox/latest.json
docs/inbox/index.html
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
- 제품·플랫폼 공식 변경 기록
- 기술 연구 피드

원문 제목과 링크는 외부 입력으로 취급합니다. 후보 페이지를 만들 때 HTML 이스케이프를 적용하고, 페이지에는 검색 제외 메타데이터를 사용합니다.

## 프로젝트 구조

```text
.github/workflows/collect-news.yml   정기 뉴스 수집
blog_pipeline/collection/            수집·정규화·중복 제거·선정
config/news_sources.json             출처와 선정 규칙
docs/inbox/                           최신 뉴스 후보 JSON·페이지
tests/                                수집 파이프라인 회귀 테스트
```

## 데이터 원칙

- 원뉴스 후보는 `latest` 두 파일만 유지합니다.
- 실제 활용한 기사의 URL은 최근 기록과 비교해 반복 선정을 줄입니다.
- 수집 과정에는 생성형 AI API 키가 필요하지 않습니다.
- 로그인 정보와 외부 서비스 API 키를 저장소에 저장하지 않습니다.

## 이용 안내

이 저장소는 프로젝트 구조와 뉴스 탐색 결과를 공개하기 위한 개인 프로젝트입니다. 별도의 오픈소스 라이선스를 부여하지 않으며, 코드와 콘텐츠의 재사용·재배포에는 작성자의 허락이 필요합니다.
