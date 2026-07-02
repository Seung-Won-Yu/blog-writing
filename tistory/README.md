# 티스토리 발행 흐름

## 1. Pages 글 가져오기

매일 GitHub Actions가 실행되면 다음 파일이 생긴다.

```text
https://ihan0316.github.io/ai-weekly-newsroom/days/YYYY-MM-DD.html
```

가장 빠른 준비 명령은 이미 발행된 Pages 글을 티스토리용 HTML로 바꾸는 것이다.
본문 이미지도 Pages의 이미지 URL을 절대 경로로 넣는다.

```bash
python pages_to_tistory.py --day 2026-07-01
```

결과 파일:

```text
docs/tistory/YYYY-MM-DD.html
docs/tistory/YYYY-MM-DD.json
```

## 2. 티스토리 임시저장 만들기

```bash
python draft_tistory_post.py --day 2026-07-01 --from-pages
```

저장 전에 payload만 확인하려면:

```bash
python draft_tistory_post.py --day 2026-07-01 --from-pages --dry-run
```

## 3. 발행 전 확인

티스토리 글쓰기에서:

1. 글쓰기 화면에서 `임시저장` 목록을 연다.
2. 방금 생성된 `[데일리 IT 뉴스] ...` 초안을 불러온다.
3. 이미지, 원문 링크 3개와 정처기 문제를 확인한다.
4. 문제가 없으면 `완료`를 눌러 발행한다.

완전 무인 발행은 티스토리 Open API 종료 이후 공식 지원되지 않는다. 브라우저 자동화로 초안 작성까지는 만들 수 있지만,
로그인 세션 만료와 관리자 UI 변경에 취약하므로 운영 기본값은 위 흐름처럼 발행 전 확인을 한 번 두는 방식이 안전하다.
