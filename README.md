# Blog Writing

여러 IT·AI 출처에서 매일 글감을 모아 검토용 후보함을 만들고, 조이한 GitHub Pages의 데일리 IT 뉴스 글을 티스토리에 붙여넣을 수 있는 HTML 초안으로 바꾸는 저장소입니다.

후보함은 뉴스를 그대로 발행하거나 새 글을 자동 생성하지 않습니다. 중복 제거와 추천 점수 계산까지만 하고, 최종 글은 원문 확인과 개인 의견 추가 후 직접 발행합니다. 기존 티스토리 초안은 아래 공개 사이트를 기준으로 변환합니다.

```text
https://ihan0316.github.io/ai-weekly-newsroom/
```

## 매일 자동 흐름

```text
07:28 KST GeekNews·요즘IT·공식 AI/개발 피드·arXiv에서 글감 수집
           URL/유사 제목 중복 제거, 최신성·관심 키워드·출처 신뢰도 점수 계산
           출처가 겹치지 않게 오늘의 추천 3건 선정
           docs/inbox/YYYY-MM-DD.html 및 JSON 생성

아침 KST  조이한 GitHub Pages 쪽 데일리 뉴스 발행
07:28 KST 이 저장소의 GitHub Actions 1차 실행
08:08/08:48/09:28/10:38 KST GitHub 예약 누락 대비 보강 실행
           원본 Pages 글과 원본 JSON을 가져옴
           뉴스 이미지를 docs/tistory/assets/YYYY-MM-DD/에 저장
           docs/tistory/YYYY-MM-DD.html 생성
           docs/tistory/YYYY-MM-DD.json 생성
           이 저장소에 자동 커밋
           같은 workflow에서 GitHub Pages 복사 페이지까지 배포
```

보통 08시 50분 이후에는 복사 페이지에서 제목, 태그, 본문 HTML을 바로 복사해 티스토리 글쓰기 HTML 모드에 붙여넣으면 됩니다. GitHub 예약 실행이 지연되거나 누락될 때를 대비해 08:08, 08:48, 09:28, 10:38 KST에 한 번씩 더 시도합니다.

```text
https://seung-won-yu.github.io/blog-writing/
```

뉴스 후보함은 아래 주소에서 확인합니다.

```text
https://seung-won-yu.github.io/blog-writing/inbox/
```

## 뉴스 후보 출처

| 성격 | 출처 | 용도 |
| --- | --- | --- |
| 커뮤니티 | GeekNews | 개발자 반응과 새 도구 탐색 |
| 국내 에디토리얼 | 요즘IT | 국내 개발 현장과 읽을거리 보강 |
| 공식 발표 | OpenAI News, GitHub Changelog | 제품·기능 변경의 1차 출처 |
| 연구 | arXiv cs.AI | 중장기 AI 흐름과 주간 정리 소재 |

출처 목록, 가중치, 관심 키워드는 `config/news_sources.json`에서 바꿀 수 있습니다. 기사 제목과 짧은 피드 요약, 원문 링크만 후보함에 저장하며 외부 이미지를 자동 복제하지 않습니다.

추천 순서는 정답이 아니라 검토 순서입니다. `맥락 확인 필요`가 표시된 커뮤니티·에디토리얼·논문은 원 출처, 게시일, 핵심 주장을 한 번 더 확인하세요.

## 필요한 파일

```text
.github/workflows/tistory-draft.yml # 매일 07:28~10:38 KST 초안 생성 및 보강 실행
collect_news.py                     # RSS/Atom 뉴스 수집 및 검토 페이지 생성
news_pipeline.py                    # 정규화, 중복 제거, 점수 계산, 출처 분산 선택
config/news_sources.json            # 출처, 관심 키워드, 추천 개수 설정
pages_to_tistory.py                 # 원본 Pages 글을 읽어 티스토리용 데이터로 변환
export_tistory.py                   # 티스토리 본문 HTML 생성
build_copy_page.py                  # HTML 복사 페이지 생성
docs/tistory/                       # 생성된 티스토리 초안 보관
docs/tistory/assets/                # 날짜별 백업 이미지 보관
docs/inbox/                         # 날짜별 뉴스 후보함 HTML/JSON
docs/index.html                     # 복사 전용 페이지
```

## 수동 실행

복사 페이지의 `초안 수동 생성/배포` 버튼을 누르면 GitHub Actions 화면이 열립니다. 그 화면에서 `Run workflow`를 누르면 오늘 날짜 초안을 직접 만들고 GitHub Pages 복사 페이지까지 배포합니다.

오늘 날짜 초안을 직접 만들 때:

```bash
python collect_news.py --today
python pages_to_tistory.py --today
```

뉴스 후보함만 특정 날짜 이름으로 만들 때:

```bash
python collect_news.py --day 2026-07-12
```

결과는 `docs/inbox/2026-07-12.html`, `docs/inbox/2026-07-12.json`과 최신본인 `docs/inbox/index.html`에 저장됩니다. 수집처 하나가 일시적으로 실패해도 나머지 후보함은 만들어지고, 실패한 출처는 페이지 아래 `수집 상태`에 표시됩니다.

특정 날짜 초안을 만들 때:

```bash
python pages_to_tistory.py --day 2026-07-02
python build_copy_page.py
```

결과 파일:

```text
docs/tistory/2026-07-02.html
docs/tistory/2026-07-02.json
docs/tistory/assets/2026-07-02/
```

## 티스토리 발행 방법

1. GitHub에서 `docs/tistory/YYYY-MM-DD.html` 파일을 연다.
2. 또는 복사 페이지에서 날짜를 선택한다.
3. 제목, 태그, 본문 HTML을 복사한다.
4. 티스토리 글쓰기에서 HTML 모드로 전환한다.
5. 본문에 붙여넣는다.
6. 이미지, 원문 링크, 정처기 문제를 확인한다.
7. 발행한다.

제목과 태그는 같은 날짜의 JSON 파일에서 확인할 수 있습니다.

```text
docs/tistory/YYYY-MM-DD.json
```

이미지는 원본 URL을 그대로 쓰지 않고 이 저장소의 GitHub Pages 주소로 다시 저장해 둡니다. 그래서 원본 사이트의 이미지 경로가 바뀌어도, 저장소에 커밋된 이미지가 남아 있으면 티스토리 글에서 계속 사용할 수 있습니다.

## GitHub Actions

이 저장소의 뉴스 수집과 기존 초안 자동화는 로그인이나 비밀 키가 필요 없습니다.

- `GEMINI_API_KEY` 필요 없음
- 티스토리 로그인 필요 없음
- 별도 비밀 키 필요 없음

07:28 KST부터 뉴스 후보함을 먼저 만들고 기존 초안 HTML과 이미지를 가져옵니다. 원본 뉴스 workflow는 07:23 KST schedule이지만 최근 실제 실행은 GitHub 지연으로 08:25~08:34 KST에 완료되고 있어, 이 저장소도 원본 schedule 5분 뒤부터 여러 번 시도합니다. 기존 초안 변환이 실패해도 수집된 후보함은 먼저 커밋하며, workflow 결과에는 변환 실패를 표시합니다. 관련 파일이 `main`에 푸시될 때도 같은 workflow에서 GitHub Pages를 배포합니다.

## 주의

티스토리 Open API의 글 작성 기능은 종료되어 공식 API로 자동 발행할 수 없습니다. 이 저장소는 발행 자동화가 아니라, 사람이 원문과 사실관계를 검토해 글로 발전시키는 후보 수집과 블로그 글 초안 생성을 담당합니다.
