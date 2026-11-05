# 실제 검색어에서 시작하는 편집

2026-10-28 사용자 승인으로 다음 예약부터 적용한다. 주제 선정은 **실제 유입·노출
검색어 → 기존 글의 답 확인 → 남은 독자 질문 → 공식 근거와 수집 후보** 순서다.
`selected` 후보나 최신 발표를 먼저 고른 뒤 검색어를 끼워 맞추는 이전 순서보다 우선한다.
09:00 시작, 월·수·금 새 글 / 화·목 개선, 6.1 Sol Medium, 수동 티스토리 발행은 유지한다.

## 실행 시작에 읽을 데이터

```bash
sh scripts/blog-env python3 -m blog_pipeline.collection.search_demand --today
```

현재 스냅샷 경로는 `config/content_growth_trial.json`의 `demand_snapshot`이다.
`data/search_demand/YYYY-MM-DD.json`은 실제 관측일과 보고 기간을 담은 보존 자료다.
과거 원고가 인용한 파일은 다음 갱신 때 덮어쓰지 않는다. 같은 날 다시 관측하면 기존
원고가 인용 중인지 확인하고, 필요하면 다음 관측일까지 현재 검증본을 유지한다.

- 웹 검색의 최근 28일/직전 28일, 검색어 표의 클릭·노출을 읽는다. 화요일 또는
  `refresh_due: true`일 때 앱 내 Search Console에서 갱신을 우선 시도한다.
  나머지 날은 새 관측이 필요하지 않으면 파일을 재사용해 조사 시간을 줄인다.
- 관측 시각·정확한 기간·필터·표에서 확인한 행 수를 함께 남긴다. 현재 파일은
  154행 중 클릭 순 첫 50행만 확인한 자료다. 표 밖 검색어와 익명화된 값은 추정하지 않는다.
- 로그인·접근이 막히면 실제 오류를 기록하고 검증된 캐시를 쓴다. 7일이 지나면
  갱신 대상으로 표시하며, 관측일 또는 보고 종료일이 30일을 넘으면 신규 선정 근거로
  통과시키지 않는다. 날짜만 오늘로 바꾸지 않는다.
- 검색어 합계에 페이지 합계를 연결하지 않는다. 해당 검색어가 어느 글로 이어졌는지
  말하려면 검색어/페이지 필터로 별도 확인한다. 작은 표본은 작은 표본이라고 쓴다.
  노출은 이 사이트가 검색 결과에 나온 횟수이며 시장 검색량이 아니다.

## 질문을 고르는 순서

### 2026-11-05: 후보 소진·조회 실패 뒤에도 선정 계속

`growth_plan.target: null`은 `DISCOVERY_REQUIRED`이며 종료 조건이 아니다. 새 글 실행도
검색어 상위 몇 개만 보고 선정 불가로 끝내지 않는다. 아래 명령은 보존 스냅샷의 유효한
**전체 검색어**와 전체 원고의 제목·검색어·태그를 대조한 검토 목록을 만든다.
현재 파일은 50행 중 탐색 검색어 1개를 제외한 49개다. 기존 20행 출력 제한은 제거했다.

```bash
sh scripts/blog-env python3 -m blog_pipeline.publishing.selection_worklist --today
```

- `source_hints`는 어휘 탐색 힌트다. 검색어별 페이지 성과·같은 의도·공개 URL을 입증하지
  않는다. `page_url: null`이면 실제 공개 글 제목과 본문으로 매핑한 뒤 기록한다.
- `ready_for_review`는 보존하고, 다음 검색어·다른 기존 글·별도 후속 과제로 이동한다.
  이미 `published`인 글도 새로 확인한 공백이 있을 때만 다시 보완한다.
- `refresh_due: true`는 갱신 알림이다. Search Console 로그인 접근을 한 번 확인한 뒤
  없으면 유효한 30일 이내 캐시로 계속한다. 로그인 없는 QA 브라우저에 계정을 복사하거나
  앱 패널이 올 때까지 대기하지 않는다. 오래된 관측을 갱신한 것처럼 기록하지 않는다.
- 웹 도구의 Cache miss·일시적 조회 실패는 본문 부재나 보안 거절이 아니다. 아래 명령으로
  이 블로그의 공개 HTML을 로그인·쿠키·JS 없이 직접 읽어 대조한다. HTTP 오류·로그인
  페이지·다른 글·본문 추출 실패는 READ_UNAVAILABLE이며 성공으로 꾸미지 않는다.

```bash
sh scripts/blog-env python3 -m blog_pipeline.publishing.public_article --url https://won0322.tistory.com/214 --output /tmp/blog-writing-qa/DATE/214-public.json
```

URL과 DATE는 실제 후보·실행일로 바꾼다. 이 명령은 숫자 글 경로만 허용하고 로그인·
외부·다른 글로의 리다이렉트는 거절한다. 실제 보안/접근 거절을 우회하는 용도가 아니다.
한 후보를 읽을 수 없으면 사유를 남기고 다른 후보를 조사한다.

선정 기록은 `/tmp/blog-writing-qa/DATE/selection-review.json`에 남긴다. `snapshot`과
`reviews`를 기록하고 각 검토에 실제 `queries` 배열, `decision`, 20자 이상 구체적
`reason`을 쓴다. decision은 `already_answered`, `pending_handoff`, `unrelated`,
`source_unavailable`, `gap_confirmed`다. 의미가 같은 변형은 한 검토에 묶어도 된다.
선정된 `gap_confirmed`는 `action`, `source`, 실제 `page_url`, `public_evidence`,
`official_evidence`를 기록한다. 새 글은 action `new_article`, `existing_page_urls` 배열과
20자 이상 `distinct_outcome`도 필요하다. 해당 글의 별도 과제·변화·중복·원고 가드는 그대로다.

```bash
sh scripts/blog-env python3 -m blog_pipeline.publishing.selection_worklist --today --check-review /tmp/blog-writing-qa/DATE/selection-review.json
```

확인된 공백 하나를 찾으면 `SELECTED` 뒤 집필·QA·배포를 진행한다. 후보가 없다는
결론은 전체 유효 검색어 검토와 서로 다른 공식 자료 3곳의 직접 조사 후에만 낸다.
`direct_research`에 각각 실제 `url`·20자 이상 `finding`을 남겨 `EXHAUSTED`를 확인한다.
`RESEARCH_REQUIRED`면 미검토 질문·근거부터 계속한다. 이 검사는 기록의 범위·형식을
확인하며 실제 읽기·의미 판정을 대신하지 않는다. 실패 때문에 가짜 공백·검색어·관측일을
만들거나 품질 기준을 낮추지 않는다. 추적 보고서는 최종 커밋에 함께 정리한다.

1. 클릭이 있는 검색어를 먼저 보고, 노출은 있으나 클릭이 적은 검색어도 함께 읽는다.
   철자·띄어쓰기 변형은 사람이 같은 의도로 묶는다. 변형마다 새 글을 만들지 않는다.
   `site:` 탐색, 무관한 이름, 해석 불가능한 문자열은 글감에서 제외한다.
2. 실제 공개 본문과 원고에서 그 질문의 답을 찾는다. 기존 글과 같은 질문·결론이면
   **같은 URL 개선**이다. 이미 사용자가 반영한 답을 매번 다시 쓰지 않는다. 새로운
   오류·검색 의도 불일치·빠진 실행 단계처럼 구체적인 공백이 있어야 개선한다.
3. 새 글은 관측 검색어의 독자가 다음에 해야 하는 **별도의 일**이 있을 때만 쓴다.
   예를 들어 설치법과 결과 해석은 독립 과제가 될 수 있지만, 단순 철자 변형이나
   같은 설치법의 제목 변경은 아니다. 기존 글과 새 글의 질문·결과 차이를 적는다.
4. 그 뒤 수집기와 웹 조사로 답의 근거를 찾는다. 수집기 점수·별·최신성은 실제 수요를
   대체하지 않는다. 관련 후보가 없으면 관측 질문 자체를 직접 조사한다.
   월요일은 재사용 가능한 해결, 수요일은 그 질문과 관련된 최근 확인된 변화,
   금요일은 도구·스킬로 끝낼 구체적인 작업이나 선택을 다룬다.
5. 새 글 역할에 맞는 별도 질문이 없다면 그 실행은 관측 검색어에 연결된 기존 글의
   확인된 공백 하나를 보완해 인계한다. `demand_selected_refresh`와 사유를 실행
   기록에 남기며, 새 글 수를 채우기 위한 가설 기사·중복 예약은 만들지 않는다.
   기존 ID·날짜·URL을 유지하고 CONTENT_GROWTH_TRIAL의 개선·검수·배포 절차를 따른다.
   접근 불가로 최신 근거를 못 얻은 날도 신규 수요를 꾸미지 않고 이 개선 경로를 쓴다.

## 신규 원고에 남길 선정 근거

2026-10-29 이후 새 일일 글과 금요일 도구 글은 `editorial.search_demand`가 필수다.

```json
{
  "snapshot": "data/search_demand/2026-10-28.json",
  "query": "관측 파일에 실제로 있는 검색어 원문",
  "relation": "distinct_followup",
  "existing_page_urls": ["https://won0322.tistory.com/197"],
  "intent_gap": "기존 글이 끝내는 일과 이번 글이 끝내는 일이 어떻게 다른지 실제 본문 대조 결과를 쓴다."
}
```

`relation`은 `same_intent`(그 질문의 유효한 기존 답이 없는 경우) 또는
`distinct_followup`이다. `existing_page_urls`는 실제 읽고 대조한 글이며, 없으면 빈
배열이다. `primary_query`는 독자가 이해할 표현으로 다듬을 수 있지만 원 관측 검색어와
질문이 연결돼야 한다. `value_review.selection_reason`에도 실제 근거와 작은 표본의
한계를 남긴다. 가드는 보존된 검색어의 존재·양수 노출·범위·시점을 검사한다. 의미
연결과 기존 글 공백은 편집자가 실제 본문으로 검수한다. 점수만으로 통과하지 않는다.

관측 파일이 없거나 오래됐거나 실제 없는 검색어면 `quality_observed_search_demand`다.
원고 날짜를 바꾸거나 편집 가설을 관측값처럼 넣어 통과시키지 않는다. 오늘 이미 만든
2026-10-28 글과 과거 글에는 소급해 가짜 검색 수요를 붙이지 않는다.

## 출처 표기

npm 같은 제품의 공식 문서는 `official` 또는 `documentation`이며 독립 해설이 아니다.
문헌 비교(`document_comparison`)가 서로 다른 제공자의 공식 동작을 대조하는 경우,
제공자 이름(`publisher`)과 원문 URL을 기록한다. 서로 다른 제공자·도메인의 공식
자료를 비교하면 억지로 독립 자료를 채우거나 공식 문서를 잘못 분류할 필요가 없다.
실험·성능·사용 경험을 주장할 때 필요한 실제 증거는 이 예외로 대체할 수 없다.
