import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "publish-drafts.yml"


class WorkflowConfigTests(unittest.TestCase):
    def test_github_only_validates_builds_and_deploys_committed_results(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("name: Publish reviewed drafts", workflow)
        self.assertIn("python3 -m unittest discover -s tests", workflow)
        self.assertIn("python3 -m blog_pipeline.publishing.build_copy_page", workflow)
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

    def test_agent_contract_and_clean_package_layout_exist(self):
        expected = (
            ROOT / "agent" / "DAILY_EDITOR.md",
            ROOT / "blog_pipeline" / "collection" / "collect_news.py",
            ROOT / "blog_pipeline" / "collection" / "news_pipeline.py",
            ROOT / "blog_pipeline" / "publishing" / "export_tistory.py",
            ROOT / "blog_pipeline" / "publishing" / "build_copy_page.py",
            ROOT / "blog_pipeline" / "legacy" / "generate_daily_draft.py",
        )
        for path in expected:
            self.assertTrue(path.is_file(), str(path))


if __name__ == "__main__":
    unittest.main()
