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
GUIDE_CONTRACT = ROOT / "agent" / "DEVELOPMENT_GUIDE.md"


class WorkflowConfigTests(unittest.TestCase):
    def test_editor_contracts_use_one_scheduled_run_without_retry_slots(self):
        for contract_path in (
            EDITOR_CONTRACT,
            SATURDAY_CONTRACT,
            GUIDE_CONTRACT,
        ):
            contract = contract_path.read_text(encoding="utf-8")
            self.assertIn("예약 실행은 한 번만", contract)
            self.assertNotIn("RETRY_PENDING", contract)
            self.assertNotIn("09:25", contract)
            self.assertNotIn("14:25", contract)

    def test_daily_contract_does_not_backfill_or_block_on_missed_days(self):
        contract = EDITOR_CONTRACT.read_text(encoding="utf-8")

        self.assertIn("과거 날짜의 뉴스 글이나 티스토리 발행이 누락됐어도", contract)
        self.assertIn("누락일을 자동으로 소급 생성하지", contract)

    def test_weekly_contracts_do_not_depend_on_the_daily_draft(self):
        for contract_path in (SATURDAY_CONTRACT, GUIDE_CONTRACT):
            contract = contract_path.read_text(encoding="utf-8")
            self.assertIn("다른 예약 글의 누락과 관계없이", contract)
            self.assertNotIn("daily_guard --today --require-complete", contract)

    def test_editor_contracts_keep_browser_qa_outside_repository(self):
        for contract_path in (
            EDITOR_CONTRACT,
            SATURDAY_CONTRACT,
            GUIDE_CONTRACT,
        ):
            contract = contract_path.read_text(encoding="utf-8")
            self.assertIn("/tmp/blog-writing-qa/", contract)
            self.assertIn("저장소 루트가 아니라", contract)

    def test_editor_contracts_never_launch_the_chrome_app_directly(self):
        for contract_path in (
            EDITOR_CONTRACT,
            SATURDAY_CONTRACT,
            GUIDE_CONTRACT,
        ):
            contract = contract_path.read_text(encoding="utf-8")
            self.assertIn("Google Chrome 앱 실행 파일을 직접 호출하지 않습니다", contract)
            self.assertIn("Playwright CLI 또는 제공된 브라우저 도구", contract)

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

    def test_pages_deploy_does_not_depend_on_runtime_apt_packages(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertNotIn("apt-get", workflow)
        self.assertIn(
            "BLOG_FONT_PATH: /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            workflow,
        )
        self.assertIn('test -r "$BLOG_FONT_PATH"', workflow)

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
        self.assertIn("cron: '20 23 * * *'", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn(
            "python3 -m blog_pipeline.collection.collect_news --today", workflow
        )
        self.assertIn(
            "python3 -m blog_pipeline.collection.sync_tistory_posts", workflow
        )
        self.assertIn("tests.test_sync_tistory_posts", workflow)
        self.assertIn("git add config/tistory_public_posts.json docs/inbox", workflow)
        self.assertIn("git pull --rebase origin main", workflow)
        self.assertIn("git push origin HEAD:main", workflow)
        self.assertNotIn("generate_daily_draft", workflow)
        self.assertNotIn("generate_editorial_images", workflow)
        self.assertNotIn("GEMINI_API_KEY", workflow)
        self.assertNotIn("models: read", workflow)

    def test_saturday_collection_workflow_only_collects_ranked_candidates(self):
        workflow = AUTOMATION_COLLECT_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("name: Collect Saturday automation candidates", workflow)
        self.assertIn("cron: '17 22 * * 5'", workflow)
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
            ROOT / "agent" / "DEVELOPMENT_GUIDE.md",
            ROOT / "agent" / "REPOSITORY_SYNC.md",
            ROOT / "config" / "tistory_public_posts.json",
            ROOT / "config" / "search_opportunities.json",
            ROOT / "blog_pipeline" / "collection" / "sync_tistory_posts.py",
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

        self.assertIn("agent/REPOSITORY_SYNC.md", contract)
        self.assertIn("git fetch origin main", contract)
        self.assertIn("git rev-list --left-right --count", contract)
        self.assertNotIn("git pull --ff-only origin main", contract)
        self.assertNotIn("git ls-remote origin refs/heads/main", contract)
        self.assertIn("LOCAL_COMPLETE", contract)
        self.assertNotIn("sync_main", contract)
        self.assertIn("daily_guard --today", contract)
        self.assertIn("daily_guard --today --source-only", contract)
        self.assertIn("원고 사전검사", contract)
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
        self.assertIn("실전 IT 아티클 1건", contract)
        self.assertIn("`primary_query`", contract)
        self.assertIn("후보 5건", contract)
        self.assertIn("관련 글 2개", contract)
        self.assertIn("35~45%", contract)
        self.assertIn("하나의 로컬 커밋", contract)
        self.assertIn("digest-news-copy", contract)
        self.assertIn("사용자 인계 지점", contract)
        self.assertIn("오늘 글 발행 준비", contract)
        self.assertIn("실제 조립·복사 흐름", contract)
        self.assertIn("직전 2일에 사용한 원문 호스트", contract)
        self.assertIn("추천 5건에서 제외", contract)
        self.assertIn("`recent_publisher`, `recent_topic_family`, `recent_brands`", contract)
        self.assertIn("긴급 보안 취약점이나 대규모 서비스 장애", contract)
        self.assertIn("반복 브랜드를 제목에서 제외", contract)
        self.assertIn("대표 이미지는 새 핵심 대상", contract)
        self.assertIn("매주 월·목 09:00 KST", contract)
        self.assertIn("소식은 글을 여는 단서로만", contract)
        self.assertIn("발표 후 30일 이내", contract)
        self.assertIn("요즘IT·GeekNews", contract)
        self.assertIn("검색자가 반복해서 묻는 질문", contract)
        self.assertIn("최신성은 동점자를 가르는 조건", contract)
        self.assertIn("검색 지속성 35 · 실제 문제 해결성 30", contract)
        self.assertIn("본문의 80% 이상", contract)
        self.assertIn("문제 장면 → 왜 생기는지", contract)
        self.assertIn("후보 하나의 공식 근거가 부족하거나 중복이라고 해서", contract)
        self.assertIn("상위 후보를 최대 10건까지 검토", contract)
        self.assertIn("공식 제품 블로그·변경 기록·문서 최소 3곳", contract)
        self.assertIn("`selected` 일부만 확인했거나", contract)
        self.assertIn("실제 검토한 후보 제목과 탈락 이유", contract)
        self.assertIn("`temporary_source_unavailable`", contract)
        self.assertIn("한 후보의 원문 접근에 30초 이상 머물지 않습니다", contract)
        self.assertNotIn("`RETRY_PENDING`", contract)
        self.assertNotIn("09:25 재실행", contract)
        self.assertIn("같은 `topic_family`를 한 건만 포함", contract)
        self.assertIn("직전 4일에 제목·핵심 개체로 노출된 제품·회사 브랜드", contract)
        self.assertIn("직전 2일의 핵심 `topic_family`", contract)
        self.assertIn("단순 기능 추가·가격·사용법·일반 연구에는 `rotation_exception`을 쓰지 않습니다", contract)

    def test_saturday_contract_stages_and_checks_the_complete_publish_bundle(self):
        contract = SATURDAY_CONTRACT.read_text(encoding="utf-8")

        self.assertIn("agent/REPOSITORY_SYNC.md", contract)
        self.assertIn("git fetch origin main", contract)
        self.assertIn("git rev-list --left-right --count", contract)
        self.assertNotIn("git pull --ff-only origin main", contract)
        self.assertNotIn("git ls-remote origin refs/heads/main", contract)
        self.assertIn("LOCAL_COMPLETE", contract)
        self.assertIn("publish_bundle --draft-id YYYY-MM-DD-automation --resume-check", contract)
        self.assertIn(
            "publish_bundle --draft-id YYYY-MM-DD-automation --stage",
            contract,
        )
        self.assertIn(
            "publish_bundle --draft-id YYYY-MM-DD-automation --check",
            contract,
        )

    def test_development_guide_contract_enforces_the_complete_pipeline(self):
        contract = GUIDE_CONTRACT.read_text(encoding="utf-8")

        self.assertIn("agent/REPOSITORY_SYNC.md", contract)
        self.assertIn("git fetch origin main", contract)
        self.assertIn("git rev-list --left-right --count", contract)
        self.assertNotIn("git pull --ff-only origin main", contract)
        self.assertNotIn("git ls-remote origin refs/heads/main", contract)
        self.assertIn("LOCAL_COMPLETE", contract)
        self.assertIn("publish_bundle --draft-id YYYY-MM-DD-guide --resume-check", contract)
        self.assertIn("현업 도구·공개 지식 비교", contract)
        self.assertIn("인기도와 품질을 같은 것처럼", contract)
        self.assertIn("같은 입력으로 실행할 수 있는 비교", contract)
        self.assertIn("daily_guard --draft-id YYYY-MM-DD-guide --source-only", contract)
        self.assertIn("publish_bundle --draft-id YYYY-MM-DD-guide --stage", contract)
        self.assertIn("publish_bundle --draft-id YYYY-MM-DD-guide --check", contract)
        self.assertIn("config/tistory_public_posts.json", contract)
        self.assertIn("content_role: hook", contract)
        self.assertIn("content_role: explanation", contract)

    def test_repository_sync_contract_allows_safe_offline_generation(self):
        contract = (ROOT / "agent" / "REPOSITORY_SYNC.md").read_text(encoding="utf-8")

        self.assertIn("git fetch origin main", contract)
        self.assertIn("git rev-list --left-right --count HEAD...refs/remotes/origin/main", contract)
        self.assertIn("OFFLINE_SAFE", contract)
        self.assertIn("LOCAL_COMPLETE", contract)
        self.assertIn("REMOTE_PUSHED_VERIFY_PENDING", contract)
        self.assertIn("실제 분기", contract)
        self.assertNotIn("git pull --ff-only origin main", contract)
        self.assertNotIn("최대 세 번", contract)

    def test_all_editorial_contracts_require_varied_cover_art_direction(self):
        for contract_path in (
            EDITOR_CONTRACT,
            GUIDE_CONTRACT,
            SATURDAY_CONTRACT,
        ):
            contract = contract_path.read_text(encoding="utf-8")

            with self.subTest(contract=contract_path.name):
                self.assertIn("`art_direction`", contract)
                self.assertIn("`composition_type`", contract)
                self.assertIn("`palette_family`", contract)
                self.assertIn("`cover_kind: editorial_scene`", contract)
                self.assertIn("`Asset intent: editorial-scene`", contract)
                self.assertIn("최근 7개 대표", contract)
                self.assertIn("three_column_cards", contract)
                self.assertIn("대표 이미지에는 단계 화살표", contract)

    def test_all_editorial_contracts_keep_cover_text_light_and_links_natural(self):
        for contract_path in (
            EDITOR_CONTRACT,
            GUIDE_CONTRACT,
            SATURDAY_CONTRACT,
        ):
            contract = contract_path.read_text(encoding="utf-8")

            with self.subTest(contract=contract_path.name):
                self.assertIn("대표 이미지의 한국어 라벨", contract)
                self.assertIn("1~3개", contract)
                self.assertIn("억지", contract)

    def test_all_editorial_contracts_require_search_intent_and_link_roles(self):
        for contract_path in (
            EDITOR_CONTRACT,
            GUIDE_CONTRACT,
            SATURDAY_CONTRACT,
        ):
            contract = contract_path.read_text(encoding="utf-8")

            with self.subTest(contract=contract_path.name):
                self.assertIn("config/search_opportunities.json", contract)
                self.assertIn("editorial.search_intent", contract)
                self.assertIn("foundation", contract)
                self.assertIn("next_step", contract)

    def test_editor_contract_requires_article_specific_image_briefs_and_review(self):
        contract = EDITOR_CONTRACT.read_text(encoding="utf-8")

        self.assertIn("대표 이미지 1장", contract)
        self.assertIn("설명 이미지 2~4장", contract)
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
        self.assertIn("도구·워크플로 비교 실험", contract)
        self.assertIn("GitHub 스타·버전·최근 활동·라이선스", contract)
        self.assertIn("상황별 선택", contract)
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
        self.assertIn("완성한 작업이나 해결한 문제를 제목 앞부분", contract)
        self.assertIn("`origin`", contract)
        self.assertIn("`imagegen`", contract)
        self.assertIn("결정적 대체 이미지는 발행 준비를 통과하지", contract)

    def test_all_editorial_contracts_require_natural_search_focused_writing(self):
        for path in (EDITOR_CONTRACT, SATURDAY_CONTRACT, GUIDE_CONTRACT):
            with self.subTest(path=path.name):
                contract = path.read_text(encoding="utf-8")
                self.assertIn("핵심 검색어", contract)
                self.assertIn("태그 5~8개", contract)
                self.assertIn("보고서", contract)
                self.assertIn("이번 글에서는", contract)

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
