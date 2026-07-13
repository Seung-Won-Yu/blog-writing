import unittest
from pathlib import Path


class WorkflowConfigTests(unittest.TestCase):
    def test_daily_workflow_generates_own_draft_with_builtin_github_token(self):
        workflow = (
            Path(__file__).parents[1] / ".github" / "workflows" / "tistory-draft.yml"
        ).read_text(encoding="utf-8")

        collect_command = "python collect_news.py --today"
        generate_command = "python generate_daily_draft.py --today --fallback-on-error"
        image_command = "python generate_editorial_images.py --today"
        copy_command = "python build_copy_page.py"
        self.assertIn(collect_command, workflow)
        self.assertIn(generate_command, workflow)
        self.assertIn("'collect_news.py'", workflow)
        self.assertIn("'generate_daily_draft.py'", workflow)
        self.assertIn("'generate_editorial_images.py'", workflow)
        self.assertIn("'article_context.py'", workflow)
        self.assertIn("'quiz_bank.py'", workflow)
        self.assertIn("'visual_direction.py'", workflow)
        self.assertIn("'requirements-images.txt'", workflow)
        self.assertIn("'config/news_sources.json'", workflow)
        self.assertIn("models: read", workflow)
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", workflow)
        self.assertIn("GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}", workflow)
        self.assertIn("git add docs data", workflow)
        self.assertIn("description: '생성할 날짜", workflow)
        self.assertIn("REQUESTED_DAY: ${{ inputs.day }}", workflow)
        self.assertIn("FORCE_REBUILD: ${{ inputs.force }}", workflow)
        self.assertIn('FORCE_FLAG="--force"', workflow)
        self.assertIn("강제로 다시 생성", workflow)
        self.assertIn('python collect_news.py --day "$REQUESTED_DAY"', workflow)
        self.assertIn(
            'python generate_daily_draft.py --day "$REQUESTED_DAY" --fallback-on-error',
            workflow,
        )
        self.assertIn(image_command, workflow)
        self.assertIn('python generate_editorial_images.py --day "$REQUESTED_DAY"', workflow)
        self.assertIn("fonts-noto-cjk", workflow)
        self.assertIn("requirements-images.txt", workflow)
        self.assertIn("id: editorial_images", workflow)
        self.assertIn("Build draft copy page", workflow)
        self.assertIn("if: always()", workflow)
        self.assertIn("continue-on-error: true", workflow)
        self.assertNotIn("python pages_to_tistory.py --today", workflow)
        self.assertLess(workflow.index(collect_command), workflow.index(generate_command))
        self.assertLess(workflow.index(generate_command), workflow.index(image_command))
        self.assertLess(workflow.index(image_command), workflow.index(copy_command))


if __name__ == "__main__":
    unittest.main()
