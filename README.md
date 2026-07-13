# Blog Writing

여러 IT·AI 출처에서 매일 글감을 모으고, 내 GitHub 저장소 안에서 티스토리용 초안까지 만드는 자동화입니다. 다른 사람의 뉴스 저장소에는 의존하지 않습니다. GitHub 저장소 Secret에 `GEMINI_API_KEY`가 있으면 Gemini를 먼저 쓰고, 실패하면 GitHub Models로 자동 전환합니다.

자동화가 만든 결과는 바로 발행하지 않습니다. 뉴스 후보와 원문 링크, AI가 정리한 초안을 확인하고 내 의견을 더한 뒤 티스토리에 직접 붙여넣는 흐름입니다.

## 매일 자동 흐름

```text
07:28 KST GitHub Actions 실행
           AI타임스 인기기사·GeekNews·요즘IT·공식 AI/개발 피드·arXiv에서 글감 수집
           URL/유사 제목 중복 제거와 최신성·관심 키워드 점수 계산
           일상에 닿는 소식 → 바로 쓰는 도구 → 깊이 있는 기술 순으로 3건 선정
           docs/inbox/YYYY-MM-DD.html 및 JSON 생성
           선정된 원문 3건의 공개 본문을 실행 중에만 제한적으로 읽어 근거 보강
           Gemini 또는 GitHub Models로 7~9분 분량의 사실·독자 영향·개발자 관점·확인할 점 생성
           기사마다 '승원의 메모 · 자료 기반 해석' 생성(가짜 사용 경험은 차단)
           정처기 문제와 개발 용어를 글 뒤쪽 복습 콘텐츠로 구성
           data/days/YYYY-MM-DD.json에 자체 원본 저장
           기사의 핵심 흐름을 폰·사진·관측 데이터·서버 장면으로 대표·본문 이미지 생성
           docs/tistory/YYYY-MM-DD.html 및 JSON 생성
           저장소에 자동 커밋하고 GitHub Pages 배포
```

티스토리 초안 복사 페이지:

```text
https://seung-won-yu.github.io/blog-writing/
```

뉴스 후보 검토 페이지:

```text
https://seung-won-yu.github.io/blog-writing/inbox/
```

## API 키와 비용

현재 저장소는 GitHub Actions Secret의 `GEMINI_API_KEY`를 Gemini 텍스트 초안에 사용합니다. 키는 요청 헤더로만 전송하며 코드, 결과 파일, GitHub Pages, 브라우저 JavaScript에 넣지 않습니다. Secret이 없거나 Gemini 모델 요청이 실패하면 workflow가 실행될 때 GitHub가 잠시 발급하는 `GITHUB_TOKEN`과 `models: read` 권한으로 GitHub Models를 호출합니다.

Gemini는 `gemini-3.5-flash`를 먼저 시도하고 `gemini-3-flash-preview`, `gemini-3.1-flash-lite` 순으로 텍스트 모델을 재시도합니다. 이후 기본 GitHub 모델 `openai/gpt-4o-mini`로 전환합니다. 외부 기사와 히스토리가 길어져도 입력을 보수적으로 7,600토큰 이하로 줄입니다. 첫 응답이 짧거나 상투적이거나 실제 7분 분량에 못 미치면 본문과 편집 문단만 최대 두 번 다시 작성합니다. 무료 한도와 모델 제공 상태는 각 서비스 정책에 따라 바뀔 수 있습니다.

예약 실행과 push 실행은 유료 이미지 사용을 활성화하지 않습니다. GitHub 계정에서 별도로 paid usage를 켜지 않았다면 무료 텍스트 한도 초과 시 모델 요청이 차단되고, 자동화는 수집된 제목과 피드 요약만 사용하는 최소 초안으로 전환됩니다.

- `GEMINI_API_KEY`는 선택 사항이며 현재 저장소에는 Actions Secret으로 등록
- OpenAI API 키 필요 없음
- 티스토리 로그인 정보 필요 없음
- Gemini 키는 GitHub Pages에 노출되지 않음
- 저장소 쓰기 권한이 없는 방문자는 수동 workflow를 실행할 수 없음
- 기본 이미지는 API 키 없이 Pillow로 무료 생성
- 수동 실행의 `유료 Gemini 이미지` 체크 시에만 같은 Secret으로 이미지 API 호출

기본 대표 이미지는 구체적인 대상과 짧은 질문만 남기고, 본문 이미지는 제목·출처·설명 문구를 이미지 안에 반복하지 않는 텍스트 없는 장면형 일러스트로 생성합니다. 예를 들어 사진 AI 기사는 휴대폰 사진, AI 연동, 사용자 통제 장면으로 표현합니다. 기본 경로에는 추가 API 비용이 없으며 이미지 생성만 실패해도 뉴스 수집과 텍스트 초안은 그대로 남습니다.

Google의 현재 Gemini 이미지 모델은 무료 티어가 없습니다. 그래서 예약·push 실행은 계속 무료 Pillow 이미지를 사용합니다. 저장소 소유자가 Actions의 `Run workflow`에서 `유료 Gemini 이미지`를 직접 체크한 경우에만 대표 1장과 본문 3장을 만듭니다. 기본 `gemini-3.1-flash-lite-image`는 1K 한 장 약 US$0.0336, 네 장 약 US$0.1344입니다. 더 나은 품질의 `gemini-3.1-flash-image`도 선택할 수 있으며 한 장 약 US$0.067, 네 장 약 US$0.268입니다. 입력 토큰 비용은 소액 더해질 수 있습니다. 유료 요청이 하나라도 실패하면 기존 무료 이미지 파일을 그대로 유지하지만, 실패 전에 성공한 요청에는 일부 비용이 발생할 수 있습니다.

기사 원본 사진은 자동 복제·편집하지 않습니다. 크롭, 필터, 글자 삽입을 해도 원본 저작권이 사라지지 않고 상업적 블로그에서는 위험할 수 있기 때문입니다. 원본은 본문의 `원문 보기` 링크로 안내하고, 자동화는 허용된 제목·요약에서 확인한 구조만 새 이미지로 제작합니다.

정보처리기사 문제는 뉴스 기사에서 모델이 즉석으로 만들지 않습니다. 검증한 문제은행에서 5개 필기 과목의 문항을 날짜별로 골라 붙이며, 최근 출제된 질문은 가능한 한 피합니다. 선택지는 본문에 `1.`부터 `4.`까지 직접 표시하므로 티스토리 스킨이 목록 마커를 숨겨도 정답 번호와 어긋나지 않습니다.

관련 공식 문서:

- [GitHub Models 빠른 시작](https://docs.github.com/en/github-models/quickstart)
- [GitHub Models 무료 한도](https://docs.github.com/en/github-models/use-github-models/prototyping-with-ai-models#rate-limits)
- [GitHub Models 과금 방식](https://docs.github.com/en/billing/concepts/product-billing/github-models)
- [Gemini 이미지 생성 문서](https://ai.google.dev/gemini-api/docs/image-generation)
- [Gemini API 가격](https://ai.google.dev/gemini-api/docs/pricing)

## 뉴스 후보 출처

| 성격 | 출처 | 용도 |
| --- | --- | --- |
| 일반 관심 | AI타임스 인기기사 | 개인정보·일자리·의료·소비자 이슈로 글의 첫 관심 열기 |
| 커뮤니티 | GeekNews | 개발자 반응과 새 도구 탐색 |
| 국내 에디토리얼 | 요즘IT | 국내 개발 현장과 읽을거리 보강, RSS 405 시 잡지 메인 폴백 |
| 공식 발표 | OpenAI News, GitHub Changelog | 제품·기능 변경의 1차 출처 |
| 연구 | arXiv cs.AI | 중장기 AI 흐름과 주간 정리 소재 |

출처, 가중치, 독자 층위별 키워드는 `config/news_sources.json`에서 수정합니다. AI타임스는 일반 관심 선택지, GitHub와 요즘IT는 실용 선택지, GeekNews는 깊이 있는 선택지에서 먼저 비교합니다. arXiv는 주간 정리 후보로는 남기지만 일일 3건에서는 실무 글을 먼저 고릅니다.

AI에는 공개된 제목·허용된 피드 요약과 선정된 기사 3건의 제한된 본문 근거만 전달합니다. 원문 텍스트는 Actions 실행 중에만 사용하고 `docs/inbox`나 `data/days`에는 저장하지 않습니다. AI타임스는 저작권 범위를 보수적으로 지키기 위해 공개 후보함에는 제목·게시일·원문 링크만 남기고, 모델이 정리할 때 RSS 설명을 메모리에서만 읽은 뒤 저장하지 않습니다. 발행 제목은 신뢰된 첫 기사 원제목을 사용하고 대표 이미지 문구도 기사 텍스트에서 결정론적으로 만들므로, 모델이 존재하지 않는 사건을 제목이나 커버에 추가할 수 없습니다. 커뮤니티·에디토리얼·논문은 원 출처, 게시일, 핵심 주장을 한 번 더 확인하세요.

## 주요 파일

```text
.github/workflows/tistory-draft.yml # 매일 07:28 KST 자체 초안 생성·배포
collect_news.py                     # RSS/Atom 뉴스 수집 및 후보함 생성
article_context.py                   # 선정 원문의 비저장·제한 근거 텍스트 추출
news_pipeline.py                    # 정규화, 중복 제거, 독자 층위 점수, AI·연구 과다 방지
generate_daily_draft.py             # GitHub Models 호출, 검증, 로컬 day JSON 생성
config/editorial_persona.json        # 승원 페르소나·문체·가짜 경험 금지 규칙
quiz_bank.py                         # 검증된 정처기 5과목 문제은행과 중복 회피 선택
generate_editorial_images.py         # 대표 이미지·뉴스별 본문 PNG 생성
generate_gemini_images.py            # 수동 opt-in 유료 Gemini 이미지 교체
visual_direction.py                  # 구체적인 훅 검증과 기사별 설명 장면 선택
requirements-images.txt              # 이미지 생성용 Pillow 버전
config/news_sources.json            # 출처, 관심 키워드, 추천 개수 설정
export_tistory.py                   # 로컬 day JSON을 티스토리 HTML로 변환
build_copy_page.py                  # HTML 복사 페이지 생성
data/days/                          # 날짜별 자체 뉴스·문제·용어 원본
docs/inbox/                         # 날짜별 뉴스 후보함 HTML/JSON
docs/tistory/                       # 날짜별 티스토리 초안 HTML/JSON
docs/index.html                     # 복사 전용 페이지
```

`pages_to_tistory.py`는 과거 조이한 Pages 글을 다시 가져올 때만 쓰는 레거시 도구입니다. 매일 자동 workflow에서는 더 이상 사용하지 않습니다.

## 실행 방법

가장 간단한 방법은 GitHub의 `Actions → Daily news draft → Run workflow`입니다. 이 경우 기본 `GITHUB_TOKEN`이 자동으로 연결됩니다. 날짜 입력을 비우면 오늘 초안을 만들고, 자동화가 빠진 날은 `2026-07-13`처럼 날짜를 넣어 다시 생성할 수 있습니다. 같은 날짜의 글을 새 구조로 다시 만들고 싶다면 `기존 초안도 강제로 다시 생성`을 체크합니다. 과금 계정으로 더 자연스러운 대표·본문 이미지를 만들 때만 `유료 Gemini 이미지`를 체크합니다.

이미 발행했던 과거 글을 보강할 때는 날짜를 입력하고 `과거 후보함을 다시 수집하지 않고 현재 장문 구조로 보강`을 체크합니다. 이 모드는 해당 날짜의 `docs/inbox/YYYY-MM-DD.json`을 그대로 사용하므로 최신 뉴스가 과거 글에 섞이지 않습니다. 날짜나 기존 후보함이 없으면 실행을 중단하며, 보강 결과는 바로 발행하지 않고 복사 페이지에서 확인합니다.

GitHub Pages 복사 화면 상단의 `빠진 날짜 직접 생성` 버튼도 같은 Actions 화면으로 연결됩니다.

로컬에서 후보 수집과 최소 초안을 확인하려면:

```bash
python -m pip install -r requirements-images.txt
python collect_news.py --today
python generate_daily_draft.py --today --fallback-on-error
python generate_editorial_images.py --today
python build_copy_page.py
```

로컬 환경에 `models: read` 권한의 GitHub 토큰이 `GITHUB_TOKEN`으로 설정되어 있으면 AI 초안을 만들고, 없으면 검증된 피드 요약만 사용합니다. 실제 토큰은 `.env`나 소스 코드에 기록하지 마세요.

특정 날짜 이름으로 실행하려면:

```bash
python collect_news.py --day 2026-07-13
python generate_daily_draft.py --day 2026-07-13 --fallback-on-error
python generate_editorial_images.py --day 2026-07-13
python build_copy_page.py
```

## 티스토리 발행 방법

1. 복사 페이지에서 날짜를 선택합니다.
2. `본문 미리보기`로 대표 이미지와 실제 글 흐름을 먼저 확인합니다. 미리보기는 격리된 창에서 열려 본문 안의 스크립트를 실행하지 않습니다.
3. 제목 후보, 태그, 본문 HTML을 복사합니다.
4. 티스토리 글쓰기에서 HTML 모드로 전환해 붙여넣습니다. 대표·본문 이미지는 HTML에 이미 포함되어 있습니다.
5. 원문 링크와 사실관계, 정처기 정답을 확인합니다.
6. 티스토리 목록 썸네일까지 지정하려면 복사 페이지에서 대표 이미지를 내려받아 글쓰기 화면의 대표 이미지로 선택합니다.
7. 내 생각이나 직접 해본 내용을 한두 문단 추가합니다.
8. 카테고리를 지정하고 발행합니다.

티스토리 Open API의 글 작성 기능은 종료되어 공식 API로 자동 발행할 수 없습니다. 이 저장소는 후보 수집과 초안 생성을 담당하고 최종 발행은 사람이 검토해서 진행합니다.
