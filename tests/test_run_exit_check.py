import json
from pathlib import Path
import tempfile
import unittest

from blog_pipeline.publishing.run_exit_check import check_run


class RunExitCheckTests(unittest.TestCase):
    def test_real_selected_text_draft_without_blocker_must_continue(self):
        result = check_run({'status':'INCOMPLETE','stage':'SELECTED_TEXT_DRAFT','draft_id':'2026-11-06-automation','selection':'SELECTED','blocker':None,'remaining':['images','HTML','QA','commit','deploy']})
        self.assertEqual(result['status'],'CONTINUE_REQUIRED')
        self.assertIn('images',result['next_steps'])

    def test_unspecified_blocker_is_not_a_valid_exit(self):
        self.assertEqual(check_run({'blocker':'time ran out'})['status'],'CONTINUE_REQUIRED')
        self.assertEqual(check_run({'blocker':{'kind':'qa_environment','reason':'준비 중'}})['status'],'CONTINUE_REQUIRED')

    def test_explicit_actual_failure_can_be_reported_without_faking_completion(self):
        blocker={'kind':'authorization','reason':'해당 명령의 실행 승인이 실제 거절되어 같은 대상 작업을 더 진행할 수 없다.','evidence':'/tmp/approval-result.json'}
        self.assertEqual(check_run({'blocker':blocker})['status'],'BLOCKED')

    def test_complete_needs_metadata_and_actual_final_check_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            record={'draft_id':'2026-11-06-automation','status':'COMPLETE'}
            self.assertEqual(check_run(record,root=root)['reason'],'publish_metadata_missing')
            p=root/'docs/tistory/2026-11-06-automation.json';p.parent.mkdir(parents=True);p.write_text(json.dumps({'publish_ready':True}))
            self.assertEqual(check_run(record,root=root)['status'],'CONTINUE_REQUIRED')
            record.update(final_guard='COMPLETE',bundle='READY',visual_review='PASS',tests='PASS',commit='a'*40)
            self.assertEqual(check_run(record,root=root)['reason'],'deployment_unverified')
            record.update(actions='success',published_qa='PASS')
            self.assertEqual(check_run(record,root=root)['status'],'COMPLETE')
            record.update(status='LOCAL_COMPLETE')
            self.assertEqual(check_run(record,root=root)['status'],'LOCAL_COMPLETE')


if __name__ == '__main__':
    unittest.main()
