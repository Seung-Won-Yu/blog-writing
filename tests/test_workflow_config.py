import unittest
from pathlib import Path


class WorkflowConfigTests(unittest.TestCase):
    def test_daily_workflow_collects_inbox_without_losing_it_when_export_fails(self):
        workflow = (
            Path(__file__).parents[1] / ".github" / "workflows" / "tistory-draft.yml"
        ).read_text(encoding="utf-8")

        collect_command = "python collect_news.py --today"
        export_step = "id: tistory_export"
        self.assertIn(collect_command, workflow)
        self.assertIn("'collect_news.py'", workflow)
        self.assertIn("'config/news_sources.json'", workflow)
        self.assertIn(export_step, workflow)
        self.assertIn("continue-on-error: true", workflow)
        self.assertLess(workflow.index(collect_command), workflow.index(export_step))


if __name__ == "__main__":
    unittest.main()
