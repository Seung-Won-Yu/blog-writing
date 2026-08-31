# 예약 편집 저장소 동기화 계약

이 문서는 월·수 실전 IT 아티클, 화·목 궁금한 IT 원리, 금요일 개발·AI 인사이트, 토요일 프로젝트 연재가
함께 사용하는 저장소 동기화 계약입니다. 일시적인 GitHub DNS·네트워크 장애는
원고 제작을 막지 않습니다. 원격과 실제로 충돌할 가능성이 있을 때만 중단합니다.

## 시작

1. 프로젝트 경로와 작업 트리를 확인합니다.

   ```bash
   pwd -P
   git rev-parse --show-toplevel
   git status --porcelain
   ```

2. 작업 트리가 깨끗하면 `git fetch origin main`을 독립 명령으로 한 번 실행합니다. 같은 DNS 오류를 반복 호출하지 않습니다.

3. fetch 성공 여부와 관계없이 캐시된 원격 참조를 확인합니다.

   ```bash
   git show-ref --verify --quiet refs/remotes/origin/main
   git rev-list --left-right --count HEAD...refs/remotes/origin/main
   ```

   출력은 `로컬 전용 커밋 수  원격 전용 커밋 수`입니다.

   - `0 0`: 동기화 상태. 계속합니다.
   - `N 0`: 로컬 커밋이 앞선 상태. 이전 실행의 전송 대기분이므로 계속합니다. 네트워크가 되면 최종 push에 함께 포함합니다.
   - `0 N`: 캐시된 원격이 앞선 상태. `git merge --ff-only refs/remotes/origin/main` 후 계속합니다.
   - `N M`: 양쪽 모두 커밋이 있는 실제 분기 상태. 파일을 만들지 않고 `BLOCKED`로 종료합니다.
   - `origin/main` 캐시 없음: 안전 비교가 불가능하므로 `BLOCKED`로 종료합니다.

4. fetch가 `Could not resolve host`, DNS, 502, 503, 504, timeout으로 실패해도 위 결과의 원격 전용 커밋 수가 0이면 `OFFLINE_SAFE`로 계속합니다. 인증 실패, 권한 실패, non-fast-forward, 실제 분기는 오프라인으로 우회하지 않습니다.

5. 작업 트리가 더러우면 새 글을 만들지 않습니다. 해당 편집 계약의 `publish_bundle --resume-check`로 완성 묶음인지 판별합니다. `READY`면 누락된 검증·스테이징부터 복구하고, 아니면 변경을 보존한 채 `BLOCKED`로 종료합니다.

## 완료와 전송

1. 원고·이미지·HTML·가드·테스트가 모두 통과하면 네트워크 상태와 무관하게 발행 묶음을 스테이징하고 하나의 로컬 커밋으로 확정합니다. 검증 전 커밋은 금지합니다.

2. 검증된 커밋은 아래 단일 배포 명령으로 전송합니다.

   ```bash
   python3 -m blog_pipeline.publishing.repository_sync push --remote origin --ref main
   ```

   이 명령은 DNS·연결 실패·timeout·HTTP 5xx만 3초, 6초 간격으로 최대 3회 재시도합니다. 실행 환경이 GitHub 네트워크를 제한하면 같은 명령을 승인된 외부 네트워크 권한으로 실행합니다. 원시 `git push`를 제한된 환경에서 반복하지 않습니다.

   - 성공: 해당 커밋의 GitHub Actions와 공개 Pages를 확인합니다. 둘 다 확인된 경우만 `COMPLETE`입니다.
   - 최대 3회 뒤에도 DNS·5xx·timeout: 커밋과 깨끗한 작업 트리를 보존하고 `LOCAL_COMPLETE`로 보고합니다. 다음 예약 실행은 시작 단계에서 이 커밋을 감지해 새 작업과 함께 다시 push합니다.
   - 인증·권한·non-fast-forward: 재시도하지 않고 `BLOCKED`로 보고합니다. 강제 push, rebase, reset은 하지 않습니다.

3. GitHub Actions API만 일시적으로 열리지 않지만 push가 성공했다면 `REMOTE_PUSHED_VERIFY_PENDING`으로 보고합니다. 새 원고를 다시 만들지 않습니다.

4. `LOCAL_COMPLETE`와 `REMOTE_PUSHED_VERIFY_PENDING`은 콘텐츠 실패가 아닙니다. 생성 파일, 검증 수, 로컬 커밋 해시, 미확인 단계만 짧게 보고합니다. 별도 25분 재예약이나 중복 작업을 만들지 않습니다.
