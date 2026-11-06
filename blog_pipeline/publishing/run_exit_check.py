"""Reject an unblocked text-only handoff after editorial selection succeeds."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from ..collection.search_demand import ROOT


def check_run(record, *, root=ROOT):
    if not isinstance(record, dict):
        return {"status": "CONTINUE_REQUIRED", "reason": "missing_run_record"}
    blocker = record.get("blocker")
    if blocker:
        kinds = {"authorization", "authentication", "divergence", "qa_environment", "network", "evidence_exhausted"}
        if not isinstance(blocker, dict) or blocker.get("kind") not in kinds or len(str(blocker.get("reason", ""))) < 20 or not blocker.get("evidence"):
            return {"status": "CONTINUE_REQUIRED", "reason": "unsubstantiated_blocker"}
        return {"status": "BLOCKED", "blocker": blocker,
                "note": "실제 오류와 증거를 확인해 보고한다. 정상 완료가 아니다."}
    draft_id = str(record.get("draft_id", ""))
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:-automation)?", draft_id):
        return {"status": "CONTINUE_REQUIRED", "reason": "actual_draft_id_required"}
    if record.get("status") not in {"COMPLETE", "LOCAL_COMPLETE", "REMOTE_PUSHED_VERIFY_PENDING"}:
        return {"status": "CONTINUE_REQUIRED", "stage": record.get("stage"),
                "reason": "selection_and_text_are_not_completion",
                "next_steps": record.get("remaining") or ["source", "images", "HTML", "visual_QA", "tests", "commit", "deploy"]}
    meta = Path(root) / "docs/tistory" / f"{draft_id}.json"
    try:
        ready = json.loads(meta.read_text())
    except (OSError, ValueError):
        return {"status": "CONTINUE_REQUIRED", "reason": "publish_metadata_missing"}
    required = ("final_guard", "bundle", "visual_review", "tests")
    expected = ("COMPLETE", "READY", "PASS", "PASS")
    if not ready.get("publish_ready") or any(record.get(k) != v for k, v in zip(required, expected)) or not re.fullmatch(r"[0-9a-f]{40}", str(record.get("commit", ""))):
        return {"status": "CONTINUE_REQUIRED", "reason": "final_checks_or_commit_missing"}
    if record["status"] == "COMPLETE" and (record.get("actions") != "success" or record.get("published_qa") != "PASS"):
        return {"status": "CONTINUE_REQUIRED", "reason": "deployment_unverified"}
    return {"status": record["status"], "draft_id": draft_id,
            "note": "완료 기록의 일관성 검사다. 실제 가드·테스트·화면·원격 검증을 대신하지 않는다."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = check_run(json.loads(args.record.read_text()))
    except (OSError, ValueError) as exc:
        result = {"status": "CONTINUE_REQUIRED", "reason": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["status"] == "CONTINUE_REQUIRED")


if __name__ == "__main__":
    raise SystemExit(main())
