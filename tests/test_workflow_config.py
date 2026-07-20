import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "publish-drafts.yml"
COLLECT_WORKFLOW = ROOT / ".github" / "workflows" / "collect-news.yml"
AUTOMATION_COLLECT_WORKFLOW = (
    ROOT / ".github" / "workflows" / "collect-automation.yml"
)
EDITOR_CONTRACT = ROOT / "agent" / "DAILY_EDITOR.md"
SATURDAY_CONTRACT = ROOT / "agent" / "SATURDAY_AUTOMATION.md"


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

    def test_pages_deploy_checks_every_future_publish_ready_draft(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        guard = (
            "python3 -m blog_pipeline.publishing.daily_guard "
            "--all-publish-ready"
        )
        self.assertIn(guard, workflow)
        self.assertLess(
            workflow.index(guard), workflow.index("actions/upload-pages-artifact@v3")
        )

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
        self.assertIn("git pull --rebase origin main", workflow)
        self.assertIn("git push origin HEAD:main", workflow)
        self.assertNotIn("generate_daily_draft", workflow)
        self.assertNotIn("generate_editorial_images", workflow)
        self.assertNotIn("GEMINI_API_KEY", workflow)
        self.assertNotIn("models: read", workflow)

    def test_saturday_collection_workflow_only_collects_ranked_candidates(self):
        workflow = AUTOMATION_COLLECT_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("name: Collect Saturday automation candidates", workflow)
        self.assertIn("cron: '17 2 * * 6'", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn(
            "python3 -m blog_pipeline.collection.collect_automation --today",
            workflow,
        )
        self.assertIn("tests.test_collect_automation", workflow)
        self.assertIn("git add docs/automation-inbox", workflow)
        self.assertIn("git pull --rebase origin main", workflow)
        self.assertIn("git push origin HEAD:main", workflow)
        self.assertNotIn("generate_daily_draft", workflow)
        self.assertNotIn("generate_editorial_images", workflow)
        self.assertNotIn("export_tistory", workflow)
        self.assertNotIn("GEMINI_API_KEY", workflow)
        self.assertNotIn("models: read", workflow)

    def test_agent_contract_and_clean_package_layout_exist(self):
        expected = (
            ROOT / "agent" / "DAILY_EDITOR.md",
            ROOT / "agent" / "SATURDAY_AUTOMATION.md",
            ROOT / "blog_pipeline" / "collection" / "collect_news.py",
            ROOT / "blog_pipeline" / "collection" / "collect_automation.py",
            ROOT / "blog_pipeline" / "collection" / "news_pipeline.py",
            ROOT / "blog_pipeline" / "publishing" / "export_tistory.py",
            ROOT / "blog_pipeline" / "publishing" / "build_copy_page.py",
            ROOT / "blog_pipeline" / "publishing" / "build_integration_page.py",
            ROOT / "blog_pipeline" / "publishing" / "daily_guard.py",
            ROOT / "blog_pipeline" / "publishing" / "publish_bundle.py",
            ROOT / "blog_pipeline" / "publishing" / "saturday_guard.py",
            ROOT / "blog_pipeline" / "publishing" / "generate_editorial_images.py",
            ROOT / "blog_pipeline" / "publishing" / "optimize_images.py",
        )
        for path in expected:
            self.assertTrue(path.is_file(), str(path))

    def test_editor_contract_enforces_one_deep_story_single_run_and_deduplication(self):
        contract = EDITOR_CONTRACT.read_text(encoding="utf-8")

        self.assertIn("daily_guard --today", contract)
        self.assertIn("daily_guard --today --check-duplicates", contract)
        self.assertIn("daily_guard --today --require-complete", contract)
        self.assertIn("publish_bundle --today --stage", contract)
        self.assertIn("publish_bundle --today --check", contract)
        self.assertIn("optimize_images --today", contract)
        self.assertIn("webp-v1", contract)
        self.assertIn("`COMPLETE`: 즉시 종료", contract)
        self.assertIn("`docs/inbox/latest.json`", contract)
        self.assertIn("당일 날짜와 다르면", contract)
        self.assertNotIn("`docs/inbox/YYYY-MM-DD.json`", contract)
        self.assertIn("최근 60일", contract)
        self.assertIn("`lead-story-v1`", contract)
        self.assertIn("핵심뉴스 1건", contract)
        self.assertIn("`primary_query`", contract)
        self.assertIn("후보 5건", contract)
        self.assertIn("관련 글 2개", contract)
        self.assertIn("35~45%", contract)
        self.assertIn("하나의 커밋", contract)
        self.assertIn("digest-news-copy", contract)
        self.assertIn("사용자 인계 지점", contract)
        self.assertIn("오늘 글 발행 준비", contract)
        self.assertIn("실제 조립·복사 흐름", contract)
        self.assertIn("최근 3일", contract)
        self.assertIn("직전 1일", contract)
        self.assertIn("추천 5건에서 제외", contract)
        self.assertIn("같은 핵심 브랜드·발행처", contract)
        self.assertIn("긴급 보안·서비스 장애", contract)
        self.assertIn("반복 브랜드를 제목에서 제외", contract)
        self.assertIn("대표 이미지는 새 핵심 대상", contract)

    def test_saturday_contract_stages_and_checks_the_complete_publish_bundle(self):
        contract = SATURDAY_CONTRACT.read_text(encoding="utf-8")

        self.assertIn(
            "publish_bundle --draft-id YYYY-MM-DD-automation --stage",
            contract,
        )
        self.assertIn(
            "publish_bundle --draft-id YYYY-MM-DD-automation --check",
            contract,
        )

    def test_editor_contract_requires_article_specific_image_briefs_and_review(self):
        contract = EDITOR_CONTRACT.read_text(encoding="utf-8")

        self.assertIn("대표 이미지 1장", contract)
        self.assertIn("설명 이미지 2~6장", contract)
        self.assertIn("기사 고유 시각 단서", contract)
        self.assertIn("원인 → 결과", contract)
        self.assertIn("노트북 앞 사람", contract)
        self.assertIn("1초 안에", contract)
        self.assertIn("curiosity_hook", contract)
        self.assertIn("시각적 질문", contract)
        self.assertIn("제목을 가렸을 때", contract)
        self.assertIn("45~70%", contract)
        self.assertIn("클릭베이트", contract)
        self.assertIn("짧은 한국어 설명", contract)
        self.assertIn("한글 파일명", contract)
        self.assertIn("표·차트·타임라인·비교·동작 흐름", contract)
        self.assertIn("실패한 이미지만 다시", contract)
        self.assertIn("`evidence_type`", contract)
        self.assertIn("`logic_type`", contract)
        self.assertIn("`condition`", contract)
        self.assertIn("조건부 사건", contract)
        self.assertIn("실제 제품 화면", contract)
        self.assertIn("생성 이미지로 가짜 UI", contract)
        self.assertIn("대표는 문제·결과", contract)

    def test_editor_contract_requires_search_titles_complete_facts_and_real_internal_links(self):
        contract = EDITOR_CONTRACT.read_text(encoding="utf-8")

        self.assertIn("핵심 검색어는 한 번", contract)
        self.assertIn("적용 범위·요금·선행 조건", contract)
        self.assertIn("작동 확인 신호", contract)
        self.assertIn("https://won0322.tistory.com/<숫자>", contract)
        self.assertIn("GitHub Pages 미리보기 링크", contract)

    def test_editor_contract_matches_the_enforced_quality_schema(self):
        contract = EDITOR_CONTRACT.read_text(encoding="utf-8")

        for field in (
            "audience_problem",
            "reader_takeaway",
            "why_now",
            "topic_key",
            "reader_question",
            "entities",
            "coverage",
            "origin",
            "generation_prompt",
            "generation_model",
            "korean_labels",
            "capture_tool",
            "capture_target",
            "captured_at",
            "capture_sha256",
            "measurement_source",
            "unit",
            "sample_count",
            "measurement_environment",
            "data_points",
            "measurement_sha256",
            "topic_match",
            "caption_match",
            "mobile_readable",
            "text_reviewed",
            "not_generic",
            "sha256",
        ):
            self.assertIn(f"`{field}`", contract)
        self.assertIn("`generation.image_provider`", contract)
        self.assertIn("소제목 5~7개", contract)
        self.assertIn("결정적 대체 이미지는 발행 준비를 통과하지", contract)

    def test_saturday_contract_owns_verified_hands_on_automation_cases(self):
        daily = EDITOR_CONTRACT.read_text(encoding="utf-8")
        contract = SATURDAY_CONTRACT.read_text(encoding="utf-8")

        self.assertIn("SATURDAY_AUTOMATION.md", daily)
        self.assertNotIn("### GitHub 적용 사례형", daily)
        self.assertIn("토요일 14:00 KST", contract)
        self.assertIn("18:00 예약 발행", contract)
        self.assertIn("직접 실행 실험기", contract)
        self.assertIn("따라하기", contract)
        self.assertIn("공개 도구 적용 사례", contract)
        self.assertIn("검색 지속성 20", contract)
        self.assertIn("검증한 버전·커밋", contract)
        self.assertIn("기대 결과와 실제 결과", contract)
        self.assertIn("임시 디렉터리", contract)
        self.assertIn("의심스러운 설치 스크립트", contract)
        self.assertIn("구조 분석", contract)
        self.assertIn("측정하지 않은 숫자", contract)
        self.assertIn("실제 실행 화면", contract)
        self.assertIn("화면이나 터미널 결과를 이미지 생성으로 꾸며내지 않습니다", contract)
        self.assertIn("대표 이미지 1장과 본문 시각물 3~6개", contract)
        self.assertIn("YYYY-MM-DD-automation", contract)
        self.assertIn("saturday_guard --today --require-complete", contract)
        self.assertIn("같은 날짜의 `data/days/YYYY-MM-DD.json`", contract)
        self.assertIn("`docs/automation-inbox/latest.json`", contract)
        self.assertIn("당일 날짜와 다르면", contract)
        self.assertIn("임시 점수", contract)
        self.assertIn("검증 완료의 증거가 아닙니다", contract)
        self.assertIn("공식 출처를 직접 검색", contract)
        self.assertIn("도구명을 지워도", contract)
        self.assertIn("대중 공감도", contract)
        self.assertIn("이메일·문서·PDF·표·일정·파일", contract)
        self.assertIn("결과를 제목 앞부분", contract)
        self.assertIn("`origin`", contract)
        self.assertIn("`imagegen`", contract)
        self.assertIn("결정적 대체 이미지는 발행 준비를 통과하지", contract)

    def test_saturday_contract_matches_the_enforced_experiment_schema(self):
        contract = SATURDAY_CONTRACT.read_text(encoding="utf-8")

        for field in (
            "verification",
            "mode",
            "environment",
            "commands",
            "input_fixture",
            "expected",
            "actual",
            "failure",
            "rollback",
            "evidence_files",
            "started_at",
            "completed_at",
            "command_exit_code",
            "stdout_excerpt",
            "capture_tool",
            "capture_target",
            "captured_at",
            "capture_sha256",
            "measurement_source",
            "unit",
            "sample_count",
            "measurement_environment",
            "data_points",
            "measurement_sha256",
            "measurement_files",
            "measurement_note",
            "korean_labels",
            "problem_lane",
            "tool_brand",
            "topic_match",
            "caption_match",
            "mobile_readable",
            "text_reviewed",
            "not_generic",
            "sha256",
        ):
            self.assertIn(f"`{field}`", contract)
        self.assertIn("`generation.image_provider`", contract)


if __name__ == "__main__":
    unittest.main()
