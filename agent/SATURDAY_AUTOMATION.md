# 쑥쑥자라나라 금요일 실전 개발·자동화 편집 계약

이 문서는 매주 금요일 09:00 KST에 실행되는 Codex 작업의 유일한 계약입니다. 예약 실행은 한 번만 수행하며 자동 재실행 슬롯을 두지 않습니다. 월·수 09:00 실행되는 실전 IT 아티클 작업과 원본·이미지·HTML·가드를 완전히 분리합니다. 품질 기준을 통과할 때만 `executed_experiment` 역할로 독자가 실제로 따라 할 수 있는 자동화 실험기, 사용법, 공개 도구 적용 사례, 개발·AI 실전 검증 글을 작성하며 발행 횟수를 채우기 위한 실험은 하지 않습니다. Codex가 원고·이미지·검증·도우미까지 1차 완료하고, 티스토리 붙여넣기와 발행은 사용자가 최종 확인 뒤 직접 합니다.

사용자가 현재 대화에서 당일 추가 발행을 명시한 경우에만 `publication_mode: "manual_extra"`를 사용할 수 있습니다. 이때 `manual_extra_reason`에 요청 근거를 남기고 `scheduled_at`은 같은 날짜의 KST 실행 시각으로 기록합니다. 수집기·정기 워크플로는 이 값을 만들지 않으며, 별도 요청이 없는 비금요일 실행은 계속 건너뜁니다.

## 시작 조건과 단일 실행

1. `agent/REPOSITORY_SYNC.md`를 먼저 읽고 공통 동기화 계약을 적용한 뒤 자동화 글 자체의 당일 상태를 확인합니다. 다른 예약 글의 누락과 관계없이 이 자동화 글을 독립적으로 진행합니다.

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
   - `COMPLETE`: 같은 날짜 자동화글을 다시 조사·집필·생성하지 않고 종료합니다.
   - `PARTIAL`: 출력된 `reasons`에 해당하는 단계만 복구합니다.
   - `NEW`: 아래 흐름을 정확히 한 번 수행합니다.

3. `docs/automation-inbox/latest.json`을 먼저 읽습니다.

   - `day`가 당일 날짜와 다르면 오래된 후보를 사용하지 않고 GitHub Trending·공식 릴리스·공식 변경 내역·요즘IT 개발 실전 글을 직접 검색합니다.
   - `selected`의 임시 점수는 제목·요약 메타데이터로 계산한 우선순위이며 검증 완료의 증거가 아닙니다.
   - 후보함이 없거나 비어 있거나 수집 오류가 크면 공식 출처를 직접 검색해 같은 선정 기준으로 대체 후보를 만듭니다.
   - 선택한 한 건의 저장소·공식 문서·최신 버전과 권한 요구를 다시 확인한 뒤에만 실행 단계로 이동합니다.
   - 현재 후보가 모두 75점 미만·중복·실행 불가이면 `python3 -m blog_pipeline.collection.collect_automation --today`를 같은 실행에서 딱 한 번 다시 실행하고 새 추천·후보를 평가합니다.
   - 재수집 뒤에도 없으면 Codex 웹 리서치로 공식 저장소·공식 가이드·GitHub Trending·독립 실전 자료에서 후보함에 없던 반복 문제를 최대 10건까지 찾습니다. 같은 도구나 제목을 바꿔 채우지 않습니다.

4. 결과는 뉴스글과 분리해 저장합니다.

   - 원본: `data/automation_cases/YYYY-MM-DD.json`
   - 초안 ID: `YYYY-MM-DD-automation`
   - 이미지: `docs/tistory/assets/YYYY-MM-DD-automation/`
   - HTML·메타·광고본: `docs/tistory/YYYY-MM-DD-automation*`
   - 미리보기: `docs/preview/YYYY-MM-DD-automation.html`

같은 날짜의 `data/days/YYYY-MM-DD.json`과 뉴스 이미지·HTML은 읽기 참고 외에는 수정하지 않습니다.

## 글감과 실제 검증

다음 다섯 형식 중 하나만 선택합니다.

- 직접 실행 실험기: 반복 작업을 수동으로 해 본 뒤 자동화하고 전후 차이를 확인
- 따라하기: 독자가 작은 예제를 그대로 재현할 수 있는 단계별 사용법
- 공개 도구 적용 사례: 유명한 GitHub 저장소·공식 도구를 실제 작은 작업에 적용
- 개발·AI 실전 검증: 흥미로운 개념 글을 작은 오류·복구·전후 비교 실험으로 바꾸고 공식 문서와 실제 결과로 검증
- 도구·워크플로 비교 실험: 성격이 다른 2~3개 도구나 에이전트 스킬에 같은 작은 과제를 주고 중간 행동·결과·실패·사람 승인 지점을 같은 기준으로 비교

글감은 `검색 지속성 20 · 실제 문제 해결성 25 · 재현 가능성 20 · 시각 설명 가능성 15 · 대중 공감도 20`으로 비교합니다. 총점 75점 이상이면서 `직접 실행 가능한 작은 실험`, `재현 가능한 증거`, `독자가 가져갈 산출물`, `최근 90일 비중복`을 모두 충족한 주제만 진행합니다. 대중 공감도가 최소 기준에 못 미치면 총점이 높아도 추천하지 않습니다. 기존 후보 평가, 1회 재수집, Codex 직접 리서치를 모두 마친 뒤에도 기준을 통과한 주제가 없을 때만 오류가 아닌 `NO_PUBLISH_QUALITY`로 종료하고, 검토한 후보·점수·탈락 이유·확장 리서치 범위만 보고하며 원고·이미지·커밋·푸시를 만들지 않습니다. 최근 90일 중 발행 준비까지 완료된 자동화글의 URL·저장소·`primary_query` 지문과 겹치면 다른 주제를 고릅니다. 미완성 초안은 중복 이력으로 세지 않습니다. 뉴스 요약을 두 번째로 만들지 않습니다.

도구명을 지워도 비개발자가 자신의 문제를 떠올릴 수 있는 주제만 선택합니다. 우선 분야는 `이메일·문서·PDF·표·일정·파일` 정리, 반복 입력, 웹페이지 변경 알림, 보고서 생성, 사진·다운로드 폴더 정리와 `바이브 코딩·AI 글쓰기·Git·오픈소스 도구`의 실제 활용입니다. 프레임워크 버전, locator, 패키지 설치, 릴리스 자체는 주제가 될 수 없습니다. 익숙한 문제를 해결하는 과정에서 필요한 도구로만 설명합니다. 파일·문서 → 웹 변경 감지 → 보고서·표 → 생활·사무 노코드 자동화 → 개발·AI 실전 순으로 주제를 바꾸며 같은 도구·브랜드를 연속 사용하지 않습니다.

글감을 고를 때 `코드를 이해해야만 효용을 얻는가`를 먼저 묻습니다. 비개발자가 준비물과 실행 순서를 그대로 따라 결과를 얻을 수 없거나, 복사 가능한 완성 설정·스크립트·템플릿을 제공할 수 없는 주제는 금요일 글로 선택하지 않습니다. 개발자만 재현할 수 있는 패키지 내부 구조·API 검증·벤치마크는 별도 개발 기록의 소재일 뿐 글의 중심이 될 수 없습니다.

코드를 쓰기 전에 같은 문제를 운영체제 기본 기능이나 설치 없는 방법으로 해결할 수 있는지 확인합니다. 그다음 계정 없이 로컬에서 쓰는 화면 도구를 비교하고, 같은 규칙이 정기적으로 반복되어 코드 준비 비용보다 수동 작업 비용이 커질 때만 자동화를 고급 선택지로 제시합니다. 민감한 업무 파일은 업로드 범위와 보관 정책을 확인할 수 없는 온라인 변환 사이트를 기본 방법으로 추천하지 않습니다. 더 쉬운 안전한 방법이 있으면 제목·도입·첫 실행 순서에 그 방법을 먼저 놓고, 자동화 코드는 반복 작업이 필요한 독자에게만 이어서 제공합니다.

실험 결과가 `pocket-desk-os` 같은 실제 프로젝트의 기능·운영·복구와 연결되면 관련 개발일지를 우선 연결합니다. 프로젝트 이름만 빌린 홍보 글은 만들지 않고, 독자가 재사용할 수 있는 명령·설정·실패 복구 중 하나가 있을 때만 프로젝트 사례로 다룹니다.

요즘IT 같은 매체 글은 독자가 궁금해할 질문을 찾는 보조 출처로만 사용합니다. 원문의 문장·목차·표·이미지를 옮기거나 순서만 바꿔 재서술하지 않습니다. 최종 글은 공식 저장소·공식 문서·직접 실행 결과를 중심으로 새로 구성합니다. 다른 글에 나온 수치나 설문 결과는 출처를 명시해 인용할 때만 사용하며, 직접 측정한 결과처럼 쓰지 않습니다. 가능하면 같은 질문을 작은 공개 예제에서 직접 측정해 표본·환경·횟수와 함께 제시합니다.

인기 순위·Top N·추천 글을 발견하면 그 순서를 글의 결론으로 가져오지 않습니다. GitHub 스타·버전·최근 활동·라이선스는 작업 시점에 공식 API와 저장소로 다시 확인하고, 인기도를 품질·안전성·내 작업 적합성으로 바꿔 말하지 않습니다. 실험에서는 같은 입력·종료 조건·검사 명령을 쓰고 `계획 전 질문`, `변경 범위`, `검증`, `사람 승인`, `복구` 중 주제에 맞는 3~5개를 사전에 평가 기준으로 고정합니다. 추천은 종합 1등 하나가 아니라 `어떤 상황에 맞는지`를 설명합니다.

후보 수집기는 공개 메타데이터를 모아 우선순위만 계산합니다. 저장소를 복제하거나 설치 명령을 실행하지 않고 글·이미지·티스토리 HTML도 만들지 않습니다. 실제 검증과 집필은 이 09:00 작업에서 선택한 한 건에만 수행합니다.

실행 전 README, 설치 명령, 의존성, 권한 요구를 읽습니다. 별도 임시 디렉터리와 테스트 데이터만 사용하며 비밀키·개인 계정·운영 서비스·`sudo`·알 수 없는 바이너리·의심스러운 설치 스크립트·과도한 권한이 필요한 작업은 실행하지 않습니다. 안전하게 실행할 수 없으면 `구조 분석`으로 명시하고 실행·검증·벤치마크했다고 쓰지 않습니다.

실제 실행에는 다음 기록이 있어야 합니다.

- 운영체제, 런타임, 도구 버전과 공개 저장소의 태그·커밋
- 입력 데이터와 실행 명령 또는 설정
- 실행 전 예상 결과
- 실제 출력·로그·생성 파일
- 실패한 시도와 바꾼 조건
- 적용 범위, 비용·보안·권한·복구 한계

검증한 버전·커밋·환경·기대 결과·실제 결과는 `verification`에 빠짐없이 기록합니다. 본문에는 독자가 실행하는 데 필요한 버전과 결과만 먼저 보여 주고, 커밋 해시·종료 코드·파일 해시·fixture 생성 실패 같은 개발 증거는 마지막 `개발 기록`에서 짧게 요약합니다. 측정하지 않은 숫자는 만들지 않습니다. 측정했다면 표본, 횟수, 단위, 환경을 함께 기록합니다.

## 글 구성

검색형 제목은 완성한 작업이나 해결한 문제를 제목 앞부분에 놓고 핵심 검색어를 자연스럽게 붙이며 도구명은 뒤에 둡니다. 효용을 설명하는 대신 실제 자동화 대상과 결과를 말합니다. 예: `메일 첨부파일을 날짜별 폴더로 자동 정리하기: n8n 실험`. `충격`, `역대급`, `무조건` 같은 클릭베이트는 쓰지 않습니다. 태그 5~8개는 `자동화 대상`, `반복 문제`, `사용 도구`, `완성 결과`를 섞고 최소 2개를 `primary_query`와 직접 연결합니다. 전체는 약 10~15분 분량, 소제목 5~8개로 작성합니다.

30일 이내의 `config/search_opportunities.json`을 확인하되, 실제 실험이 그 질문을 해결할 때만 사용합니다. `editorial.search_intent`에는 짧은 실제 검색어 `query`, 자동화하려는 구체적 반복 문제 `reader_need`, 실행 화면·코드·비교 중 답을 증명할 방식 `answer_format`을 기록합니다. `query`는 제목 앞 20자 안에 그대로 자연스럽게 둡니다. `related_posts`는 기반 원리를 설명하는 `foundation`과 다음 실행으로 이어지는 `next_step`을 각각 1개 이상 사용합니다.

일반 독자가 따라 하는 글의 기본 흐름은 다음과 같습니다.

`반복되는 문제와 완성 결과 → 이 방법이 맞는 사람 → 준비물 → 번호를 붙인 실행 단계 → 성공 확인 → 실패 복구 → 수동 방식과 비교 → 적용 전 주의사항 → 개발 기록`

비교 실험은 위 흐름을 억지로 따르지 않고 `우리가 막힌 한 장면 → 왜 이 후보들을 골랐는지 → 같은 과제·같은 평가 기준 → 각 후보가 다르게 행동한 순간 → 결과와 실패 비교 → 상황별 선택`으로 쓸 수 있습니다. 후보별 기능 목록을 동일한 길이로 반복하지 말고, 선택을 바꾸는 차이만 본문에 남깁니다.

- 첫 5문장 안에 실제 반복 작업과 자동화 후 확인할 결과를 보여 줍니다.
- 첫 코드보다 앞에 준비물 목록을 둡니다. 코드가 있다면 `그대로 전체 복사`, 저장할 파일명, 실행 위치, Windows·macOS처럼 달라지는 명령을 함께 설명합니다.
- 20줄을 넘는 전체 코드는 기본으로 접어 두고 `반복 작업용 전체 코드 보기`처럼 용도를 적습니다. 본문에는 선택 기준, 짧은 실행 명령, 예상 결과를 먼저 보여 주며 긴 코드가 화면 대부분을 차지하게 만들지 않습니다.
- 단계는 설치·입력 준비·실행·성공 확인이 끊기지 않게 이어져야 합니다. 일부 함수만 보여 주거나 핵심 예외 처리를 생략한 예제는 재사용 산출물로 인정하지 않습니다.
- 성공 여부를 독자가 눈으로 확인할 파일·화면·개수 중 하나로 설명하고, 실패 시 원본이 남는지와 다시 시작할 위치를 바로 뒤에 적습니다.
- 커밋 해시·SHA-256·종료 코드·테스트용 글꼴 오류 같은 검증 세부값을 실행 단계 앞에 두지 않습니다. 필요한 값은 마지막 `개발 기록`에 모읍니다.
- 구현 순서가 실제 실행 순서일 때만 소제목에 번호를 붙입니다. 문제·실패·결과를 설명하는 장은 질문형·장면형 제목으로 연결합니다.
- 설치·버전·코드보다 수동 작업의 불편, 완성 화면, 줄어든 단계처럼 일반 독자가 먼저 이해할 장면을 앞에 둡니다.
- 복사 가능한 최소 코드·설정을 넣고 버전과 실행 위치를 명시합니다.
- 비교가 쉬워질 때 HTML 표 1~3개를 사용합니다.
- 광고는 정확히 1개, 첫 완결된 구현 섹션 뒤 전체 비광고 블록의 35~45% 위치에 `ad_break`로 둡니다. 블록 순서는 반드시 `완결 문단·표·목록·코드·인용 → ad_break → 다음 h`여야 하며 소제목과 첫 설명 사이에는 넣지 않습니다.
- 블로그 관련 글은 같은 문제의 기준을 설명한 가이드 1개와 이전 실험·프로젝트 글 1개를 우선하되, 연결이 억지스러우면 개수를 채우지 않습니다. 공식 문서·저장소·보조 자료는 3~6개를 연결합니다.
- `정리해보겠습니다`, `자동화로 작성했습니다`, 과장된 성공담, 하지 않은 체험 표현을 쓰지 않습니다.

## 자연스러운 실험기 문체

- 기능 목록으로 시작하지 않고 반복해서 불편했던 장면이나 실제 실패 화면에서 시작합니다. 독자가 결과를 먼저 보고, 왜 그렇게 됐는지 따라오게 씁니다.
- 실험 과정은 성공담으로 매끈하게 꾸미지 않습니다. 실패한 입력, 바꾼 조건, 다시 실행한 결과를 시간 순서로 자연스럽게 연결합니다.
- 표와 체크리스트는 비교하거나 다시 실행할 때만 사용합니다. 본문 전체를 PPT 카드처럼 잘게 쪼개지 않습니다.
- `개요`, `현황`, `분석`, `결론`, `시사점` 같은 보고서형 한 단어 소제목과 `이번 글에서는`, `살펴보겠습니다`, `다음과 같습니다`, `도움이 되길 바랍니다` 같은 상투 문구를 금지합니다.
- `독자에게 미치는 영향`, `사용자에게 미치는 영향`, `우리에게 미치는 영향`, `왜 중요한가`, `독자가 얻는 것` 같은 편집용 소제목도 금지합니다. 불편했던 장면, 실행 결과, 실패 원인을 서로 붙여 보여 주면 유용성은 따로 설명하지 않아도 드러납니다.
- 실제 검증 기록이 있을 때는 `테스트에서`, `실행 결과`처럼 증거에 붙여 서술합니다. 사용자 개인 경험으로 꾸며낸 1인칭 문장은 쓰지 않습니다.

## 많이 보여 주되 사실만 보여 주는 시각물

대표 이미지 1장과 본문 시각물 3~6개를 기본으로 합니다. 장수를 채우는 장식 이미지는 만들지 않습니다. 각 시각물은 본문의 특정 질문 하나를 답해야 합니다.

생성 전에 대표 브리프를 `visual.cover`, 본문 브리프를 `visual.assets`에 기록합니다. 대표는 `content_role: hook`, 본문은 `content_role: explanation`을 사용합니다. 모든 `label`은 서로 다른 질문이어야 하며 대표에서 보여 준 문제·결과를 본문 이미지가 같은 구도로 반복하면 실패로 처리합니다.

우선순위는 다음과 같습니다.

1. 실제 실행 화면·설정 화면·터미널 로그·생성 결과 캡처
2. 실제 측정값으로 만든 전후 표·차트
3. 코드와 결과를 연결하는 주석 이미지
4. 구성 요소·데이터 이동·분기·복구를 설명하는 한국어 도식

실제 화면은 실행한 환경에서 직접 캡처하고 계정·경로·토큰·개인정보를 가립니다. 화면이나 터미널 결과를 이미지 생성으로 꾸며내지 않습니다. 본문에는 실제 캡처 또는 주석 캡처를 최소 1장, Codex 이미지 생성으로 만든 기사 고유 설명 이미지를 최소 1장 넣습니다. 대표 이미지 `images.cover`는 반드시 `imagegen`으로 만들고 기사 고유 상황·대상·결과를 보여 줍니다. 캡처·주석 캡처·실측 차트를 대표 이미지로 표시하지 않습니다. 이미지 생성은 개념 흐름도·구조도·대표 일러스트에만 사용합니다. 제품 로고만 크게 둔 그림, 포괄적인 컴퓨터·개발자 책상, AI 로봇·빛나는 뇌, 가짜 대시보드, 근거 없는 차트는 금지합니다. 단순 방패·DB 원통·상승 막대처럼 캡션과 관계없이 재사용할 수 있는 추상 도형도 금지합니다.

생성 전 프롬프트는 `용도 → 실제 대상 → 구도 → 시각 스타일 → 색·조명 → 필수 물체 → 짧은 한국어 → 금지 요소` 순으로 작성합니다. 실제 버튼, 폴더, 메일, 문서, 전후 결과처럼 그 글만의 물체와 관계를 화면 중심 45~70%에 둡니다. 생성 직후 1초 안에 주제가 읽히는지, 캡션의 원인·결과와 같은 장면인지, 한국어가 정확한지, 모바일에서 핵심이 보이는지 확인하고 하나라도 실패하면 해당 이미지만 다시 생성합니다.

대표 이미지의 한국어 라벨은 없거나 1~3개만 사용하고, 제목과 실행 순서를 이미지 안에 다시 써 넣지 않습니다. 실제 순서·수치·복구 경로는 본문 시각물에서 2~6개의 짧은 라벨로 설명합니다.

2026-07-29 이후 대표 브리프와 `images.cover`에는 `cover_kind: editorial_scene`과 같은 `art_direction`, `composition_type`, `palette_family`을 기록합니다. 2026-08-04 이후 두 곳에 `render_family`도 기록하며 `photorealistic_natural`, `editorial_collage`, `flat_illustration`, `ink_drawing`, `isometric_model`, `tactile_paper`, `macro_object` 중 최근 3개 글에서 쓰지 않은 표현 방식을 고릅니다. 대표 프롬프트는 장면 성격에 맞게 `Use case: illustration-story`, `Use case: photorealistic-natural`, `Use case: stylized-concept` 중 하나로 시작하고 `Asset intent: editorial-scene`을 포함하며 최근 7개 대표와 세 값이 모두 같은 조합을 반복하지 않습니다. 대표는 실험의 문제·버튼·실패·복구 결과 중 하나를 실제 행동이 보이는 한 장면의 초점으로 삼습니다. 대표 이미지에는 단계 화살표·여러 카드·표·차트·로드맵·흐름도를 넣지 않습니다. 본문 도식은 원리와 실행 순서를 맡습니다. 고정 아이보리 배경·네이비/청록/주황·3단 카드 구성을 기본값으로 쓰지 않으며 `three_column_cards`, `four_step_cards`, `centered_dashboard_grid`, `title_slide`, `linear_flow`, `process_diagram`, `roadmap`, `comparison_grid`, `timeline_cards`, `split_panel_infographic`, `dashboard`는 대표 이미지에서 금지합니다.

2026-08-26 이후 `visual.cover`와 `images.cover`에 같은 `editorial_treatment`, `focal_subject`, `texture_cue`, `authenticity_cue`를 기록합니다. `editorial_treatment`는 `tactile_realism`, `documentary_closeup`, `quiet_minimalism`, `playful_surrealism`, `local_workplace` 중 실험의 실제 물건·작업 흔적·환경을 가장 잘 보여 주는 하나를 선택합니다. `images.cover.alt`는 15~160자로 `primary_query`나 `focal_subject`의 구체적 대상과 결과를 설명하고, `cover.webp`·`image-1.webp`처럼 의미 없는 파일명은 쓰지 않습니다. 유행하는 질감과 콜라주는 실제 내용을 선명하게 할 때만 사용하고, 실행 증거를 대체하지 않습니다.

2026-08-04 이후 `editorial.article_shape`은 `hands_on_test` 또는 `troubleshooting`을 우선하되 주제에 따라 `decision_guide`, `incident_trace`, `research_interpretation`, `change_impact`를 쓸 수 있습니다. 실제 장애나 실패가 여러 단계로 번진 실험은 `incident_trace`로 원인과 파급 경로를 추적합니다. 직전 글과 같은 전개는 금지합니다. `editorial.revisit`에 `quick_answer`, `reuse_case`, `failure_case`, `artifact_type`, `update_triggers` 2~4개를 기록하되, 이는 편집용 내부 메타데이터일 뿐 본문에 그대로 옮기거나 `다시 찾을 때` 같은 상자로 출력하지 않습니다. 핵심 답·실패 조건·재확인 변화는 필요한 문단에 자연스럽게 설명합니다. `artifact_type`은 `command_recipe`, `configuration`, `decision_matrix`, `checklist`, `troubleshooting_tree`, `experiment_fixture` 중 하나입니다. 실제로 다시 실행할 `code`, `table`, `ul` 블록 하나에 `reusable: true`와 `reuse_label`을 내부 메타데이터로 넣되, 별도 제목·상자·배지 없이 일반 본문 요소로 출력합니다. 실험 fixture·완전한 명령·실패 복구 순서 중 하나는 독자가 그대로 재현할 수 있어야 합니다.

`editorial.original_value`에 `durable_question`, `source_gap`, `contribution`, `proof_method`, `reader_outcome`, `limits`를 기록합니다. 이 레인은 실제 실험이므로 `proof_method: executed_test`를 기본으로 하고, 직접 측정 비교가 핵심이면 `measured_comparison`, 장애 파급 경로를 재현했으면 `incident_trace`를 쓸 수 있습니다. `contribution`에는 실제 입력·실패·복구·결과 중 원문에 없던 새 가치를 적습니다.

`editorial.action`은 `closing` 뒤에 이어지는 자연스러운 마지막 문장으로 작성합니다. `직접 확인해보려면` 같은 고정 제목이나 별도 행동 유도 상자는 사용하지 않습니다.

`visual.assets`마다 `label`, `scene_label`, `steps`, `curiosity_hook`, `evidence_type`, `origin`을 기록합니다. `origin`은 실제 캡처 `capture`, 주석 캡처 `annotated_capture`, 실측 차트 `measured_chart`, Codex 생성 `imagegen` 중 하나입니다. `imagegen`에는 실제 `generation_prompt`, `generation_model`, 모바일에서도 읽히는 짧은 `korean_labels` 2~6개를 기록합니다. 브리프와 대응 `images.visual_N`의 프롬프트·모델 값은 정확히 일치해야 합니다. `images.cover`와 각 `images.visual_N`에도 같은 `origin`을 기록해 브리프와 파일 출처가 일치해야 합니다. 생성 도식에는 짧은 한국어 설명을 넣고, 한글 파일명과 독자가 봐야 할 결과를 적은 HTML 캡션을 사용합니다.

`capture`와 `annotated_capture`에는 브리프와 이미지 양쪽에 같은 `capture_tool`, `capture_target`, `captured_at`을 기록합니다. `capture_tool`은 `browser`, `computer-use`, `playwright`, `system-screenshot`, `terminal` 중 실제 사용한 도구만 쓰고, `captured_at`은 타임존이 있는 ISO 시각으로 예약 시각 14일 이내에서 기록합니다. 최적화기가 실제 WebP 파일과 같은 `capture_sha256`을 이미지에 기록하며, 이 해시는 기록과 파일의 일치를 검증할 뿐 캡처 사실 자체를 대신하지 않습니다. 실제 화면인지는 실행 과정·출력·전후 상태와 함께 교차 확인합니다.

`measured_chart`는 브리프에 `measurement_source`, `unit`, `sample_count`, `measurement_environment`, 2~20개의 `data_points`(`label`, 유한한 숫자 `value`)를 넣습니다. `measurement_sha256`은 최적화기가 이 다섯 필드 전체를 UTF-8 compact JSON(키만 정렬, 배열 순서 유지)으로 직렬화해 자동 기록합니다. NaN·무한대·중복 라벨은 허용하지 않습니다. 금요일 실험에서 사용한 실측 차트는 `verification`의 `measurement_files`에 이미지 키를 넣고 `measurement_note`에 측정 방법·횟수·제외 조건을 적습니다. 이 필드가 없으면 차트로 발행하지 않습니다.

각 브리프와 대응 이미지의 `qa`에 `topic_match`, `caption_match`, `mobile_readable`, `text_reviewed`, `not_generic`을 모두 `true`로 기록합니다. 최적화 후에는 실제 WebP 디코딩 결과와 메타데이터의 크기·용량·`sha256`을 비교합니다. 직접 캡처를 지정하고 실제 캡처 파일이 없거나, 생성 이미지를 캡처로 표시하면 발행을 막습니다.

모든 이미지는 최종적으로 `1200×630 WebP`, 장당 최대 256KB, 전체 최대 2MB의 `webp-v1`을 지킵니다. Codex 이미지 생성이 실패하면 결정적 대체 생성기는 작업 상태 확인용으로만 사용할 수 있습니다. 결정적 대체 이미지는 발행 준비를 통과하지 않으며, 이미지 생성을 다시 시도하거나 실제 캡처로 교체해야 합니다.

## 저장 형식

`schema_version: 3`, `format: lead-story-v1`을 재사용하며 다음 식별 필드는 필수입니다.

```json
{
  "draft_id": "YYYY-MM-DD-automation",
  "publish_date": "YYYY-MM-DD",
  "content_type": "automation_case",
  "content_label": "업무자동화 실험",
  "category": "자동화·실험",
  "publication_mode": "manual_review",
  "scheduled_at": "YYYY-MM-DDT09:00:00+09:00"
}
```

`scheduled_at`은 Codex 제작 시작 기준이며 티스토리 예약 발행 시각이 아닙니다. 도우미가 1차 검수 완료 상태가 된 뒤 사용자가 티스토리에서 직접 발행합니다.

`editorial.weekly_lane`은 `executed_experiment`로, `editorial.article_shape`은 `hands_on_test`, `troubleshooting`, `incident_trace` 중 실제 실험 흐름과 맞는 값으로 기록합니다. `editorial.reader_hook`에는 구체적인 작업 장면 `scene`, 자동화하지 않거나 잘못 실행했을 때의 `stakes`, 독자가 가져갈 검증된 결과 `payoff`, 실험으로 답할 `open_question`을 각각 20~180자로 기록하고 이 내용이 실제 도입에 이어지게 합니다.

`editorial.reader_walkthrough`에는 `reader_level: beginner|general`, 2~6개의 `prerequisites`, 실제 순서의 `steps` 3~7개, 결과를 눈으로 판단하는 `success_check`, 실패 뒤 다시 시작하는 `recovery`, 가장 쉬운 안전한 대안을 먼저 검토한 `easiest_method_considered`, 코드를 선택할 반복 조건 `code_needed_when`을 기록합니다. 본문 소제목에는 준비·실행 단계·결과 확인이 드러나야 하고 첫 코드 앞에 준비물 목록이 있어야 합니다. 20줄을 넘는 전체 `code` 블록은 `collapsed: true`와 의미 있는 `summary`를 사용합니다. 마지막 35% 안에는 `개발 기록` 소제목을 두어 일반 독자의 실행 흐름과 기술 증거를 분리합니다.

티스토리에서는 `실전 IT > 자동화·실험`을 선택합니다. `실전 IT`에는 글을 직접 넣지 않습니다.

그 밖에 `date_label`, `weekday`, `primary_query`, `tags`, `visual`, `editorial`, `news` 정확히 1건, `related_posts` 2건 이상, `generation`, `images`를 사용합니다. `editorial.reader_hook`에는 `scene`, `stakes`, `payoff`, `open_question`을, `editorial.search_intent`에는 `query`, `reader_need`, `answer_format`을, `editorial.original_value`에는 `durable_question`, `source_gap`, `contribution`, `proof_method`, `reader_outcome`, `limits`를 기록합니다. `related_posts`는 `config/tistory_public_posts.json`에 등록된 실제 공개 URL만 사용하고 각 항목에 `title`, `url`, 현재 실험과 연결되는 `reason`, `role`을 기록합니다. `role`은 `foundation`과 `next_step`을 각각 1개 이상 포함합니다. `news[0].content`에는 `h`, `p`, `table`, `visual`, `code`, `ul`, `quote`, `ad_break`를 필요한 만큼 배치합니다. 이름은 기존 렌더러 호환을 위한 저장 필드이며 내용은 뉴스 요약이 아니라 실제 자동화 실험 전체입니다.

`publish_date`는 2026-08-28부터 금요일이어야 하며 `date_label`과 `weekday`는 그 날짜에서 계산한 값과 정확히 일치해야 합니다. 이전 토요일 발행본은 역사 자료로 계속 유효합니다. `generation.provider`는 `codex-agent`, `generation.model`은 실제 사용한 Codex 모델 ID, `generation.revision`은 7 이상을 기록합니다. `generation.image_provider`는 생성 이미지와 실제 캡처·실측 자료를 함께 쓰므로 `mixed`로 기록하며, 비워 두거나 결정적 대체기 이름을 넣지 않습니다.

`verification`은 문장 요약이 아닌 실행 증거 계약입니다. `mode`는 실제 실행한 경우에만 `executed`, `environment`에는 OS·런타임·도구 버전·소스 리비전을 넣습니다. 복제 가능한 `commands`, 테스트 입력 `input_fixture`, 예상 `expected`, 관찰 `actual`, 실패 `failure`, 복구 `rollback`, 캡처로 증명할 이미지 키 `evidence_files`를 모두 기록합니다. 주제 회전을 위해 `problem_lane`과 `tool_brand`도 필수입니다. `evidence_files`는 `capture` 또는 `annotated_capture` 출처인 본문 이미지만 가리켜야 합니다. 실행 직전·직후의 타임존 포함 ISO 시각 `started_at`, `completed_at`, 실제 종료 코드 `command_exit_code`(0), 개인정보를 제거한 실제 출력 `stdout_excerpt`도 필수입니다. 시작·종료 시각은 예약 시각 14일 이내에서 시간순으로 일치해야 합니다.

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

데스크톱과 모바일 미리보기에서 실제 캡처 글자, 한국어 도식, 표·코드 가로 스크롤, 광고 위치, 이미지 캡션을 확인합니다. GitHub Pages 루트에서 당일 `업무자동화 실험` 카드의 제목·카테고리·태그·대표 이미지·광고 조립·미리보기·최종 HTML이 연결돼야 합니다. 같은 날 뉴스 카드의 존재 여부는 완료 조건으로 삼지 않습니다.

실제 분기가 없고 `publish_bundle`이 `READY`이며 staged diff가 있을 때 하나의 로컬 커밋으로 확정합니다. `git push origin main`이 DNS·5xx·timeout으로 실패하면 `LOCAL_COMPLETE`, push 성공 뒤 API 확인만 실패하면 `REMOTE_PUSHED_VERIFY_PENDING`으로 보고합니다. 해당 커밋의 `Publish reviewed drafts` 성공과 공개 루트의 당일 자동화 카드 연결까지 확인된 경우만 `COMPLETE`입니다. 티스토리에는 자동 발행하지 않습니다.

## 발행 전 체크

- 실제로 실행한 범위와 문서만 확인한 범위가 구분되는가
- 독자가 같은 버전·명령·입력으로 최소 예제를 따라 할 수 있는가
- 준비물 → 번호가 있는 실행 단계 → 눈으로 확인하는 성공 기준 → 실패 복구가 끊기지 않고 이어지는가
- 전체 복사 가능한 산출물이 있고 일부 코드나 설명되지 않은 개발 환경에 의존하지 않는가
- 커밋·해시·종료 코드 같은 개발 증거가 일반 독자용 실행보다 먼저 나오지 않는가
- 기대 결과와 실제 결과, 실패 조건, 되돌리는 방법이 있는가
- 실제 화면·로그는 직접 캡처했고 가짜 UI나 생성 로그가 없는가
- 표·차트 수치는 직접 측정했으며 환경·단위·횟수가 적혀 있는가
- 대표 1장과 본문 시각물 3~6개가 서로 다른 질문을 설명하는가
- 실제 캡처와 `imagegen` 설명 이미지가 각각 최소 1장 있고 모든 `origin`이 실제 제작 방식과 일치하는가
- 캡션을 가려도 이미지의 실제 물체·전후 상태만으로 본문 질문을 설명하는가
- 이미지의 한국어 글자와 HTML 캡션이 모바일에서 읽히는가
- 광고가 정확히 1개이고 전체 35~45% 위치에서 `완결 블록 → 광고 → 다음 소제목` 순서인가
- `editorial.revisit`가 별도 내부 메모 상자로 노출되지 않고 본문에 자연스럽게 반영됐는가
- `editorial.original_value`의 새 기여가 실제 실행·측정 증거와 일치하는가
- 뉴스글 원본·이미지·HTML을 덮어쓰지 않았는가
- 최종 `saturday_guard`가 `COMPLETE`인가
- 최종 `publish_bundle`이 `READY`이고 Pages 배포가 성공했는가
