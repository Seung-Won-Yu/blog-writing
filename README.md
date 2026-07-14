# Blog Writing Desk

[![Publish reviewed drafts](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/publish-drafts.yml/badge.svg)](https://github.com/Seung-Won-Yu/blog-writing/actions/workflows/publish-drafts.yml)

`쑥쑥자라나라`의 AI·IT 뉴스 편집 저장소입니다.

- 블로그: [하루 한 시간 나를 Develop!](https://won0322.tistory.com/)
- 초안 미리보기·복사: [GitHub Pages](https://seung-won-yu.github.io/blog-writing/)
- 뉴스 후보함: [오늘의 수집 결과](https://seung-won-yu.github.io/blog-writing/inbox/)

이 프로젝트는 모델 API로 글을 자동 생성하지 않습니다. Python은 뉴스 후보만 수집하고, Codex 편집자가 원문을 확인해 글을 작성합니다. GitHub Actions는 커밋된 결과를 테스트하고 GitHub Pages에 배포하는 역할만 맡습니다. 티스토리 발행은 미리보기 확인 후 직접 진행합니다.

## 운영 구조

```text
Python 수집기
  → GitHub Actions가 07:17 KST에 뉴스 후보함 생성·커밋
  → Codex Terra / Medium이 09:00 KST에 원문 확인·기사 선정·집필·이미지 생성·검수
  → 결정적 Python 도구가 본문·AdFit 삽입 지점·미리보기 생성
  → Git commit / push
  → GitHub Actions가 테스트·Pages 배포
  → 운영자가 티스토리에 직접 발행
```

매일 글의 역할 분담과 문체·사실 확인 기준은 [`agent/DAILY_EDITOR.md`](agent/DAILY_EDITOR.md)가 단일 기준입니다.

## 일일 운영

매일 `07:17 KST`에는 GitHub Actions가 뉴스 후보를 수집하고, `09:00 KST`에는 Codex 데스크톱 자동 작업이 다음 흐름을 실행합니다. 예약 지연에 대비해 1시간 43분의 버퍼를 둡니다.

1. 최신 `main`을 받습니다.
2. Actions가 커밋한 당일 후보함을 읽습니다. 누락된 날만 Python 수집기를 직접 실행합니다.
3. Codex `gpt-5.6-terra`를 Medium reasoning으로 사용해 후보 원문을 확인하고 기사 3건을 집필합니다.
4. Codex가 대표·본문 이미지를 만들고, Python 도구가 `NEWS 01` 뒤에 광고가 정확히 한 번 들어갈 티스토리 HTML·인라인 미리보기를 만듭니다.
5. 테스트와 콘텐츠 금칙어 검사를 통과한 결과만 GitHub에 푸시합니다.
6. GitHub Actions가 초안 페이지를 배포합니다.

GitHub Actions Secret에 `GEMINI_API_KEY`를 둘 필요가 없습니다. 키가 브라우저나 GitHub Pages에 노출될 경로도 없습니다.

## 수동 실행

Python 3.12를 권장합니다. 이미지 도구와 테스트 의존성을 설치합니다.

```bash
python3 -m pip install -r requirements-images.txt
```

오늘의 뉴스 후보 수집:

```bash
python3 -m blog_pipeline.collection.collect_news --today
```

Codex가 `data/days/YYYY-MM-DD.json`을 작성한 뒤 결과 생성:

```bash
python3 -m blog_pipeline.publishing.generate_editorial_images --today
python3 -m blog_pipeline.publishing.export_tistory --today
python3 -m blog_pipeline.publishing.build_copy_page
python3 -m unittest discover -s tests
```

특정 날짜는 `--today` 대신 `--day YYYY-MM-DD`를 사용합니다.

## 글 품질 기준

- 제목은 주제·핵심 키워드·독자가 확인할 변화를 담고, 날짜나 `데일리 IT 뉴스`만 반복하는 제목은 쓰지 않습니다.
- 첫 기사는 일반 독자도 궁금해할 생활·사회·일자리·개인정보 이슈를 우선합니다.
- 둘째 기사는 바로 활용할 개발 도구·보안·제품 변화, 셋째 기사는 깊이 읽을 기술 이야기를 고릅니다.
- 기사별로 확인된 사실, 독자에게 생기는 변화, 한계와 확인 방법을 한 흐름으로 씁니다.
- 별도 `승원의 메모`, `개발자 편집자의 체크포인트`, 자동화 고지문을 넣지 않습니다.
- 개인적 해석은 근거 다음 문장에 자연스럽게 녹이고, 가짜 체험담은 쓰지 않습니다.
- 정처기 선택지는 티스토리 스킨과 무관하게 `1.`부터 `4.`까지 실제 숫자가 보이게 출력합니다.
- 대표·본문 이미지는 글 이해를 도와야 합니다. 큰 문구와 카드가 가득한 PPT형 이미지는 기본값으로 쓰지 않습니다.
- 모든 기사에 원문 링크를 두고 원문 문장을 길게 복제하지 않습니다.

## 프로젝트 구조

```text
.github/workflows/
  collect-news.yml         07:17 KST 뉴스 후보 수집·커밋
  publish-drafts.yml       테스트와 GitHub Pages 배포 전용

agent/
  DAILY_EDITOR.md          Codex 집필·검수 계약

blog_pipeline/
  collection/              RSS·Atom·HTML 수집, 정규화, 중복 제거, 후보 선정
  publishing/              이미지·티스토리 HTML·미리보기 생성
  legacy/                  더 이상 실행하지 않는 과거 모델 API 생성기

config/
  news_sources.json        출처, 독자 층위, 중복 제외 규칙
  editorial_persona.json   레거시 생성기 복구용 문체 설정

data/days/                 날짜별 편집 원본 JSON
docs/inbox/                수집된 뉴스 후보함
docs/tistory/              복사할 본문 HTML과 메타데이터
docs/preview/              격리된 본문 미리보기
docs/index.html            GitHub Pages 초안 도구
tests/                     수집·출력·금칙어·워크플로 회귀 테스트
```

`blog_pipeline/legacy/`는 과거 결과를 복구할 때 참고할 수 있도록 보존했지만 일일 작업과 GitHub Actions에서는 호출하지 않습니다.

## 발행 방법

1. [초안 페이지](https://seung-won-yu.github.io/blog-writing/)에서 날짜를 고릅니다.
2. 첫 화면의 본문 미리보기로 글과 이미지를 확인합니다.
3. 추천 제목·카테고리·태그·대표 이미지를 확인합니다.
4. `광고 HTML 태그`에는 기본 AdFit 태그가 미리 들어 있습니다. 새 태그를 쓸 때만 교체하고 `최종 HTML 만들기`를 누릅니다.
5. `최종 HTML 복사` 후 티스토리 HTML 모드에 본문을 한 번 붙여넣습니다. 광고는 `NEWS 01` 종료 뒤, 본문 여백 밖의 728px 영역에 정확히 한 번 들어갑니다.
6. 서식 손실을 막기 위해 기본 모드로 전환하지 않고, HTML 모드에서 저장합니다.
7. 대표 이미지·카테고리·공개 상태를 확인해 발행합니다.

날짜별 완성본은 `docs/tistory/YYYY-MM-DD-adfit.html`입니다. 이 파일을 하나의 본문으로 취급하며, 광고 위치를 맞추기 위해 본문을 둘로 나누지 않습니다.

티스토리 로그인 정보와 API 키는 저장소에 넣지 않습니다. 저장소 쓰기 권한이 없는 사람은 일일 Codex 작업이나 GitHub 배포 결과를 변경할 수 없습니다.
