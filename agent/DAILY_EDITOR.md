# 쑥쑥자라나라 실전 IT 아티클 편집 계약

원고를 쓰기 전에 `agent/READER_QUALITY_LOOP.md`를 함께 읽고, 8.5 미달을
사용자 재실행 요청으로 넘기지 않는 공통 자동 복구 계약을 적용합니다.
먼저 `agent/WEEKLY_PIPELINE.md`에서 06:30 수집·09:00 제작·사용자 수동 발행
경계와 월·수의 서로 다른 선정 통과선을 확인합니다.
이어서 `agent/WEEKLY_READER_PROMISES.md`를 읽고 공통 디자인 골격과 월·수의
독자 약속을 적용합니다. 새 원고의 `editorial.reader_path`는 선택 사항이 아닙니다.
이미지를 만들기 전 `agent/WEEKLY_VISUAL_PROMISES.md`를 읽고 월요일의
`practical_diagnosis` 또는 수요일의 `change_impact` 역할을 실제 브리프에 적용합니다.

이 문서는 매주 월·수 09:00 KST에 실행되는 Codex 편집자의 유일한 작업 계약입니다. 예약 실행은 한 번만 수행하며 자동 재실행 슬롯을 두지 않습니다. GitHub Actions의 수집 결과는 주제를 찾는 레이더로만 사용합니다. 기준을 통과하면 소식 요약이 아니라 실제 문제, 작동 원리, 예시, 선택 기준을 남기는 실전 IT 아티클 1건을 만들고, 통과하지 못하면 발행 횟수를 채우기 위해 글을 만들지 않습니다. 티스토리 붙여넣기와 발행은 사용자가 직접 합니다.

월요일과 수요일은 같은 글을 날짜만 바꾸어 만들지 않습니다. 월요일 `evergreen_problem`은 오래 검색되는 개발 문제와 재사용 가능한 해결 기준을 남기고 `개발 가이드`에 넣습니다. 수요일 `change_explainer`는 최근 변화가 기존 사용·개발 흐름을 어떻게 바꾸는지 확인하고 `IT 트렌드 해설`에 넣습니다. 월·수 외 날짜에는 이 계약으로 새 원고를 만들지 않습니다.

## 운영 흐름

1. `agent/REPOSITORY_SYNC.md`를 먼저 읽고 공통 동기화 계약을 적용한 뒤 당일 가드를 실행합니다.

   ```bash
   git fetch origin main
   git show-ref --verify --quiet refs/remotes/origin/main
   git rev-list --left-right --count HEAD...refs/remotes/origin/main
   python3 -m blog_pipeline.publishing.daily_guard --today
   ```

   `git fetch`는 독립 명령으로 한 번만 실행합니다. DNS·5xx·timeout이어도 캐시된 `origin/main`보다 로컬이 뒤처지지 않았으면 `OFFLINE_SAFE`로 계속합니다. 실제 분기, 인증·권한 실패, 원격 캐시 없음만 `BLOCKED`입니다.

   사용자가 수동으로 다시 실행했을 때 작업 트리가 더러우면 사용자 변경이라고 단정하지 않습니다. 먼저 `python3 -m blog_pipeline.publishing.publish_bundle --today --resume-check`를 실행합니다. `READY`면 당일 완성 묶음만 남은 상태입니다. 원고·이미지를 다시 만들지 않고 9단계 최종 가드·스테이징부터 복구합니다. `PARTIAL`이면 변경을 보존하고 중단합니다.

   과거 날짜의 뉴스 글이나 티스토리 발행이 누락됐어도 오늘 실행의 오류로 취급하지 않습니다. 누락일을 자동으로 소급 생성하지 않고, `--today`가 가리키는 오늘 초안만 `NEW`·`PARTIAL`·`COMPLETE`로 판단해 정상 진행합니다. 과거 글 복구는 사용자가 날짜를 지정해 별도로 요청할 때만 수행합니다.

   브라우저·Playwright 검증의 스냅샷, 로그, 원본 캡처는 저장소 루트가 아니라 `/tmp/blog-writing-qa/YYYY-MM-DD/`에서만 생성합니다. Playwright CLI도 그 임시 디렉터리에서 실행하고 저장소에는 최종 검증을 통과한 `docs/tistory/assets/YYYY-MM-DD/*.webp`만 남깁니다. Google Chrome 앱 실행 파일을 직접 호출하지 않습니다. GUI Chrome이나 사용자 프로필을 재사용하지 않고 Playwright CLI 또는 제공된 브라우저 도구만 사용합니다. 임시 검증 파일 때문에 작업 트리를 더럽히거나 사용자 파일을 자동 삭제하지 않습니다.

   - `COMPLETE`: 즉시 종료합니다. 원문 확인, 재집필, 이미지 재생성, 테스트, 커밋, 푸시를 반복하지 않습니다.
   - `PARTIAL`: 출력된 `reasons`의 누락 단계만 복구합니다. 이미 유효한 JSON·이미지·HTML은 다시 만들지 않습니다. 단, `quality_reader_access`는 중단 사유가 아니며 공통 독자 품질 루프로 원고 JSON을 자동 재편집합니다.
   - `NEW`: 아래 전체 흐름을 한 번만 수행합니다.

2. 먼저 `python3 -m blog_pipeline.collection.inbox_guard --kind news --today`를 실행합니다. `READY`면 후보함을 사용하고, `READY_WITH_RESEARCH_FALLBACK`이면 후보함의 부족 사유를 유지한 채 추가 후보와 직접 리서치까지 확인합니다. `RECOLLECT_REQUIRED`면 보존된 `latest.json`을 읽기 전에 `collect_news --today`를 같은 실행에서 한 번만 다시 수행하고 가드를 재실행합니다. 재실행 뒤에도 준비되지 않으면 이전 후보를 쓰지 않고 Codex 웹 리서치로 이동합니다.

   그다음 `docs/inbox/latest.json`의 `day`, `selection.editorial_lane`, `selected`, `problem_signals`, `candidates` 상위 10건에서 제목·날짜·출처·URL과 `durable_problem_score`, `weekly_lane_score`, `editorial_angle`, `search_feedback`만 읽습니다. 월요일 후보함은 `evergreen_problem`, 수요일 후보함은 `change_explainer`여야 합니다. `problem_signals`는 요즘IT·커뮤니티·편집 글에서 문제만 발견하는 보조 목록이며, `unknown_publication_date: true`는 원문에서 30일 이내 발행을 확인한 뒤에만 선택합니다. `search_feedback.existing_page_conflict: true`는 새 글 후보에서 제외하고, `search_feedback.demand_score > 0`는 제안 action이 `new_article`, `expand_cluster`, `supporting_article`일 때만 수요 신호로 사용합니다. 당일 후보함에 후보가 있으면 `selected`를 먼저 보고, 추천이 3건 미만이거나 적합한 주제가 없을 때는 `problem_signals`과 `candidates`의 서로 다른 발행처를 최대 10건까지 검토합니다. 후보함 전체 JSON을 문맥으로 읽지 않습니다.

   후보 하나의 공식 근거가 부족하거나 중복이라고 해서 전체 편집을 중단하지 않습니다. 검증 가능한 주제를 찾을 때까지 다음 대체 순서를 반드시 지킵니다.

   1. `selected`를 날짜·중복·독자 문제 기준으로 모두 검토합니다.
   2. 모두 탈락하면 `problem_signals`와 `candidates`에서 발표 후 30일 이내, 서로 다른 발행처의 상위 후보를 최대 10건까지 검토합니다. 요즘IT·GeekNews·Hacker News·Lobsters 같은 편집·커뮤니티 글은 문제 발견 단서로, 기업 기술블로그와 공식 문서는 구현·운영 근거로 구분합니다. 제목·날짜·출처·최근 글 중복으로 먼저 좁히고, 독자의 문제·원리·판단 기준으로 풀어낼 후보만 원문을 엽니다.
   3. 모두 75점 미만·중복·근거 부족이면 `python3 -m blog_pipeline.collection.collect_news --today`를 같은 실행에서 딱 한 번 다시 실행하고, 새 `selected`·`problem_signals`·`candidates` 상위 10건만 다시 평가합니다. 수집 결과가 실질적으로 같아도 반복 수집하지 않습니다.
   4. 재수집 뒤에도 없으면 Codex 웹 리서치로 공식 제품 블로그·변경 기록·표준·문서 최소 3곳과 독립 자료 1곳 이상을 직접 검색해 후보함에 없던 질문을 찾습니다.
   5. 첫 원문이 부정확하면 같은 사건을 억지로 보강하지 말고 다음 후보로 이동합니다. 공식 근거가 충분한 후보를 찾는 즉시 아래 집필 단계로 진행합니다.

   후보 원문이 `Could not resolve host`, DNS 오류, 502, 503, 504로 열리지 않으면 5초 뒤 한 번만 다시 확인합니다. 두 번 실패하면 해당 후보를 `temporary_source_unavailable`로 기록하고 즉시 다음 후보로 이동합니다. 일시적 네트워크 오류가 한 후보의 탈락 이유가 될 수는 있어도 전체 후보 검토를 멈추는 이유가 되어서는 안 됩니다. 한 후보의 원문 접근에 30초 이상 머물지 않습니다.

   기존 후보 평가, 1회 재수집, Codex 직접 리서치를 모두 끝낸 뒤에도 75점 기준이나 필수 품질 조건을 통과한 질문이 없을 때만 오류가 아닌 `NO_PUBLISH_QUALITY`로 종료합니다. 실제 검토한 후보 제목과 탈락 이유, 편집 점수, 재수집·직접 리서치 범위를 보고하고 원고·이미지·커밋·푸시를 만들지 않습니다. `BLOCKED`는 저장소 충돌·권한 문제 또는 모든 유효 후보의 원문이 일시적으로 열리지 않아 품질 판단 자체가 불가능할 때만 사용합니다. `selected` 일부만 확인했거나 `candidates`에 미검토 최신 공식 후보가 남아 있으면 중단하지 않습니다. 모든 유효 후보가 일시적 원문 접근 오류로만 남았더라도 같은 실행에서 대체 후보 검토를 끝낸 뒤 `BLOCKED`로 종료하며, 별도 예약 재실행 상태를 만들지 않습니다.

3. 다음 기준으로 오래 갈 실전 아티클 주제 1건을 고릅니다.

   - 월요일: 반복되는 오류·설정·선택 질문을 잡고 원리, 재현 또는 문서 비교, 실패 조건, 다시 쓸 판단표·체크리스트를 남깁니다. 단순 발표 대응형 `change_impact`는 월요일 글로 선택하지 않습니다.
   - 수요일: 최근 7일 안의 확인된 변화를 잡고 바뀐 전제, 영향받는 독자, 기존 방식과의 차이, 지금 확인할 행동과 아직 모르는 범위를 설명합니다. `change_impact`, `incident_trace`, `research_interpretation`, `troubleshooting` 중 하나를 사용합니다.

   - 독자가 실제로 바뀐 점을 이해하거나 적용할 수 있는가
   - 공식 발표·문서·데이터로 핵심 사실을 교차 확인할 수 있는가
   - 원리, 비교, 설정법, 영향, 한계를 한 흐름으로 깊게 설명할 수 있는가
   - 표·차트·타임라인·비교·동작 흐름 중 주제에 맞는 설명 시각물이 가능한가
   - 같은 URL은 최근 60일, `primary_query`·핵심 질문·주제는 최근 365일과 겹치지 않는가

   후보함에서는 예약 시각 기준 30일 이내 자료를 검토할 수 있지만, 최종 글의 핵심 단서는 최근 7일 안에 확인된 공식 발표·변경 기록·문서에서 선택합니다. 최신성은 동점자를 가르는 조건이며 같은 품질의 후보 사이에서만 우선순위에 반영합니다. 순수 릴리스 노트·가격·기능 발표는 시간이 지나도 남을 문제·원리·비교·사례와 연결되지 않으면 탈락시킵니다. 소식은 글을 여는 단서로만 쓰고, 본문의 80% 이상은 나중에도 쓸 설명·예시·트레이드오프로 구성합니다. 후보 하나를 요약해 재작성하지 말고, 검색자가 반복해서 묻는 질문 하나를 정한 뒤 공식·1차 자료와 독립 자료를 더 찾아 답합니다. 30일을 넘긴 자료는 배경 근거로만 사용할 수 있고 주제 선정의 최신 단서로 계산하지 않습니다.

   최종 주제는 `실전 개발 문제 해결`, `AI·업무자동화 활용`, `실제 프로젝트에서 다시 쓰일 기술` 중 하나와 연결돼야 합니다. 블로그의 기존 축과 이어지지 않는 화제성 기사, 원문을 요약하는 것 외에 새 가치가 없는 기사는 점수가 높아도 선택하지 않습니다. 관련 글은 같은 축의 오래가는 기준 글 1개와 직접 실행한 실험·프로젝트 글 1개를 우선합니다. 둘 중 어느 한 쪽도 자연스럽게 이어지지 않으면 역할을 억지로 채우지 말고 주제상 가장 가까운 공개 글만 선택합니다.

   후보끼리 비교할 때는 `검색 지속성 35 · 실제 문제 해결성 30 · 근거의 신뢰성 20 · 현재 관심도 10 · 기존 글 연결성 5`의 100점 편집 점수를 사용합니다. 월요일은 지속성·문제 해결성·재사용 산출물을 먼저 보고, 수요일은 최신 변화·독자 영향·행동 가능성을 먼저 보되 장기 질문과 연결되지 않는 발표 요약은 제외합니다. 총점 75점 이상이면서 `반복 검색 질문`, `공식 근거`, `원문에 없던 기여`, `기존 글 비중복`을 모두 충족한 후보만 집필합니다. 점수가 높아도 필수 조건 하나가 빠지면 탈락입니다. 이 점수는 수집기의 `lead_score`와 요일별 `weekly_lane_score`를 보완하며, 오래 검색되고 실제로 써먹을 수 있는 주제를 고르는 최종 기준입니다. 수집기는 독자 관련성 기준을 낮춰 추천 수를 채우지 않으며, 추천 5건도 같은 `topic_family`를 한 건만 포함합니다. 기준을 만족한 후보가 모두 중복이면 직접 조사로 새 문제를 찾고, 찾지 못하면 `NO_PUBLISH_QUALITY`로 종료합니다.

   같은 canonical URL은 제외합니다. 제목이 거의 같거나 결론이 같은 사건도 제외합니다. 후속 보도는 이전 글 이후 달라진 사실이 제목과 본문에 분명할 때만 선택합니다.

   수집기는 직전 2일에 사용한 원문 호스트, 직전 2일의 핵심 `topic_family`, 직전 4일에 제목·핵심 개체로 노출된 제품·회사 브랜드의 새 기사를 추천 5건에서 제외하고 전체 후보에만 남깁니다. `recent_publisher`, `recent_topic_family`, `recent_brands`가 기록된 후보를 일반 업데이트라는 이유로 되살리지 않습니다. 일반 연구 후보는 제품·서비스에 바로 적용할 수 있는 독자 문제와 검증 증거가 편집 기사보다 명확할 때만 선택합니다. 기술 주제가 달라도 목록에서 같은 회사 글로 먼저 읽히면 반복으로 판단합니다. 예외는 긴급 보안 취약점이나 대규모 서비스 장애처럼 독자가 당일 해야 할 행동이 달라진 경우만 허용합니다. 단순 기능 추가·가격·사용법·일반 연구에는 `rotation_exception`을 쓰지 않습니다. 긴급 예외라면 반복 브랜드를 제목에서 제외하고 패치 대상·영향받는 사용자·복구 행동처럼 새 핵심 대상을 앞세웁니다. 대표 이미지는 새 핵심 대상과 달라진 행동을 보여 주며 반복 회사 로고나 같은 제품 구도를 중심에 두지 않습니다.

4. 선택한 원문을 직접 열고 `primary_query`로 추가 조사합니다. 최소 다음 자료를 확보합니다.

   - 핵심 사실을 발표한 공식 원문 1개
   - 설정·수치·동작을 확인할 공식 문서나 사양 1개
   - 맥락이나 한계를 보완할 독립 자료 1개 이상
   - 블로그 안에서 자연스럽게 이어지는 관련 글 2개

   참고 자료는 보통 3~6개로 제한합니다. 검색 결과 요약만 인용하지 않고 실제 페이지에서 날짜, 수치, 전제, 적용 범위와 예외를 확인합니다.

   공식 문서에서 확인 가능한 `적용 범위·요금·선행 조건·다른 설정과의 우선순위·작동 확인 신호·실패 또는 롤백 조건`을 먼저 표로 메모합니다. 해당되는 항목은 본문 설정법이나 체크리스트에 넣고, 찾지 못한 항목은 추측하지 않습니다. 관련 글은 `https://won0322.tistory.com/<숫자>` 형식의 실제 공개 글만 사용합니다. GitHub Pages 미리보기 링크나 다른 블로그 링크를 내부 관련 글로 넣지 않습니다.

여러 GitHub 저장소·공식 문서·Agent Skills를 엮는 생태계 지도, 도구 비교, 개발자 커리어 분석은 이 작업에 섞지 않고 금요일 `agent/SATURDAY_AUTOMATION.md`가 담당합니다. 월요일은 하나의 오래가는 문제 해결, 수요일은 확인된 최신 변화의 영향에 집중합니다.

5. `data/days/YYYY-MM-DD.json`을 `lead-story-v1` 형식으로 한 번에 작성합니다. 이미지 생성 전에 원고 사전검사를 실행합니다.

   ```bash
   python3 -m blog_pipeline.publishing.daily_guard --today --source-only --window-days 365
   ```

   `READY`일 때만 다음 단계로 갑니다. `PARTIAL`이면 출력된 `expected_identity`, `editorial_lengths`, `invalid_scene_labels`, `depth`, `duplicates`에서 실패한 JSON 필드만 고쳐 같은 명령을 다시 실행합니다. 원고 사전검사가 실패한 상태에서는 이미지와 HTML을 만들지 않습니다.

6. 기사 고유 대표 이미지 1장은 Codex 이미지 생성으로 만들고, 본문 설명 이미지는 기본 2장, 서로 다른 세 번째 설명 지점이나 실제 증거가 꼭 필요할 때만 최대 4장까지 생성·직접 캡처·실측 차트로 준비합니다. 필요한 장수는 글의 실제 설명 지점으로 결정하며, 장수를 채우기 위한 장식 이미지와 같은 이미지의 변형본은 만들지 않습니다. 생성 전에 대표 브리프를 `visual.cover`, 본문 브리프를 `visual.assets`에 기록합니다. 둘 다 아래 필드를 사용하되 대표는 `content_role: hook`, 본문은 `content_role: explanation`으로 기록합니다. 모든 `label`은 서로 다른 질문이어야 하며 대표가 답한 비교·순서·결과를 본문 이미지에서 다시 만들지 않습니다.

   2026-09-02 이후에는 요일별 이미지 역할을 먼저 확정합니다. 월요일은 `visual.weekday_profile: practical_diagnosis`, 대표 `weekday_role: problem_scene`, 본문 필수 `teaching_role: diagnosis_flow`, `recovery_boundary`를 사용합니다. 수요일은 `visual.weekday_profile: change_impact`, 대표 `weekday_role: changed_condition_scene`, 본문 필수 `teaching_role: before_after_change`, `action_check`를 사용합니다. 프로필과 대표 역할은 `visual.cover`·`images.cover`에, 각 교육 역할은 브리프·대응 `images.visual_N`에 똑같이 기록합니다. 정확한 허용 `logic_type`은 공통 이미지 약속을 따릅니다.

   - `label`: 이미지가 답할 핵심 질문
   - `scene_label`: 기사 고유 시각 단서 2~4개
   - `steps`: 원인 → 결과, 이전 → 이후, 비교, 시간, 데이터 흐름 중 보여줄 관계
   - `curiosity_hook`: 독자가 먼저 발견할 선택, 막힌 지점, 의외의 결과 같은 시각적 질문
   - `evidence_type`: 생성 도식은 `diagram`, 실제 제품·문서 화면은 `screenshot`, 확인된 수치 시각화는 `chart`
   - `origin`: 실제 캡처 `capture`, 주석 캡처 `annotated_capture`, 실측 차트 `measured_chart`, Codex 생성 도식 `imagegen` 중 하나
   - `logic_type`: `flow`, `before_after`, `comparison`, `conditional`, `timeline`, `architecture`, `evidence` 중 하나
   - `condition`: `logic_type`이 `conditional`일 때만 쓰며 `DNS·IP를 변경한 경우`처럼 분기 조건을 정확히 기록

   2026-08-26 이후 `visual.cover`와 `images.cover`에는 서로 같은 `editorial_treatment`, `focal_subject`, `texture_cue`, `authenticity_cue`를 기록합니다. `editorial_treatment`는 `tactile_realism`, `documentary_closeup`, `quiet_minimalism`, `playful_surrealism`, `local_workplace` 중 주제에 맞는 하나를 선택합니다. 유행 스타일을 복제하지 말고 실제 물건·질감·불완전한 사용 흔적·국내 작업 환경 중 주제를 설명하는 단서만 사용합니다. `images.cover.alt`는 15~160자로 `primary_query`나 `focal_subject`의 실제 대상을 설명하고, 파일명도 `cover.webp`처럼 포괄적으로 짓지 않습니다.

   2026-07-29 이후 대표 브리프와 `images.cover`에는 `cover_kind: editorial_scene`과 서로 같은 `art_direction`, `composition_type`, `palette_family`을 기록합니다. 2026-08-04 이후에는 두 곳에 같은 `render_family`도 기록하며 값은 `photorealistic_natural`, `editorial_collage`, `flat_illustration`, `ink_drawing`, `isometric_model`, `tactile_paper`, `macro_object` 중 하나입니다. 최근 3개 글과 같은 `render_family`은 쓰지 않습니다. 대표 이미지 생성 프롬프트는 장면 성격에 맞게 `Use case: illustration-story`, `Use case: photorealistic-natural`, `Use case: stylized-concept` 중 하나로 시작하고 `Asset intent: editorial-scene`을 포함하며 `infographic-diagram`으로 시작하지 않습니다. 최근 7개 대표 이미지와 세 값이 모두 같은 조합은 재사용하지 않습니다. 브랜드 일관성은 고정된 카드 틀이나 고정 팔레트가 아니라 여백, 정보 정확도, 짧은 한국어, 선명한 초점으로 유지합니다.

   대표 이미지는 정보 전체를 요약하는 교재 도식이 아니라 독자가 글을 열 이유가 되는 한 장면이어야 합니다. 실제 대상과 막힌 지점·선택·의외의 결과 중 하나를 크게 보여 주고, 필요하면 주제와 직접 관련된 사람·손·물건·공간을 사용합니다. 단, 포괄적인 개발자와 노트북 장면은 금지합니다. `editorial_scenario`, `single_object_conflict`, `cutaway_process`, `before_after_scene`, `annotated_closeup`, `spatial_comparison`처럼 주제에 맞는 아트 디렉션을 선택합니다. 대표 이미지에는 단계 화살표·여러 카드·표·차트·로드맵·흐름도를 넣지 않습니다. 같은 아이보리 배경·네이비/청록/주황·3단 카드 구성을 기본값으로 삼지 않습니다. `three_column_cards`, `four_step_cards`, `centered_dashboard_grid`, `title_slide`, `linear_flow`, `process_diagram`, `roadmap`, `comparison_grid`, `timeline_cards`, `split_panel_infographic`, `dashboard`는 대표 이미지 구성으로 금지합니다. 반대로 본문 이미지는 정확한 흐름도·비교표·구조도를 맡으며 대표와 색·구도·질문을 반복하지 않습니다.

   대표 이미지의 한국어 라벨은 없거나 1~3개만 사용하고, 제목과 본문 요약을 이미지 안에 다시 써 넣지 않습니다. 정확한 절차·비교·수치는 본문 이미지에서만 2~6개의 짧은 라벨로 설명합니다.

   설명 도식에는 모바일에서도 읽히는 짧은 한국어 설명을 직접 넣습니다. 불가피한 제품명·표준명·코드 외에는 영어 문장을 쓰지 않습니다. 세부 의미와 출처는 정확한 HTML 캡션으로 보충합니다. 파일은 `일반업데이트-보안업데이트-비교.png`처럼 내용을 알 수 있는 한글 파일명을 사용합니다.

   제목을 가렸을 때도 해당 기사만 떠올릴 수 있도록 실제 대상·변화·관계를 보여 줍니다. 핵심 대상은 화면의 약 45~70%를 차지하게 하고 작은 모바일 썸네일에서도 흐름이 읽혀야 합니다. 설명 이미지 유형은 다음처럼 주제에 맞게 고릅니다.

   - 과정: 타임라인, 전후 흐름, 분기, 검증 게이트
   - 차이: 두 방식 비교, 위험도별 단계, 조건별 선택
   - 수치: 단위·기간·출처가 확인된 간단한 차트
   - 구조: 구성 요소와 데이터 이동을 보여 주는 아키텍처 도식
   - 사용법: 실제 설정과 동작 결과를 연결한 예제 그림

   조건부 사건은 필수 순서의 가운데에 놓지 않습니다. `~한 경우`, `변경 시`, `실패했을 때` 같은 조건 라벨을 단 별도 분기로 그립니다. 대표는 문제·결과를 한 장면으로 보여 주고, 본문 이미지는 원리·비교·조건·실제 조작을 맡아 같은 구도를 반복하지 않습니다.

   직전 글과 본문 이미지의 `logic_type` 순서 전체가 같으면 안 됩니다. 최근 두 글의 본문 이미지가 모두 `imagegen`이었다면 이번 글에는 실제 캡처·주석 캡처·실측 차트 중 하나를 반드시 넣습니다. `hands_on_test`와 `troubleshooting`은 실제 증거를 최소 1개, `research_interpretation`은 주석 캡처 또는 실측 차트를 최소 1개 사용합니다. 이 세 유형은 본문 시각물도 최소 3개입니다.

   설정·사용법이 핵심인 글은 실제 제품 화면이나 공식 문서 화면 1장을 우선 사용합니다. 직접 캡처한 화면은 계정·IP·토큰·개인정보를 가리고 `capture_note`를 기록합니다. 공식 화면은 `source_url`을 기록하고 캡션에 출처를 밝힙니다. 공개 화면을 확보할 수 없으면 `visual.screenshot_unavailable_reason`과 정확한 메뉴 경로를 남깁니다. 생성 이미지로 가짜 UI·가짜 터미널·가짜 측정 화면을 만들지 않습니다. 문서·제품 화면은 `--full-page` 전체 페이지 캡처를 금지하고, 본문에서 설명할 제목·코드·설정이 한 화면에 읽히는 뷰포트 또는 요소 단위로 캡처합니다. 1200×630 변환 후에도 내용이 가느다란 세로 띠가 되거나 390px 모바일에서 핵심 텍스트를 읽을 수 없으면 발행하지 않습니다.

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

9. 공통 동기화 계약에서 실제 분기가 없음을 확인한 상태로 최종 가드와 당일 발행 묶음 검사를 진행합니다. 네트워크 오류만으로 검증·스테이징·로컬 커밋을 막지 않습니다.

   ```bash
   python3 -m blog_pipeline.publishing.daily_guard --today --require-complete --window-days 365
   python3 -m blog_pipeline.publishing.publish_bundle --today --stage
   python3 -m blog_pipeline.publishing.publish_bundle --today --check
   git diff --cached --check
   ```

   `publish_bundle`은 원고 JSON, 메타, 본문·광고 분할본, AdFit 결합본, 미리보기, 이미지, 루트 발행 도우미를 한 묶음으로 취급합니다. `READY`가 아니면 커밋하거나 완료로 보고하지 않습니다. 로컬에만 남은 파일을 저장소 정책상 제외 파일이라고 추측하지 않습니다.

10. 모든 기준을 통과하고 실제 diff가 있을 때 하나의 로컬 커밋으로 확정한 뒤 공통 계약의 `python3 -m blog_pipeline.publishing.repository_sync push --remote origin --ref main`을 한 번 실행합니다. 이 명령 내부의 일시적 네트워크 최대 5회 재시도까지 실패하면 커밋을 보존하고 `LOCAL_COMPLETE`, push 성공 뒤 API 확인만 실패하면 `REMOTE_PUSHED_VERIFY_PENDING`으로 보고합니다. 푸시와 `Publish reviewed drafts`, 공개 Pages의 실제 조립·복사 흐름이 모두 확인된 경우만 `COMPLETE`입니다. 사용자 인계 지점은 GitHub Pages 루트의 `오늘 글 발행 준비` 페이지 하나입니다. 새 결과를 별도 페이지로만 남기지 말고 반드시 이 페이지의 당일 카드에 제목·카테고리·태그·대표 이미지·광고 조립·미리보기·최종 HTML이 모두 연결됐는지 확인합니다. 티스토리에는 자동 발행하지 않습니다.

## 단일 실행과 토큰 원칙

- 완료 표시는 `daily_guard`의 `COMPLETE`, `publish_bundle`의 `READY`, 원격 Pages 배포 성공과 공개 루트 확인을 모두 충족한 상태입니다.
- `COMPLETE` 날짜는 사용자가 명시적으로 재작성을 요청하지 않는 한 읽기 전용입니다.
- 한 실행에서 같은 JSON·이미지를 처음부터 두 번 만들지 않습니다.
- 한 실행에서 커밋 1회, 배포 명령 1회를 넘기지 않습니다. 배포 명령 내부의 제한 재시도는 중복 작업으로 세지 않습니다.
- 기본 문맥은 당일 후보 5건, 선택 원문 1개, 보조 자료, 최근 60일 URL과 최근 365일 `primary_query`·제목뿐입니다.
- 저장소 전체, 과거 본문 전체, 이미지 바이너리를 불필요하게 문맥으로 읽지 않습니다.
- 결정적 Python 도구가 HTML·AdFit 삽입·미리보기·검사를 맡고, Codex는 선정·조사·집필·이미지 판단에 집중합니다.

## 실전 아티클 구성

- 제목은 `핵심 검색어 + 구체적으로 달라진 대상·상황·결과`로 만듭니다. 핵심 검색어는 한 번만 쓰고 앞 20자 안에 자연스럽게 배치합니다. 제목에서 `독자에게 미치는 영향`, `우리에게 중요한 이유`처럼 글의 효용을 설명하지 말고 실제 제품·기능·문제·결과를 직접 말합니다. 보통 35~60자 안에서 모바일 2~3줄을 목표로 하며 `충격`, `역대급`, `무조건 봐야` 같은 클릭베이트와 검색어 나열은 금지합니다.
- 태그 5~8개는 `핵심 제품·기술`, `독자가 겪는 문제`, `세부 기능·설정`, `사용 상황`을 섞습니다. `AI`, `IT`, `뉴스`, `정보`처럼 내용과 연결되지 않는 넓은 단어로 칸을 채우지 않습니다. 최소 2개는 `primary_query`의 실제 검색어와 직접 연결합니다.
- 첫 5문장 안에 구체적인 장면, 확인된 변화, 계속 읽을 이유를 둡니다.
- `editorial.reader_hook`에는 독자가 마주친 구체적 `scene`, 방치했을 때의 `stakes`, 끝까지 읽고 얻는 `payoff`, 다음 문단을 여는 `open_question`을 각각 20~180자로 기록합니다. 네 값 중 최소 두 값의 핵심 단어가 실제 도입에 나타나야 하며, 내부 필드명을 본문에 노출하거나 클릭베이트 문장으로 바꾸지 않습니다.
- 기본 글은 약 8~12분 분량으로 씁니다. 다만 `change_impact`처럼 답이 짧고 분명한 변경 대응 글은 6~10분으로 끝내며 분량을 채우려고 배경 설명을 늘리지 않습니다. 소제목 5~7개를 사용합니다.
- 모바일에서 한 문단이 벽처럼 보이지 않도록 도입은 320자, 본문 문단은 220자를 넘기지 않습니다. 한 문단에는 한 생각만 두고 긴 조건은 표나 목록으로 나눕니다.
- 2026-09-01 이후 내보내기가 계산하는 `reader_scores.general_reader_understanding`과 `reader_scores.public_readability`는 둘 다 8.5 이상이어야 합니다. `quality_reader_access`가 나오면 보류 상태로 넘기지 말고 도입·긴 문단·연속 블록·넓은 표·긴 코드를 같은 실행에서 다시 편집한 뒤 재검사합니다.
- 월요일과 수요일의 `editorial.reader_path.reader_level`은 `practitioner`입니다. 월요일은 해결 순서와 실패 경계를, 수요일은 영향받는 조건과 지금 확인할 일을 본문 앞 절반 안의 실제 목록으로 보여 줍니다. 구현명·약어·버전 번호를 독자의 문제 장면과 먼저 할 일보다 앞에 쌓지 않습니다.
- 핵심 흐름은 `독자가 마주칠 문제 장면 → 왜 생기는지 → 작동 원리 → 실제 예시 → 선택과 트레이드오프 → 남는 기준`입니다. 주제에 맞게 순서를 바꾸되 단순 발표 요약으로 시작해 영향 정리로 끝내지 않습니다.
- 2026-08-04 이후 `editorial.article_shape`은 `change_impact`, `hands_on_test`, `decision_guide`, `incident_trace`, `troubleshooting`, `research_interpretation` 중 하나를 고릅니다. 직전 글과 같은 전개를 쓰지 않습니다. 사고·유출·장애처럼 한 지점의 문제가 여러 서비스나 사용자에게 번지는 주제는 `incident_trace`를 사용해 `발생 지점 → 데이터·서비스 이동 경로 → 확인된 영향과 미확인 범위 → 지금 할 일` 순서로 추적합니다. 고른 형태에 맞춰 독자의 실제 질문 순서로 소제목을 만들며 `무엇이 바뀌었나`를 모든 글의 첫 소제목으로 반복하지 않습니다.
- 실제 순서대로 따라 해야 하는 절차가 아니라면 모든 소제목에 번호를 붙이지 않습니다. 질문·장면·결과가 자연스럽게 이어지도록 제목 형식을 섞습니다.
- `editorial.revisit`에는 첫 방문용 `quick_answer`, 다시 활용할 수 있는 `reuse_case`, 막혔을 때 볼 `failure_case`, `artifact_type`, 다시 검토해야 할 변화 2~4개인 `update_triggers`를 기록합니다. 이는 편집자가 글의 지속 가치를 점검하는 내부 메타데이터일 뿐입니다. 값을 본문에 그대로 옮기거나 `다시 찾을 때`, `처음 읽기`, `적용할 때`, `막혔을 때` 같은 상자로 출력하지 않습니다. 글의 흐름에 필요한 핵심 답·실패 조건·변경 조건만 자연스럽게 설명합니다. `artifact_type`은 `command_recipe`, `configuration`, `decision_matrix`, `checklist`, `troubleshooting_tree`, `experiment_fixture` 중 하나입니다.
- `editorial.original_value`에 `durable_question`, `source_gap`, `contribution`, `proof_method`, `reader_outcome`, `limits`를 기록합니다. `proof_method`는 `executed_test`, `document_comparison`, `source_triangulation`, `configuration_walkthrough`, `incident_trace`, `measured_comparison` 중 실제 작업과 맞는 값을 쓰고, `contribution`에는 원문에 없던 비교·예제·실패 조건·적용 기준 중 적어도 하나를 구체적으로 남깁니다. `reader_question`을 복사하거나 원문 요약을 새 가치로 포장하지 않습니다.
- `code`, `table`, `ul`이 실제로 복사·비교·점검에 유용할 때만 최대 하나에 `reusable: true`와 구체적인 `reuse_label`을 내부 메타데이터로 넣습니다. 뉴스 주제에 맞지 않으면 재사용 블록을 만들지 않습니다. 이 메타데이터는 별도 제목·상자·배지로 출력하지 않습니다.
- 표는 비교가 실제로 쉬워질 때 1~3개 사용합니다. 설정·코드가 핵심이면 복사 가능한 코드 예제를 넣습니다.
- 본문 설명 이미지 2~4장을 관련 문단 직후에 배치하고, 캡션은 그림에서 읽어야 할 결론을 설명합니다.
- 참고 자료 목록과 관련 글 2개를 본문 하단에 둡니다.
- `quiz`, `terms`, 억지 목차, 반복 요약은 넣지 않습니다.
- 광고 태그는 글마다 1개만 유지하고, 첫 번째 완결된 핵심 설명 뒤 전체 비광고 블록의 35~45% 위치에 `ad_break`를 둡니다. 블록 순서는 반드시 `완결 문단·표·목록·코드·인용 → ad_break → 다음 h`여야 하며 `h → ad_break → 첫 설명`은 금지합니다.
- 제목·도입·표·이미지·마무리에서 같은 문장을 바꿔 쓰며 반복하지 않습니다.

## 검색 노출을 실제 클릭으로 연결하기

- `config/search_opportunities.json`이 30일 이내 자료이면 먼저 확인합니다. 노출은 있지만 클릭이 없는 검색어는 현재 주제가 그 질문에 정확히 답할 때만 사용합니다. 관련 없는 뉴스에 인기 검색어를 억지로 붙이지 않습니다.
- 먼저 독자가 입력할 짧은 질문 하나를 `editorial.search_intent.query`로 확정합니다. 제목 앞 20자 안에 이 문구를 그대로 자연스럽게 넣고, 첫 두 문단에서 `reader_need`에 답하기 시작합니다.
- `editorial.search_intent`에는 `query`, 그 검색어를 쓴 사람이 해결하려는 상황 `reader_need`, 표·코드·비교·실행 순서 중 답을 보여 줄 방식 `answer_format`을 기록합니다. 이는 내부 편집 메타데이터이며 본문에 항목명으로 노출하지 않습니다.
- 관련 글은 `foundation` 1개와 `next_step` 1개를 우선합니다. `foundation`은 지금 글의 전제나 원리를 설명하고, `next_step`은 바로 이어서 적용할 설정·실험·가이드로 연결합니다. 단순히 최신 글이거나 같은 제품명이라는 이유만으로 넣지 않습니다.

## 문체와 사실 기준

- 차분한 개발자가 친구에게 방금 확인한 내용을 설명하듯 씁니다. 정확한 정보는 유지하되 문서 요약이나 브리핑처럼 항목만 늘어놓지 않습니다.
- 도입은 `업데이트가 발표됐다`가 아니라 독자가 실제로 마주칠 장면·막힌 순간·선택에서 시작합니다. 이후 사실을 자연스럽게 연결하고, 해석은 근거 바로 다음 문장에 둡니다.
- 짧은 문장과 조금 긴 설명을 섞고, 문단마다 한 생각만 담습니다. 모든 소제목을 같은 문장형으로 만들거나 매 장을 표·목록으로 끝내지 않습니다.
- `개요`, `현황`, `분석`, `결론`, `시사점`처럼 보고서에서 떼어 온 한 단어 소제목은 쓰지 않습니다. 독자가 실제로 궁금해할 질문이나 결과를 소제목으로 씁니다.
- `독자에게 미치는 영향`, `사용자에게 미치는 영향`, `개발자에게 미치는 영향`, `우리에게 미치는 영향`, `왜 중요한가`, `독자가 얻는 것`처럼 편집 의도를 드러내는 소제목도 쓰지 않습니다. 사실 바로 뒤에 그 사실이 바꾸는 실제 장면을 한두 문장으로 연결하고, 다음 소제목은 `기존 검색 범위가 달라진다`, `권한이 없으면 여기서 멈춘다`처럼 기사 고유 대상과 결과를 말합니다.
- 원문 요약 뒤에 별도의 '영향' 장을 붙이지 않습니다. `확인된 사실 → 작동 이유 → 실제 사용 장면 또는 선택 → 한계`가 문단 사이에서 이어지게 쓰고, 각 장에는 새로운 정보가 있어야 합니다.
- `이번 글에서는`, `살펴보겠습니다`, `알아보겠습니다`, `다음과 같습니다`, `결론적으로`, `도움이 되길 바랍니다` 같은 상투 문구는 쓰지 않습니다.
- `정리해보겠습니다`, `개발자 편집자의 견해`, `승원의 메모`, `자동화로 작성했습니다` 같은 문구를 쓰지 않습니다.
- 직접 하지 않은 일을 체험담처럼 쓰지 않습니다. 판단은 근거 다음 문장에 자연스럽게 녹입니다.
- 첫 문단에서 결론을 모두 요약하지 않고 구체적인 장면이나 질문으로 시작합니다.
- 원문 문장을 길게 복사하지 않습니다. 사실은 새 문장으로 설명하고 자료 링크를 둡니다.
- 수치에는 조사 대상, 기간, 단위, 비교 기준을 함께 씁니다. 조건을 찾지 못하면 단정하지 않습니다.
- 공식 자료와 기사 설명이 다르면 공식 자료를 우선하고 차이를 밝힙니다.
- 관찰, 공식 주장, 작성자의 추론을 섞지 않습니다. 확인할 수 없는 내용은 빼거나 한계를 명시합니다.

## 저장 형식

당일 파일은 `schema_version: 3`, `format: lead-story-v1`을 사용합니다.

- 식별 필드는 정확히 `draft_id: YYYY-MM-DD`, `publish_date: YYYY-MM-DD`, `date_label: YYYY. M. D`, `weekday: 월|수`, `content_type: daily_news`, `publication_mode: manual_review`, `scheduled_at: YYYY-MM-DDT09:00:00+09:00`으로 기록합니다. `scheduled_at`은 Codex 제작 시작 기준이며 티스토리 예약 발행 시각이 아닙니다. 월요일은 `content_label: 개발 가이드`, `category: 개발 가이드`, `editorial.weekly_lane: evergreen_problem`이고, 수요일은 `content_label: IT 트렌드 해설`, `category: IT 트렌드 해설`, `editorial.weekly_lane: change_explainer`입니다. 티스토리의 `실전 IT`는 큰 묶음이므로 글을 직접 넣지 않고 해당 하위 카테고리를 선택합니다.
- `primary_query`, `tags`
- `visual.subject`, `hook`, `motif`, `assets`
- `editorial.headline`, `opening`, `closing`, `action`. `action`은 별도 행동 유도 상자로 출력하지 않고 `closing` 뒤에 자연스러운 마지막 문장으로 이어집니다. 주제상 행동 제안이 어색하면 관찰하거나 다시 확인할 조건을 한 문장으로 적습니다.
- `editorial` 확장 필드: `audience_problem`, `reader_takeaway`, `why_now`, `topic_key`, `reader_question`, `entities`, `coverage`, `article_shape`, `weekly_lane`, `reader_hook`, `reader_path`, `revisit`, `search_intent`, `original_value`. `reader_hook`에는 `scene`, `stakes`, `payoff`, `open_question`을 기록합니다. `reader_path`에는 `reader_level: practitioner`, 실제 첫 소제목과 같은 `entry_heading`, 초반 답인 `immediate_answer`, 본문 앞 절반의 목록과 연결되는 `action_steps` 2~5개, 마지막 확인 문장과 연결되는 `completion_check`를 기록합니다. `search_intent`에는 `query`, `reader_need`, `answer_format`을 기록합니다. `original_value`에는 `durable_question`, `source_gap`, `contribution`, `proof_method`, `reader_outcome`, `limits`를 기록합니다. `freshness_exception`은 2026-08-25 이전 산출물을 위한 호환 필드일 뿐 새 아티클에 추가하지 않습니다.
- `news` 정확히 1건: `title_kr`, `source`, `url`, `published_at`, `blurb_kr`, `references`, `content`
- `content` 블록: `h`, `p`, `table`, `visual`, `code`, `ul`, `quote`, `ad_break`
- `related_posts` 2건 이상: `config/tistory_public_posts.json`에 있는 실제 공개 URL만 사용하고 각 항목의 `title`, `url`, 현재 글과 연결되는 이유 `reason`, 연결 역할 `role`을 기록합니다. 역할은 `foundation`과 `next_step`을 각각 1개 이상 포함합니다.
- `generation`, `images.cover`, `images.visual_1`부터 실제 사용 이미지까지

모든 `visual_N`은 `content`에서 실제로 한 번 이상 사용합니다. `coverage`는 `change`, `mechanism`, `comparison`, `application`, `limits`, `decision`을 모두 포함합니다. `decision`은 별도 체크리스트를 강요하는 항목이 아니라 독자가 선택하거나 확인할 기준이 본문에 자연스럽게 설명됐는지 확인하는 내부 분류입니다. 태그는 중복 없이 5~8개, 참고 자료는 3~6개로 공식 발표·문서와 독립 자료를 모두 포함합니다. `generation.provider`는 `codex-agent`, `generation.model`은 실제 사용 모델 ID, `generation.revision`은 7 이상을 기록합니다. `generation.image_provider`는 전부 생성 이미지면 `codex-imagegen`, 생성 이미지와 실제 캡처·실측 차트를 함께 쓰면 `mixed`로 기록하며 비워 두거나 결정적 대체기 이름을 넣지 않습니다. 최적화 명령이 `generation.image_policy`를 `webp-v1`으로 기록합니다. `author_note` 필드는 금지합니다.

`editorial` 문자열 길이는 `headline 25~60`, `opening 120~600`, `closing 100~1000`, `action 30~500`, `audience_problem 40~500`, `reader_takeaway 40~500`, `why_now 40~500`, `topic_key 6~100`, `reader_question 30~300`자입니다. 실제 발행 대상의 도입은 320자 이하로 씁니다. `visual.assets[*].scene_label`은 쉼표로 합친 문자열이 아니라 비어 있지 않은 문자열 2~4개의 JSON 배열로 기록합니다.

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
- 광고가 정확히 1개이며 전체 35~45% 위치에서 `완결 문단·표·목록·코드·인용 → 광고 → 다음 소제목` 순서인가
- `editorial.revisit` 값이 별도 내부 메모 상자로 노출되지 않고 본문에 자연스럽게 반영됐는가
- 관련 글 2개가 주제상 자연스럽고 `https://won0322.tistory.com/<숫자>` 형식의 실제 공개 글인가
- 데스크톱·모바일에서 좌우 여백, 표·코드 스크롤, 이미지 글자가 깨지지 않는가
- 본문에 `style=`이나 중첩 패딩, 중복 제목이 없는가
- 같은 URL은 최근 60일, 사실상 같은 `primary_query`·주제는 최근 365일에 없는가
- `editorial.original_value`의 새 기여와 증명 방법이 본문에 실제로 반영됐는가
- 최종 가드가 `COMPLETE`이고 커밋·푸시·배포 확인이 각각 한 번뿐인가
