# 쑥쑥자라나라 수요일 개발 가이드 편집 계약

이 문서는 매주 수요일 14:00 KST에 실행되는 Codex 개발 가이드 작업의 유일한 계약입니다. 뉴스 속보를 반복하지 않고, 검색으로 오래 찾아올 수 있으며 독자가 공부하거나 바로 적용할 수 있는 개발·AI 가이드 한 편을 만듭니다. 티스토리 붙여넣기와 18:00 예약 발행은 사용자가 직접 합니다.

## 시작 조건과 단일 실행

1. 최신 `main`을 받고 당일 뉴스글이 완성됐는지 확인합니다.

   ```bash
   git pull --ff-only origin main
   python3 -m blog_pipeline.publishing.daily_guard --today --require-complete
   python3 -m blog_pipeline.publishing.daily_guard --draft-id YYYY-MM-DD-guide
   ```

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

후보는 `검색 지속성 30 · 문제 해결성 25 · 학습 가치 20 · 실제 예제 가능성 15 · 시각 설명 가능성 10`으로 비교합니다. 최근 365일 가이드의 canonical URL, `primary_query`, 핵심 질문과 겹치면 다른 주제를 고릅니다. 최근 뉴스에서 다룬 제품을 그대로 다시 소개하지 않습니다. 최신 사건이 출발점이어도 글의 중심은 오래 남는 원리·판단 기준·실행법이어야 합니다.

요즘IT 같은 매체와 커뮤니티 글은 독자의 질문을 찾는 보조 자료로만 씁니다. 문장·목차·표·이미지를 옮기거나 순서만 바꿔 재서술하지 않습니다.

## 조사와 사실 확인

선택한 주제는 실제 페이지를 열어 다음 자료를 3~6개 확보합니다.

- 현재 동작·버전·설정을 확인할 공식 문서 1개 이상
- 표준·사양·공식 튜토리얼 또는 공식 저장소 1개 이상
- 한계·비교·운영 맥락을 보완할 독립 자료 1개 이상
- 주제상 자연스럽게 이어지는 블로그 공개 글 2개 이상

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

`독자의 구체적 문제 → 핵심 원리 → 요청·데이터 동작 흐름 → 선택지 비교 → 실행 가능한 예제 → 보안·운영 주의 → 적용 계획과 체크리스트`

- 제목은 핵심 검색어와 독자가 얻을 결과를 담고 보통 35~65자로 씁니다.
- 첫 5문장 안에 실제 문제 장면, 이 글에서 풀 질문, 읽고 얻을 결과를 둡니다.
- 표 1~3개, 필요한 경우 복사 가능한 최소 코드·설정을 넣습니다.
- 용어를 처음 쓸 때 짧게 풀고, 개념끼리 어떤 순서로 이어지는지 보여 줍니다.
- 장점만 나열하지 않고 쓰지 말아야 할 조건, 실패 방식, 비용·보안·운영 한계를 적습니다.
- 광고는 정확히 1개, 첫 완결된 핵심 섹션 뒤이자 전체 비광고 블록의 35~45% 위치에 `ad_break`로 둡니다.
- `정리해보겠습니다`, `개발자 편집자의 견해`, `자동화로 작성했습니다`, 근거 없는 전망과 과장된 성공담을 쓰지 않습니다.

## 시각물

대표 이미지 1장과 본문 설명 이미지 3~6장을 준비합니다. 모든 이미지는 본문의 특정 질문 하나를 답해야 합니다.

- 대표 이미지는 주제의 실제 대상·갈림길·결과를 한 장면으로 보여 주는 `imagegen` 자산으로 만듭니다.
- 본문은 동작 흐름, 이전·이후 비교, 조건별 선택, 구조, 단계별 적용, 확인된 수치 중 주제에 맞는 형식을 사용합니다.
- 설정·도구 사용법이 핵심이면 실제 공식 화면이나 직접 캡처를 우선합니다. 계정·토큰·IP·개인정보를 가리고 출처와 캡처 정보를 기록합니다.
- 수치 차트는 확인된 자료나 직접 측정값만 사용하고 단위·기간·출처·환경을 남깁니다.
- 생성 도식에는 모바일에서 읽히는 짧은 한국어 라벨을 넣고 세부 설명은 HTML 캡션으로 보충합니다.
- 파일명은 `JWT-인증-요청흐름.webp`처럼 내용을 알 수 있는 한글로 만듭니다.

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
python3 -m blog_pipeline.publishing.daily_guard --draft-id YYYY-MM-DD-guide --require-complete --window-days 365
python3 -m blog_pipeline.publishing.publish_bundle --draft-id YYYY-MM-DD-guide --stage
python3 -m blog_pipeline.publishing.publish_bundle --draft-id YYYY-MM-DD-guide --check
git diff --cached --check
```

데스크톱과 모바일 미리보기에서 제목, 표·코드 가로 스크롤, 이미지 글자, 캡션, 광고 위치, 본문 여백을 확인합니다. `daily_guard`가 `COMPLETE`, `publish_bundle`이 `READY`이고 실제 staged diff가 있을 때만 하나의 커밋으로 `main`에 한 번 푸시합니다. 해당 커밋의 `Publish reviewed drafts` 성공과 공개 GitHub Pages 루트에서 가이드 카드·미리보기·최종 HTML 연결을 확인한 뒤에만 완료로 보고합니다. 티스토리에는 자동 발행하지 않습니다.

## 발행 전 체크

- 최신 공식 문서와 독립 자료를 실제로 열어 확인했는가
- 뉴스 요약이 아니라 오래 검색될 질문과 해결 흐름인가
- 원리, 요청·데이터 흐름, 비교, 예제, 보안, 운영, 적용 순서가 연결되는가
- 코드·표·이미지가 각각 본문의 이해를 높이는가
- 대표 1장과 설명 3~6장이 포괄적이거나 서로 중복되지 않는가
- 관련 글은 실제 `https://won0322.tistory.com/<숫자>` 공개 글인가
- 광고가 정확히 1개이며 전체 35~45% 위치인가
- 수요일 18:00 예약값과 `개발 가이드` 카테고리가 정확한가
- 최종 가드·묶음·테스트·Pages 배포가 모두 성공했는가
