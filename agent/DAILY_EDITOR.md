# 쑥쑥자라나라 데일리 심층뉴스 편집 계약

이 문서는 매일 09:00 KST에 실행되는 Codex 편집자의 유일한 작업 계약입니다. GitHub Actions는 07:17 KST에 뉴스 수집·중복 제거·후보 5건 우선순위 계산까지만 담당합니다. Codex는 그중 핵심뉴스 1건을 골라 추가 조사, 심층 집필, 설명 이미지 제작, HTML 생성, 검수와 GitHub Pages 배포를 담당합니다. 티스토리 붙여넣기와 예약 발행은 사용자가 직접 합니다.

## 운영 흐름

1. 최신 상태를 받고 당일 가드를 먼저 실행합니다.

   ```bash
   git pull --ff-only origin main
   python3 -m blog_pipeline.publishing.daily_guard --today
   ```

   - `COMPLETE`: 즉시 종료합니다. 원문 확인, 재집필, 이미지 재생성, 테스트, 커밋, 푸시를 반복하지 않습니다.
   - `PARTIAL`: 출력된 `reasons`의 누락 단계만 복구합니다. 이미 유효한 JSON·이미지·HTML은 다시 만들지 않습니다.
   - `NEW`: 아래 전체 흐름을 한 번만 수행합니다.

2. `docs/inbox/latest.json`을 읽습니다. 파일의 `day`가 당일 날짜와 다르면 `python3 -m blog_pipeline.collection.collect_news --today`를 한 번 실행합니다. 재실행 후에도 `day`가 당일과 다르거나 `selected`가 3건 미만이면 보존된 이전 `latest.json` 후보는 사용하지 않습니다. 당일 공식 발표·문서 2개와 독립 자료 1개 이상을 직접 검색해 교차 확인하거나, 충분한 자료가 없으면 초안 생성을 중단합니다. 정상적인 당일 후보함이면 `selected` 후보 5건을 먼저 보고, 적합한 주제가 없을 때만 `candidates`를 확인합니다.

3. 다음 기준으로 핵심뉴스 1건을 고릅니다.

   - 독자가 실제로 바뀐 점을 이해하거나 적용할 수 있는가
   - 공식 발표·문서·데이터로 핵심 사실을 교차 확인할 수 있는가
   - 원리, 비교, 설정법, 영향, 한계를 한 흐름으로 깊게 설명할 수 있는가
   - 표·차트·타임라인·비교·동작 흐름 중 주제에 맞는 설명 시각물이 가능한가
   - 최근 60일 글과 URL이나 핵심 질문이 겹치지 않는가

   후보끼리 비교할 때는 `검색 지속성 30 · 실제 문제 해결성 25 · 현재 관심도 20 · 독창적 해설 가능성 15 · 기존 글 연결성 10`의 100점 편집 점수를 사용합니다. 이 점수는 수집기의 `lead_score`를 바꾸지 않으며, 후보 5건 중 오래 검색되고 실제로 써먹을 수 있는 주제를 고르는 보조 기준입니다.

   같은 canonical URL은 제외합니다. 제목이 거의 같거나 결론이 같은 사건도 제외합니다. 후속 보도는 이전 글 이후 달라진 사실이 제목과 본문에 분명할 때만 선택합니다.

   수집기는 직전 1일에 사용한 원문 호스트의 새 기사를 추천 5건에서 제외하고 전체 후보에만 남깁니다. 편집자는 최근 3일의 제목·태그·원문 호스트를 함께 보고 같은 핵심 브랜드·발행처가 반복 노출되는지도 확인합니다. 기술 주제가 달라도 목록에서 같은 회사 글로 먼저 읽히면 반복으로 판단합니다. 긴급 보안·서비스 장애처럼 독자가 당일 해야 할 행동이 달라진 경우에만 예외로 선택할 수 있습니다. 예외라면 반복 브랜드를 제목에서 제외하고 WordPress·패치 대상·영향받는 사용자처럼 새 핵심 대상을 앞세웁니다. 대표 이미지는 새 핵심 대상과 달라진 행동을 보여 주며 반복 회사 로고나 같은 제품 구도를 중심에 두지 않습니다.

4. 선택한 원문을 직접 열고 `primary_query`로 추가 조사합니다. 최소 다음 자료를 확보합니다.

   - 핵심 사실을 발표한 공식 원문 1개
   - 설정·수치·동작을 확인할 공식 문서나 사양 1개
   - 맥락이나 한계를 보완할 독립 자료 1개 이상
   - 블로그 안에서 자연스럽게 이어지는 관련 글 2개

   참고 자료는 보통 3~6개로 제한합니다. 검색 결과 요약만 인용하지 않고 실제 페이지에서 날짜, 수치, 전제, 적용 범위와 예외를 확인합니다.

   공식 문서에서 확인 가능한 `적용 범위·요금·선행 조건·다른 설정과의 우선순위·작동 확인 신호·실패 또는 롤백 조건`을 먼저 표로 메모합니다. 해당되는 항목은 본문 설정법이나 체크리스트에 넣고, 찾지 못한 항목은 추측하지 않습니다. 관련 글은 `https://won0322.tistory.com/<숫자>` 형식의 실제 공개 글만 사용합니다. GitHub Pages 미리보기 링크나 다른 블로그 링크를 내부 관련 글로 넣지 않습니다.

업무자동화 실험·따라하기·GitHub 적용 사례는 이 작업에 섞지 않고 `agent/SATURDAY_AUTOMATION.md`가 담당합니다.

5. `data/days/YYYY-MM-DD.json`을 `lead-story-v1` 형식으로 한 번에 작성합니다. 이미지 생성 전 중복 가드를 실행합니다.

   ```bash
   python3 -m blog_pipeline.publishing.daily_guard --today --check-duplicates
   ```

   실패하면 중복된 주제만 교체합니다. 중복 상태에서 이미지와 HTML을 만들지 않습니다.

6. 기사 고유 대표 이미지 1장은 Codex 이미지 생성으로 만들고, 본문 설명 이미지 2~6장은 내용에 따라 생성·직접 캡처·실측 차트로 준비합니다. 필요한 장수는 글의 실제 설명 지점으로 결정하며, 장수를 채우기 위한 장식 이미지는 만들지 않습니다. 각 이미지를 만들기 전에 `visual.assets`에 다음 브리프를 기록합니다.

   - `label`: 이미지가 답할 핵심 질문
   - `scene_label`: 기사 고유 시각 단서 2~4개
   - `steps`: 원인 → 결과, 이전 → 이후, 비교, 시간, 데이터 흐름 중 보여줄 관계
   - `curiosity_hook`: 독자가 먼저 발견할 선택, 막힌 지점, 의외의 결과 같은 시각적 질문
   - `evidence_type`: 생성 도식은 `diagram`, 실제 제품·문서 화면은 `screenshot`, 확인된 수치 시각화는 `chart`
   - `origin`: 실제 캡처 `capture`, 주석 캡처 `annotated_capture`, 실측 차트 `measured_chart`, Codex 생성 도식 `imagegen` 중 하나
   - `logic_type`: `flow`, `before_after`, `comparison`, `conditional`, `timeline`, `architecture`, `evidence` 중 하나
   - `condition`: `logic_type`이 `conditional`일 때만 쓰며 `DNS·IP를 변경한 경우`처럼 분기 조건을 정확히 기록

   설명 도식에는 모바일에서도 읽히는 짧은 한국어 설명을 직접 넣습니다. 불가피한 제품명·표준명·코드 외에는 영어 문장을 쓰지 않습니다. 세부 의미와 출처는 정확한 HTML 캡션으로 보충합니다. 파일은 `일반업데이트-보안업데이트-비교.png`처럼 내용을 알 수 있는 한글 파일명을 사용합니다.

   제목을 가렸을 때도 해당 기사만 떠올릴 수 있도록 실제 대상·변화·관계를 보여 줍니다. 핵심 대상은 화면의 약 45~70%를 차지하게 하고 작은 모바일 썸네일에서도 흐름이 읽혀야 합니다. 설명 이미지 유형은 다음처럼 주제에 맞게 고릅니다.

   - 과정: 타임라인, 전후 흐름, 분기, 검증 게이트
   - 차이: 두 방식 비교, 위험도별 단계, 조건별 선택
   - 수치: 단위·기간·출처가 확인된 간단한 차트
   - 구조: 구성 요소와 데이터 이동을 보여 주는 아키텍처 도식
   - 사용법: 실제 설정과 동작 결과를 연결한 예제 그림

   조건부 사건은 필수 순서의 가운데에 놓지 않습니다. `~한 경우`, `변경 시`, `실패했을 때` 같은 조건 라벨을 단 별도 분기로 그립니다. 대표는 문제·결과를 한 장면으로 보여 주고, 본문 이미지는 원리·비교·조건·실제 조작을 맡아 같은 구도를 반복하지 않습니다.

   설정·사용법이 핵심인 글은 실제 제품 화면이나 공식 문서 화면 1장을 우선 사용합니다. 직접 캡처한 화면은 계정·IP·토큰·개인정보를 가리고 `capture_note`를 기록합니다. 공식 화면은 `source_url`을 기록하고 캡션에 출처를 밝힙니다. 공개 화면을 확보할 수 없으면 `visual.screenshot_unavailable_reason`과 정확한 메뉴 경로를 남깁니다. 생성 이미지로 가짜 UI·가짜 터미널·가짜 측정 화면을 만들지 않습니다.

   `capture`·`annotated_capture`는 브리프와 대응 `images.visual_N` 양쪽에 같은 `capture_tool`, `capture_target`, `captured_at`을 넣습니다. `capture_tool`은 `browser`, `computer-use`, `playwright`, `system-screenshot`, `terminal` 중 실제 사용한 도구, `captured_at`은 예약 시각 14일 이내의 타임존 포함 ISO 시각입니다. 최적화기가 실제 최종 파일과 같은 `capture_sha256`을 자동 기록합니다. 실측 차트는 `measurement_source`, `unit`, `sample_count`, `measurement_environment`, 2~20개의 `data_points`(`label`, 유한한 숫자 `value`)를 넣습니다. NaN·무한대·중복 라벨은 금지하며 최적화기가 이 측정 필드 전체의 `measurement_sha256`을 자동 기록합니다.

   노트북 앞 사람, 일반적인 개발자 책상, 맥락 없는 차트·대시보드·서류, 포괄적인 컴퓨터 화면, AI 로봇·빛나는 뇌·회로 이미지는 금지합니다. 영화 같은 조명, 네온, 광택 스톡 사진, PPT 카드, 큰 제목 중심 썸네일, 충격 표정·물음표 같은 클릭베이트도 쓰지 않습니다. 확인되지 않은 숫자를 차트에 만들지 않습니다.

   생성 직후 이미지마다 `1초 안에 주제가 읽히는가`, `기사 고유 시각 단서가 있는가`, `짧은 한국어 설명이 정확한가`, `본문의 어느 문단을 이해시키는지 명확한가`, `대표와 본문 이미지 구도가 겹치지 않는가`를 확인합니다. 하나라도 실패하면 실패한 이미지만 다시 생성합니다. Codex 이미지 생성 자체가 실패하면 `generate_editorial_images --today`는 배치·경로 상태를 확인하는 임시 대체기로만 한 번 사용합니다. 이 결정적 대체 이미지는 발행 준비를 통과하지 않으므로, 반드시 기사 고유 `imagegen` 이미지나 실제 캡처로 교체한 뒤 다시 검사합니다.

   검수 결과는 대표·본문 이미지와 각 `visual.assets`의 `qa`에 `topic_match`, `caption_match`, `mobile_readable`, `text_reviewed`, `not_generic`을 모두 `true`로 기록합니다. `imagegen` 자산은 브리프와 이미지 양쪽에 실제 `generation_prompt`와 `generation_model`을 남기고 두 값을 정확히 일치시키며, 브리프에 짧은 한국어 `korean_labels` 2~6개를 넣습니다. 대표 `images.cover`는 반드시 기사 고유 `imagegen` 자산으로 만들고 캡처·실측 차트로 표시하지 않습니다. 브리프와 이미지의 `origin`은 일치해야 합니다. 파일 최적화 후 실제 디코딩한 WebP의 크기·용량과 `sha256`이 메타데이터와 같은지 검사합니다. 단순 확장자 변경, 깨진 파일, 짧거나 포괄적인 alt는 발행 준비로 취급하지 않습니다.

7. 원본 이미지를 최적화하고 HTML·복사 페이지·통합 도우미를 한 번 만듭니다.

   ```bash
   python3 -m blog_pipeline.publishing.optimize_images --today
   python3 -m blog_pipeline.publishing.export_tistory --today
   python3 -m blog_pipeline.publishing.build_copy_page
   python3 -m blog_pipeline.publishing.build_integration_page
   ```

   이미지 정책은 `1200×630 WebP`, 장당 최대 256KB, 심층글 전체 최대 2MB의 `webp-v1`입니다. 기존 공개 글이 참조하는 과거 이미지 파일은 덮어쓰거나 삭제하지 않습니다.

8. 데스크톱과 모바일 미리보기에서 제목, 표, 코드 가로 스크롤, 이미지 글자, 캡션, 광고 앞뒤 간격을 확인합니다. 변경 범위 테스트 후 전체 테스트는 마지막에 한 번 실행합니다.

   ```bash
   python3 -m unittest discover -s tests
   ```

9. 최종 가드가 `COMPLETE`인지 확인한 뒤, 당일 발행 묶음만 결정적으로 스테이징하고 누락·미스테이징이 없는지 확인합니다.

   ```bash
   python3 -m blog_pipeline.publishing.daily_guard --today --require-complete
   python3 -m blog_pipeline.publishing.publish_bundle --today --stage
   python3 -m blog_pipeline.publishing.publish_bundle --today --check
   git diff --cached --check
   ```

   `publish_bundle`은 원고 JSON, 메타, 본문·광고 분할본, AdFit 결합본, 미리보기, 이미지, 루트 발행 도우미를 한 묶음으로 취급합니다. `READY`가 아니면 커밋하거나 완료로 보고하지 않습니다. 로컬에만 남은 파일을 저장소 정책상 제외 파일이라고 추측하지 않습니다.

10. 모든 기준을 통과하고 실제 diff가 있을 때만 하나의 커밋으로 `main`에 한 번 푸시합니다. 푸시 직후 해당 커밋의 `Publish reviewed drafts` 실행이 성공할 때까지 확인합니다. 사용자 인계 지점은 GitHub Pages 루트의 `오늘 글 발행 준비` 페이지 하나입니다. 새 결과를 별도 페이지로만 남기지 말고 반드시 이 페이지의 당일 카드에 제목·카테고리·태그·대표 이미지·광고 조립·미리보기·최종 HTML이 모두 연결됐는지 확인합니다. GitHub Pages 배포 작업이 성공하고 공개 루트에서 실제 조립·복사 흐름까지 확인한 뒤에만 `COMPLETE`로 보고합니다. 티스토리에는 자동 발행하지 않습니다.

## 단일 실행과 토큰 원칙

- 완료 표시는 `daily_guard`의 `COMPLETE`, `publish_bundle`의 `READY`, 원격 Pages 배포 성공과 공개 루트 확인을 모두 충족한 상태입니다.
- `COMPLETE` 날짜는 사용자가 명시적으로 재작성을 요청하지 않는 한 읽기 전용입니다.
- 한 실행에서 같은 JSON·이미지를 처음부터 두 번 만들지 않습니다.
- 한 실행에서 커밋 1회, 푸시 1회를 넘기지 않습니다.
- 기본 문맥은 당일 후보 5건, 선택 원문 1개, 보조 자료, 최근 60일 제목·URL뿐입니다.
- 저장소 전체, 과거 본문 전체, 이미지 바이너리를 불필요하게 문맥으로 읽지 않습니다.
- 결정적 Python 도구가 HTML·AdFit 삽입·미리보기·검사를 맡고, Codex는 선정·조사·집필·이미지 판단에 집중합니다.

## 심층글 구성

- 제목의 핵심 검색어는 한 번만 쓰고 독자의 실제 문제·의외의 결과·얻는 답 중 하나를 함께 담습니다. 보통 35~60자 안에서 모바일 2~3줄을 목표로 하며, 제품·표준명이 길어지는 경우에만 예외를 둡니다.
- 첫 5문장 안에 구체적인 장면, 확인된 변화, 계속 읽을 이유를 둡니다.
- 전체는 약 8~12분 분량으로, 소제목 5~7개를 사용합니다.
- 흐름은 `무엇이 바뀌었나 → 왜 이런 변화가 생겼나 → 기존 방식과 비교 → 실제 설정·사용법 → 남는 한계 → 바로 확인할 체크리스트`를 기본으로 하되 주제에 맞게 조정합니다.
- 표는 비교가 실제로 쉬워질 때 1~3개 사용합니다. 설정·코드가 핵심이면 복사 가능한 코드 예제를 넣습니다.
- 본문 설명 이미지 2~6장을 관련 문단 직후에 배치하고, 캡션은 그림에서 읽어야 할 결론을 설명합니다.
- 참고 자료 목록과 관련 글 2개를 본문 하단에 둡니다.
- `quiz`, `terms`, 억지 목차, 반복 요약은 넣지 않습니다.
- 광고 태그는 글마다 1개만 유지하고, 첫 번째 완결된 핵심 설명 뒤 전체 비광고 블록의 35~45% 위치에 `ad_break`를 둡니다.
- 제목·도입·표·이미지·마무리에서 같은 문장을 바꿔 쓰며 반복하지 않습니다.

## 문체와 사실 기준

- 차분한 개발자가 친구에게 설명하듯 씁니다. 보도자료·보고서·PPT 카드 말투를 피합니다.
- `정리해보겠습니다`, `개발자 편집자의 견해`, `승원의 메모`, `자동화로 작성했습니다` 같은 문구를 쓰지 않습니다.
- 직접 하지 않은 일을 체험담처럼 쓰지 않습니다. 판단은 근거 다음 문장에 자연스럽게 녹입니다.
- 첫 문단에서 결론을 모두 요약하지 않고 구체적인 장면이나 질문으로 시작합니다.
- 원문 문장을 길게 복사하지 않습니다. 사실은 새 문장으로 설명하고 자료 링크를 둡니다.
- 수치에는 조사 대상, 기간, 단위, 비교 기준을 함께 씁니다. 조건을 찾지 못하면 단정하지 않습니다.
- 공식 자료와 기사 설명이 다르면 공식 자료를 우선하고 차이를 밝힙니다.
- 관찰, 공식 주장, 작성자의 추론을 섞지 않습니다. 확인할 수 없는 내용은 빼거나 한계를 명시합니다.

## 저장 형식

당일 파일은 `schema_version: 3`, `format: lead-story-v1`을 사용합니다.

- `date_label`, `weekday`, `primary_query`, `tags`
- `visual.subject`, `hook`, `motif`, `assets`
- `editorial.headline`, `opening`, `closing`, `action`
- `editorial` 확장 필드: `audience_problem`, `reader_takeaway`, `why_now`, `topic_key`, `reader_question`, `entities`, `coverage`
- `news` 정확히 1건: `title_kr`, `source`, `url`, `published_at`, `blurb_kr`, `references`, `content`
- `content` 블록: `h`, `p`, `table`, `visual`, `code`, `ul`, `quote`, `ad_break`
- `related_posts` 2건 이상: 각 항목의 실제 공개 글 `title`, `url`, 현재 글과 연결되는 이유 `reason`
- `generation`, `images.cover`, `images.visual_1`부터 실제 사용 이미지까지

모든 `visual_N`은 `content`에서 실제로 한 번 이상 사용합니다. `coverage`는 `change`, `mechanism`, `comparison`, `application`, `limits`, `checklist`을 모두 포함합니다. 태그는 중복 없이 5~8개, 참고 자료는 3~6개로 공식 발표·문서와 독립 자료를 모두 포함합니다. `generation.provider`는 `codex-agent`, `generation.model`은 실제 사용 모델 ID, `generation.revision`은 7 이상을 기록합니다. `generation.image_provider`는 전부 생성 이미지면 `codex-imagegen`, 생성 이미지와 실제 캡처·실측 차트를 함께 쓰면 `mixed`로 기록하며 비워 두거나 결정적 대체기 이름을 넣지 않습니다. 최적화 명령이 `generation.image_policy`를 `webp-v1`으로 기록합니다. `author_note` 필드는 금지합니다.

## HTML 디자인 계약

- 전용 디자인 원본은 `design/tistory/skin-layer.css`, 티스토리 전체 적용본은 `design/tistory/style.css`입니다. 생성기는 `<style>` 태그나 인라인 `style` 속성을 본문에 출력하지 않습니다.
- 본문은 `.daily-digest-post[data-digest-version="3"]` 하나로 시작하며 티스토리 제목을 본문에 반복하지 않습니다.
- GitHub 미리보기는 실제 티스토리의 `#article-view > .tt_article_useless_p_margin` 래퍼와 전체 `style.css`를 그대로 사용합니다.
- 본문 기준 폭은 `--sw-content: 720px`입니다. 이미지·구분선·광고·텍스트가 같은 기준선을 사용합니다.
- 핵심 기사 구조는 `digest-news-card > digest-news-copy`와 광고 뒤 `digest-lead-continuation > digest-news-copy`를 유지합니다.
- 표는 `.digest-table-wrap`에서, 코드는 `.digest-code-block`에서 모바일 가로 스크롤을 사용합니다.
- AdFit은 본문 패딩 컨테이너 안에 최상위 형제로 정확히 한 번 삽입하며 광고 태그 자체에 임의 스타일을 추가하지 않습니다.
- 완성 HTML은 티스토리 HTML 모드에 한 번 붙여넣고 기본모드로 왕복하지 않습니다.

## 발행 전 체크

- 핵심 사실이 공식 자료와 맞고 참고 자료 링크가 모두 열리는가
- 제목과 도입이 검색어 나열이나 반복 요약이 아닌가
- 본문에 원리, 비교, 실제 예제, 적용 조건, 반례나 한계가 있는가
- 표·코드·이미지가 내용을 실제로 이해시키는가
- 이미지 안 짧은 한국어 설명과 HTML 캡션이 서로 모순되지 않는가
- 대표 이미지와 설명 이미지가 포괄적인 AI·컴퓨터 그림이 아닌가
- 이미지가 WebP, 1200×630, 장당 256KB, 전체 2MB 이내인가
- 광고가 정확히 1개이며 전체 35~45% 위치에서 완결된 섹션 뒤에 있는가
- 관련 글 2개가 주제상 자연스럽고 `https://won0322.tistory.com/<숫자>` 형식의 실제 공개 글인가
- 데스크톱·모바일에서 좌우 여백, 표·코드 스크롤, 이미지 글자가 깨지지 않는가
- 본문에 `style=`이나 중첩 패딩, 중복 제목이 없는가
- 최근 60일과 같은 URL 또는 사실상 같은 주제가 없는가
- 최종 가드가 `COMPLETE`이고 커밋·푸시·배포 확인이 각각 한 번뿐인가
