# 예약 편집 저장소 동기화 계약

이 문서는 월·수 실전 IT 아티클, 화·목 궁금한 IT 원리, 금요일 개발·AI 인사이트, 토요일 프로젝트 연재가
함께 사용하는 저장소 동기화 계약입니다. 일시적인 GitHub DNS·네트워크 장애는
원고 제작을 막지 않습니다. 원격과 실제로 충돌할 가능성이 있을 때만 중단합니다.

## 시작

### 2026-09-11 추가: 최신 원격 확인과 승인 근거

아래 사전점검은 기존 캐시 비교보다 우선한다. 작업 시작의 깨끗한 트리와 최종
커밋 후 푸시 직전에 각각 `python3 -m blog_pipeline.publishing.repository_sync preflight`를
실행한다. 이 명령은 정확한 HTTPS origin 주소(읽기·쓰기 모두), main 브랜치,
깨끗한 트리를 확인하고 fetch 후 비교한다. 병합·푸시·권한 변경은 하지 않는다.

- `READY`: 최신 원격과 비교됐으며 원격 전용 커밋이 없다.
- `REMOTE_AHEAD`: 시작 단계에서만 기존 `--ff-only` 동기화 후 다시 확인한다.
- `DIVERGED`: 원격 변경 파일·로컬 변경 파일을 보고하고 자동 충돌 해결은 하지 않는다.
  사용자가 해당 통합을 승인한 경우에만 양쪽 기록을 보존하는 일반 병합을 검토한다.
- `NETWORK_UNAVAILABLE`: 같은 제한 환경에서 반복 수집·인증 진단을 하지 않는다.
  네트워크 권한으로 동일 사전점검을 한 번 요청한다. 승인 거절 시 캐시가 최신이라고
  보고하지 않는다. 오프라인 원고 제작은 가능하지만 원격 배포는 미완료로 구분한다.
- 그 밖의 `BLOCKED`: 실제 사유를 보고하고 대상·권한·브랜치를 임의 변경하지 않는다.

정상 원격 후보함을 가져오지 못한 상태의 로컬 재수집 실패로 생성된 status.json은
공개 후보함 갱신으로 커밋하지 않는다. 실패 기록은 실행 메모에 남기고, 자신이 만든
실패 상태 변경임을 diff로 확인한 경우에만 기존 커밋의 상태로 복구한다. 다른 사용자
변경은 보존한다. 원격 후보 JSON·화면·상태 파일은 동일 수집 실행의 묶음으로 유지한다.

외부 실행 승인 요청에는 저장소 URL, main, 대상 커밋, 변경 파일 요약, 검증 결과,
GitHub Pages 공개 배포라는 부수 효과와 사용자의 기존 반복 배포 승인 범위를 함께
명시한다. 예약 문구는 실제 안전 검토 승인을 보장하지 않는다. 거절 시 우회하거나
승인 정책을 약화하지 않고 그 사유를 그대로 인계한다. 이 절차는 자동 승인 보장이 아니다.

당일 콘텐츠 가드가 COMPLETE라도 원격 미전송 커밋이 있으면 재집필하지 않고 이
사전점검부터 배포만 복구한다. 푸시 이후 새 원격 커밋으로 거절되면 실패 푸시를
반복하지 않고 최신 비교와 변경 범위를 확인한다.

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

## 예약 프롬프트의 외부 쓰기 경계

이 계약 문서 자체는 외부 쓰기 승인을 대신하지 않습니다. 활성 Codex 예약 프롬프트가
해당 실행에 대해 `origin/main`의 외부 쓰기와 그 결과로 시작되는 GitHub Actions·
GitHub Pages 배포를 직접 승인하고, 아래 범위를 함께 고정한 경우에만 전송합니다.

- 모든 로컬 가드·테스트·단일 커밋이 성공하고, 시작 비교에서 원격 전용 커밋이
  0개이며 실제 분기가 없어야 합니다.
- 전송은 정확히 `python3 -m blog_pipeline.publishing.repository_sync push --remote origin --ref main`
  한 명령만 사용합니다. 원시 `git push`, `--force/--force-with-lease`, `git rebase`,
  `git reset`, 다른 원격이나 다른 브랜치로의 쓰기는 허용하지 않습니다.
- 토요일 프로젝트 묶음은 `publish_bundle --stage`와 `--check`의 비공개 증거 유출
  검사를 먼저 통과해야 합니다. 실패하거나 공개 안전 여부가 불명확하면 커밋·push를
  하지 않고 `BLOCKED`로 인계합니다.
- 이 승인은 GitHub 저장소와 그 Pages 배포에만 적용합니다. 티스토리 붙여넣기와
  발행은 언제나 사용자가 최종 검수 뒤 직접 합니다.
- 예약 프롬프트에 위 승인이 없거나 범위가 더 넓다면 로컬 커밋까지만 보존하고
  `LOCAL_COMPLETE`로 보고합니다.

## 완료와 전송

1. 원고·이미지·HTML·가드·테스트가 모두 통과하면 네트워크 상태와 무관하게 발행 묶음을 스테이징하고 하나의 로컬 커밋으로 확정합니다. 검증 전 커밋은 금지합니다.

2. 검증된 커밋은 아래 단일 배포 명령으로 전송합니다.

   ```bash
   python3 -m blog_pipeline.publishing.repository_sync push --remote origin --ref main
   ```

   이 명령은 예약 실행에 주입된 `GH_TOKEN`·`GITHUB_TOKEN`을 push subprocess에서
   제거하고, 저장소에 설정된 Git credential helper를 사용합니다. 만료된 환경 토큰이
   macOS 키체인 또는 `gh auth git-credential`의 정상 로그인을 가리는 일을 막습니다.

   DNS·연결 실패·timeout·HTTP 5xx만 3초, 6초, 12초, 24초 간격으로 최대 5회
   재시도합니다. 백오프 대기 합계는 45초입니다.
   실행 환경이 GitHub 네트워크를 제한하면 같은 명령을 승인된 외부 네트워크 권한으로
   한 번 요청합니다. 원시 `git push`를 제한된 환경에서 반복하지 않습니다.

   샌드박스 안에서 DNS가 막힌 뒤 실행한 `gh auth status` 결과만으로 토큰 만료를
   판정하지 않습니다. 이 상태에서는 GitHub API 검증도 같은 네트워크 제한을 받기
   때문입니다. 승인 거절은 인증 실패가 아니므로 `LOCAL_COMPLETE`로 보고하고,
   정리된 환경으로 실행한 실제 push가 `Authentication failed` 또는 권한 오류를
   반환한 경우에만 인증·권한 `BLOCKED`로 분류합니다.

   - 성공: 해당 커밋의 GitHub Actions와 공개 Pages를 확인합니다. `Publish reviewed drafts`는 배포 뒤 `pages_smoke`로 공개 발행 도우미와 CI의 `docs/index.html` SHA-256이 같은지 제한 재시도합니다. 둘 다 확인된 경우만 `COMPLETE`입니다.
   - 최대 5회 뒤에도 DNS·5xx·timeout: 커밋과 깨끗한 작업 트리를 보존하고 `LOCAL_COMPLETE`로 보고합니다. 다음 예약 실행은 시작 단계에서 이 커밋을 감지해 새 작업과 함께 다시 push합니다.
   - 인증·권한·non-fast-forward: 재시도하지 않고 `BLOCKED`로 보고합니다. 강제 push, rebase, reset은 하지 않습니다.

3. GitHub Actions API가 일시적으로 열리지 않거나 Pages 전파 지연으로 `pages_smoke`가 일치하지 않지만 push와 배포가 성공했다면 `REMOTE_PUSHED_VERIFY_PENDING`으로 보고합니다. 배포를 반복하거나 새 원고를 다시 만들지 않습니다.

4. `LOCAL_COMPLETE`와 `REMOTE_PUSHED_VERIFY_PENDING`은 콘텐츠 실패가 아닙니다. 생성 파일, 검증 수, 로컬 커밋 해시, 미확인 단계만 짧게 보고합니다. 별도 25분 재예약이나 중복 작업을 만들지 않습니다.
