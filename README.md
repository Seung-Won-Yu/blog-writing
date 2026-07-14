# Tistory Editorial Pipeline

[![Daily news draft](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/tistory-draft.yml/badge.svg)](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/tistory-draft.yml)

AI·IT 뉴스를 수집하고, 읽을 만한 티스토리 초안과 대표·본문 이미지를 만드는 개인 블로그 자동화입니다.

자동 발행 도구가 아닙니다. 원문과 초안을 확인하고 내 의견을 더한 뒤 티스토리에 직접 발행하는 편집 보조 도구입니다.

- 블로그: [하루 한 시간 나를 Develop!](https://won0322.tistory.com/)
- 초안 복사·미리보기: [GitHub Pages](https://seung-won-yu.github.io/blog-writing/)
- 뉴스 후보함: [오늘의 수집 결과](https://seung-won-yu.github.io/blog-writing/inbox/)
- 자동화: [Daily news draft](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/tistory-draft.yml)

## 목차

- [무엇을 자동화하나](#무엇을-자동화하나)
- [운영 방식](#운영-방식)
- [처음 설정](#처음-설정)
- [수동 생성](#수동-생성)
- [티스토리 발행](#티스토리-발행)
- [품질·보안 장치](#품질보안-장치)
- [로컬 실행](#로컬-실행)
- [프로젝트 구조](#프로젝트-구조)
- [문제 해결](#문제-해결)

## 무엇을 자동화하나

```text
뉴스 수집
  → URL·유사 제목 중복 제거
  → 일반 관심 / 실용 / 심화 기사 3건 선정
  → 선정 원문에서 제한된 근거만 임시 추출
  → Gemini 우선, GitHub Models 보조로 장문 초안 생성
  → 정처기 문제·개발 용어 추가
  → 대표 이미지 1장·본문 이미지 최대 3장 생성
  → 품질 검사
  → 복사·미리보기 페이지 배포
  → 사람이 검토 후 티스토리에 발행
```

생성 글은 다음 구조를 지향합니다.

- 일반 독자도 이해할 수 있는 첫 기사
- 바로 써보거나 판단에 활용할 수 있는 개발 소식
- 구조와 원리를 파고드는 기술 소식
- 기사별 사실, 독자에게 미치는 변화, 확인할 점
- 별도 견해 상자 없이 본문에 자연스럽게 녹인 개발자 해설
- 번호가 항상 보이는 정보처리기사 문제와 정답
- 오늘 해볼 수 있는 작은 행동

## 운영 방식

| 실행 방식 | 동작 |
| --- | --- |
| 예약 실행 | 매일 `17:10 KST`에 뉴스 수집부터 초안·이미지·Pages 배포까지 실행 |
| 수동 실행 | 원하는 날짜 생성, 강제 재생성, 과거 글 보강, 유료 Gemini 이미지 선택 가능 |
| 코드 push | 전체 테스트와 Pages 배포만 실행. 당일 초안을 다시 만들거나 덮어쓰지 않음 |

예약 시간을 Gemini 무료 일일 한도 초기화 이후로 두었습니다. 자동화 결과는 저장소의 `docs/`와 `data/`에 커밋됩니다.

최근 7일 동안 이미 선정한 기사 URL은 다시 추천하지 않습니다. 같은 이슈의 반복 발행을 줄이고 매일 다른 읽을거리를 고르기 위한 장치입니다.

### 뉴스 출처

| 출처 | 역할 |
| --- | --- |
| AI타임스 | 개인정보·일자리·생활처럼 일반 독자에게 닿는 AI 이슈 |
| GeekNews | 개발자 반응, 오픈소스, 새 도구 |
| 요즘IT | 국내 개발 현장과 실무 에디토리얼 |
| OpenAI News | 제품·정책·연구의 공식 발표 |
| GitHub Changelog | 개발 도구와 플랫폼의 공식 변경 사항 |
| arXiv cs.AI | 심화·주간 정리용 연구 후보 |

출처와 선정 규칙은 [`config/news_sources.json`](config/news_sources.json)에서 관리합니다.

## 처음 설정

### 1. 저장소 Secret 등록

`Settings → Secrets and variables → Actions → New repository secret`에서 다음 값을 등록합니다.

| 이름 | 필요 여부 | 용도 |
| --- | --- | --- |
| `GEMINI_API_KEY` | 권장 | Gemini 텍스트 초안과 수동 유료 이미지 생성 |

OpenAI API 키와 티스토리 로그인 정보는 필요하지 않습니다. GitHub Models는 Actions 실행 중 발급되는 `GITHUB_TOKEN`과 `models: read` 권한을 사용합니다.

### 2. GitHub Pages 확인

Pages는 `main` 브랜치의 `docs/` 결과를 Actions가 배포합니다.

```text
https://<github-id>.github.io/<repository>/
```

이 저장소의 배포 주소는 [초안 복사·미리보기 페이지](https://seung-won-yu.github.io/blog-writing/)입니다.

## 수동 생성

GitHub에서 `Actions → Daily news draft → Run workflow`를 선택합니다.

| 입력값 | 사용 시점 |
| --- | --- |
| `day` | 빠진 날짜를 `YYYY-MM-DD`로 생성. 비우면 오늘 |
| `force` | 같은 날짜의 기존 초안을 새로 생성 |
| `refresh_existing` | 과거 후보함을 유지하며 현재 장문 구조로 보강 |
| `ai_images` | 유료 Gemini 이미지 4장을 요청할 때만 사용 |
| `image_model` | Lite 또는 Flash 이미지 모델 선택 |

`refresh_existing`은 과거 날짜에 최신 뉴스가 섞이지 않게 기존 후보함을 재사용합니다. 원본 후보함과 기존 HTML이 모두 없으면 안전하게 중단합니다.

기본 이미지는 Pillow로 무료 생성됩니다. Gemini 이미지는 무료 티어가 아니므로 `ai_images`를 직접 켠 수동 실행에서만 요청합니다. 이미지 요청이 실패하면 기존 무료 이미지를 보존합니다.

## 티스토리 발행

1. [초안 복사·미리보기 페이지](https://seung-won-yu.github.io/blog-writing/)에서 날짜를 선택합니다.
2. `본문 미리보기`로 글 흐름과 이미지를 확인합니다.
3. 제목, 태그, 본문 HTML을 복사합니다.
4. 티스토리 글쓰기에서 HTML 모드로 전환해 붙여넣습니다.
5. 원문 링크, 핵심 사실, 정처기 정답을 확인합니다.
6. 내 판단이나 직접 확인한 내용을 추가합니다.
7. 대표 이미지를 지정하고 카테고리를 선택한 뒤 발행합니다.

티스토리 Open API의 글 작성 기능이 종료되어 최종 발행은 사람이 진행합니다.

## 품질·보안 장치

### 글 품질

- 짧은 요약문, 보도자료 문체, 반복적인 AI 연결어를 품질 검사에서 거절
- 기사별 설명과 전체 읽기 분량이 부족하면 재작성
- 모델이 선택 기사 URL, 출처, 발행 제목을 바꾸지 못하게 고정
- 가짜 사용 경험과 확인하지 않은 1인칭 체험 금지
- 정처기 문제는 모델 즉석 생성 대신 검증된 문제은행 사용
- 티스토리 스킨과 무관하게 선택지 `1.`~`4.`를 본문에 명시
- 저품질 fallback은 저장하되 `publish_ready: false`로 복사 차단

### Secret과 외부 콘텐츠

- `GEMINI_API_KEY`는 GitHub Actions Secret에서 요청 헤더로만 전달
- API 키를 코드, 로그, 생성 JSON, GitHub Pages JavaScript에 저장하지 않음
- 외부 기사 본문은 실행 중 제한적으로만 사용하고 저장소에 원문 전체를 보관하지 않음
- 기사 원본 이미지는 자동 복제·편집하지 않음
- 초안·후보함·미리보기 Pages에는 `noindex,nofollow,noarchive` 적용
- 저장소 쓰기 권한이 없는 사용자는 수동 workflow 실행 불가

### 모델 fallback

```text
gemini-3.5-flash
  → gemini-3-flash-preview
  → gemini-3.1-flash-lite
  → GitHub Models openai/gpt-4o-mini
  → 사실 기반 검토용 최소 초안
```

마지막 최소 초안까지 내려가면 workflow는 실패 상태로 표시됩니다. 후보함은 남지만 복사 버튼은 비활성화되므로 실패가 정상 발행처럼 보이지 않습니다.

## 로컬 실행

Python 3.12를 권장합니다. 한글 이미지 생성에는 Noto CJK 계열 폰트가 필요합니다.

```bash
python -m pip install -r requirements-images.txt
python -m unittest discover -s tests

python collect_news.py --today
python generate_daily_draft.py --today --fallback-on-error --fail-on-fallback
python generate_editorial_images.py --today
python build_copy_page.py
```

특정 날짜는 `--today` 대신 `--day YYYY-MM-DD`를 사용합니다.

로컬 AI 생성에는 환경 변수 `GEMINI_API_KEY` 또는 GitHub Models 권한이 있는 `GITHUB_TOKEN`이 필요합니다. 실제 키는 `.env`, 코드, 커밋에 넣지 마세요.

## 프로젝트 구조

```text
.github/workflows/tistory-draft.yml  예약·수동·push 자동화
config/news_sources.json             출처·독자 층위·7일 중복 제외 설정
config/editorial_persona.json        쑥쑥자라나라 개발자 편집자 페르소나와 금지 문체
collect_news.py                      RSS/Atom/HTML 뉴스 수집
news_pipeline.py                     정규화·점수·중복 제거·기사 선정
article_context.py                   선정 기사 근거의 제한 추출
generate_daily_draft.py              모델 호출·재시도·품질 검증
quiz_bank.py                         정처기 문제은행과 중복 회피
generate_editorial_images.py         무료 대표·본문 이미지 생성
generate_gemini_images.py            수동 유료 Gemini 이미지 생성
visual_direction.py                  기사별 이미지 장면 결정
export_tistory.py                    day JSON → 티스토리 HTML
build_copy_page.py                   복사·인라인 미리보기 페이지 생성
data/days/                           날짜별 편집 원본
docs/inbox/                          날짜별 뉴스 후보함
docs/tistory/                        티스토리 본문·메타·이미지
docs/preview/                        격리된 본문 미리보기
docs/index.html                      GitHub Pages 진입점
tests/                               수집·생성·품질·workflow 회귀 테스트
```

`pages_to_tistory.py`는 과거 외부 Pages 데이터를 가져올 때만 사용하는 레거시 도구이며, 현재 일일 자동화에서는 사용하지 않습니다.

## 문제 해결

### Actions가 `Report daily generation failure`에서 실패한다

Gemini 무료 한도, 모델 장애 또는 글 품질 미달입니다. 후보함과 검토용 초안은 저장되지만 발행용 복사는 차단됩니다. 쿼터 초기화 후 다시 실행하거나 원문을 직접 확인해 수동으로 보강하세요.

### `본문 HTML 복사` 버튼이 비활성화된다

해당 초안의 `publish_ready`가 `false`입니다. 모델 품질 검사를 통과하지 못한 결과이므로 그대로 발행하지 마세요.

### 이미지 생성에서 한글 폰트 오류가 난다

Ubuntu에서는 `fonts-noto-cjk`, macOS에서는 한글을 지원하는 시스템 폰트를 설치합니다. 필요하면 `BLOG_FONT_PATH`로 폰트 파일 경로를 지정합니다.

### 특정 뉴스 출처만 실패한다

한 출처의 장애가 전체 수집을 중단하지 않습니다. 요즘IT은 RSS가 거절되면 잡지 페이지 fallback을 시도하고, 나머지 출처로도 후보 선정을 계속합니다.

### 같은 기사가 다시 선택된다

`config/news_sources.json`의 `selection.exclude_recent_days`를 확인합니다. 기본값은 7일입니다.

## 운영 원칙

자동화는 초안을 빠르게 만들기 위한 도구입니다. 사실 확인, 저작권 판단, 개인적인 해석과 최종 발행 책임은 운영자에게 있습니다.
