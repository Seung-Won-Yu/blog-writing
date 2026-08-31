# 쑥쑥자라나라 금요일 개발·AI 인사이트 편집 계약

이 문서는 매주 금요일 09:00 KST에 실행되는 Codex 작업의 유일한 계약입니다. 예약 실행은 한 번만 수행하며 자동 재실행 슬롯을 두지 않습니다. 월·수 실전 IT 아티클, 화·목 궁금한 IT 원리, 토요일 프로젝트 개발일지와 원본·이미지·HTML·가드를 완전히 분리합니다. 2026-08-28부터 금요일은 `developer_insight` 역할로 GitHub·공식 문서·공개 저장소·연구를 읽고 개발자가 저장해 두고 다시 볼 만한 개발·AI 인사이트를 만듭니다. 단순 소식 요약이나 억지 따라하기로 발행 횟수를 채우지 않습니다. Codex가 원고·이미지·검증·도우미까지 1차 완료하고, 티스토리 붙여넣기와 발행은 사용자가 최종 확인 뒤 직접 합니다. 이전 토요일의 `executed_experiment` 자동화 글은 역사 자료로 그대로 유지합니다.

사용자가 현재 대화에서 당일 추가 발행을 명시한 경우에만 `publication_mode: "manual_extra"`를 사용할 수 있습니다. 이때 `manual_extra_reason`에 요청 근거를 남기고 `scheduled_at`은 같은 날짜의 KST 실행 시각으로 기록합니다. 수집기·정기 워크플로는 이 값을 만들지 않으며, 별도 요청이 없는 비금요일 실행은 계속 건너뜁니다.

## 시작 조건과 단일 실행

1. `agent/REPOSITORY_SYNC.md`를 먼저 읽고 공통 동기화 계약을 적용한 뒤 금요일 글 자체의 당일 상태를 확인합니다. 다른 예약 글의 누락과 관계없이 이 금요일 글을 독립적으로 진행합니다.

   ```bash
   git fetch origin main
   git show-ref --verify --quiet refs/remotes/origin/main
   git rev-list --left-right --count HEAD...refs/remotes/origin/main
   python3 -m blog_pipeline.publishing.saturday_guard --today
   ```

   `git fetch`는 독립 명령으로 한 번만 실행합니다. DNS·5xx·timeout이어도 캐시된 `origin/main`보다 로컬이 뒤처지지 않았으면 `OFFLINE_SAFE`로 계속합니다. 실제 분기, 인증·권한 실패, 원격 캐시 없음만 `BLOCKED`입니다.

   사용자가 수동으로 다시 실행했을 때 작업 트리가 더러우면 `python3 -m blog_pipeline.publishing.publish_bundle --draft-id YYYY-MM-DD-automation --resume-check`를 먼저 실행합니다. `READY`면 원고·이미지를 다시 만들지 않은 채 최종 가드·스테이징부터 복구합니다. `PARTIAL`이면 변경을 보존하고 중단합니다.

   브라우저·Playwright 검증의 스냅샷, 로그, 원본 캡처는 저장소 루트가 아니라 `/tmp/blog-writing-qa/YYYY-MM-DD-automation/`에서만 생성합니다. Playwright CLI도 그 임시 디렉터리에서 실행하고 저장소에는 최종 검증을 통과한 `docs/tistory/assets/YYYY-MM-DD-automation/*.webp`만 남깁니다. Google Chrome 앱 실행 파일을 직접 호출하지 않습니다. GUI Chrome이나 사용자 프로필을 재사용하지 않고 Playwright CLI 또는 제공된 브라우저 도구만 사용합니다. 임시 검증 파일 때문에 작업 트리를 더럽히거나 사용자 파일을 자동 삭제하지 않습니다.

2. `saturday_guard` 결과를 따릅니다.

   - `SKIP`: 금요일이 아니므로 즉시 종료합니다.
   - `COMPLETE`: 같은 날짜 금요일 글을 다시 조사·집필·생성하지 않고 종료합니다.
   - `PARTIAL`: 출력된 `reasons`에 해당하는 단계만 복구합니다.
   - `NEW`: 아래 흐름을 정확히 한 번 수행합니다.

3. `docs/automation-inbox/latest.json`을 먼저 읽습니다.

   - `day`가 당일 날짜와 다르면 오래된 후보를 사용하지 않고 GitHub·공식 문서·공개 저장소·원 논문·요즘IT 개발 글을 직접 검색합니다.
   - `selected`의 임시 점수는 제목·요약 메타데이터로 계산한 우선순위이며 검증 완료의 증거가 아닙니다.
   - 후보함이 없거나 비어 있거나 수집 오류가 크면 공식 출처를 직접 검색해 같은 선정 기준으로 대체 후보를 만듭니다.
   - 선택한 한 건은 최소 3개의 추적 가능한 출처를 확보하고, 원문에 없는 새 지도·비교표·판단 기준을 먼저 정의합니다. 직접 실행이 필요한 도구 비교·실습만 안전한 실행 단계로 이동합니다.
   - 현재 후보가 모두 75점 미만·중복·출처 부족·새 기여 부족이면 `python3 -m blog_pipeline.collection.collect_automation --today`를 같은 실행에서 딱 한 번 다시 실행하고 새 추천·후보를 평가합니다.
   - 재수집 뒤에도 없으면 Codex 웹 리서치로 공식 저장소·공식 가이드·GitHub Trending·원 논문·독립 개발 자료에서 후보함에 없던 질문을 최대 10건까지 찾습니다. 같은 도구나 제목을 바꿔 채우지 않습니다.

4. 결과는 뉴스글과 분리해 저장합니다.

   - 원본: `data/automation_cases/YYYY-MM-DD.json`
   - 초안 ID: `YYYY-MM-DD-automation`
   - 이미지: `docs/tistory/assets/YYYY-MM-DD-automation/`
   - HTML·메타·광고본: `docs/tistory/YYYY-MM-DD-automation*`
   - 미리보기: `docs/preview/YYYY-MM-DD-automation.html`

같은 날짜의 `data/days/YYYY-MM-DD.json`과 뉴스 이미지·HTML은 읽기 참고 외에는 수정하지 않습니다.

## 글감과 근거 검증

다음 형식 중 질문과 증거에 맞는 하나만 선택합니다.

- 생태계 지도: 공개 저장소·표준·공식 문서를 역할별로 분류해 무엇이 어디에 쓰이는지 보여 줌
- 공식 문서 해설: 번역·요약이 아니라 숨은 제약, 좋은 예와 나쁜 예, 적용 판단 순서를 더함
- 근거 기반 목록: 숫자를 채우기 위한 Top N이 아니라 사전에 공개한 기준으로 선별하고 탈락 이유까지 설명
- 도구·Agent Skill 비교: 같은 과제·환경·평가표로 직접 실행해 결과·실패·사람 승인 지점을 비교
- 개발자 커리어 분석: 실제로 수집한 공개 공고·데이터의 표본과 방법을 공개하고 역할별 스킬 지도를 만듦
- 연구 해설·실패 유형 분석: 원 논문의 실험 설계·결과·한계를 공식 구현 자료와 연결
- 직접 실행 실험기·따라하기·공개 도구 적용 사례: 독자가 재현할 실습 자체가 질문의 답일 때만 사용

글감은 `검색 지속성 20 · 개발자 관련성 25 · 출처 신뢰도 20 · 원문에 더하는 분석 20 · 궁금증 유발력 15`로 비교합니다. 총점 75점 이상이면서 `공식·원출처 포함 3개 이상의 근거`, `독자가 가져갈 지도·비교표·읽기 순서·평가표 중 하나`, `최근 180일 비중복`을 모두 충족한 주제만 진행합니다. 개발자 관련성이 최소 기준에 못 미치면 총점이 높아도 추천하지 않습니다. 기존 후보 평가, 1회 재수집, Codex 직접 리서치를 모두 마친 뒤에도 기준을 통과한 주제가 없을 때만 오류가 아닌 `NO_PUBLISH_QUALITY`로 종료하고, 검토한 후보·점수·탈락 이유·확장 리서치 범위만 보고하며 원고·이미지·커밋·푸시를 만들지 않습니다. 미완성 초안은 중복 이력으로 세지 않습니다. 뉴스 요약을 두 번째로 만들지 않습니다.

핵심 독자는 개발자와 IT에 관심 있는 독자입니다. `Agent Skills는 어디에 쓰일까`, `GitHub 스타가 많으면 좋은 스킬일까`, `공식 문서에서 먼저 봐야 할 제약은 무엇일까`, `AI 엔지니어 채용 공고가 반복해서 요구하는 능력은 무엇일까`처럼 제목만 보고도 답이 궁금한 질문을 고릅니다. 제품 발표 한 건, 릴리스 노트 번역, 기능 목록, 설치 로그, 프레임워크 버전 자체는 주제가 될 수 없습니다.

도구명을 지워도 질문의 가치가 남는지 확인하되 비개발자용으로 억지 단순화하지 않습니다. 코드를 이해해야만 효용을 얻는 개발 주제도 허용하지만, 코드는 결론을 뒷받침할 때만 넣습니다. 독자가 공식 문서·저장소·데이터를 어떻게 읽고 선택해야 하는지가 중심이며 패키지 내부 구현을 길게 복사하지 않습니다. 월요일의 문제 해결 가이드, 수요일의 최신 변화 해설, 토요일의 프로젝트 개발일지와 질문이 겹치면 금요일 고유의 `여러 출처를 엮은 지도·비교·분석`으로 좁힙니다.

실행이 필요 없는 생태계 지도·공식 문서 해설·연구 해설은 억지로 샘플 앱을 만들지 않습니다. 대신 출처 선택 규칙, 확인일, 비교 축, 빠진 범위, 반례를 기록합니다. 도구 비교·벤치마크·따라하기만 같은 입력·환경·종료 조건으로 직접 실행하고, 검증한 버전·커밋, 기대 결과와 실제 결과, 실패와 복구를 남깁니다. 의심스러운 설치 스크립트나 과도한 권한 때문에 실행할 수 없으면 `구조 분석`으로 명시합니다. 측정하지 않은 숫자는 제목·표·결론에 만들지 않습니다.

`pocket-desk-os` 같은 실제 프로젝트와 자연스럽게 연결되면 관련 개발일지를 보조 사례로 연결할 수 있습니다. 프로젝트 이름만 빌린 홍보 글은 만들지 않습니다.

요즘IT 같은 매체 글은 독자가 궁금해할 질문을 찾는 보조 출처로만 사용합니다. 원문의 문장·목차·표·이미지를 옮기거나 순서만 바꿔 재서술하지 않습니다. 최종 글은 공식 저장소·공식 문서·직접 실행 결과를 중심으로 새로 구성합니다. 다른 글에 나온 수치나 설문 결과는 출처를 명시해 인용할 때만 사용하며, 직접 측정한 결과처럼 쓰지 않습니다. 가능하면 같은 질문을 작은 공개 예제에서 직접 측정해 표본·환경·횟수와 함께 제시합니다.

인기 순위·Top N·추천 글을 발견하면 그 순서를 글의 결론으로 가져오지 않습니다. GitHub 스타·버전·최근 활동·라이선스는 작업 시점에 공식 API와 저장소로 다시 확인하고, 인기도를 품질·안전성·내 작업 적합성으로 바꿔 말하지 않습니다. 비교형에서는 같은 입력·종료 조건·검사 명령을 쓰고 `계획 전 질문`, `변경 범위`, `검증`, `사람 승인`, `복구` 중 주제에 맞는 3~5개를 사전에 평가 기준으로 고정합니다. 추천은 종합 1등 하나가 아니라 `어떤 상황에 맞는지`를 설명합니다.

후보 수집기는 공개 메타데이터를 모아 우선순위만 계산합니다. 저장소를 복제하거나 설치 명령을 실행하지 않고 글·이미지·티스토리 HTML도 만들지 않습니다. 출처 검증과 집필은 이 09:00 작업에서 선택한 한 건에만 수행합니다.

직접 실행형은 실행 전 README, 설치 명령, 의존성, 권한 요구를 읽습니다. 별도 임시 디렉터리와 테스트 데이터만 사용하며 비밀키·개인 계정·운영 서비스·`sudo`·알 수 없는 바이너리·의심스러운 설치 스크립트·과도한 권한이 필요한 작업은 실행하지 않습니다. 안전하게 실행할 수 없으면 `구조 분석`으로 명시하고 실행·검증·벤치마크했다고 쓰지 않습니다.

`verification.mode: executed`인 실제 실행형에는 다음 기록이 있어야 합니다.

- 운영체제, 런타임, 도구 버전과 공개 저장소의 태그·커밋
- 입력 데이터와 실행 명령 또는 설정
- 실행 전 예상 결과
- 실제 출력·로그·생성 파일
- 실패한 시도와 바꾼 조건
- 적용 범위, 비용·보안·권한·복구 한계

검증한 버전·커밋·환경·기대 결과·실제 결과는 `verification`에 빠짐없이 기록합니다. 본문에는 독자가 실행하는 데 필요한 버전과 결과만 먼저 보여 주고, 커밋 해시·종료 코드·파일 해시·fixture 생성 실패 같은 개발 증거는 마지막 `개발 기록`에서 짧게 요약합니다. 측정하지 않은 숫자는 만들지 않습니다. 측정했다면 표본, 횟수, 단위, 환경을 함께 기록합니다.

## 글 구성

제목은 `구체적 대상 + 독자가 가진 질문 + 읽고 얻을 판단`을 한 줄에 담습니다. 예: `Agent Skills는 어디에 쓰일까: 공개 스킬 생태계 지도`, `GitHub 스타가 많으면 좋은 스킬일까: 평가 기준 7가지`. 제목에 표본 수·도구 수·숫자를 쓰면 실제로 확보한 근거와 정확히 일치해야 합니다. `충격`, `역대급`, `무조건` 같은 클릭베이트는 쓰지 않습니다. 핵심 검색어는 제목에 한 번 자연스럽게 두고 태그 5~8개는 `핵심 개념`, `개발 작업`, `출처 유형`, `독자가 얻는 판단`을 섞습니다. 전체는 약 8~20분 분량, 소제목 5~8개로 작성합니다.

30일 이내의 `config/search_opportunities.json`을 확인하되, 실제 질문과 맞을 때만 사용합니다. `editorial.search_intent`에는 짧은 실제 검색어 `query`, 독자가 판단하려는 구체적 질문 `reader_need`, 지도·비교표·근거 목록·실행 결과 중 답을 증명할 방식 `answer_format`을 기록합니다. `related_posts`는 기반 원리를 설명하는 `foundation`과 다음 읽을거리로 이어지는 `next_step`을 각각 1개 이상 사용합니다.

글의 흐름은 형식에 맞게 고릅니다.

- 지도·목록: `답이 궁금해지는 장면 → 조사 범위와 기준 → 역할별 지도 → 의외의 차이 → 어떤 상황에 무엇을 볼지 → 빠진 범위와 업데이트 조건`
- 공식 문서·연구 해설: `널리 퍼진 주장 → 원문이 실제로 말한 것 → 작동 원리 → 잘못 읽기 쉬운 부분 → 개발 작업에 적용하는 판단 → 한계`
- 비교 실험: `우리가 막힌 한 장면 → 왜 이 후보들을 골랐는지 → 같은 과제·같은 평가 기준 → 각 후보가 다르게 행동한 순간 → 결과와 실패 비교 → 상황별 선택`
- 커리어 분석: `궁금한 역할 → 실제 표본과 수집 규칙 → 반복 신호 → 역할별 차이 → 학습 우선순위 → 표본 한계`

후보별 기능 목록을 동일한 길이로 반복하지 말고, 선택을 바꾸는 차이만 본문에 남깁니다.

- 첫 5문장 안에 독자가 가진 질문, 먼저 답할 핵심 결론, 끝까지 읽어야 알 수 있는 판단 하나를 보여 줍니다.
- 실행형에서 첫 코드보다 앞에 준비물 목록을 둡니다. 코드가 있다면 저장할 파일명, 실행 위치, 운영체제별 차이를 함께 설명합니다.
- 20줄을 넘는 전체 코드는 기본으로 접어 두고 구체적인 용도를 적습니다. 본문에는 선택 기준, 짧은 실행 명령, 예상 결과를 먼저 보여 주며 긴 코드가 화면 대부분을 차지하게 만들지 않습니다.
- 실행형 단계는 설치·입력 준비·실행·성공 확인이 끊기지 않게 이어져야 합니다. 연구·지도형은 출처 선택·분류·비교·판단이 끊기지 않게 이어져야 합니다.
- 성공 여부를 독자가 눈으로 확인할 파일·화면·개수 중 하나로 설명하고, 실패 시 원본이 남는지와 다시 시작할 위치를 바로 뒤에 적습니다.
- 커밋 해시·SHA-256·종료 코드·테스트용 글꼴 오류 같은 검증 세부값을 실행 단계 앞에 두지 않습니다. 필요한 값은 마지막 `개발 기록`에 모읍니다.
- 구현 순서가 실제 실행 순서일 때만 소제목에 번호를 붙입니다. 문제·실패·결과를 설명하는 장은 질문형·장면형 제목으로 연결합니다.
- 설치·버전·코드보다 개발자가 실제로 선택을 고민하는 장면과 결론을 앞에 둡니다.
- 코드는 필수가 아닙니다. 넣을 때만 복사 가능한 최소 코드·설정과 버전·실행 위치를 명시합니다.
- 비교가 쉬워질 때 HTML 표 1~3개를 사용합니다.
- 광고는 정확히 1개, 첫 완결된 구현 섹션 뒤 전체 비광고 블록의 35~45% 위치에 `ad_break`로 둡니다. 블록 순서는 반드시 `완결 문단·표·목록·코드·인용 → ad_break → 다음 h`여야 하며 소제목과 첫 설명 사이에는 넣지 않습니다.
- 블로그 관련 글은 같은 문제의 기준을 설명한 가이드 1개와 이전 실험·프로젝트 글 1개를 우선하되, 연결이 억지스러우면 개수를 채우지 않습니다. 공식 문서·저장소·보조 자료는 3~6개를 연결합니다.
- `정리해보겠습니다`, `자동화로 작성했습니다`, 과장된 성공담, 하지 않은 체험 표현을 쓰지 않습니다.

## 자연스러운 개발 매거진 문체

- 기능 목록으로 시작하지 않고 개발자가 실제로 선택을 고민하는 장면이나 널리 퍼진 질문에서 시작합니다. 먼저 짧은 답을 주고 근거를 따라가게 씁니다.
- 조사·비교 과정을 성공담으로 꾸미지 않습니다. 빠진 자료, 충돌한 주장, 분류가 애매한 사례와 판단 한계를 자연스럽게 연결합니다.
- 표와 체크리스트는 비교하거나 다시 실행할 때만 사용합니다. 본문 전체를 PPT 카드처럼 잘게 쪼개지 않습니다.
- `개요`, `현황`, `분석`, `결론`, `시사점` 같은 보고서형 한 단어 소제목과 `이번 글에서는`, `살펴보겠습니다`, `다음과 같습니다`, `도움이 되길 바랍니다` 같은 상투 문구를 금지합니다.
- `독자에게 미치는 영향`, `사용자에게 미치는 영향`, `우리에게 미치는 영향`, `왜 중요한가`, `독자가 얻는 것` 같은 편집용 소제목도 금지합니다. 불편했던 장면, 실행 결과, 실패 원인을 서로 붙여 보여 주면 유용성은 따로 설명하지 않아도 드러납니다.
- 실제 검증 기록이 있을 때는 `테스트에서`, `실행 결과`처럼 증거에 붙여 서술합니다. 사용자 개인 경험으로 꾸며낸 1인칭 문장은 쓰지 않습니다.

## 많이 보여 주되 사실만 보여 주는 시각물

대표 이미지 1장과 본문 시각물 3~6개를 기본으로 합니다. 장수를 채우는 장식 이미지는 만들지 않습니다. 각 시각물은 본문의 특정 질문 하나를 답해야 합니다.

생성 전에 대표 브리프를 `visual.cover`, 본문 브리프를 `visual.assets`에 기록합니다. 대표는 `content_role: hook`, 본문은 `content_role: explanation`을 사용합니다. 모든 `label`은 서로 다른 질문이어야 하며 대표에서 보여 준 문제·결과를 본문 이미지가 같은 구도로 반복하면 실패로 처리합니다.

우선순위는 다음과 같습니다.

1. 핵심 근거가 있는 공식 문서·GitHub 화면의 주석 캡처
2. 실제 수집·측정값으로 만든 분류표·비교 차트
3. 코드와 결과를 연결하는 주석 이미지
4. 구성 요소·데이터 이동·선택 갈림길을 설명하는 한국어 도식

실제 화면은 실행한 환경에서 직접 캡처하고 계정·경로·토큰·개인정보를 가립니다. 화면이나 터미널 결과를 이미지 생성으로 꾸며내지 않습니다. 본문에는 실제 캡처 또는 주석 캡처를 최소 1장, Codex 이미지 생성으로 만든 기사 고유 설명 이미지를 최소 1장 넣습니다. 대표 이미지 `images.cover`는 반드시 `imagegen`으로 만들고 기사 고유 상황·대상·결과를 보여 줍니다. 캡처·주석 캡처·실측 차트를 대표 이미지로 표시하지 않습니다. 이미지 생성은 개념 흐름도·구조도·대표 일러스트에만 사용합니다. 제품 로고만 크게 둔 그림, 포괄적인 컴퓨터·개발자 책상, AI 로봇·빛나는 뇌, 가짜 대시보드, 근거 없는 차트는 금지합니다. 단순 방패·DB 원통·상승 막대처럼 캡션과 관계없이 재사용할 수 있는 추상 도형도 금지합니다.

생성 전 프롬프트는 `용도 → 실제 대상 → 구도 → 시각 스타일 → 색·조명 → 필수 물체 → 짧은 한국어 → 금지 요소` 순으로 작성합니다. 실제 버튼, 폴더, 메일, 문서, 전후 결과처럼 그 글만의 물체와 관계를 화면 중심 45~70%에 둡니다. 생성 직후 1초 안에 주제가 읽히는지, 캡션의 원인·결과와 같은 장면인지, 한국어가 정확한지, 모바일에서 핵심이 보이는지 확인하고 하나라도 실패하면 해당 이미지만 다시 생성합니다.

대표 이미지의 한국어 라벨은 없거나 1~3개만 사용하고, 제목과 실행 순서를 이미지 안에 다시 써 넣지 않습니다. 실제 순서·수치·복구 경로는 본문 시각물에서 2~6개의 짧은 라벨로 설명합니다.

2026-07-29 이후 대표 브리프와 `images.cover`에는 `cover_kind: editorial_scene`과 같은 `art_direction`, `composition_type`, `palette_family`을 기록합니다. 2026-08-04 이후 두 곳에 `render_family`도 기록하며 `photorealistic_natural`, `editorial_collage`, `flat_illustration`, `ink_drawing`, `isometric_model`, `tactile_paper`, `macro_object` 중 최근 3개 글에서 쓰지 않은 표현 방식을 고릅니다. 대표 프롬프트는 장면 성격에 맞게 `Use case: illustration-story`, `Use case: photorealistic-natural`, `Use case: stylized-concept` 중 하나로 시작하고 `Asset intent: editorial-scene`을 포함하며 최근 7개 대표와 세 값이 모두 같은 조합을 반복하지 않습니다. 대표는 문서·저장소·도구·판단 갈림길 중 하나를 실제 행동이 보이는 한 장면의 초점으로 삼습니다. 대표 이미지에는 단계 화살표·여러 카드·표·차트·로드맵·흐름도를 넣지 않습니다. 본문 도식은 원리와 비교를 맡습니다. 고정 아이보리 배경·네이비/청록/주황·3단 카드 구성을 기본값으로 쓰지 않으며 `three_column_cards`, `four_step_cards`, `centered_dashboard_grid`, `title_slide`, `linear_flow`, `process_diagram`, `roadmap`, `comparison_grid`, `timeline_cards`, `split_panel_infographic`, `dashboard`는 대표 이미지에서 금지합니다.

2026-08-26 이후 `visual.cover`와 `images.cover`에 같은 `editorial_treatment`, `focal_subject`, `texture_cue`, `authenticity_cue`를 기록합니다. `editorial_treatment`는 `tactile_realism`, `documentary_closeup`, `quiet_minimalism`, `playful_surrealism`, `local_workplace` 중 실제 문서·도구·조사 흔적을 가장 잘 보여 주는 하나를 선택합니다. `images.cover.alt`는 15~160자로 `primary_query`나 `focal_subject`의 구체적 대상과 결과를 설명하고, `cover.webp`·`image-1.webp`처럼 의미 없는 파일명은 쓰지 않습니다. 유행하는 질감과 콜라주는 실제 내용을 선명하게 할 때만 사용하고, 근거를 대체하지 않습니다.

2026-08-28 이후 `editorial.article_shape`은 `ecosystem_map`, `official_document_guide`, `evidence_based_list`, `developer_career_analysis`, `research_interpretation`, `decision_guide`, `hands_on_test`, `troubleshooting` 중 질문과 증거에 맞는 값을 사용합니다. 직전 글과 같은 전개는 금지합니다. `editorial.revisit`에 `quick_answer`, `reuse_case`, `failure_case`, `artifact_type`, `update_triggers` 2~4개를 기록하되, 이는 편집용 내부 메타데이터일 뿐 본문에 그대로 옮기거나 `다시 찾을 때` 같은 상자로 출력하지 않습니다. `artifact_type`은 `source_map`, `evaluation_matrix`, `skill_map`, `reading_guide`, `command_recipe`, `configuration`, `checklist`, `troubleshooting_tree` 중 하나입니다. 실제로 다시 참고할 `table`, `ul`, 필요할 때의 `code` 블록 하나에 `reusable: true`와 `reuse_label`을 내부 메타데이터로 넣습니다.

`editorial.original_value`에 `durable_question`, `source_gap`, `contribution`, `proof_method`, `reader_outcome`, `limits`를 기록합니다. 기본 `proof_method`는 `source_research`이며 직접 측정 비교는 `measured_comparison`, 안전하게 실행한 실습은 `executed_test`를 사용합니다. `contribution`에는 여러 출처를 엮어 새로 만든 분류·비교·판단 기준 또는 실제 입력·실패·복구 결과를 적습니다.

`editorial.action`은 `closing` 뒤에 이어지는 자연스러운 마지막 문장으로 작성합니다. `직접 확인해보려면` 같은 고정 제목이나 별도 행동 유도 상자는 사용하지 않습니다.

`visual.assets`마다 `label`, `scene_label`, `steps`, `curiosity_hook`, `evidence_type`, `origin`을 기록합니다. `origin`은 실제 캡처 `capture`, 주석 캡처 `annotated_capture`, 실측 차트 `measured_chart`, Codex 생성 `imagegen` 중 하나입니다. `imagegen`에는 실제 `generation_prompt`, `generation_model`, 모바일에서도 읽히는 짧은 `korean_labels` 2~6개를 기록합니다. 브리프와 대응 `images.visual_N`의 프롬프트·모델 값은 정확히 일치해야 합니다. `images.cover`와 각 `images.visual_N`에도 같은 `origin`을 기록해 브리프와 파일 출처가 일치해야 합니다. 생성 도식에는 짧은 한국어 설명을 넣고, 한글 파일명과 독자가 봐야 할 결과를 적은 HTML 캡션을 사용합니다.

`capture`와 `annotated_capture`에는 브리프와 이미지 양쪽에 같은 `capture_tool`, `capture_target`, `captured_at`을 기록합니다. `capture_tool`은 `browser`, `computer-use`, `playwright`, `system-screenshot`, `terminal` 중 실제 사용한 도구만 쓰고, `captured_at`은 타임존이 있는 ISO 시각으로 예약 시각 14일 이내에서 기록합니다. 최적화기가 실제 WebP 파일과 같은 `capture_sha256`을 이미지에 기록하며, 이 해시는 기록과 파일의 일치를 검증할 뿐 캡처 사실 자체를 대신하지 않습니다. 실제 화면인지는 실행 과정·출력·전후 상태와 함께 교차 확인합니다.

`measured_chart`는 브리프에 `measurement_source`, `unit`, `sample_count`, `measurement_environment`, 2~20개의 `data_points`(`label`, 유한한 숫자 `value`)를 넣습니다. `measurement_sha256`은 최적화기가 이 다섯 필드 전체를 UTF-8 compact JSON(키만 정렬, 배열 순서 유지)으로 직렬화해 자동 기록합니다. NaN·무한대·중복 라벨은 허용하지 않습니다. 금요일 글에서 사용한 실측 차트는 `verification`의 `measurement_files`에 이미지 키를 넣고 `measurement_note`에 측정 방법·횟수·제외 조건을 적습니다. 이 필드가 없으면 차트로 발행하지 않습니다.

각 브리프와 대응 이미지의 `qa`에 `topic_match`, `caption_match`, `mobile_readable`, `text_reviewed`, `not_generic`을 모두 `true`로 기록합니다. 최적화 후에는 실제 WebP 디코딩 결과와 메타데이터의 크기·용량·`sha256`을 비교합니다. 직접 캡처를 지정하고 실제 캡처 파일이 없거나, 생성 이미지를 캡처로 표시하면 발행을 막습니다.

모든 이미지는 최종적으로 `1200×630 WebP`, 장당 최대 256KB, 전체 최대 2MB의 `webp-v1`을 지킵니다. Codex 이미지 생성이 실패하면 결정적 대체 생성기는 작업 상태 확인용으로만 사용할 수 있습니다. 결정적 대체 이미지는 발행 준비를 통과하지 않으며, 이미지 생성을 다시 시도하거나 실제 캡처로 교체해야 합니다.

## 저장 형식

`schema_version: 3`, `format: lead-story-v1`을 재사용하며 다음 식별 필드는 필수입니다.

```json
{
  "draft_id": "YYYY-MM-DD-automation",
  "publish_date": "YYYY-MM-DD",
  "content_type": "automation_case",
  "content_label": "개발·AI 인사이트",
  "category": "AI·개발 도구",
  "publication_mode": "manual_review",
  "scheduled_at": "YYYY-MM-DDT09:00:00+09:00"
}
```

`scheduled_at`은 Codex 제작 시작 기준이며 티스토리 예약 발행 시각이 아닙니다. 도우미가 1차 검수 완료 상태가 된 뒤 사용자가 티스토리에서 직접 발행합니다.

`editorial.weekly_lane`은 `developer_insight`로 기록합니다. `editorial.reader_hook`에는 독자가 궁금해할 구체적인 장면 `scene`, 잘못 판단할 때의 `stakes`, 독자가 가져갈 지도·비교·기준 `payoff`, 근거로 답할 `open_question`을 각각 20~180자로 기록하고 실제 도입에 이어지게 합니다.

`editorial.reader_walkthrough`는 `hands_on_test`와 `troubleshooting`에서만 사용합니다. 이때 `reader_level`, `prerequisites`, `steps`, `success_check`, `recovery`, `easiest_method_considered`, `code_needed_when`을 기록하고 첫 코드보다 앞에 준비물 목록을 둡니다. 20줄을 넘는 전체 코드 블록은 접습니다. 연구·지도형은 이를 억지로 만들지 않고 마지막에 `근거와 한계`를 둡니다.

티스토리에서는 `실전 IT > AI·개발 도구`를 선택합니다. `실전 IT`에는 글을 직접 넣지 않습니다.

그 밖에 `date_label`, `weekday`, `primary_query`, `tags`, `visual`, `editorial`, `news` 정확히 1건, `related_posts` 2건 이상, `generation`, `images`를 사용합니다. `editorial.reader_hook`에는 `scene`, `stakes`, `payoff`, `open_question`을, `editorial.search_intent`에는 `query`, `reader_need`, `answer_format`을, `editorial.original_value`에는 `durable_question`, `source_gap`, `contribution`, `proof_method`, `reader_outcome`, `limits`를 기록합니다. `related_posts`는 `config/tistory_public_posts.json`에 등록된 실제 공개 URL만 사용하고 각 항목에 `title`, `url`, 현재 글과 연결되는 `reason`, `role`을 기록합니다. `role`은 `foundation`과 `next_step`을 각각 1개 이상 포함합니다. `news[0].content`에는 `h`, `p`, `table`, `visual`, 필요할 때의 `code`, `ul`, `quote`, `ad_break`를 배치합니다. `news` 이름은 기존 렌더러 호환용이며 내용은 뉴스 요약이 아니라 개발·AI 인사이트 한 편입니다.

`publish_date`는 금요일이어야 하며 `date_label`과 `weekday`는 그 날짜에서 계산한 값과 정확히 일치해야 합니다. 2026-08-28부터의 금요일 개발·AI 인사이트와 그 이전 토요일 자동화 발행본은 각 시대의 규칙으로 계속 유효합니다. 내부 파일명·초안 ID·`content_type`은 기존 렌더러와 이력을 깨지 않기 위해 유지합니다. `generation.provider`는 `codex-agent`, `generation.model`은 실제 사용한 Codex 모델 ID, `generation.revision`은 7 이상을 기록합니다. `generation.image_provider`는 `mixed`로 기록합니다.

`verification`은 출처 추적과 실행 여부를 구분하는 증거 계약입니다. 모든 글에 `mode`, `checked_at`, `scope`, `method`, `selection_rule`, `limitations`, `source_urls` 3개 이상, 정확한 `source_count`, `evidence_files`, `problem_lane`, `tool_brand`를 기록합니다. `mode`는 `source_research`, `measured_analysis`, `executed` 중 하나입니다. `evidence_files`는 공식 문서·저장소에 주석을 단 `annotated_capture` 또는 실제 값으로 만든 `measured_chart`를 최소 1개 가리킵니다. `measured_analysis`는 `measurement_files`, `measurement_note`가 필요합니다. `executed`일 때만 `environment`, `commands`, `input_fixture`, `expected`, `actual`, `failure`, `rollback`, `started_at`, `completed_at`, `command_exit_code`, `stdout_excerpt`를 추가합니다.

`news[0].url`에는 후보함에서 최종 선택한 저장소·릴리스·공식 가이드의 URL을 기록합니다.

## 생성·검수·배포

이미지 생성 전에 최근 중복을 확인합니다.

```bash
python3 -m blog_pipeline.publishing.saturday_guard --today --check-duplicates
```

이미지와 원본을 완성한 뒤 다음 명령을 각각 한 번 실행합니다.

```bash
python3 -m blog_pipeline.publishing.optimize_images --draft-id YYYY-MM-DD-automation
python3 -m blog_pipeline.publishing.export_tistory --draft-id YYYY-MM-DD-automation
python3 -m blog_pipeline.publishing.build_copy_page
python3 -m blog_pipeline.publishing.build_integration_page
python3 -m unittest discover -s tests
python3 -m blog_pipeline.publishing.saturday_guard --today --require-complete
python3 -m blog_pipeline.publishing.publish_bundle --draft-id YYYY-MM-DD-automation --stage
python3 -m blog_pipeline.publishing.publish_bundle --draft-id YYYY-MM-DD-automation --check
git diff --cached --check
```

데스크톱과 모바일 미리보기에서 실제 캡처 글자, 한국어 도식, 표·코드 가로 스크롤, 광고 위치, 이미지 캡션을 확인합니다. GitHub Pages 루트에서 당일 `개발·AI 인사이트` 카드의 제목·카테고리·태그·대표 이미지·광고 조립·미리보기·최종 HTML이 연결돼야 합니다. 같은 날 다른 카드의 존재 여부는 완료 조건으로 삼지 않습니다.

실제 분기가 없고 `publish_bundle`이 `READY`이며 staged diff가 있을 때 하나의 로컬 커밋으로 확정합니다. 공통 계약의 `python3 -m blog_pipeline.publishing.repository_sync push --remote origin --ref main`이 일시적 네트워크 최대 3회 재시도 뒤에도 실패하면 `LOCAL_COMPLETE`, push 성공 뒤 API 확인만 실패하면 `REMOTE_PUSHED_VERIFY_PENDING`으로 보고합니다. 해당 커밋의 `Publish reviewed drafts` 성공과 공개 루트의 당일 개발·AI 인사이트 카드 연결까지 확인된 경우만 `COMPLETE`입니다. 티스토리에는 자동 발행하지 않습니다.

## 발행 전 체크

- 제목만 보고 개발자가 답을 궁금해할 구체적인 질문인가
- 공식·원출처를 포함한 서로 다른 출처 3개 이상을 실제로 확인했는가
- 원문 요약을 넘어 지도·비교표·평가 기준·읽기 순서 중 하나를 새로 제공하는가
- 제목과 본문의 모든 수치가 실제 수집·측정 근거와 일치하는가
- 조사 범위·선택 규칙·빠진 범위·업데이트 조건이 드러나는가
- 직접 실행형이라면 같은 버전·명령·입력으로 재현할 수 있고 기대 결과와 실제 결과, 실패와 복구가 있는가
- 실제 화면·로그는 직접 캡처했고 가짜 UI나 생성 로그가 없는가
- 표·차트 수치는 직접 측정했으며 환경·단위·횟수가 적혀 있는가
- 대표 1장과 본문 시각물 3~6개가 서로 다른 질문을 설명하는가
- 실제 캡처와 `imagegen` 설명 이미지가 각각 최소 1장 있고 모든 `origin`이 실제 제작 방식과 일치하는가
- 캡션을 가려도 이미지의 실제 물체·전후 상태만으로 본문 질문을 설명하는가
- 이미지의 한국어 글자와 HTML 캡션이 모바일에서 읽히는가
- 광고가 정확히 1개이고 전체 35~45% 위치에서 `완결 블록 → 광고 → 다음 소제목` 순서인가
- `editorial.revisit`가 별도 내부 메모 상자로 노출되지 않고 본문에 자연스럽게 반영됐는가
- `editorial.original_value`의 새 기여가 출처·분류·실행·측정 증거와 일치하는가
- 뉴스글 원본·이미지·HTML을 덮어쓰지 않았는가
- 최종 `saturday_guard`가 `COMPLETE`인가
- 최종 `publish_bundle`이 `READY`이고 Pages 배포가 성공했는가
