# 예약 실행의 종료 검사

2026-11-06에는 `SELECTED_TEXT_DRAFT`까지 진행하고 환경 차단이 없는데도
이미지·HTML·검수·배포를 남긴 채 종료했다. 선정 성공과 텍스트 저장은 중간 상태다.
이 문서는 기존 품질·권한·원격 동기화 계약을 유지하며 그 조기 종료를 검사한다.

- 시작 시 `.local-drafts/YYYY-MM-DD.run.json`에 실제 원고 ID, 단계, 남은 작업,
  `blocker`를 기록한다. 텍스트도 같은 디렉터리에 보존한다. `/tmp`와 삭제될 채팅만을
  재개 입력으로 사용하지 않는다. 이 디렉터리는 공개·커밋 대상이 아니다.
- `SELECTED` 이후 정식 원고와 사전 가드 → 이미지 → 최종 HTML → 실제 PC·모바일
  검수 → 최종 가드·테스트·게시 묶음 → 단일 커밋 → push → Actions·공개 검수 순으로
  같은 실행에서 진행한다. 실제 단계가 끝날 때 기록을 갱신한다.
- 최종 답변 전에 아래 명령을 실행한다. `CONTINUE_REQUIRED`(종료 코드 1)이면
  미완료 작업을 계속한다. 텍스트를 저장했다는 이유, 10시가 됐다는 이유, 다음에
  이어갈 수 있다는 이유로 정상 작업을 중단하지 않는다. 새 예약·새 채팅은 만들지 않는다.

  ```bash
  sh scripts/blog-env python3 -m blog_pipeline.publishing.run_exit_check \
    --record .local-drafts/YYYY-MM-DD.run.json
  ```

- 실제 승인 거절·인증 실패·분기·검수 환경 오류·네트워크 장애·근거 소진으로
  계속할 수 없다면 `blocker`에 `kind`, 구체적 `reason`, 실제 `evidence` 경로/기록을
  남긴다. 선정 소진은 전체 검토의 `EXHAUSTED` 증거가 필요하다. 허용된 복구를 먼저
  수행하고, 명시적인 보안 거절을 우회하거나 품질 기준을 낮추지 않는다.
- 로컬 완료 기록은 `final_guard: COMPLETE`, `bundle: READY`, `visual_review: PASS`,
  `tests: PASS`, 40자리 `commit` 해시와 실제 `publish_ready` 메타가 필요하다.
  `COMPLETE`에는 `actions: success`, `published_qa: PASS`도 필요하다. 원격 문제는
  기존 동기화 계약에 따라 `LOCAL_COMPLETE`/`REMOTE_PUSHED_VERIFY_PENDING`으로 구분한다.

검사 명령은 완료 기록의 일관성을 검사한다. 실제 테스트·시각 판정·원격 검증을
대신하거나 Codex 앱 실행 시간을 강제로 늘리는 기능은 아니다. 완료 값을 꾸며
통과시키지 않는다. 재개 시 기존 원고·이미지·커밋을 먼저 확인해 끝난 단계는 반복하지 않는다.
