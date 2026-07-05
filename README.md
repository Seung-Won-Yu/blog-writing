# Blog Writing

조이한 GitHub Pages에 매일 발행되는 데일리 IT 뉴스 글을 가져와서, 티스토리 블로그에 붙여넣을 수 있는 HTML 초안을 만드는 저장소입니다.

이 저장소는 뉴스를 직접 생성하지 않습니다. 원본 뉴스 생성과 Pages 발행은 아래 공개 사이트를 기준으로 합니다.

```text
https://ihan0316.github.io/ai-weekly-newsroom/
```

## 매일 자동 흐름

```text
아침 KST  조이한 GitHub Pages 쪽 데일리 뉴스 발행
10:35 KST 이 저장소의 GitHub Actions 실행
           원본 Pages 글과 원본 JSON을 가져옴
           뉴스 이미지를 docs/tistory/assets/YYYY-MM-DD/에 저장
           docs/tistory/YYYY-MM-DD.html 생성
           docs/tistory/YYYY-MM-DD.json 생성
           이 저장소에 자동 커밋
           GitHub Pages가 main /docs를 공개 페이지로 자동 배포
```

보통 10시 40분 이후에는 복사 페이지에서 제목, 태그, 본문 HTML을 바로 복사해 티스토리 글쓰기 HTML 모드에 붙여넣으면 됩니다.

```text
https://seung-won-yu.github.io/blog-writing/
```

## 필요한 파일

```text
.github/workflows/tistory-draft.yml # 매일 10:35 KST 초안 생성
pages_to_tistory.py                 # 원본 Pages 글을 읽어 티스토리용 데이터로 변환
export_tistory.py                   # 티스토리 본문 HTML 생성
build_copy_page.py                  # HTML 복사 페이지 생성
docs/tistory/                       # 생성된 티스토리 초안 보관
docs/tistory/assets/                # 날짜별 백업 이미지 보관
docs/index.html                     # 복사 전용 페이지
```

## 수동 실행

복사 페이지의 `초안 수동 생성/배포` 버튼을 누르면 GitHub Actions 화면이 열립니다. 그 화면에서 `Run workflow`를 누르면 오늘 날짜 초안을 직접 만들고 GitHub Pages 배포까지 요청합니다.

오늘 날짜 초안을 직접 만들 때:

```bash
python pages_to_tistory.py --today
```

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

이 저장소의 자동화는 로그인이나 비밀 키가 필요 없습니다.

- `GEMINI_API_KEY` 필요 없음
- 티스토리 로그인 필요 없음
- 별도 비밀 키 필요 없음

원본 사이트가 정상 발행되어 있으면, 10:35 KST에 초안 HTML과 이미지를 가져와 저장합니다. 예약 방식은 조이한 원본 저장소와 같은 단순 UTC cron 구조를 사용합니다.

## 주의

티스토리 Open API의 글 작성 기능은 종료되어 공식 API로 자동 발행할 수 없습니다. 이 저장소는 발행 자동화가 아니라, 사람이 검토해서 붙여넣을 수 있는 블로그 글 초안 생성을 담당합니다.
