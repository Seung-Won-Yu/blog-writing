# 요일별 이미지 약속과 공통 시각 품질

이 문서는 2026-09-02 이후 월요일부터 토요일까지의 정규 글에 적용한다.
이미지 크기와 진위·가독성은 공통으로 지키고, 대표 이미지의 질문과 본문
이미지가 설명할 일은 요일마다 다르게 설계한다.

## 공통으로 유지할 것

- 대표와 본문 이미지는 1200×630 WebP, 장당 256KB 이하로 만든다.
- 대표는 글을 열게 만드는 한 장면이고, 본문 이미지는 문단을 이해시키는 근거다.
- 이미지마다 구체적인 파일명·대체 텍스트·캡션·출처 또는 생성 기록·QA를 남긴다.
- 가짜 제품 화면·가짜 측정값·근거 없는 상승 차트는 만들지 않는다.
- 최근 글과 같은 `render_family`, 대표 스타일 서명, 본문 논리 순서를 연속 사용하지 않는다.
- 요일별 고정 색상이나 고정 그림체는 쓰지 않는다. 다만 화요일 `하루`의 얼굴·
  복장·시그니처 소품은 캐릭터 정체성으로 고정하고, 배경·구도·원리 표현은 순환한다.

## 요일별 시각 역할

| 요일 | `visual.weekday_profile` | 대표 이미지 `weekday_role` | 본문 이미지의 필수 `teaching_role` |
| --- | --- | --- | --- |
| 월요일 | `practical_diagnosis` | `problem_scene` — 실제 오류·막힌 설정 장면 | `diagnosis_flow`, `recovery_boundary` |
| 화요일 | `everyday_mechanism` | `surprising_everyday_result` — 일상 사물에서 보이는 의외의 결과 | `mechanism_cutaway`, `one_minute_check` |
| 수요일 | `change_impact` | `changed_condition_scene` — 이전 전제와 바뀐 결과가 충돌하는 장면 | `before_after_change`, `action_check` |
| 목요일 | `myth_evidence` | `belief_result_conflict` — 흔한 믿음과 실제 판정의 차이 | `myth_fact_boundary`, `history_or_direct_check` |
| 금요일 | `developer_decision` | `tool_choice_scene` — 문서·저장소·도구 사이의 실제 선택 장면 | `source_evidence`, `decision_map` |
| 토요일 | `project_evidence_story` | `episode_conflict` — 이번 회차의 설계 갈등·실험 장면 | `implementation_evidence`, `decision_result` |

대표의 `weekday_profile`과 `weekday_role`은 `visual.cover`와 `images.cover`에
같은 값으로 기록한다. 각 본문 브리프의 `teaching_role`도 대응하는
`images.visual_N`에 같은 값으로 기록한다. 필드만 맞추지 말고 라벨·장면·캡션·
`logic_type`이 그 역할을 실제로 설명해야 한다.

메타데이터 태그만 맞춘 이미지는 통과시키지 않는다.

- `visual.subject_terms`에는 `primary_query`·제목·독자 질문·핵심 개체에서 실제로
  확인되는 기사 고유 표현 2~5개를 기록한다. `기술`, `방법`, `결과`, `확인`처럼
  어느 글에도 붙는 말만 쓰지 않는다.
- 대표 브리프와 `images.cover`에는 같은 `visual_claim`을 기록하고, 이 문장을
  `images.cover.alt`에도 자연스럽게 포함한다.
- 각 본문 브리프와 대응 `images.visual_N`에는 같은 `teaching_claim`을 기록한다.
  이 문장은 해당 `visual_N`의 실제 HTML 캡션에 그대로 포함돼야 한다.
- 대표와 본문 브리프의 `label`·`steps`·`curiosity_hook`, 각 이미지의 `alt`,
  실제 `generation_prompt` 또는 `capture_target`·`measurement_source`에는
  `subject_terms` 중 하나 이상이 들어가야 한다. 다른 주제의 그림에 역할 태그만
  붙이는 방식은 발행 실패다.

본문 역할별 허용 `logic_type`은 다음과 같다. 한 글의 모든 본문 이미지에
허용 역할 중 하나를 기록하고, 필수 역할 두 개는 최소 한 번씩 사용한다.

| 요일 | 역할과 허용 `logic_type` |
| --- | --- |
| 월요일 | `diagnosis_flow`: `flow`·`conditional`·`evidence`; `recovery_boundary`: `conditional`·`before_after`·`comparison`; 선택 `real_evidence`: `evidence`·`comparison` |
| 화요일 | `everyday_scene`: `comparison`·`before_after`·`flow`; `mechanism_cutaway`: `flow`·`architecture`; `one_minute_check`: `evidence`·`comparison`·`conditional`·`before_after`; `misconception_boundary`: `comparison`·`conditional` |
| 수요일 | `before_after_change`: `before_after`·`comparison`·`timeline`; `action_check`: `flow`·`conditional`·`evidence`; 선택 `source_evidence`: `evidence`·`comparison` |
| 목요일 | `myth_fact_boundary`: `comparison`·`conditional`·`before_after`; `history_or_direct_check`: `timeline`·`evidence`·`flow`; 선택 `mechanism_context`: `flow`·`architecture` |
| 금요일 | `source_evidence`: `evidence`; `decision_map`: `comparison`·`architecture`·`conditional`·`flow`; 선택 `mechanism_map`: `flow`·`architecture`; 선택 `use_case`: `evidence`·`comparison`·`flow` |
| 토요일 | `implementation_evidence`: `flow`·`architecture`·`evidence`; `decision_result`: `comparison`·`before_after`·`conditional`·`evidence`; 선택 `next_question`: `flow`·`conditional` |

금요일의 `source_evidence`는 생성 도식이 아니라 실제 `capture`,
`annotated_capture`, `measured_chart` 중 하나여야 한다. 다른 역할도 실제 화면이나
수치를 주장하면 같은 진위 규칙을 적용한다.

## 요일별 구성 원칙

- 월요일: 증상을 재현하거나 조건을 좁히는 흐름과 실패·되돌리기 분기를 보여 준다.
- 화요일: 보이지 않는 원리를 쉬운 단면·흐름으로 보여 주고, 독자가 1분 안에 직접 확인할 장면을 둔다.
- 수요일: 이전과 이후를 비교하고 영향받는 대상과 지금 확인할 행동을 분리해 보여 준다.
- 목요일: 선정적인 O/X 카드 대신 사실과 오해의 경계, 역사적 전환점 또는 직접 확인 근거를 보여 준다.
- 금요일: 공식 문서·저장소의 실제 근거와 도구 선택 지도를 최소 하나씩 둔다.
- 토요일: 비공개 코드를 그대로 노출하지 않고 공개 가능한 구현 흐름과 실험 결과·판정을 재구성한다.

색상·`render_family`·구도는 요일 프로필에 고정하지 않는다. 같은 요일 안에서도
주제의 실제 사물·공간·증거에 맞춰 바꾸되, 위 역할을 다른 요일의 이미지 역할로
대체하지 않는다.

## 화요일 `하루의 IT 원리툰`

2026-09-08 이후 화요일 `curiosity_mechanism`은
`editorial/curiosity/characters/HARU_CHARACTER_BIBLE.md`를 먼저 읽고, 고정
남성 캐릭터 `하루`가 등장하는 네 컷 원리툰으로 만든다. 목요일과 다른 요일에는
툰 계약이나 캐릭터 메타데이터를 붙이지 않는다.

- `visual.toon.format`: `it_explainer_comic`
- `visual.toon.series`: `하루의 IT 원리툰`
- `character_id`: `haru-v1`, `character_version`: `1`, `character_name`: `하루`
- `reference_asset`: `editorial/curiosity/characters/haru-character-sheet-v1.png`
- `reference_sha256`: 캐릭터 바이블에 기록된 기준 시트 해시
- `panel_count`: `4`, `dialogue_mode`: `html_bubbles`

대표와 모든 `images.visual_N`에는 캐릭터 ID·버전·기준 해시를 똑같이 기록한다.
네 개의 `visual.assets`는 1부터 연속된 `toon_panel`과 아래 `toon_beat`를 차례로
사용한다.

1. `everyday_question` / `everyday_scene`
2. `hidden_mechanism` / `mechanism_cutaway`
3. `one_minute_check` / `one_minute_check`
4. `exception_boundary` / `misconception_boundary`

각 본문 `visual` 블록은 같은 `toon_panel`과 하루의 대사 1~2개를 가진다. 대사는
한 개당 6~55자, 전체 8개 이하로 제한한다. 생성 프롬프트에는 캐릭터 바이블의
영문 앵커를 그대로 넣고 `no text; no letters; no labels; no speech bubbles`를
명시한다. 그림 안 대사를 생성하지 않으며 내보내기가 이미지 아래에 접근 가능한
HTML 말풍선으로 붙인다. 대표는 4분할 콜라주가 아니라 하루가 질문과 의외의
결과를 발견하는 단일 장면으로 만든다.
