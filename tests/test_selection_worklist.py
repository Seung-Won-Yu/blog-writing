import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest

from blog_pipeline.publishing.selection_worklist import worklist, review_result
from tests.test_search_demand import snapshot


class SelectionWorklistTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ref = 'data/search_demand/2026-10-28.json'
        path = self.root / self.ref; path.parent.mkdir(parents=True)
        path.write_text(json.dumps(snapshot()))
        self.path = self.root / 'data/days/2026-08-08.json'
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({'draft_id':'2026-08-08', 'primary_query':'im-not-ai 사용법', 'editorial':{'headline':'im-not-ai 안내'}}))
        self.plan = {'demand_snapshot': self.ref, 'refresh_queue':[{'draft_id':'2026-08-08','source':'data/days/2026-08-08.json','status':'ready_for_review','page_url':'https://won0322.tistory.com/197'}]}
        self.report = worklist(self.plan, dt.date(2026,11,5), root=self.root)

    def test_exhausted_queue_still_yields_all_queries_and_protects_handoffs(self):
        self.assertEqual(self.report['status'], 'REVIEW_REQUIRED')
        self.assertEqual(len(self.report['queries']), 2)
        hints = self.report['queries'][0]['source_hints']
        self.assertEqual(hints[0]['queue_status'], 'ready_for_review')
        self.assertFalse(hints[0]['refresh_eligible'])
        self.assertNotIn('page_url', self.report['queries'][0])

    def test_one_answered_topic_cannot_exhaust_the_entire_review(self):
        review={'snapshot':self.ref,'reviews':[{'queries':['im-not-ai 사용법'],'decision':'pending_handoff','reason':'이미 준비된 검수 대기 원고를 보존하고 다른 질문을 찾아야 한다.'}]}
        result=review_result(self.report,review)
        self.assertEqual(result['status'],'RESEARCH_REQUIRED')
        self.assertIn('gpt 도구 선택',result['unreviewed_queries'])

    def test_false_exhaustion_without_direct_research_is_rejected(self):
        review={'snapshot':self.ref,'reviews':[{'queries':[r['query'] for r in self.report['queries']],'decision':'already_answered','reason':'기존 글의 답을 실제로 대조했으나 새로운 별도 과제를 확인하지 못했다.'}]}
        self.assertEqual(review_result(self.report,review)['status'],'RESEARCH_REQUIRED')
        review['direct_research']=[{'url':f'https://docs.example.org/{i}','finding':'공식 자료의 범위를 대조했지만 새로운 별도 작업의 근거를 확인하지 못했다.'} for i in range(3)]
        self.assertEqual(review_result(self.report,review)['status'],'EXHAUSTED')

    def test_observed_gap_selection_needs_evidence_and_cannot_rewrite_pending(self):
        item={'queries':['im-not-ai 사용법'],'decision':'gap_confirmed','reason':'공개 본문과 공식 설명을 대조해 누락된 실행 조건을 구체적으로 확인했다.', 'source':'data/days/2026-08-08.json','page_url':'https://won0322.tistory.com/197'}
        review={'snapshot':self.ref,'reviews':[item]}
        self.assertEqual(review_result(self.report,review)['status'],'RESEARCH_REQUIRED')
        item.update(public_evidence='/tmp/public.json',official_evidence=['https://docs.example.org/'])
        self.assertEqual(review_result(self.report,review)['reason'],'pending_handoff_protected')
        item['source']='data/days/2026-08-26.json';item['page_url']='https://won0322.tistory.com/214'
        self.assertEqual(review_result(self.report,review)['status'],'SELECTED')

    def test_refresh_reminder_keeps_valid_cache_and_never_changes_observation_date(self):
        self.assertTrue(self.report['refresh_due'])
        self.assertEqual(self.report['observed_at'],snapshot()['observed_at'])

    def test_distinct_new_task_can_be_selected_without_fabricating_an_existing_url(self):
        item={'queries':['gpt 도구 선택'],'decision':'gap_confirmed','action':'new_article','reason':'기존 도구 소개와 다른 실제 실행 선택 과제를 공식 자료와 대조해 확인했다.',
              'source':'data/days/2026-11-06.json','existing_page_urls':[],
              'distinct_outcome':'기존 설치 설명과 다른 실행 방식의 선택 조건 및 확인 결과를 제공한다.',
              'public_evidence':'/tmp/catalog-review.json','official_evidence':['https://docs.example.org/']}
        self.assertEqual(review_result(self.report,{'snapshot':self.ref,'reviews':[item]})['status'],'SELECTED')


if __name__ == '__main__':
    unittest.main()
