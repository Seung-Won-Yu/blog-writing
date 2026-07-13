import unittest
from pathlib import Path


class WorkflowConfigTests(unittest.TestCase):
    def test_push_validates_without_regenerating_daily_content(self):
        workflow = (
            Path(__file__).parents[1] / ".github" / "workflows" / "tistory-draft.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("name: Install Python dependencies", workflow)
        self.assertIn("name: Run tests", workflow)
        self.assertIn("python -m unittest discover -s tests", workflow)
        self.assertLess(
            workflow.index("name: Install Python dependencies"),
            workflow.index("name: Run tests"),
        )
        self.assertLess(
            workflow.index("name: Install editorial image tools"),
            workflow.index("name: Run tests"),
        )
        for step_name in (
            "Collect today's news review inbox",
            "Generate today's local Tistory draft",
            "Generate branded cover and story images",
        ):
            step = workflow.split("- name: {}".format(step_name), 1)[1].split(
                "\n      - ", 1
            )[0]
            self.assertIn("github.event_name != 'push'", step)

    def test_daily_schedule_runs_after_gemini_daily_quota_reset(self):
        workflow = (
            Path(__file__).parents[1] / ".github" / "workflows" / "tistory-draft.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("cron: '10 8 * * *'", workflow)
        self.assertIn("17:10 KST", workflow)

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
        self.assertIn("'generate_gemini_images.py'", workflow)
        self.assertIn("'article_context.py'", workflow)
        self.assertIn("'quiz_bank.py'", workflow)
        self.assertIn("'visual_direction.py'", workflow)
        self.assertIn("'requirements-images.txt'", workflow)
        self.assertIn("'config/news_sources.json'", workflow)
        self.assertIn("models: read", workflow)
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", workflow)
        self.assertIn("GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}", workflow)
        self.assertIn("--fail-on-fallback", workflow)
        self.assertIn("ai_images:", workflow)
        self.assertIn("image_model:", workflow)
        self.assertIn("default: false", workflow)
        self.assertIn("inputs.ai_images == true", workflow)
        self.assertIn("gemini-3.1-flash-image", workflow)
        self.assertIn("GEMINI_IMAGE_MODEL: ${{ inputs.image_model }}", workflow)
        self.assertIn("python generate_gemini_images.py --today", workflow)
        self.assertIn('python generate_gemini_images.py --day "$REQUESTED_DAY"', workflow)
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

    def test_generated_docs_and_data_do_not_retrigger_the_workflow(self):
        workflow = (
            Path(__file__).parents[1] / ".github" / "workflows" / "tistory-draft.yml"
        ).read_text(encoding="utf-8")
        push_paths = workflow.split("schedule:", 1)[0]

        self.assertNotIn("- 'docs/**'", push_paths)
        self.assertNotIn("- 'data/**'", push_paths)

    def test_manual_refresh_can_reuse_historical_inbox_without_recollecting_news(self):
        workflow = (
            Path(__file__).parents[1] / ".github" / "workflows" / "tistory-draft.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("refresh_existing:", workflow)
        self.assertIn("REFRESH_EXISTING: ${{ inputs.refresh_existing }}", workflow)
        self.assertIn("Verify historical review inbox", workflow)
        self.assertIn("python restore_review_inbox.py", workflow)
        self.assertIn('test -n "$REQUESTED_DAY"', workflow)
        self.assertIn('test -f "docs/inbox/$REQUESTED_DAY.json"', workflow)
        self.assertIn("inputs.refresh_existing != true", workflow)

    def test_historical_refresh_always_forces_a_new_draft(self):
        workflow = (
            Path(__file__).parents[1] / ".github" / "workflows" / "tistory-draft.yml"
        ).read_text(encoding="utf-8")

        self.assertIn('if [ "$REFRESH_EXISTING" = "true" ]; then', workflow)
        self.assertIn('FORCE_FLAG="--force"', workflow)

    def test_queued_manual_runs_checkout_the_latest_main_revision(self):
        workflow = (
            Path(__file__).parents[1] / ".github" / "workflows" / "tistory-draft.yml"
        ).read_text(encoding="utf-8")

        checkout = workflow.split("uses: actions/checkout@v4", 1)[1].split(
            "uses: actions/setup-python@v5", 1
        )[0]
        self.assertIn("ref: main", checkout)


if __name__ == "__main__":
    unittest.main()
