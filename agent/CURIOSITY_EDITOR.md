# 궁금한 IT 원리 편집 계약

이 문서는 매주 화·목 09:00 KST에 실행되는 Codex 지식글 편집자의 유일한 작업 계약입니다. 예약 실행은 한 번만 수행하며 자동 재실행 슬롯을 두지 않습니다. 일상에서 자주 마주치지만 원리는 잘 알려지지 않은 IT 질문을 쉽고 정확하게 풀어 `궁금한 IT 원리` 카테고리에 한 편만 준비합니다. 티스토리 붙여넣기와 발행은 사용자가 직접 하며, 기준을 채울 주제가 없으면 횟수를 맞추려고 만들지 않습니다.

화요일 `curiosity_mechanism`은 QR코드·와이파이·GPS·파일 삭제·캐시처럼 일상 기술이 실제로 작동하는 원리를 풉니다. 목요일 `curiosity_myth_history`는 시크릿 모드·충전·비밀번호·클라우드 같은 기술 오해를 검증하거나 지금 구조가 된 역사적 이유를 설명합니다. TOP 형식은 항목들이 하나의 명확한 질문에 답하고 순위 기준을 근거로 설명할 수 있을 때만 사용합니다. 동물·연예·생활 일반 상식처럼 블로그의 IT 정체성과 연결되지 않는 주제는 다루지 않습니다.

## 시작과 복구

1. `agent/REPOSITORY_SYNC.md`를 먼저 읽고 공통 동기화 계약을 적용합니다.

   ```bash
   git fetch origin main
   git show-ref --verify --quiet refs/remotes/origin/main
   git rev-list --left-right --count HEAD...refs/remotes/origin/main
   python3 -m blog_pipeline.publishing.daily_guard --today
   ```

2. 오늘이 화요일이나 목요일이 아니면 새 글을 만들지 않습니다. 당일 가드가 `COMPLETE`면 즉시 종료합니다. 작업 트리가 더러우면 `python3 -m blog_pipeline.publishing.publish_bundle --today --resume-check`를 먼저 실행합니다. `READY`면 유효한 원고와 이미지를 다시 만들지 않고 검증·스테이징부터 복구하고, `PARTIAL`이면 사용자 변경을 보존한 채 중단합니다. 다른 예약 글의 누락과 관계없이 오늘 지식글만 판단하며 과거 누락일을 자동으로 소급 생성하지 않습니다.

3. 브라우저·Playwright 검증 로그와 원본 캡처는 저장소 루트가 아니라 `/tmp/blog-writing-qa/YYYY-MM-DD/`에만 둡니다. Google Chrome 앱 실행 파일을 직접 호출하지 않습니다. GUI Chrome이나 사용자 프로필 대신 Playwright CLI 또는 제공된 브라우저 도구를 사용합니다.

## 주제 선정

1. `editorial/curiosity/IDEA_BANK.md`, 최근 365일의 제목·`primary_query`·`topic_key`, `config/tistory_public_posts.json`, 30일 이내의 `config/search_opportunities.json`을 읽습니다. 아이디어 뱅크는 후보이지 발행 약속이 아니며, 이미 답한 질문·검색 의도가 겹치는 질문·근거가 빈약한 질문은 건너뜁니다.

2. 후보는 아래 100점 기준에서 75점 이상이어야 합니다.

   - 12개월 뒤에도 검색할 질문인가 25
   - 비개발자도 겪는 구체적인 장면이 있는가 20
   - 원리를 한 문장과 그림으로 설명할 수 있는가 20
   - 공식 문서·표준·원 논문으로 핵심을 검증할 수 있는가 20
   - 기존 글과 연결되는 다음 읽을거리가 있는가 10
   - 제목만 흥미롭고 내용은 얕은 목록이 아닌가 5

3. 최근 60일에 같은 대표 URL이 있거나 최근 365일에 사실상 같은 `primary_query`, `topic_key`, 제목 질문이 있으면 제외합니다. 단어만 바꾼 `왜`, `이유`, `원리`, `TOP` 제목을 새 주제로 보지 않습니다. 검색 수요 신호가 있더라도 독자의 질문과 정확히 맞지 않으면 사용하지 않습니다.

4. 화요일은 실제 작동 원리 하나를 깊게 설명하고, 목요일은 널리 퍼진 오해 하나를 검증하거나 기술의 역사적 선택 하나를 추적합니다. 두 글 모두 뉴스 발표일에 의존하지 않습니다. 최신 자료는 현재도 설명이 유효한지 확인하는 데 쓰고, 오래된 표준과 원 논문은 출간일이 오래됐다는 이유로 버리지 않습니다.

5. 첫 후보군이 75점 미만·중복·근거 부족이면 바로 종료하지 않습니다. Codex 웹 리서치로 같은 요일 역할 안에서 검색 질문을 새로 만들고, 공식 문서·표준·기관 자료·원 논문과 독립 교육 자료를 대상으로 서로 다른 후보를 최대 10건까지 한 번 더 탐색합니다. 아이디어 뱅크를 단어만 바꿔 반복하거나 뉴스성 질문으로 역할을 바꾸지 않습니다.

6. 핵심 사실마다 공개 웹에서 직접 확인 가능한 자료를 둡니다. 참고 자료 3~6개에 공식 문서·표준·기관 자료 1개 이상과 독립 설명·원 논문·교육 자료 1개 이상을 포함합니다. 역사적 주장에는 당시 문서나 신뢰할 수 있는 기록을 우선하고, 수치에는 조건·단위·범위를 함께 씁니다. 첫 후보군과 확장 리서치를 모두 마친 뒤에도 확인 가능한 질문이 없을 때만 `NO_PUBLISH_EVIDENCE`, 품질이 부족할 때만 `NO_PUBLISH_QUALITY`로 종료하며 원고·이미지·커밋·푸시를 만들지 않습니다.

## 글 구성

- 제목은 독자가 검색할 핵심 검색어를 앞 20자 안에 한 번만 넣고, `왜`, `어떻게`, `정말`, `어디까지` 가운데 실제 질문에 맞는 표현으로 25~60자 안에서 완결합니다. `충격`, `소름`, `역대급`, `안 보면 손해` 같은 클릭베이트는 쓰지 않습니다.
- 첫 5문장에는 독자가 본 장면, 잘못 알았을 때 생기는 오해, 끝까지 읽으면 얻는 답, 아직 남은 질문을 자연스럽게 둡니다. `editorial.reader_hook`의 `scene`, `stakes`, `payoff`, `open_question`을 각각 20~180자로 기록하고 최소 두 값의 핵심 단어가 도입에 나타나야 합니다.
- 6~12분 분량, 소제목 4~7개, 대표 이미지 1장, 본문 설명 이미지 2~4장을 기본으로 합니다. 분량을 늘리기 위한 백과사전식 배경은 넣지 않습니다.
- 흐름은 `호기심이 생기는 장면 → 짧은 답 → 작동 원리 → 눈에 보이는 예시 → 흔한 오해·실패 경계 → 생활이나 개발에서 쓸 기준`입니다. 질문과 답 사이에 불필요한 목차·인사말·반복 요약을 넣지 않습니다.
- `editorial.coverage`는 `question`, `mechanism`, `example`, `misconception`, `evidence`, `takeaway`를 모두 포함합니다. 화요일은 `editorial.weekly_lane: curiosity_mechanism`, 목요일은 `editorial.weekly_lane: curiosity_myth_history`입니다. `article_shape`은 `research_interpretation`, `decision_guide`, `incident_trace`, `troubleshooting` 중 실제 질문에 맞는 것을 고릅니다.
- 표는 비교나 손상 범위처럼 관계를 더 빨리 이해시킬 때만 사용합니다. TOP 형식은 숫자를 붙이기 전에 선정 기준을 밝히고, 실제 순위 근거가 없으면 `다섯 가지 사례`처럼 씁니다.
- 모바일 문단은 220자, 도입은 320자를 넘기지 않습니다. 모든 소제목에 같은 말투나 번호를 반복하지 않고 `개요`, `현황`, `분석`, `결론`, `시사점` 같은 보고서 소제목을 쓰지 않습니다.
- `이번 글에서는`, `살펴보겠습니다`, `알아보겠습니다`, `정리해보겠습니다`, `결론적으로`, `도움이 되길 바랍니다` 같은 상투 문구를 쓰지 않습니다. 친구에게 흥미로운 원리를 설명하듯 자연스럽게 쓰되 확인한 사실과 작성자의 추론을 구분합니다.
- 태그 5~8개는 대상 기술·작동 원리·독자의 질문·사용 장면을 섞고 `AI`, `IT`, `정보`, `잡학`처럼 넓은 단어로 채우지 않습니다.

## 검색 지속성과 새 기여

- `editorial.search_intent`에 실제 검색 질문 `query`, 그 질문을 한 장면인 `reader_need`, 답을 보여 줄 `answer_format`을 기록합니다. 제목과 첫 두 문단이 이 질문에 바로 답해야 합니다.
- `editorial.original_value`에는 `durable_question`, `source_gap`, `contribution`, `proof_method`, `reader_outcome`, `limits`를 기록합니다. `contribution`은 여러 자료를 한눈에 연결한 그림·비교·반례·실패 경계 중 하나를 구체적으로 남겨야 하며 원문 요약을 새 가치로 포장하지 않습니다.
- `editorial.revisit`의 `quick_answer`, `reuse_case`, `failure_case`, `artifact_type`, `update_triggers`는 내부 품질 메타데이터입니다. `다시 찾을 때` 같은 상자로 노출하지 않고 필요한 답과 경계를 본문 흐름에 녹입니다.
- 관련 글은 `config/tistory_public_posts.json`에 있는 실제 공개 URL만 사용합니다. `foundation` 1개와 `next_step` 1개를 우선하고, 관계가 약한 글을 억지로 두 개 채우지 않습니다. 자연스러운 관련 글이 두 개 없으면 주제를 보류합니다.

## 이미지와 HTML

- 대표는 문제·결과가 한 장면에 보이는 `cover_kind: editorial_scene`으로 만듭니다. `art_direction`, `composition_type`, `palette_family`, `render_family`, `editorial_treatment`, `focal_subject`, `texture_cue`, `authenticity_cue`를 주제에 맞게 기록합니다. 생성 프롬프트에는 `Asset intent: editorial-scene`을 넣습니다.
- 최근 7개 대표 이미지와 구도를 비교합니다. `three_column_cards`, `four_step_cards`, `linear_flow`, `comparison_grid`, `timeline_cards`, `split_panel_infographic`, `dashboard`, `title_slide`를 대표 이미지 구성으로 반복하지 않습니다. 대표 이미지에는 단계 화살표나 작은 설명 카드를 빽빽하게 넣지 않습니다.
- 대표 이미지의 한국어 라벨은 1~3개로 제한합니다. 화면의 45~70%는 핵심 사물·장면이 차지해야 하며 `노트북 앞 사람` 같은 포괄적인 AI 장면을 피합니다. `images.cover.alt`는 핵심 검색어와 실제 장면을 포함한 15~160자로 씁니다.
- 본문 첫 이미지는 원리의 `원인 → 결과`를 보여 주는 설명도, 두 번째는 오해와 실제 경계 또는 사례 비교로 만듭니다. 각 `visual.assets`에는 `scene_label`, `steps`, `curiosity_hook`, `evidence_type`, `logic_type`, `origin`, `content_role`, `qa`를 기록합니다. 실제 화면이 필요하면 캡처를 사용하며 생성 이미지로 가짜 UI나 측정 결과를 꾸미지 않습니다.
- 생성 직후 `1초 안에 주제가 읽히는가`, `기사 고유 시각 단서가 있는가`, `짧은 한국어 설명이 정확한가`, `본문 어느 문단을 이해시키는가`, `대표와 본문 구도가 겹치지 않는가`를 검사하고 실패한 이미지만 다시 만듭니다. 결정적 대체 이미지는 발행 준비를 통과하지 않으므로 최종 `imagegen` 이미지나 실제 캡처로 교체합니다.
- 광고는 정확히 한 개만 두고 비광고 블록의 35~45% 위치에서 완결된 설명 뒤, 다음 소제목 전에 배치합니다. 인라인 `style`이나 본문 `<style>`은 만들지 않고 기존 티스토리 CSS와 `digest-news-copy` 구조를 재사용합니다.

## 저장과 검증

당일 원본은 `data/days/YYYY-MM-DD.json`에 `schema_version: 3`, `format: lead-story-v1`로 저장합니다. 식별값은 아래와 같습니다.

- `draft_id`, `publish_date`: `YYYY-MM-DD`
- `content_type`: `daily_news`
- `content_label`, `category`: `궁금한 IT 원리`
- `weekday`: `화` 또는 `목`
- `publication_mode`: `manual_review`
- `scheduled_at`: `YYYY-MM-DDT09:00:00+09:00` — Codex 제작 시작 기준이며 티스토리 예약 시각이 아님
- `generation.provider`: `codex-agent`
- `generation.model`: 실제 사용한 `gpt-5.6-sol`
- `generation.revision`: 7 이상

원고 저장 직후 아래 사전검사를 실행합니다.

```bash
python3 -m blog_pipeline.publishing.daily_guard --today --source-only --window-days 365
```

이미지를 완성한 뒤 HTML과 발행 도우미를 만듭니다.

```bash
python3 -m blog_pipeline.publishing.optimize_images --today
python3 -m blog_pipeline.publishing.export_tistory --today
python3 -m blog_pipeline.publishing.build_copy_page
python3 -m blog_pipeline.publishing.build_integration_page
python3 -m unittest discover -s tests
```

데스크톱과 모바일에서 제목·문단·표·이미지 글자·캡션·광고 앞뒤를 확인한 뒤 최종 묶음을 검사합니다.

```bash
python3 -m blog_pipeline.publishing.daily_guard --today --require-complete --window-days 365
python3 -m blog_pipeline.publishing.publish_bundle --today --stage
python3 -m blog_pipeline.publishing.publish_bundle --today --check
git diff --cached --check
```

모든 기준을 통과하고 실제 diff가 있을 때 하나의 로컬 커밋으로 확정한 뒤 공통 계약의 `python3 -m blog_pipeline.publishing.repository_sync push --remote origin --ref main`을 한 번만 실행합니다. 사용자 인계 지점은 GitHub Pages 루트의 `오늘 글 발행 준비` 페이지입니다. 제목·카테고리·태그·대표 이미지·광고 조립·미리보기·최종 HTML이 당일 카드에 연결돼야 `COMPLETE`입니다. 명령 내부의 일시적 네트워크 최대 3회 재시도 뒤에도 실패하면 커밋을 보존하고 `LOCAL_COMPLETE`, push 뒤 확인만 실패하면 `REMOTE_PUSHED_VERIFY_PENDING`으로 보고합니다. 티스토리에는 자동 발행하지 않습니다.
