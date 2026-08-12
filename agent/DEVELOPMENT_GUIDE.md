# 쑥쑥자라나라 수요일 개발 가이드 편집 계약

이 문서는 매주 수요일 14:00 KST에 실행되는 Codex 개발 가이드 작업의 유일한 계약입니다. 뉴스 속보를 반복하지 않고, 검색으로 오래 찾아올 수 있으며 독자가 공부하거나 바로 적용할 수 있는 개발·AI 가이드 한 편을 만듭니다. 티스토리 붙여넣기와 18:00 예약 발행은 사용자가 직접 합니다.

## 시작 조건과 단일 실행

1. 최신 `main`을 받고 당일 뉴스글이 완성됐는지 확인합니다.

   ```bash
   python3 -m blog_pipeline.publishing.sync_main --today --allow-current-inbox --attempts 3 --retry-delay 5
   python3 -m blog_pipeline.publishing.daily_guard --today --require-complete
   python3 -m blog_pipeline.publishing.daily_guard --draft-id YYYY-MM-DD-guide
   ```

   동기화 명령은 안전한 fast-forward를 세 번 시도합니다. DNS·502·503·504가 계속되어도 작업 트리가 깨끗하고 당일 뉴스 후보함이 유효하면 `LOCAL_CACHE_READY`로 제작을 계속합니다. 후보함이 오래됐거나 비었거나 작업 트리가 더러우면 중단합니다. fast-forward 불가 같은 비네트워크 오류는 우회하지 않습니다.

   14:25 재실행에서 작업 트리가 더러우면 `python3 -m blog_pipeline.publishing.publish_bundle --draft-id YYYY-MM-DD-guide --resume-check`를 먼저 실행합니다. `READY`면 수요일 완성 묶음만 남은 상태이므로 `python3 -m blog_pipeline.publishing.sync_main --verify-current --attempts 3 --retry-delay 5`로 로컬 HEAD와 원격 main 일치를 확인하고, 원고·이미지를 다시 만들지 않은 채 최종 가드·스테이징부터 복구합니다. `PARTIAL`이거나 원격 HEAD가 다르면 사용자·불완전 변경을 보호하기 위해 중단합니다.

2. 수요일이 아니면 파일을 만들지 않고 종료합니다. 가드 결과가 `COMPLETE`면 같은 글을 다시 조사·집필·생성하지 않습니다. `PARTIAL`이면 출력된 누락 단계만 복구하고, `NEW`일 때만 전체 흐름을 한 번 수행합니다.

3. 결과는 다른 글과 분리합니다.

   - 원본: `data/guides/YYYY-MM-DD.json`
   - 초안 ID: `YYYY-MM-DD-guide`
   - 이미지: `docs/tistory/assets/YYYY-MM-DD-guide/`
   - HTML·메타·광고본: `docs/tistory/YYYY-MM-DD-guide*`
   - 미리보기: `docs/preview/YYYY-MM-DD-guide.html`

같은 날짜의 뉴스·자동화 원본과 산출물은 수정하지 않습니다.

## 주제 선정

개발자가 검색해서 배우거나 문제를 해결할 수 있는 주제 한 건만 고릅니다. 단순 최신 소식, 제품 홍보, 개념 사전식 나열은 제외합니다.

우선순위는 다음 네 갈래를 순환합니다.

- 기초를 실제 흐름으로 이해하는 가이드: HTTP 요청, DB 트랜잭션, 인증, 캐시, 메시지 큐
- 선택과 비교: 언어·프레임워크·DB·배포 방식의 조건별 선택
- 오류 해결과 운영: 로그 읽기, 성능 병목, 보안 설정, 배포·복구
- AI 개발 도구 활용: 코딩 에이전트, RAG, MCP, 평가, 비용·권한 관리
- 현업 도구·공개 지식 비교: 에이전트 스킬, 개발 워크플로, 오픈소스 도구를 같은 문제와 기준으로 비교

후보는 `검색 지속성 30 · 문제 해결성 25 · 학습 가치 20 · 실제 예제 가능성 15 · 시각 설명 가능성 10`으로 비교합니다. 최근 365일 가이드의 canonical URL, `primary_query`, 핵심 질문과 겹치면 다른 주제를 고릅니다. 최근 뉴스에서 다룬 제품을 그대로 다시 소개하지 않습니다. 최신 사건이 출발점이어도 글의 중심은 오래 남는 원리·판단 기준·실행법이어야 합니다.

주제는 `Java·Spring·PostgreSQL·API`, `인증·보안·운영`, `AI 개발 도구와 비용·권한`, `실제 프로젝트의 설계·오류·복구` 축을 순환합니다. 관련 글은 같은 축의 최신 변화를 다룬 글 1개와 직접 적용한 실험·프로젝트 글 1개를 우선합니다. 연결이 억지스러우면 자리를 채우지 말고, 실제로 다음 학습·적용 단계가 되는 글만 이유와 함께 연결합니다.

요즘IT 같은 매체와 커뮤니티 글은 독자의 질문을 찾는 보조 자료로만 씁니다. 문장·목차·표·이미지를 옮기거나 순서만 바꿔 재서술하지 않습니다.

매주 후보를 찾을 때 요즘IT 개발·AI 글에서 `독자가 실제로 검색할 문제`, `비교할 선택지`, `다시 쓸 판단 기준`을 하나씩 메모합니다. 그런 뒤 같은 주제의 공식 문서·표준·저장소에서 사실을 새로 확인해 원문과 다른 핵심 질문과 확인 결과를 만듭니다. 일회성 소식이나 순위표는 시작점일 뿐이며, 최종 글은 설정·선택·실패·적용 조건 중 하나를 독자가 스스로 판단할 수 있게 끝내야 합니다.

비교·Top N 주제는 기준일과 지표 정의를 먼저 고정하고 공식 API로 수치를 다시 확인합니다. 인기도와 품질을 같은 것처럼 쓰지 않고, 공통 평가 축·잘 맞는 상황·제약·업데이트 트리거를 함께 제시합니다. 같은 입력으로 실행할 수 있는 비교라면 토요일 실험으로 보내고, 원리·선택 기준이 중심이면 수요일 가이드로 작성합니다. 공식 발표가 예약 시각 기준 72시간 이내이고 독자의 당일 행동을 바꾸는 경우에만 데일리 뉴스로 보냅니다.

## 조사와 사실 확인

선택한 주제는 실제 페이지를 열어 다음 자료를 3~6개 확보합니다.

- 현재 동작·버전·설정을 확인할 공식 문서 1개 이상
- 표준·사양·공식 튜토리얼 또는 공식 저장소 1개 이상
- 한계·비교·운영 맥락을 보완할 독립 자료 1개 이상
- `config/tistory_public_posts.json`에 URL이 등록된 블로그 공개 글 2개 이상

버전, 가격, 지원 범위, 기본값, 보안 조건처럼 바뀔 수 있는 정보는 발행일 기준으로 다시 확인합니다. 공식 자료와 독립 자료가 충돌하면 차이를 본문에 적고 단정하지 않습니다. 실행 결과를 쓸 때만 안전한 임시 환경에서 재현하며, 실행하지 않은 내용을 체험담처럼 쓰지 않습니다.

## 원고 계약

`data/guides/YYYY-MM-DD.json`은 `schema_version: 3`, `format: lead-story-v1`을 사용하며 다음 식별값을 정확히 기록합니다.

```json
{
  "draft_id": "YYYY-MM-DD-guide",
  "publish_date": "YYYY-MM-DD",
  "content_type": "evergreen_guide",
  "content_label": "개발 가이드",
  "category": "개발 가이드",
  "publication_mode": "scheduled",
  "scheduled_at": "YYYY-MM-DDT18:00:00+09:00"
}
```

티스토리에서는 `실전 개발 노트 > 개발 가이드`를 선택합니다.

`editorial.coverage`에는 `foundation`, `request_flow`, `stack`, `data`, `security`, `operations`, `plan`을 모두 넣고 실제 본문에서 각각 답합니다. 주제에 직접 해당하지 않는 항목은 억지로 별도 장을 만들지 말고, 선택 조건·보안 주의·운영 체크·학습 또는 적용 순서 안에서 자연스럽게 설명합니다.

전체는 약 10~20분 분량, 소제목 6~9개로 작성합니다. 기본 흐름은 다음과 같습니다.

`독자의 구체적 문제 → 핵심 원리 → 요청·데이터 동작 흐름 → 선택지 비교 → 실행 가능한 예제 → 보안·운영 주의 → 적용 조건·한계·다음 단계`

- 제목은 `핵심 검색어 + 풀어낼 구체적 문제·확인 가능한 결과`로 만들고 핵심 검색어를 앞 20자 안에 둡니다. `독자가 얻는 것`, `개발자에게 중요한 이유`처럼 효용을 설명하지 말고 코드·설정·오류·결과를 직접 말합니다. 보통 35~65자로 쓰며 클릭베이트나 검색어 나열은 금지합니다.
- 태그 5~8개는 `핵심 기술`, `구체적 문제`, `세부 기능`, `사용 상황`을 섞고 최소 2개를 `primary_query`와 직접 연결합니다. `AI`, `IT`, `개발`, `정보` 같은 넓은 단어만으로 채우지 않습니다.
- 첫 5문장 안에 실제 문제 장면, 이 글에서 풀 질문, 읽고 얻을 결과를 둡니다.
- 실제 순서가 중요한 튜토리얼이 아니라면 모든 소제목에 번호를 붙이지 않습니다. 질문형·결과형 제목을 섞어 교재 목차처럼 보이지 않게 합니다.
- 표 1~3개, 필요한 경우 복사 가능한 최소 코드·설정을 넣습니다.
- 용어를 처음 쓸 때 짧게 풀고, 개념끼리 어떤 순서로 이어지는지 보여 줍니다.
- 장점만 나열하지 않고 쓰지 말아야 할 조건, 실패 방식, 비용·보안·운영 한계를 적습니다.
- 광고는 정확히 1개, 첫 완결된 핵심 섹션 뒤이자 전체 비광고 블록의 35~45% 위치에 `ad_break`로 둡니다. 블록 순서는 반드시 `완결 문단·표·목록·코드·인용 → ad_break → 다음 h`여야 하며 소제목과 첫 설명 사이에는 넣지 않습니다.
- `정리해보겠습니다`, `개발자 편집자의 견해`, `자동화로 작성했습니다`, 근거 없는 전망과 과장된 성공담을 쓰지 않습니다.

## 검색 질문과 내부 링크

- 30일 이내의 `config/search_opportunities.json`을 확인하되, 가이드가 해당 검색 질문을 끝까지 해결할 때만 기회를 사용합니다. 노출 수만 보고 다른 주제를 끼워 맞추지 않습니다.
- `editorial.search_intent`에 짧은 실제 검색어 `query`, 독자의 구체적 막힘 `reader_need`, 이를 답할 표·코드·실행 순서 `answer_format`을 기록합니다. `query`는 제목 앞 20자 안에 그대로 자연스럽게 둡니다.
- `related_posts`는 원리를 보충하는 `foundation`과 바로 적용할 글인 `next_step`을 각각 1개 이상 사용합니다. 두 링크 모두 실제 공개 글이어야 하며 현재 글에서 왜 이어지는지 `reason`으로 설명합니다.

## 자연스러운 블로그 문체

- 교재 목차를 채우듯 쓰지 않고, 독자가 코드를 실행하다 막힌 한 장면에서 출발해 원리와 해결 과정으로 넘어갑니다.
- 정확한 용어는 풀어 설명하되 같은 결론을 도입·표·마무리에서 반복하지 않습니다. 짧은 문장과 긴 설명을 섞고 문단마다 한 생각만 담습니다.
- `개요`, `현황`, `분석`, `결론`, `시사점` 같은 보고서형 한 단어 소제목은 금지합니다. `왜 요청이 두 번 처리될까`, `이 설정에서 로그가 갈린다`처럼 독자의 질문과 결과를 씁니다.
- `독자에게 미치는 영향`, `개발자에게 미치는 영향`, `우리에게 미치는 영향`, `왜 중요한가`, `독자가 얻는 것` 같은 편집용 설명을 소제목으로 쓰지 않습니다. 원리 뒤에는 그 원리가 코드·로그·데이터에서 만드는 차이를 바로 보여 주고, 효용은 사례와 결과 안에서 드러냅니다.
- 공식 문서의 사용법을 다시 배열하는 데서 끝내지 않습니다. 실제로 확인한 오류·선택·비교가 있으면 근거와 함께 본문 중심에 두고, 직접 실행하지 않았다면 현실적인 예제로 설명하되 체험담처럼 꾸미지 않습니다.
- `이번 글에서는`, `살펴보겠습니다`, `알아보겠습니다`, `다음과 같습니다`, `결론적으로`, `도움이 되길 바랍니다` 같은 AI 상투 문구를 쓰지 않습니다.
- 실행하지 않은 일을 체험담처럼 꾸미지 않습니다. 실제 실행 증거가 있는 경우에만 실패한 지점과 바꾼 조건을 담담하게 서술합니다.

## 시각물

대표 이미지 1장과 본문 설명 이미지 3~6장을 준비합니다. 모든 이미지는 본문의 특정 질문 하나를 답해야 합니다.

생성 전에 대표 브리프를 `visual.cover`, 본문 브리프를 `visual.assets`에 기록합니다. 대표는 `content_role: hook`, 본문은 `content_role: explanation`을 사용합니다. 각 브리프의 `label`은 서로 다른 질문이어야 하며 대표와 본문이 같은 비교·로드맵·동작 흐름을 반복하면 원고 사전검사를 통과시키지 않습니다.

- 대표 이미지는 주제의 실제 대상·갈림길·결과를 한 장면으로 보여 주는 `imagegen` 자산으로 만듭니다.
- 본문은 동작 흐름, 이전·이후 비교, 조건별 선택, 구조, 단계별 적용, 확인된 수치 중 주제에 맞는 형식을 사용합니다.
- 설정·도구 사용법이 핵심이면 실제 공식 화면이나 직접 캡처를 우선합니다. 계정·토큰·IP·개인정보를 가리고 출처와 캡처 정보를 기록합니다.
- 수치 차트는 확인된 자료나 직접 측정값만 사용하고 단위·기간·출처·환경을 남깁니다.
- 생성 도식에는 모바일에서 읽히는 짧은 한국어 라벨을 넣고 세부 설명은 HTML 캡션으로 보충합니다.
- 파일명은 `JWT-인증-요청흐름.webp`처럼 내용을 알 수 있는 한글로 만듭니다.

대표 이미지의 한국어 라벨은 없거나 1~3개만 사용하고, 제목과 목차를 이미지 안에 다시 써 넣지 않습니다. 본문 설명 이미지는 정확한 절차·비교·구조를 2~6개의 짧은 라벨로 보여 줍니다.

2026-07-29 이후 대표 브리프와 `images.cover`에는 `cover_kind: editorial_scene`과 같은 `art_direction`, `composition_type`, `palette_family`을 기록합니다. 2026-08-04 이후 두 곳에 `render_family`도 기록하며 `photorealistic_natural`, `editorial_collage`, `flat_illustration`, `ink_drawing`, `isometric_model`, `tactile_paper`, `macro_object` 중 최근 3개 글에서 쓰지 않은 표현 방식을 고릅니다. 대표 프롬프트는 장면 성격에 맞게 `Use case: illustration-story`, `Use case: photorealistic-natural`, `Use case: stylized-concept` 중 하나로 시작하고 `Asset intent: editorial-scene`을 포함하며 최근 7개 대표와 세 값이 모두 같은 조합을 반복하지 않습니다. 대표는 독자가 겪는 실패·선택·결과를 보여 주는 한 장면을 우선하고, 본문 도식은 원리와 절차의 정확성을 우선합니다. 대표 이미지에는 단계 화살표·여러 카드·표·차트·로드맵·흐름도를 넣지 않습니다. 고정된 아이보리 배경·네이비/청록/주황·3단 카드 조합을 기본 템플릿으로 사용하지 않으며 `three_column_cards`, `four_step_cards`, `centered_dashboard_grid`, `title_slide`, `linear_flow`, `process_diagram`, `roadmap`, `comparison_grid`, `timeline_cards`, `split_panel_infographic`, `dashboard`는 대표 구성에서 제외합니다.

2026-08-04 이후 `editorial.article_shape`은 `change_impact`, `hands_on_test`, `decision_guide`, `incident_trace`, `troubleshooting`, `research_interpretation` 중 하나이며 직전 같은 유형 글과 반복하지 않습니다. 사고·유출·장애의 원인과 파급 경로를 설명하는 가이드라면 `incident_trace`를 사용합니다. `editorial.revisit`에 `quick_answer`, `reuse_case`, `failure_case`, `artifact_type`, `update_triggers` 2~4개를 기록하되, 이는 편집용 내부 메타데이터일 뿐 본문에 그대로 옮기거나 `다시 찾을 때` 같은 상자로 출력하지 않습니다. 핵심 답·실패 조건·재확인 변화는 필요한 문단에 자연스럽게 설명합니다. `artifact_type`은 `command_recipe`, `configuration`, `decision_matrix`, `checklist`, `troubleshooting_tree`, `experiment_fixture` 중 하나입니다. 본문의 `code`, `table`, `ul` 중 실제로 바로 적용할 수 있는 블록 하나에 `reusable: true`와 `reuse_label`을 내부 메타데이터로 넣되, 별도 제목·상자·배지 없이 일반 본문 요소로 출력합니다.

`editorial.action`은 `closing` 뒤에 이어지는 자연스러운 마지막 문장으로 작성합니다. `직접 확인해보려면` 같은 고정 제목이나 별도 행동 유도 상자는 사용하지 않습니다.

직전 같은 유형 글과 본문 `logic_type` 순서 전체를 반복하지 않습니다. 최근 두 글이 생성 이미지만 썼다면 실제 문서·제품 화면의 주석 캡처 또는 검증 가능한 실측 차트를 최소 1개 넣습니다. `hands_on_test`, `troubleshooting`, `research_interpretation`은 본문 시각물을 최소 3개 사용하고 실제 근거 요건을 지킵니다.

포괄적인 컴퓨터, 개발자 책상, AI 로봇·빛나는 뇌, 맥락 없는 차트, 가짜 UI·터미널, 로고만 큰 그림, PPT 카드형 썸네일은 금지합니다. 대표와 본문 이미지의 구도를 반복하지 않습니다.

각 `visual.assets`와 대응 `images.visual_N`에는 실제 제작 방식에 맞는 `origin`, `evidence_type`, `logic_type`, 제작 프롬프트 또는 캡처·측정 메타데이터, 완전한 `qa`를 기록합니다. 대표와 생성 이미지는 실제 `generation_prompt`, `generation_model`, 한국어 라벨을 남깁니다. 모든 최종 이미지는 `1200×630 WebP`, 장당 256KB 이하, 전체 2MB 이하를 지킵니다.

## 생성·검수·배포

이미지 생성 전 원고와 중복을 검사합니다.

```bash
python3 -m blog_pipeline.publishing.daily_guard --draft-id YYYY-MM-DD-guide --source-only --window-days 365
```

`READY`일 때만 이미지와 HTML을 만듭니다.

```bash
python3 -m blog_pipeline.publishing.optimize_images --draft-id YYYY-MM-DD-guide
python3 -m blog_pipeline.publishing.export_tistory --draft-id YYYY-MM-DD-guide
python3 -m blog_pipeline.publishing.build_copy_page
python3 -m blog_pipeline.publishing.build_integration_page
python3 -m unittest discover -s tests
python3 -m blog_pipeline.publishing.sync_main --attempts 3 --retry-delay 5
python3 -m blog_pipeline.publishing.daily_guard --draft-id YYYY-MM-DD-guide --require-complete --window-days 365
python3 -m blog_pipeline.publishing.publish_bundle --draft-id YYYY-MM-DD-guide --stage
python3 -m blog_pipeline.publishing.publish_bundle --draft-id YYYY-MM-DD-guide --check
git diff --cached --check
```

데스크톱과 모바일 미리보기에서 제목, 표·코드 가로 스크롤, 이미지 글자, 캡션, 광고 위치, 본문 여백을 확인합니다. 시작 시 `LOCAL_CACHE_READY`였더라도 스테이징 전에 위 엄격 동기화를 반드시 성공시킵니다. 실패하면 로컬 산출물을 보존하되 스테이징·커밋·푸시하지 않고 `PARTIAL`로 보고하며, 14:25 재실행이 위 `--resume-check` 경로로 복구합니다. `daily_guard`가 `COMPLETE`, `publish_bundle`이 `READY`이고 실제 staged diff가 있을 때만 하나의 커밋으로 `main`에 한 번 푸시합니다. 해당 커밋의 `Publish reviewed drafts` 성공과 공개 GitHub Pages 루트에서 가이드 카드·미리보기·최종 HTML 연결을 확인한 뒤에만 완료로 보고합니다. 티스토리에는 자동 발행하지 않습니다.

## 발행 전 체크

- 최신 공식 문서와 독립 자료를 실제로 열어 확인했는가
- 뉴스 요약이 아니라 오래 검색될 질문과 해결 흐름인가
- 원리, 요청·데이터 흐름, 비교, 예제, 보안, 운영, 적용 순서가 연결되는가
- 코드·표·이미지가 각각 본문의 이해를 높이는가
- 대표 1장과 설명 3~6장이 포괄적이거나 서로 중복되지 않는가
- 관련 글은 실제 `https://won0322.tistory.com/<숫자>` 공개 글인가
- `editorial.search_intent`와 `related_posts`의 `foundation`·`next_step` 역할이 실제 독자 흐름과 맞는가
- 광고가 정확히 1개이며 전체 35~45% 위치에서 `완결 블록 → 광고 → 다음 소제목` 순서인가
- `editorial.revisit`가 별도 내부 메모 상자로 노출되지 않고 본문에 자연스럽게 반영됐는가
- 수요일 18:00 예약값과 `개발 가이드` 카테고리가 정확한가
- 최종 가드·묶음·테스트·Pages 배포가 모두 성공했는가
