# 앱 패널 의존성을 없앤 예약 검수

## 원인과 승인

11월2·3일 예약은 iab 미제공과 open_in_codex queued에서 멈췄다. 패널 연결 지시를
추가하는 것으로는 해결되지 않았다. 11월3일에는 보완일10/30을 원고 ID로 잘못 사용해
존재하지 않는 /preview/2026-10-30.html도 열었다. 실제 그 작업의 ID는 2026-08-08-automation이다.

사용자는 ‘예약 검수는 전용 자동 브라우저로 전환’을 명시적으로 선택했다. 평소 결과
확인·도우미는 앱 내에서 유지하며, 개인 Chrome 로그인·쿠키·프로필을 사용하지 않는다.

## 구현

- browser_qa는 publish_ready 메타와 실제 존재 파일에서 준비용 ID를 고른다. 개선일로
  URL을 추측하지 않고, 최종 검수는 명시적 ID만 쓴다. HTTP200과 정확한 제목도 확인한다.
- 고정 Playwright1.64.1 및 공식 Chromium headless shell을 저장소 .venv/사용자 캐시에
  설치했다. 글로벌 설정·시스템 Python·기존 Chrome은 변경하지 않았다.
- 선택 파일만 제공하는 기존 loopback allowlist 서버를 재사용한다. 전용 새 context는
  로그인·프로필이 없고, 브라우저 요청은 선택 origin만 허용한다. 종료 시 서버·프로세스를 닫는다.
- 실제 PC1280×900/모바일390×844에서 전체 지연 로딩 이미지, 표 안팎 너비, 페이지 넘침을
  공통 audit로 측정한다. 이미지·표·코드·소제목 캡처와 가로 스크롤 오른쪽 끝을 남긴다.
- CAPTURED는 시각 승인이 아니다. agent가 PNG를 view_image로 확인하고 최종 입력 해시와
  별도 판정을 남긴다. 실행 중 입력 변경은 STALE_INPUTS, 재실행 실패는 예전 성공 manifest를 지운다.
- --published는 정확한 blog-writing Pages의 선택 파일 바이트와 실제 두 화면을 대조한다.
  앱 패널은 GitHub 배포의 선행조건이 아니고, 평소 도우미를 보여 주는 후속 동작이다.
- 공통 계약·README와 실제 예약9/9-it/14 프롬프트를 갱신했다.09:00·Sol6.1Medium·
  실제 검색어 우선·사용자 티스토리 발행·정확한 origin/main 전송 범위는 유지했다.

## 검증

8개 회귀 검사: 보완일/실제ID 분리, 없는 파일, 미완성/누락 preview 제외,404/다른 글,
두 뷰포트, 저장소 밖 증거, 브라우저 crash의 이전 성공 무효화, 네트워크 origin 경계.
기존 preview_server 검사와 함께 통과했다. 전체581개 테스트도 통과했다.
실제 --preflight와 --published도 통과했다.

앱 브라우저 연결 환경 변수와 DISPLAY를 제거한 별도 프로세스에서 오늘 /209 최종본의
두 화면 캡처를 완료했다. 실행 중 앱 브라우저 API·패널 열기 요청은 사용하지 않았다.
이것은 실제 예약 검수 명령의 앱 독립 실행 검증이며 다음 예약 전체의 무중단 보장은 아니다.
네트워크·인증·자료 부족·정식 보안 거절은 여전히 구체적 실패로 보고한다.

## 공개 화면 CSP 호환 보완

오늘 /209 공개 미리보기 최종 검사에서 Playwright의 문자열 predicate 대기가
script-src none 정책과 충돌했다. 사이트 CSP·브라우저 보안 설정을 변경하지 않고
정적 자산의 네트워크 완료 대기로 바꿨다. 같은 공개 HTML·CSS·이미지 바이트와 두
화면을 다시 검사해 CAPTURED/METRICS_PASS, console 오류 없음과 시각 판정을 확인했다.
이미 배포한 본문을 다시 만들지 않았다.

옵트인 실제 Chromium 회귀 검사 두 개를 추가했다. 엄격한 CSP의 정상 표를 캡처하고,
tbody만 좁힌 경우에는 LAYOUT_FAILED가 되는지 확인한다. 기본 CI는 브라우저 설치 없이
계약 검사를 실행하고 실제 브라우저 검사는 BLOG_BROWSER_QA_LIVE=1로 별도 실행한다.

근거: https://playwright.dev/python/docs/library , https://playwright.dev/python/docs/browsers

최종 검증은 BLOG_BROWSER_QA_LIVE=1 전체583개 테스트 성공이며 실제 Chromium 회귀2개를 포함한다.
공개 /209 교체본의 선택 HTML·CSS·이미지는 로컬 검수본과 바이트가 모두 같고, 두 화면
METRICS_PASS·console 오류 없음·수정 코드/표 시각 검수까지 확인했다.
