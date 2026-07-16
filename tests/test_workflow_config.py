import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "publish-drafts.yml"
COLLECT_WORKFLOW = ROOT / ".github" / "workflows" / "collect-news.yml"
EDITOR_CONTRACT = ROOT / "agent" / "DAILY_EDITOR.md"


class WorkflowConfigTests(unittest.TestCase):
    def test_github_only_validates_builds_and_deploys_committed_results(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("name: Publish reviewed drafts", workflow)
        self.assertIn("python3 -m unittest discover -s tests", workflow)
        self.assertIn(
            "python3 -m blog_pipeline.publishing.optimize_images --check-all",
            workflow,
        )
        self.assertIn("python3 -m blog_pipeline.publishing.build_copy_page", workflow)
        self.assertIn(
            "python3 -m blog_pipeline.publishing.build_integration_page", workflow
        )
        self.assertIn("actions/upload-pages-artifact@v3", workflow)
        self.assertIn("actions/deploy-pages@v5", workflow)

    def test_github_does_not_collect_or_write_articles(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("collect_news", workflow)
        self.assertNotIn("generate_daily_draft", workflow)
        self.assertNotIn("GEMINI_API_KEY", workflow)
        self.assertNotIn("GITHUB_TOKEN", workflow)
        self.assertNotIn("git push", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("models: read", workflow)

    def test_collection_workflow_only_collects_ranked_candidates(self):
        workflow = COLLECT_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("name: Collect daily news", workflow)
        self.assertIn("cron: '17 22 * * *'", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn(
            "python3 -m blog_pipeline.collection.collect_news --today", workflow
        )
        self.assertIn("git add docs/inbox", workflow)
        self.assertIn("git push origin HEAD:main", workflow)
        self.assertNotIn("generate_daily_draft", workflow)
        self.assertNotIn("generate_editorial_images", workflow)
        self.assertNotIn("GEMINI_API_KEY", workflow)
        self.assertNotIn("models: read", workflow)

    def test_agent_contract_and_clean_package_layout_exist(self):
        expected = (
            ROOT / "agent" / "DAILY_EDITOR.md",
            ROOT / "blog_pipeline" / "collection" / "collect_news.py",
            ROOT / "blog_pipeline" / "collection" / "news_pipeline.py",
            ROOT / "blog_pipeline" / "publishing" / "export_tistory.py",
            ROOT / "blog_pipeline" / "publishing" / "build_copy_page.py",
            ROOT / "blog_pipeline" / "publishing" / "daily_guard.py",
            ROOT / "blog_pipeline" / "legacy" / "generate_daily_draft.py",
        )
        for path in expected:
            self.assertTrue(path.is_file(), str(path))

    def test_editor_contract_enforces_single_run_and_recent_deduplication(self):
        contract = EDITOR_CONTRACT.read_text(encoding="utf-8")

        self.assertIn("daily_guard --today", contract)
        self.assertIn("daily_guard --today --check-duplicates", contract)
        self.assertIn("daily_guard --today --require-complete", contract)
        self.assertIn("optimize_images --today", contract)
        self.assertIn("webp-v1", contract)
        self.assertIn("`COMPLETE`: 즉시 종료", contract)
        self.assertIn("`docs/inbox/latest.json`", contract)
        self.assertIn("당일 날짜와 다르면", contract)
        self.assertNotIn("`docs/inbox/YYYY-MM-DD.json`", contract)
        self.assertIn("최근 14일", contract)
        self.assertIn("하나의 커밋", contract)
        self.assertIn("digest-news-copy", contract)

    def test_editor_contract_requires_article_specific_image_briefs_and_review(self):
        contract = EDITOR_CONTRACT.read_text(encoding="utf-8")

        self.assertIn("대표 이미지는 첫 기사 하나만", contract)
        self.assertIn("기사 고유 시각 단서", contract)
        self.assertIn("원인 → 결과", contract)
        self.assertIn("노트북 앞 사람", contract)
        self.assertIn("1초 안에", contract)
        self.assertIn("실패한 이미지만 다시", contract)


if __name__ == "__main__":
    unittest.main()
