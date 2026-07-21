# 쑥쑥자라나라 토요일 실전 개발·자동화 편집 계약

이 문서는 매주 토요일 14:00 KST에 실행되는 두 번째 Codex 작업의 유일한 계약입니다. 매일 08:00 제작·09:00 발행 준비되는 심층뉴스 작업과 원본·이미지·HTML·가드를 완전히 분리합니다. 독자가 실제로 따라 할 수 있는 자동화 실험기, 사용법, 공개 도구 적용 사례, 개발·AI 실전 검증 글을 작성합니다. 티스토리 붙여넣기와 18:00 예약 발행은 사용자가 직접 합니다.

사용자가 현재 대화에서 당일 추가 발행을 명시한 경우에만 `publication_mode: "manual_extra"`를 사용할 수 있습니다. 이때 `manual_extra_reason`에 요청 근거를 남기고 `scheduled_at`은 같은 날짜의 KST 실행 시각으로 기록합니다. 수집기·정기 워크플로는 이 값을 만들지 않으며, 별도 요청이 없는 비토요일 실행은 계속 건너뜁니다.

## 시작 조건과 단일 실행

1. 최신 `main`을 받고 당일 뉴스글이 먼저 완성됐는지 확인합니다.

   ```bash
   git pull --ff-only origin main
   python3 -m blog_pipeline.publishing.daily_guard --today --require-complete
   python3 -m blog_pipeline.publishing.saturday_guard --today
   ```

2. `saturday_guard` 결과를 따릅니다.

   - `SKIP`: 토요일이 아니므로 즉시 종료합니다.
   - `COMPLETE`: 같은 날짜 자동화글을 다시 조사·집필·생성하지 않고 종료합니다.
   - `PARTIAL`: 출력된 `reasons`에 해당하는 단계만 복구합니다.
   - `NEW`: 아래 흐름을 정확히 한 번 수행합니다.

3. `docs/automation-inbox/latest.json`을 먼저 읽습니다.

   - `day`가 당일 날짜와 다르면 오래된 후보를 사용하지 않고 GitHub Trending·공식 릴리스·공식 변경 내역·요즘IT 개발 실전 글을 직접 검색합니다.
   - `selected`의 임시 점수는 제목·요약 메타데이터로 계산한 우선순위이며 검증 완료의 증거가 아닙니다.
   - 후보함이 없거나 비어 있거나 수집 오류가 크면 공식 출처를 직접 검색해 같은 선정 기준으로 대체 후보를 만듭니다.
   - 선택한 한 건의 저장소·공식 문서·최신 버전과 권한 요구를 다시 확인한 뒤에만 실행 단계로 이동합니다.

4. 결과는 뉴스글과 분리해 저장합니다.

   - 원본: `data/automation_cases/YYYY-MM-DD.json`
   - 초안 ID: `YYYY-MM-DD-automation`
   - 이미지: `docs/tistory/assets/YYYY-MM-DD-automation/`
   - HTML·메타·광고본: `docs/tistory/YYYY-MM-DD-automation*`
   - 미리보기: `docs/preview/YYYY-MM-DD-automation.html`

같은 날짜의 `data/days/YYYY-MM-DD.json`과 뉴스 이미지·HTML은 읽기 참고 외에는 수정하지 않습니다.

## 글감과 실제 검증

다음 네 형식 중 하나만 선택합니다.

- 직접 실행 실험기: 반복 작업을 수동으로 해 본 뒤 자동화하고 전후 차이를 확인
- 따라하기: 독자가 작은 예제를 그대로 재현할 수 있는 단계별 사용법
- 공개 도구 적용 사례: 유명한 GitHub 저장소·공식 도구를 실제 작은 작업에 적용
- 개발·AI 실전 검증: 흥미로운 개념 글을 작은 오류·복구·전후 비교 실험으로 바꾸고 공식 문서와 실제 결과로 검증

글감은 `검색 지속성 20 · 실제 문제 해결성 25 · 재현 가능성 20 · 시각 설명 가능성 15 · 대중 공감도 20`으로 비교합니다. 대중 공감도가 최소 기준에 못 미치면 총점이 높아도 추천하지 않습니다. 최근 90일 중 발행 준비까지 완료된 자동화글의 URL·저장소·`primary_query` 지문과 겹치면 다른 주제를 고릅니다. 미완성 초안은 중복 이력으로 세지 않습니다. 뉴스 요약을 두 번째로 만들지 않습니다.

도구명을 지워도 비개발자가 자신의 문제를 떠올릴 수 있는 주제만 선택합니다. 우선 분야는 `이메일·문서·PDF·표·일정·파일` 정리, 반복 입력, 웹페이지 변경 알림, 보고서 생성, 사진·다운로드 폴더 정리와 `바이브 코딩·AI 글쓰기·Git·오픈소스 도구`의 실제 활용입니다. 프레임워크 버전, locator, 패키지 설치, 릴리스 자체는 주제가 될 수 없습니다. 익숙한 문제를 해결하는 과정에서 필요한 도구로만 설명합니다. 파일·문서 → 웹 변경 감지 → 보고서·표 → 생활·사무 노코드 자동화 → 개발·AI 실전 순으로 주제를 바꾸며 같은 도구·브랜드를 연속 사용하지 않습니다.

요즘IT 같은 매체 글은 독자가 궁금해할 질문을 찾는 보조 출처로만 사용합니다. 원문의 문장·목차·표·이미지를 옮기거나 순서만 바꿔 재서술하지 않습니다. 최종 글은 공식 저장소·공식 문서·직접 실행 결과를 중심으로 새로 구성합니다. 다른 글에 나온 수치나 설문 결과는 출처를 명시해 인용할 때만 사용하며, 직접 측정한 결과처럼 쓰지 않습니다. 가능하면 같은 질문을 작은 공개 예제에서 직접 측정해 표본·환경·횟수와 함께 제시합니다.

후보 수집기는 공개 메타데이터를 모아 우선순위만 계산합니다. 저장소를 복제하거나 설치 명령을 실행하지 않고 글·이미지·티스토리 HTML도 만들지 않습니다. 실제 검증과 집필은 이 14:00 작업에서 선택한 한 건에만 수행합니다.

실행 전 README, 설치 명령, 의존성, 권한 요구를 읽습니다. 별도 임시 디렉터리와 테스트 데이터만 사용하며 비밀키·개인 계정·운영 서비스·`sudo`·알 수 없는 바이너리·의심스러운 설치 스크립트·과도한 권한이 필요한 작업은 실행하지 않습니다. 안전하게 실행할 수 없으면 `구조 분석`으로 명시하고 실행·검증·벤치마크했다고 쓰지 않습니다.

실제 실행에는 다음 기록이 있어야 합니다.

- 운영체제, 런타임, 도구 버전과 공개 저장소의 태그·커밋
- 입력 데이터와 실행 명령 또는 설정
- 실행 전 예상 결과
- 실제 출력·로그·생성 파일
- 실패한 시도와 바꾼 조건
- 적용 범위, 비용·보안·권한·복구 한계

글에는 검증한 버전·커밋과 기대 결과와 실제 결과를 서로 붙여 기록합니다. 측정하지 않은 숫자는 만들지 않습니다. 측정했다면 표본, 횟수, 단위, 환경을 함께 기록합니다.

## 글 구성

검색형 제목은 독자가 얻게 될 결과를 제목 앞부분에 놓고 도구명은 뒤에 자연스럽게 넣습니다. 예: `메일 첨부파일을 날짜별 폴더로 자동 정리하기: n8n 실험`. 전체는 약 10~15분 분량, 소제목 5~8개로 작성합니다.

기본 흐름은 다음과 같습니다.

`반복되는 문제 장면 → 자동화 목표와 선택 이유 → 준비 환경 → 단계별 구현 → 실제 실행 화면·결과 → 수동 방식과 비교 → 실패·한계 → 재사용 체크리스트`

- 첫 5문장 안에 실제 반복 작업과 자동화 후 확인할 결과를 보여 줍니다.
- 설치·버전·코드보다 수동 작업의 불편, 완성 화면, 줄어든 단계처럼 일반 독자가 먼저 이해할 장면을 앞에 둡니다.
- 복사 가능한 최소 코드·설정을 넣고 버전과 실행 위치를 명시합니다.
- 비교가 쉬워질 때 HTML 표 1~3개를 사용합니다.
- 광고는 정확히 1개, 첫 완결된 구현 섹션 뒤 전체 비광고 블록의 35~45% 위치에 `ad_break`로 둡니다.
- 블로그 관련 글 2개 이상과 공식 문서·저장소·보조 자료 3~6개를 연결합니다.
- `정리해보겠습니다`, `자동화로 작성했습니다`, 과장된 성공담, 하지 않은 체험 표현을 쓰지 않습니다.

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

`visual.assets`마다 `label`, `scene_label`, `steps`, `curiosity_hook`, `evidence_type`, `origin`을 기록합니다. `origin`은 실제 캡처 `capture`, 주석 캡처 `annotated_capture`, 실측 차트 `measured_chart`, Codex 생성 `imagegen` 중 하나입니다. `imagegen`에는 실제 `generation_prompt`, `generation_model`, 모바일에서도 읽히는 짧은 `korean_labels` 2~6개를 기록합니다. 브리프와 대응 `images.visual_N`의 프롬프트·모델 값은 정확히 일치해야 합니다. `images.cover`와 각 `images.visual_N`에도 같은 `origin`을 기록해 브리프와 파일 출처가 일치해야 합니다. 생성 도식에는 짧은 한국어 설명을 넣고, 한글 파일명과 독자가 봐야 할 결과를 적은 HTML 캡션을 사용합니다.

`capture`와 `annotated_capture`에는 브리프와 이미지 양쪽에 같은 `capture_tool`, `capture_target`, `captured_at`을 기록합니다. `capture_tool`은 `browser`, `computer-use`, `playwright`, `system-screenshot`, `terminal` 중 실제 사용한 도구만 쓰고, `captured_at`은 타임존이 있는 ISO 시각으로 예약 시각 14일 이내에서 기록합니다. 최적화기가 실제 WebP 파일과 같은 `capture_sha256`을 이미지에 기록하며, 이 해시는 기록과 파일의 일치를 검증할 뿐 캡처 사실 자체를 대신하지 않습니다. 실제 화면인지는 실행 과정·출력·전후 상태와 함께 교차 확인합니다.

`measured_chart`는 브리프에 `measurement_source`, `unit`, `sample_count`, `measurement_environment`, 2~20개의 `data_points`(`label`, 유한한 숫자 `value`)를 넣습니다. `measurement_sha256`은 최적화기가 이 다섯 필드 전체를 UTF-8 compact JSON(키만 정렬, 배열 순서 유지)으로 직렬화해 자동 기록합니다. NaN·무한대·중복 라벨은 허용하지 않습니다. 토요일 실험에서 사용한 실측 차트는 `verification`의 `measurement_files`에 이미지 키를 넣고 `measurement_note`에 측정 방법·횟수·제외 조건을 적습니다. 이 필드가 없으면 차트로 발행하지 않습니다.

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
  "scheduled_at": "YYYY-MM-DDT18:00:00+09:00"
}
```

티스토리에서는 `실전 개발 노트 > 자동화·실험`을 선택합니다.

그 밖에 `date_label`, `weekday`, `primary_query`, `tags`, `visual`, `editorial`, `news` 정확히 1건, `related_posts` 2건 이상, `generation`, `images`를 사용합니다. `related_posts`는 `config/tistory_public_posts.json`에 등록된 실제 공개 URL만 사용하고 각 항목에 `title`, `url`, 현재 실험과 연결되는 `reason`을 기록합니다. `news[0].content`에는 `h`, `p`, `table`, `visual`, `code`, `ul`, `quote`, `ad_break`를 필요한 만큼 배치합니다. 이름은 기존 렌더러 호환을 위한 저장 필드이며 내용은 뉴스 요약이 아니라 실제 자동화 실험 전체입니다.

`publish_date`는 토요일이어야 하며 `date_label`과 `weekday`는 그 날짜에서 계산한 값과 정확히 일치해야 합니다. `generation.provider`는 `codex-agent`, `generation.model`은 실제 사용한 Codex 모델 ID, `generation.revision`은 7 이상을 기록합니다. `generation.image_provider`는 생성 이미지와 실제 캡처·실측 자료를 함께 쓰므로 `mixed`로 기록하며, 비워 두거나 결정적 대체기 이름을 넣지 않습니다.

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

데스크톱과 모바일 미리보기에서 실제 캡처 글자, 한국어 도식, 표·코드 가로 스크롤, 광고 위치, 이미지 캡션을 확인합니다. GitHub Pages 루트의 당일 그룹에 `뉴스 심층글`과 `업무자동화 실험` 두 카드가 함께 있고 각각 제목·카테고리·태그·대표 이미지·광고 조립·미리보기·최종 HTML이 독립 연결돼야 합니다.

`publish_bundle`이 `READY`가 아니면 커밋하거나 완료로 보고하지 않습니다. 모든 기준을 통과하고 diff가 있을 때만 하나의 커밋으로 `main`에 한 번 푸시합니다. 해당 커밋의 `Publish reviewed drafts` 성공과 공개 루트의 당일 두 카드 연결을 확인한 뒤에만 완료로 보고합니다. 티스토리에는 자동 발행하지 않습니다.

## 발행 전 체크

- 실제로 실행한 범위와 문서만 확인한 범위가 구분되는가
- 독자가 같은 버전·명령·입력으로 최소 예제를 따라 할 수 있는가
- 기대 결과와 실제 결과, 실패 조건, 되돌리는 방법이 있는가
- 실제 화면·로그는 직접 캡처했고 가짜 UI나 생성 로그가 없는가
- 표·차트 수치는 직접 측정했으며 환경·단위·횟수가 적혀 있는가
- 대표 1장과 본문 시각물 3~6개가 서로 다른 질문을 설명하는가
- 실제 캡처와 `imagegen` 설명 이미지가 각각 최소 1장 있고 모든 `origin`이 실제 제작 방식과 일치하는가
- 캡션을 가려도 이미지의 실제 물체·전후 상태만으로 본문 질문을 설명하는가
- 이미지의 한국어 글자와 HTML 캡션이 모바일에서 읽히는가
- 광고가 정확히 1개이고 전체 35~45%의 완결된 섹션 뒤에 있는가
- 뉴스글 원본·이미지·HTML을 덮어쓰지 않았는가
- 최종 `saturday_guard`가 `COMPLETE`인가
- 최종 `publish_bundle`이 `READY`이고 Pages 배포가 성공했는가
