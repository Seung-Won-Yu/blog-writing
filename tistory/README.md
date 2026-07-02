# 티스토리 적용 가이드

## 1. 카테고리 만들기

`CATEGORY_PLAN.md`의 구조대로 티스토리 관리자에서 카테고리를 만든다.

자동 생성 글은 현재 블로그에 만들어진 `데일리IT뉴스`에 넣는다.

## 2. 스킨 HTML에 소개 영역 추가

`관리자 > 꾸미기 > 스킨 편집 > HTML`에서 `</header>` 바로 아래에
`skin-hero-snippet.html` 내용을 붙여넣는다.

카테고리 URL은 카테고리를 실제 생성한 뒤 티스토리 관리자/블로그에서 확인한 주소로 한 번 점검한다.

HTML 편집이 부담스러우면 이 단계는 생략해도 된다. `skin-custom.css`만 붙여넣어도 홈 화면에 간단한 소개 영역이 표시된다.

## 3. 사이드바 프로필 추가

`<aside id="aside" class="sidebar">` 바로 아래쪽에 `skin-sidebar-profile-snippet.html` 내용을 붙여넣는다.

기존 사이드바 위젯은 `카테고리`, `최근글`, `태그`, `전체 방문자` 정도만 남기는 것을 추천한다.

## 4. 스킨 CSS 적용

`관리자 > 꾸미기 > 스킨 편집 > CSS` 맨 아래에 `skin-custom.css` 내용을 붙여넣는다.

기존 CSS를 지우지 말고 맨 아래에 추가한다. 문제가 생기면 추가한 블록만 삭제하면 원복된다.

## 5. 자동글 올리는 흐름

매일 GitHub Actions가 실행되면 다음 파일이 생긴다.

```text
docs/tistory/YYYY-MM-DD.html
docs/tistory/YYYY-MM-DD.json
```

티스토리 글쓰기에서:

1. `YYYY-MM-DD.json`의 `title`, `category`, `tags`를 확인한다.
2. 글쓰기 화면을 HTML 모드로 바꾼다.
3. `YYYY-MM-DD.html` 본문을 붙여넣는다.
4. 원문 링크 3개와 정처기 문제를 확인하고 발행한다.

## 6. 추천 메뉴

상단 메뉴는 아래 정도만 남기는 것을 추천한다.

```text
홈
뉴스룸
프로젝트
공부
태그
```
