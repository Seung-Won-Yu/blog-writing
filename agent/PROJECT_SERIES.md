# 토요일 주식 앱 제작기 편집 계약

원고를 쓰기 전에 `agent/READER_QUALITY_LOOP.md`를 함께 읽고, 8.5 미달을
사용자 재실행 요청으로 넘기지 않는 공통 자동 복구 계약을 적용한다.

이 문서는 2026-08-29부터 매주 토요일 09:00 KST에 실행되는 Codex 주식 앱
제작기 작업의 유일한 계약이다. 글과 티스토리 도우미까지 만들지만 티스토리에
직접 발행하지 않는다. Codex 1차 검수가 끝난 뒤 사용자가 제목·본문·이미지를
최종 확인하고 티스토리에 직접 복사해 발행한다.

## 이미 공개된 1편

- 1편 제목: `좋은 주식은 어떻게 고를까? 내가 미국주식 선정 알고리즘을 만든 이유`
- 공개 주소: `https://won0322.tistory.com/213`
- 공개일: 2026-08-25
- 저장소 원고: `editorial/edgelab/01-stock-selection-algorithm.md`
- 1편은 다시 생성하거나 미래 초안으로 내보내지 않는다.
- 2편은 2026-08-29에 시작하며, 1편의 마지막 질문인 `후보 200개를 어떤
  순서로 탈락시킬까?`를 이어받는다.

## 시작과 회차 선택

1. 블로그 저장소에서 `agent/REPOSITORY_SYNC.md`를 먼저 적용한다.
2. `editorial/edgelab/SERIES_PLAN.md`를 전부 읽고 오늘 날짜와 일치하는 회차
   하나만 선택한다. 오늘이 토요일이 아니거나 해당 회차가 없으면 `SKIP`한다.
3. 오늘 `YYYY-MM-DD-project`의 원본이나 산출물이 이미 있으면 다음 명령으로
   상태를 먼저 확인한다.

   ```bash
   python3 -m blog_pipeline.publishing.daily_guard \
     --draft-id YYYY-MM-DD-project
   python3 -m blog_pipeline.publishing.publish_bundle \
     --draft-id YYYY-MM-DD-project --resume-check
   ```

   `COMPLETE` 또는 `READY`인 묶음은 다시 조사하거나 생성하지 않는다. `PARTIAL`은
   기존 변경을 보존하고 누락 단계만 복구한다.

## 비공개 Git을 실제 근거로 사용한다

주식 앱의 근거 저장소는
`/Users/est/Documents/Playground/projects/edgelab`이다. 이 저장소는 읽기 전용
근거로 사용하며 이 작업에서 파일·브랜치·커밋을 수정하지 않는다.

글을 쓰기 전에 최소한 다음을 확인한다.

```bash
git -C "/Users/est/Documents/Playground/projects/edgelab" rev-parse --show-toplevel
git -C "/Users/est/Documents/Playground/projects/edgelab" status --short
git -C "/Users/est/Documents/Playground/projects/edgelab" log -1 --oneline
```

선택한 회차와 관련된 실제 코드, 설정, 테스트, 커밋 이력, 리플레이 결과 또는
서버 모의투자 기록을 찾아 서로 대조한다. 안전하게 실행 가능한 집중 테스트가
있으면 실행하고 명령·종료 코드·관찰 결과를 남긴다. 운영 서버 접속, 실주문,
계좌 조작, 토큰 사용, 데이터 삭제는 하지 않는다.

다음 중 하나라도 충족하지 못하면 숫자나 결과를 추정하지 말고
`NO_PUBLISH_EVIDENCE`로 보류한다.

- 회차의 핵심 주장을 뒷받침하는 코드나 설정 위치
- 실제 테스트·로그·DB 표본·리플레이 중 최소 하나
- 채택·수정·기각 중 하나로 정리할 수 있는 판단
- 공개 가능한 범위와 숨겨야 할 범위의 구분

첫 확인에서 증거가 부족하다고 바로 보류하지 않는다. 같은 회차의 실제 질문을
유지한 채 관련 코드·테스트·커밋·리플레이·모의투자 기록을 한 번 더 탐색하고,
안전한 집중 테스트가 가능하면 실행한다. 이어서 Codex 웹 리서치로 공식 문서와
원 논문을 확장해 설명 구조를 보완한다. 그래도 핵심 구현 증거가 없을 때만
`NO_PUBLISH_EVIDENCE`로 종료하며, 공개 자료를 내부 구현 증거처럼 대신 쓰거나
다음 회차의 결론을 당겨 쓰지 않는다.

## 2편의 범위

2026-08-29의 2편은 `주식 선정 알고리즘: 급등한 주식을 왜 탈락시켰을까?`를
기본 주제로 한다. 1편에서 다룬 랭킹 80개·순환 120개 구성은 짧게만
연결하고 반복 설명하지 않는다.

다음 순서를 실제 구현과 테스트로 확인한다.

`후보 200개 → 가격 하한 → 유동성 → 스프레드 → 당일 급등 제외 →
SMA20·SMA50 구조 → 전략 입력`

각 관문에서 확인 가능한 전후 후보 수나 테스트 사례가 없으면 숫자를 만들지
않는다. 구현 순서가 위 가안과 다르면 실제 코드 순서를 우선하고 차이를 글에
설명한다.

## 외부 조사와 공개 근거

비공개 코드는 글의 사실 근거로 내부 확인하되 비공개 저장소 URL, 커밋 링크,
서버 주소, 로컬 절대 경로를 공개 참고자료에 넣지 않는다. 독자가 확인할 수 있는
근거는 해당 회차와 직접 관련된 공식 문서·거래소 자료·원 논문을 웹에서 다시
확인해 3~6개 연결한다.

- 논문이 설명한 질문과 edgelab에서 선택한 파라미터를 구분한다.
- 외부 연구의 수치를 앱에서 직접 측정한 결과처럼 쓰지 않는다.
- 현재 구현 숫자는 코드·설정·테스트에서 확인된 값만 쓴다.
- 투자 성과를 보장하거나 종목을 추천하는 표현을 쓰지 않는다.

## 글의 흐름

기능 설명서가 아니라 다음 글이 궁금해지는 제작기로 쓴다.

`직전 편의 질문 → 실제로 막힌 장면 → 처음 가설 → 코드·실험 → 예상 밖 결과
→ 채택·수정·기각 → 독자가 가져갈 기준 → 다음 편 질문`

- 제목 앞에는 독자가 검색할 문제를 두고 프로젝트 이름은 필요할 때만 뒤에 둔다.
- 첫 5문장 안에 이번 회차에서 해결할 실제 문제와 판단 갈등을 보여 준다.
- 내부 클래스·함수·파일 목록을 차례로 해설하지 않는다.
- 한 회차에서는 핵심 질문 하나만 끝내고 다음 회차의 결론을 미리 소진하지 않는다.
- 표는 비교가 실제로 쉬워질 때만 사용한다. 긴 코드 상자나 PPT 카드 묶음으로
  본문을 채우지 않는다.
- 1편 링크를 `이전 글`로, 연재 계획의 다음 질문을 마지막 문장으로 연결한다.

## 일반 독자 8.5 제작 기준

이 기준은 낮은 글을 골라 탈락시키기 위한 종료 조건이 아니다. 첫 초안을 아래
기준으로 쓰고, 어느 항목이든 8.5 미만이면 같은 작업 안에서 원고를 다시 쓴다.
쉬운 말로 고치는 두 차례의 집중 수정과 필요한 공개 자료 재조사를 마치기 전에는
발행 도우미에 완성본으로 올리지 않는다. 구현 증거 자체가 없는 경우만
`NO_PUBLISH_EVIDENCE`로 보류한다.

- 대표 이미지 다음에 `30초 요약`을 정확히 세 문장으로 둔다. 각 문장은 문제,
  이번 편에서 한 선택, 숫자를 읽을 때의 한계를 하나씩 답한다.
- `먼저 알아둘 말`에 일반 독자가 막힐 용어 3~5개를 한 문장씩 설명한다.
- 도입과 30초 요약에는 `S1`, `ATR`, `SMA20`, `NaN`, `bp`, 내부 프로젝트명
  같은 약어를 쓰지 않는다. 본문 첫 사용 때는 쉬운 한국어를 먼저 쓰고 괄호 안에
  약어를 붙인다.
- 도입은 120~260자, 본문 한 문단은 200자 이하로 쓴다. 모바일에서 네 문단 이상
  같은 리듬이 이어지면 소제목·목록·이미지로 호흡을 끊는다.
- 표는 열 4개 이하로 제한하고 긴 코드는 12줄 이하만 바로 보여 준다. 그보다 긴
  코드는 접거나 핵심만 설명한다.
- 티스토리가 이미 보여 주는 제목·카테고리·날짜를 본문에서 반복하지 않는다.
  마지막 결론과 행동 문장도 한 번만 쓴다.
- 생성 후 `general_reader_understanding`과 `public_readability`를 계산해 둘 다
  8.5 이상인지 확인한다. 부족하면 `quality_reader_access`를 결과로 끝내지 말고
  해당 원인을 고친 뒤 다시 내보낸다.

## 이미지와 개인정보

대표 이미지 1장과 본문 이미지 2~4장을 기본으로 하되 장수를 채우지 않는다.

- 대표는 회차 고유의 갈등이나 판단 장면을 보여 주고 가짜 투자 화면·상승 차트·
  현금·수익 약속을 넣지 않는다.
- 본문은 실제 코드 흐름을 재구성한 한국어 도식, 개인정보를 가린 실제 화면,
  실제 측정값 차트 순으로 우선한다.
- 서버 IP, SSH 경로, 토큰, 쿠키, 계좌 정보, 내부 API 주소, 기기 식별자는
  캡처와 메타데이터에서 제거한다.
- 비공개 코드 화면을 그대로 캡처해 공개하지 않는다. 필요한 구조만 새 도식으로
  재구성한다.
- 모든 이미지는 1200×630 WebP, 장당 256KB 이하로 최적화하고 모바일에서
  글자와 관계가 읽히는지 확인한다.

## 저장과 검증

오늘 회차의 결과는 다른 발행 레인과 분리한다.

- 원본: `data/project_logs/YYYY-MM-DD.json`
- 초안 ID: `YYYY-MM-DD-project`
- 이미지: `docs/tistory/assets/YYYY-MM-DD-project/`
- HTML·메타·광고본: `docs/tistory/YYYY-MM-DD-project*`
- 미리보기: `docs/preview/YYYY-MM-DD-project.html`
- 편집 원고: `editorial/edgelab/NN-topic-slug.md`

`content_type`은 `project_log`, `content_label`은 `프로젝트 제작기`, 카테고리는
`프로젝트·회고`, `publication_mode`은 `manual_review`, `scheduled_at`은 해당
토요일 `09:00:00+09:00`으로 기록한다. 이 시각은 Codex 제작 시작 기준이며
티스토리 예약 시각이 아니다.
티스토리에서는 `실전 IT > 프로젝트·회고`를 선택하고 `실전 IT`에는 글을 직접 넣지 않는다.
광고는 정확히 한 번만 넣고 첫 완결 섹션 이후 전체 비광고 블록의 35~45%에 둔다.

완성 뒤 다음을 각각 실행한다.

```bash
python3 -m blog_pipeline.publishing.optimize_images \
  --draft-id YYYY-MM-DD-project
python3 -m blog_pipeline.publishing.export_tistory \
  --draft-id YYYY-MM-DD-project
python3 -m blog_pipeline.publishing.build_copy_page
python3 -m blog_pipeline.publishing.build_integration_page
python3 -m unittest discover -s tests
python3 -m blog_pipeline.publishing.daily_guard \
  --draft-id YYYY-MM-DD-project --require-complete
python3 -m blog_pipeline.publishing.publish_bundle \
  --draft-id YYYY-MM-DD-project --stage
python3 -m blog_pipeline.publishing.publish_bundle \
  --draft-id YYYY-MM-DD-project --check
git diff --cached --check
```

미리보기에서 데스크톱·모바일 표 가로 스크롤, 이미지 캡션, 광고 위치, 이전 글과
다음 질문을 확인한다. 검증을 모두 통과한 블로그 저장소 변경만 단일 커밋으로
확정하고 `main`에 push한 뒤 Pages 배포를 확인한다. 티스토리에는 발행하지 않는다.

최종 보고는 회차·제목·확인한 edgelab 근거·외부 근거·이미지 수·테스트·커밋·
Pages 상태만 짧게 남긴다.
