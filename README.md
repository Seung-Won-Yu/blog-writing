# AI Weekly Newsroom

매일 생성되는 GitHub Pages 데일리 다이제스트를 티스토리 블로그 초안으로 옮기기 위한 자동화 프로젝트입니다.

기본 흐름은 다음과 같습니다.

1. GitHub Actions가 매일 IT/개발 뉴스, 정처기 문제, 용어 데이터를 생성합니다.
2. 정적 사이트가 `docs/`에 빌드되고 GitHub Pages로 배포됩니다.
3. 발행된 Pages 글을 가져와 티스토리용 HTML 초안으로 변환합니다.
4. 티스토리 글쓰기 화면에서 HTML 초안을 붙여넣고 최종 확인 후 직접 발행합니다.

라이브 Pages:

```text
https://seung-won-yu.github.io/ai-weekly-newsroom/
```

## 핵심 파일

```text
.github/workflows/daily.yml     # 매일 09:30 KST Pages 글 자동 생성/빌드/커밋
.github/workflows/tistory-draft.yml # 매일 13:00 KST 티스토리 HTML 초안 생성/커밋
pipeline_gemini.py              # Gemini로 뉴스 3개, 본문, 정처기 문제, 용어 생성
fetch_images.py                 # 기사 대표 이미지 수집
gen_audio.py                    # 기사 음성 MP3 생성
build.py                        # 하루 상세 페이지 렌더러
build_site.py                   # docs/ 정적 사이트 전체 빌드
assets/site.css                 # Pages 사이트 스타일
assets/site.js                  # Pages 사이트 인터랙션
data/days/YYYY-MM-DD.json       # 하루치 원천 데이터
docs/                           # GitHub Pages 배포 결과물
pages_to_tistory.py             # Pages 글을 티스토리 HTML로 변환
export_tistory.py               # 티스토리 본문 HTML 생성기
draft_tistory_post.py           # 로컬 Chrome 로그인 세션으로 티스토리 임시저장 생성(선택)
tistory/post-view-custom.css    # 티스토리 글 상세 화면용 스킨 CSS
ask-worker/                     # 선택 기능: 기사 Q&A Cloudflare Worker
```

`docs/`는 생성 산출물이지만 GitHub Pages가 실제로 서빙하는 폴더입니다. 이미지, 오디오, 날짜별 HTML이 들어 있으므로 운영 중에는 삭제하지 않습니다.

## 매일 자동 운영

두 개의 GitHub Actions가 시간차로 실행됩니다.

```text
09:30 KST  Daily digest
           data/days/YYYY-MM-DD.json 생성
           docs/days/YYYY-MM-DD.html 생성
           GitHub Pages 배포용 파일 커밋

13:00 KST  Tistory draft HTML
           발행된 Pages 글을 다시 읽음
           docs/tistory/YYYY-MM-DD.html 생성
           docs/tistory/YYYY-MM-DD.json 생성
           Git에 커밋
```

13:00 이후에는 GitHub에서 `docs/tistory/YYYY-MM-DD.html` 파일을 열고 본문 HTML을 티스토리 글쓰기 화면에 넣으면 됩니다.

## 로컬에서 티스토리 임시저장 만들기

Chrome에 티스토리 로그인이 살아 있고, 로컬에서 바로 임시저장까지 만들고 싶을 때만 사용합니다.

```bash
python draft_tistory_post.py --day 2026-07-02 --from-pages
```

오늘 날짜를 기준으로 가져오려면:

```bash
python draft_tistory_post.py --today --from-pages
```

저장 전에 제목, 카테고리, 태그, 본문 길이만 확인하려면:

```bash
python draft_tistory_post.py --day 2026-07-02 --from-pages --dry-run
```

성공하면 다음 파일도 함께 만들어집니다.

```text
docs/tistory/YYYY-MM-DD.html
docs/tistory/YYYY-MM-DD.json
```

티스토리에서는 글쓰기 화면의 `임시저장` 목록에서 방금 생성된 글을 불러온 뒤 이미지, 원문 링크, 정처기 문제를 확인하고 발행합니다.

## 수동으로 티스토리 HTML만 만들기

브라우저 임시저장까지 하지 않고 HTML 파일만 만들 때 사용합니다.

```bash
python pages_to_tistory.py --day 2026-07-02
```

결과:

```text
docs/tistory/2026-07-02.html
docs/tistory/2026-07-02.json
```

## Pages 사이트 다시 빌드하기

로컬에서 `data/days/`를 수정한 뒤 사이트를 다시 만들 때 사용합니다.

```bash
python fetch_images.py
python gen_audio.py
python build_site.py
```

자동 운영에서는 `.github/workflows/daily.yml`이 이 과정을 실행합니다. `GEMINI_API_KEY`는 GitHub repository secret에 등록되어 있어야 합니다.

## 티스토리 스킨 CSS

티스토리 글 상세 화면 디자인은 다음 파일이 기준입니다.

```text
tistory/post-view-custom.css
```

이 CSS는 티스토리 스킨 편집의 CSS 영역에 들어가는 커스텀 블록입니다. 현재는 본문 카드, 뉴스 카드, 정처기 문제, 용어 카드, 상단 커버 스타일을 조정합니다.

수정 후에는 티스토리 스킨 편집 화면에 반영하고, 공개 글에서 강력 새로고침으로 확인합니다.

## 선택 기능: 기사 Q&A Worker

`ask-worker/`는 Pages 사이트의 "이 기사에 질문" 기능을 위한 Cloudflare Worker입니다. 티스토리 초안 생성에는 필요하지 않습니다.

배포 개요:

```bash
cd ask-worker
npx wrangler secret put GEMINI_API_KEY
npx wrangler deploy
```

배포 URL을 `build.py`의 `ASK_ENDPOINT`에 넣고 `python build_site.py`를 다시 실행하면 Pages 사이트 질문 기능에 연결됩니다.

## 문제 해결

### 카테고리 API가 404를 반환할 때

Chrome이 티스토리 관리 화면이 아닌 다른 사이트 관리 화면을 잡은 경우입니다. `draft_tistory_post.py`는 `won0322.tistory.com/manage` 도메인을 확인하도록 되어 있으니, Chrome에서 티스토리 로그인이 유지되는지 먼저 확인합니다.

### 임시저장 글이 안 보일 때

다음 명령으로 실제 저장 전 페이로드가 정상인지 확인합니다.

```bash
python draft_tistory_post.py --day YYYY-MM-DD --from-pages --dry-run
```

정상이라면 티스토리 글쓰기 화면을 새로고침하고 `임시저장` 목록을 다시 엽니다.

### 이미지가 깨질 때

`--from-pages`를 사용했는지 확인합니다. 이 옵션은 Pages에 올라간 이미지 URL을 절대 경로로 바꿔 티스토리 본문에 넣습니다.

## 정리 원칙

보존하는 파일:

- GitHub Actions와 Pages 빌드에 필요한 코드
- `data/days/` 원천 데이터
- `docs/` Pages 배포 산출물
- `docs/tistory/` 티스토리 발행 기록
- 티스토리 스킨 CSS

제거해도 되는 파일:

- `.DS_Store`
- `__pycache__/`, `*.pyc`
- 현재 코드에서 참조되지 않는 과거 샘플 JSON
- 중복 README

## 주의

티스토리 Open API의 글 작성 기능은 종료되어 공식 API로 완전 자동 발행할 수 없습니다. 이 프로젝트는 안정성을 위해 임시저장 초안까지만 자동화하고, 최종 발행은 사람이 확인하도록 설계했습니다.
