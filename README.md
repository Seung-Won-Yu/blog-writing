# Blog Writing

여러 IT·AI 출처에서 매일 글감을 모으고, 내 GitHub 저장소 안에서 티스토리용 초안까지 만드는 자동화입니다. 다른 사람의 뉴스 저장소나 별도 AI API 키에 의존하지 않습니다.

자동화가 만든 결과는 바로 발행하지 않습니다. 뉴스 후보와 원문 링크, AI가 정리한 초안을 확인하고 내 의견을 더한 뒤 티스토리에 직접 붙여넣는 흐름입니다.

## 매일 자동 흐름

```text
07:28 KST GitHub Actions 실행
           GeekNews·요즘IT·공식 AI/개발 피드·arXiv에서 글감 수집
           URL/유사 제목 중복 제거와 최신성·관심 키워드 점수 계산
           출처가 겹치지 않게 추천 뉴스 3건 선정
           docs/inbox/YYYY-MM-DD.html 및 JSON 생성
           선정된 원문 3건의 공개 본문을 실행 중에만 제한적으로 읽어 근거 보강
           GitHub Models로 6~8분 분량의 맥락·핵심 변화·개발자 관점·확인할 점 생성
           정처기 문제와 개발 용어를 글 뒤쪽 복습 콘텐츠로 구성
           data/days/YYYY-MM-DD.json에 자체 원본 저장
           짧은 질문형 훅과 기사별 시각 모티프로 대표·본문 이미지 생성
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

GitHub Actions에서는 별도 API 키가 필요 없습니다. workflow가 실행될 때 GitHub가 잠시 발급하는 `GITHUB_TOKEN`에 `models: read` 권한만 부여해 GitHub Models를 호출합니다. 토큰은 코드, 결과 파일, 로그에 저장하지 않습니다.

기본 모델은 무료 제한량이 넉넉한 `openai/gpt-4o-mini`입니다. 현재 GitHub Models의 Low 등급 무료 한도는 Copilot Free 기준 분당 15회, 하루 150회, 요청당 입력 8,000·출력 4,000토큰이며 이 자동화는 정상적으로는 하루 1회 호출합니다. 외부 기사와 히스토리가 길어져도 입력을 보수적으로 7,000토큰 이하로 줄여 여유를 남깁니다. 첫 응답이 지나치게 짧거나 상투적이거나 실제 6분 분량에 못 미치면 품질 보정을 위해 한 번만 다시 호출합니다. 무료 한도는 GitHub 정책에 따라 바뀔 수 있습니다.

이 저장소 자체는 유료 사용을 활성화하지 않습니다. GitHub 계정에서 별도로 paid usage를 켜지 않았다면 무료 한도 초과 시 모델 요청이 차단되고, 자동화는 수집된 제목과 피드 요약만 사용하는 최소 초안으로 전환됩니다.

- `GEMINI_API_KEY` 필요 없음
- OpenAI API 키 필요 없음
- 티스토리 로그인 정보 필요 없음
- GitHub 저장소 Secret 추가 필요 없음
- 이미지 생성 API 키 필요 없음

대표 이미지와 본문 이미지는 생성형 AI 그림이 아니라, 그날 선정한 뉴스에서 짧은 질문형 훅과 통신망·에이전트·메모리·보안 같은 시각 모티프를 골라 자동 조판하는 블로그 전용 에디토리얼 이미지입니다. 대표 이미지는 목록에서도 질문과 장면이 바로 보이는 풀 블리드 썸네일로 만들고, 뉴스마다 제목·출처·모티프를 반영한 1200×630 본문 이미지를 한 장씩 붙입니다. 추가 비용은 없으며 이미지 생성만 실패해도 뉴스 수집과 텍스트 초안은 그대로 남습니다.

정보처리기사 문제는 뉴스 기사에서 모델이 즉석으로 만들지 않습니다. 검증한 문제은행에서 5개 필기 과목의 문항을 날짜별로 골라 붙이며, 최근 출제된 질문은 가능한 한 피합니다. 선택지는 본문에 `1.`부터 `4.`까지 직접 표시하므로 티스토리 스킨이 목록 마커를 숨겨도 정답 번호와 어긋나지 않습니다.

관련 공식 문서:

- [GitHub Models 빠른 시작](https://docs.github.com/en/github-models/quickstart)
- [GitHub Models 무료 한도](https://docs.github.com/en/github-models/use-github-models/prototyping-with-ai-models#rate-limits)
- [GitHub Models 과금 방식](https://docs.github.com/en/billing/concepts/product-billing/github-models)

## 뉴스 후보 출처

| 성격 | 출처 | 용도 |
| --- | --- | --- |
| 커뮤니티 | GeekNews | 개발자 반응과 새 도구 탐색 |
| 국내 에디토리얼 | 요즘IT | 국내 개발 현장과 읽을거리 보강 |
| 공식 발표 | OpenAI News, GitHub Changelog | 제품·기능 변경의 1차 출처 |
| 연구 | arXiv cs.AI | 중장기 AI 흐름과 주간 정리 소재 |

출처, 가중치, 관심 키워드는 `config/news_sources.json`에서 수정합니다. 기사 제목과 피드 요약, 원문 링크만 저장하고 외부 이미지는 자동 복제하지 않습니다.

AI에는 공개된 제목·피드 요약과 선정된 기사 3건의 제한된 본문 근거만 전달합니다. 원문 텍스트는 Actions 실행 중에만 사용하고 `docs/inbox`나 `data/days`에는 저장하지 않습니다. 접근이 막힌 출처는 기존 피드 요약으로 돌아갑니다. 모델이 링크나 출처를 바꾸더라도 프로그램이 수집 단계에서 검증한 값으로 덮어씁니다. 커뮤니티·에디토리얼·논문은 원 출처, 게시일, 핵심 주장을 한 번 더 확인하세요.

## 주요 파일

```text
.github/workflows/tistory-draft.yml # 매일 07:28 KST 자체 초안 생성·배포
collect_news.py                     # RSS/Atom 뉴스 수집 및 후보함 생성
article_context.py                   # 선정 원문의 비저장·제한 근거 텍스트 추출
news_pipeline.py                    # 정규화, 중복 제거, 점수 계산, 출처 분산
generate_daily_draft.py             # GitHub Models 호출, 검증, 로컬 day JSON 생성
quiz_bank.py                         # 검증된 정처기 5과목 문제은행과 중복 회피 선택
generate_editorial_images.py         # 대표 이미지·뉴스별 본문 PNG 생성
visual_direction.py                  # 질문형 훅 검증과 기사별 시각 모티프 선택
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

가장 간단한 방법은 GitHub의 `Actions → Daily news draft → Run workflow`입니다. 이 경우 기본 `GITHUB_TOKEN`이 자동으로 연결됩니다. 날짜 입력을 비우면 오늘 초안을 만들고, 자동화가 빠진 날은 `2026-07-13`처럼 날짜를 넣어 다시 생성할 수 있습니다. 같은 날짜의 글을 새 구조로 다시 만들고 싶다면 `기존 초안도 강제로 다시 생성`을 체크합니다.

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
2. 제목 후보, 태그, 본문 HTML을 복사합니다.
3. 티스토리 글쓰기에서 HTML 모드로 전환해 붙여넣습니다. 대표·본문 이미지는 HTML에 이미 포함되어 있습니다.
4. 원문 링크와 사실관계, 정처기 정답을 확인합니다.
5. 티스토리 목록 썸네일까지 지정하려면 복사 페이지에서 대표 이미지를 내려받아 글쓰기 화면의 대표 이미지로 선택합니다.
6. 내 생각이나 직접 해본 내용을 한두 문단 추가합니다.
7. 카테고리를 지정하고 발행합니다.

티스토리 Open API의 글 작성 기능은 종료되어 공식 API로 자동 발행할 수 없습니다. 이 저장소는 후보 수집과 초안 생성을 담당하고 최종 발행은 사람이 검토해서 진행합니다.
