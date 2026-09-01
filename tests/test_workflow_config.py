import hashlib
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
CURIOSITY_CONTRACT = ROOT / "agent" / "CURIOSITY_EDITOR.md"
PROJECT_CONTRACT = ROOT / "agent" / "PROJECT_SERIES.md"
READER_QUALITY_CONTRACT = ROOT / "agent" / "READER_QUALITY_LOOP.md"
WEEKLY_READER_CONTRACT = ROOT / "agent" / "WEEKLY_READER_PROMISES.md"
WEEKLY_VISUAL_CONTRACT = ROOT / "agent" / "WEEKLY_VISUAL_PROMISES.md"
WEEKLY_PIPELINE_CONTRACT = ROOT / "agent" / "WEEKLY_PIPELINE.md"
HARU_BIBLE = ROOT / "editorial" / "curiosity" / "characters" / "HARU_CHARACTER_BIBLE.md"
HARU_SHEET = ROOT / "editorial" / "curiosity" / "characters" / "haru-character-sheet-v1.png"
PUBLISH_BUNDLE = ROOT / "blog_pipeline" / "publishing" / "publish_bundle.py"
HARU_SHA256 = "573f3b2e4d3785fa89cbdbd922248e5e1ce17d04ca88a251425dde9c6ed186da"


class WorkflowConfigTests(unittest.TestCase):
    def test_editor_contracts_use_one_scheduled_run_without_retry_slots(self):
        for contract_path in (
            EDITOR_CONTRACT,
            SATURDAY_CONTRACT,
            GUIDE_CONTRACT,
            CURIOSITY_CONTRACT,
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

    def test_collection_contracts_guard_against_stale_latest_inboxes(self):
        daily = EDITOR_CONTRACT.read_text(encoding="utf-8")
        friday = SATURDAY_CONTRACT.read_text(encoding="utf-8")

        self.assertIn("inbox_guard --kind news --today", daily)
        self.assertIn("RECOLLECT_REQUIRED", daily)
        self.assertIn("inbox_guard --kind automation --today", friday)
        self.assertIn("RECOLLECT_REQUIRED", friday)
        self.assertIn("보존된 이전 후보", friday)

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
            CURIOSITY_CONTRACT,
        ):
            contract = contract_path.read_text(encoding="utf-8")
            self.assertIn("/tmp/blog-writing-qa/", contract)
            self.assertIn("저장소 루트가 아니라", contract)

    def test_editor_contracts_never_launch_the_chrome_app_directly(self):
        for contract_path in (
            EDITOR_CONTRACT,
            SATURDAY_CONTRACT,
            GUIDE_CONTRACT,
            CURIOSITY_CONTRACT,
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
        self.assertIn("blog_pipeline.publishing.pages_smoke", workflow)
        self.assertIn("steps.deployment.outputs.page_url", workflow)
        self.assertIn("REMOTE_PUSHED_VERIFY_PENDING", workflow)

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

        self.assertIn("name: Collect Monday Wednesday news candidates", workflow)
        self.assertIn("cron: '30 21 * * 0,2'", workflow)
        self.assertIn("150-minute buffer", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn(
            "python3 -m blog_pipeline.collection.collect_news", workflow
        )
        self.assertIn("args=(--today)", workflow)
        self.assertIn(
            "python3 -m blog_pipeline.collection.sync_tistory_posts", workflow
        )
        self.assertIn("tests.test_sync_tistory_posts", workflow)
        self.assertIn("git add config/tistory_public_posts.json docs/inbox", workflow)
        self.assertIn("git pull --rebase origin main", workflow)
        self.assertIn(
            "python3 -m blog_pipeline.publishing.repository_sync push "
            "--remote origin --ref HEAD:main",
            workflow,
        )
        self.assertNotIn("generate_daily_draft", workflow)
        self.assertNotIn("generate_editorial_images", workflow)
        self.assertNotIn("GEMINI_API_KEY", workflow)
        self.assertNotIn("models: read", workflow)

    def test_friday_developer_insight_workflow_only_collects_ranked_candidates(self):
        workflow = AUTOMATION_COLLECT_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("name: Collect Friday developer insight candidates", workflow)
        self.assertIn("cron: '30 21 * * 4'", workflow)
        self.assertIn("150-minute buffer", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn(
            "python3 -m blog_pipeline.collection.collect_automation",
            workflow,
        )
        self.assertIn("args=(--today)", workflow)
        self.assertIn("tests.test_collect_automation", workflow)
        self.assertIn("git add docs/automation-inbox", workflow)
        self.assertIn("git pull --rebase origin main", workflow)
        self.assertIn(
            "python3 -m blog_pipeline.publishing.repository_sync push "
            "--remote origin --ref HEAD:main",
            workflow,
        )
        self.assertNotIn("generate_daily_draft", workflow)
        self.assertNotIn("generate_editorial_images", workflow)
        self.assertNotIn("export_tistory", workflow)
        self.assertNotIn("GEMINI_API_KEY", workflow)
        self.assertNotIn("models: read", workflow)

    def test_collection_workflows_expose_recovery_date_status_and_bounded_runtime(self):
        for workflow_path, status_path in (
            (COLLECT_WORKFLOW, "docs/inbox/status.json"),
            (AUTOMATION_COLLECT_WORKFLOW, "docs/automation-inbox/status.json"),
        ):
            workflow = workflow_path.read_text(encoding="utf-8")
            with self.subTest(workflow=workflow_path.name):
                self.assertIn("target_day:", workflow)
                self.assertIn("force_off_schedule:", workflow)
                self.assertIn("--regular-day-only", workflow)
                self.assertIn("group: content-main-writer", workflow)
                self.assertIn("timeout-minutes: 25", workflow)
                self.assertIn("continue-on-error: true", workflow)
                self.assertIn(status_path, workflow)
                self.assertIn("GITHUB_STEP_SUMMARY", workflow)
                self.assertIn("Fail when collection handoff is not ready", workflow)

    def test_weekly_pipeline_contract_fixes_schedule_inputs_and_manual_handoff(self):
        pipeline = WEEKLY_PIPELINE_CONTRACT.read_text(encoding="utf-8")

        for contract_path in (
            EDITOR_CONTRACT,
            CURIOSITY_CONTRACT,
            SATURDAY_CONTRACT,
            PROJECT_CONTRACT,
        ):
            with self.subTest(contract=contract_path.name):
                self.assertIn(
                    "WEEKLY_PIPELINE.md",
                    contract_path.read_text(encoding="utf-8"),
                )
        self.assertIn("06:30 KST", pipeline)
        self.assertIn("150분", pipeline)
        self.assertIn("09:00 KST", pipeline)
        self.assertIn("10:00 KST 전후", pipeline)
        self.assertIn("자동 발행하지 않는다", pipeline)
        self.assertIn("editorial.selection_evaluation", pipeline)
        for role in (
            "evergreen_problem",
            "curiosity_mechanism",
            "change_explainer",
            "curiosity_myth_history",
            "developer_insight",
            "project_series",
        ):
            self.assertIn(role, pipeline)

    def test_legacy_wednesday_guide_is_explicitly_inactive(self):
        legacy = GUIDE_CONTRACT.read_text(encoding="utf-8")

        self.assertIn("비활성 레거시 계약", legacy)
        self.assertIn("PAUSED", legacy)
        self.assertIn("실행 금지", legacy)

    def test_project_series_limits_private_evidence_to_public_safe_summaries(self):
        contract = PROJECT_CONTRACT.read_text(encoding="utf-8")

        self.assertIn("공개 저장소로 보낼 수 있는 payload", contract)
        self.assertIn("비식별 집계값", contract)
        self.assertIn("비공개 저장소의 원문", contract)
        self.assertIn("코드·patch·diff·로그·DB 행", contract)
        self.assertIn("토큰·키·쿠키", contract)
        self.assertIn("이미지 메타데이터", contract)
        self.assertIn("토요일 전용 100점", contract)
        self.assertIn("80점 이상", contract)
        self.assertIn("실제 코드·테스트·리플레이·모의투자 증거 30", contract)
        self.assertIn("policy: project_story-v1", contract)
        self.assertIn("quality_selection_evaluation", contract)
        publish_bundle = PUBLISH_BUNDLE.read_text(encoding="utf-8")
        self.assertIn("project_public_safety_reasons", publish_bundle)
        self.assertIn("private_evidence_leak", publish_bundle)
        self.assertIn("read_bytes", publish_bundle)

    def test_pages_deploy_has_a_bounded_runtime(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("timeout-minutes: 35", workflow)
        self.assertIn("paths-ignore:", workflow)
        self.assertIn("docs/inbox/**", workflow)
        self.assertIn("docs/automation-inbox/**", workflow)

    def test_agent_contract_and_clean_package_layout_exist(self):
        expected = (
            ROOT / "agent" / "DAILY_EDITOR.md",
            ROOT / "agent" / "SATURDAY_AUTOMATION.md",
            ROOT / "agent" / "DEVELOPMENT_GUIDE.md",
            ROOT / "agent" / "CURIOSITY_EDITOR.md",
            ROOT / "agent" / "WEEKLY_PIPELINE.md",
            ROOT / "agent" / "REPOSITORY_SYNC.md",
            ROOT / "config" / "tistory_public_posts.json",
            ROOT / "config" / "search_opportunities.json",
            ROOT / "config" / "search_performance.example.csv",
            ROOT
            / "blog_pipeline"
            / "collection"
            / "analyze_search_performance.py",
            ROOT / "blog_pipeline" / "collection" / "sync_tistory_posts.py",
            ROOT / "blog_pipeline" / "collection" / "collect_news.py",
            ROOT / "blog_pipeline" / "collection" / "collect_automation.py",
            ROOT / "blog_pipeline" / "collection" / "news_pipeline.py",
            ROOT / "blog_pipeline" / "publishing" / "export_tistory.py",
            ROOT / "blog_pipeline" / "publishing" / "build_copy_page.py",
            ROOT / "blog_pipeline" / "publishing" / "build_integration_page.py",
            ROOT / "blog_pipeline" / "publishing" / "daily_guard.py",
            ROOT / "blog_pipeline" / "publishing" / "publish_bundle.py",
            ROOT / "blog_pipeline" / "publishing" / "repository_sync.py",
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
        self.assertIn(
            "daily_guard --today --source-only --window-days 365", contract
        )
        self.assertIn("원고 사전검사", contract)
        self.assertIn(
            "daily_guard --today --require-complete --window-days 365", contract
        )
        self.assertIn("publish_bundle --today --stage", contract)
        self.assertIn("publish_bundle --today --check", contract)
        self.assertIn("optimize_images --today", contract)
        self.assertIn("webp-v1", contract)
        self.assertIn("`COMPLETE`: 즉시 종료", contract)
        self.assertIn("`docs/inbox/latest.json`", contract)
        self.assertIn("`problem_signals`", contract)
        self.assertIn("`unknown_publication_date: true`", contract)
        self.assertIn("inbox_guard --kind news --today", contract)
        self.assertNotIn("`docs/inbox/YYYY-MM-DD.json`", contract)
        self.assertIn("최근 60일", contract)
        self.assertIn("최근 365일", contract)
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
        self.assertIn("매주 월·수 09:00 KST", contract)
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
        self.assertIn("공식 제품 블로그·변경 기록·표준·문서 최소 3곳", contract)
        self.assertIn("collect_news --today`를 같은 실행에서 딱 한 번", contract)
        self.assertIn("Codex 웹 리서치", contract)
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
        self.assertIn("`NO_PUBLISH_QUALITY`", contract)
        self.assertIn("`publication_mode: manual_review`", contract)
        self.assertIn("75점", contract)
        self.assertIn("원고·이미지·커밋·푸시를 만들지", contract)
        self.assertIn("월요일 `evergreen_problem`", contract)
        self.assertIn("수요일 `change_explainer`", contract)
        self.assertIn("`selection.editorial_lane`", contract)
        self.assertIn("`weekly_lane_score`", contract)
        self.assertIn("`editorial.reader_hook`", contract)
        for field in ("`scene`", "`stakes`", "`payoff`", "`open_question`"):
            self.assertIn(field, contract)

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
        self.assertIn("`NO_PUBLISH_QUALITY`", contract)
        self.assertIn("collect_automation --today`를 같은 실행에서 딱 한 번", contract)
        self.assertIn("Codex 웹 리서치", contract)
        self.assertIn("75점", contract)
        self.assertIn("원고·이미지·커밋·푸시를 만들지", contract)
        self.assertIn("`developer_insight`", contract)
        self.assertIn("`editorial.reader_hook`", contract)

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
        self.assertIn("여러 GitHub 저장소·공식 문서·Agent Skills", contract)
        self.assertIn("금요일 개발·AI 인사이트로 보내고", contract)
        self.assertIn("daily_guard --draft-id YYYY-MM-DD-guide --source-only", contract)
        self.assertIn("publish_bundle --draft-id YYYY-MM-DD-guide --stage", contract)
        self.assertIn("publish_bundle --draft-id YYYY-MM-DD-guide --check", contract)
        self.assertIn("config/tistory_public_posts.json", contract)
        self.assertIn("content_role: hook", contract)
        self.assertIn("content_role: explanation", contract)

    def test_curiosity_contract_enforces_evergreen_tuesday_thursday_articles(self):
        contract = CURIOSITY_CONTRACT.read_text(encoding="utf-8")

        self.assertIn("매주 화·목 09:00 KST", contract)
        self.assertIn("`궁금한 IT 원리`", contract)
        self.assertIn("`curiosity_mechanism`", contract)
        self.assertIn("`curiosity_myth_history`", contract)
        self.assertIn("12개월 뒤에도 검색할 질문", contract)
        self.assertIn("공통 60점", contract)
        self.assertIn("화요일 `curiosity_mechanism` 전용 40점", contract)
        self.assertIn("목요일 `curiosity_myth_history` 전용 40점", contract)
        self.assertIn("안전한 1분 확인", contract)
        self.assertIn("믿는 설명과 실제 사실", contract)
        self.assertIn("최근 365일", contract)
        self.assertIn("공식 문서·표준·원 논문", contract)
        self.assertIn("오래된 표준과 원 논문", contract)
        self.assertIn("`NO_PUBLISH_EVIDENCE`", contract)
        self.assertIn("`NO_PUBLISH_QUALITY`", contract)
        self.assertIn("후보를 최대 10건까지 한 번 더 탐색", contract)
        self.assertIn("`publication_mode`: `manual_review`", contract)
        self.assertIn("data/days/YYYY-MM-DD.json", contract)
        self.assertIn("daily_guard --today --source-only --window-days 365", contract)
        self.assertIn("publish_bundle --today --stage", contract)
        self.assertIn("publish_bundle --today --check", contract)
        self.assertIn("티스토리에는 자동 발행하지 않습니다", contract)

    def test_project_contract_runs_at_nine_and_expands_evidence_before_hold(self):
        contract = PROJECT_CONTRACT.read_text(encoding="utf-8")

        self.assertIn("매주 토요일 09:00 KST", contract)
        self.assertIn("`publication_mode`은 `manual_review`", contract)
        self.assertIn("한 번 더 탐색", contract)
        self.assertIn("Codex 웹 리서치", contract)
        self.assertIn("그래도 핵심 구현 증거가 없을 때만", contract)
        self.assertIn("티스토리 예약 시각이 아니다", contract)
        self.assertIn("일반 독자 8.5 제작 기준", contract)
        self.assertIn("`30초 요약`", contract)
        self.assertIn("본문 한 문단은 200자 이하", contract)
        self.assertIn("결과로 끝내지 말고", contract)

    def test_all_active_editor_contracts_rewrite_until_reader_scores_reach_eight_point_five(self):
        for contract_path in (
            EDITOR_CONTRACT,
            CURIOSITY_CONTRACT,
            SATURDAY_CONTRACT,
            PROJECT_CONTRACT,
        ):
            contract = contract_path.read_text(encoding="utf-8")
            with self.subTest(contract=contract_path.name):
                self.assertIn("8.5", contract)
                self.assertIn("quality_reader_access", contract)
                self.assertIn("public_readability", contract)
                self.assertIn("READER_QUALITY_LOOP.md", contract)

        recovery = READER_QUALITY_CONTRACT.read_text(encoding="utf-8")
        self.assertIn("사용자에게 넘기지 않는다", recovery)
        self.assertIn("두 점수가 모두", recovery)
        self.assertIn("다음 후보로 원고를 새로", recovery)

    def test_all_active_editors_share_design_but_keep_distinct_reader_promises(self):
        for contract_path in (
            EDITOR_CONTRACT,
            CURIOSITY_CONTRACT,
            SATURDAY_CONTRACT,
            PROJECT_CONTRACT,
        ):
            contract = contract_path.read_text(encoding="utf-8")
            with self.subTest(contract=contract_path.name):
                self.assertIn("WEEKLY_READER_PROMISES.md", contract)
                self.assertIn("editorial.reader_path", contract)

        promises = WEEKLY_READER_CONTRACT.read_text(encoding="utf-8")
        for weekday in ("월요일", "화요일", "수요일", "목요일", "금요일", "토요일"):
            self.assertIn(weekday, promises)
        self.assertIn("공통 디자인", promises)
        self.assertIn("reader_level", promises)
        self.assertIn("entry_heading", promises)
        self.assertIn("immediate_answer", promises)
        self.assertIn("action_steps", promises)
        self.assertIn("completion_check", promises)
        self.assertIn("advanced_heading", promises)

    def test_all_active_editors_share_image_quality_but_keep_weekday_visual_roles(self):
        for contract_path in (
            EDITOR_CONTRACT,
            CURIOSITY_CONTRACT,
            SATURDAY_CONTRACT,
            PROJECT_CONTRACT,
        ):
            contract = contract_path.read_text(encoding="utf-8")
            with self.subTest(contract=contract_path.name):
                self.assertIn("WEEKLY_VISUAL_PROMISES.md", contract)

        promises = WEEKLY_VISUAL_CONTRACT.read_text(encoding="utf-8")
        for weekday in ("월요일", "화요일", "수요일", "목요일", "금요일", "토요일"):
            self.assertIn(weekday, promises)
        for field in (
            "visual.weekday_profile",
            "visual.subject_terms",
            "weekday_role",
            "teaching_role",
            "visual_claim",
            "teaching_claim",
            "render_family",
        ):
            self.assertIn(field, promises)

    def test_tuesday_toon_uses_the_locked_male_haru_reference(self):
        curiosity = CURIOSITY_CONTRACT.read_text(encoding="utf-8")
        promises = WEEKLY_VISUAL_CONTRACT.read_text(encoding="utf-8")
        bible = HARU_BIBLE.read_text(encoding="utf-8")

        self.assertTrue(HARU_SHEET.exists())
        self.assertEqual(
            hashlib.sha256(HARU_SHEET.read_bytes()).hexdigest(),
            HARU_SHA256,
        )
        self.assertIn("HARU_CHARACTER_BIBLE.md", curiosity)
        self.assertIn("고정 남성 캐릭터", curiosity)
        self.assertIn("하루의 IT 원리툰", promises)
        self.assertIn("20대 후반 한국인 남성", bible)
        self.assertIn(HARU_SHA256, bible)
        self.assertIn("no speech bubbles", bible)

    def test_toon_styles_are_scoped_and_preview_mirrors_the_skin_source(self):
        skin_css = (ROOT / "design" / "tistory" / "style.css").read_text(
            encoding="utf-8"
        )
        preview_css = (
            ROOT / "docs" / "preview" / "tistory-style.css"
        ).read_text(encoding="utf-8")

        self.assertEqual(skin_css, preview_css)
        self.assertIn(
            ".daily-digest-post .digest-content-figure.digest-toon-panel",
            skin_css,
        )
        self.assertIn(".daily-digest-post .digest-toon-dialogue", skin_css)
        self.assertIn(".daily-digest-post .digest-toon-bubble p", skin_css)

    def test_repository_sync_contract_allows_safe_offline_generation(self):
        contract = (ROOT / "agent" / "REPOSITORY_SYNC.md").read_text(encoding="utf-8")

        self.assertIn("git fetch origin main", contract)
        self.assertIn("git rev-list --left-right --count HEAD...refs/remotes/origin/main", contract)
        self.assertIn("OFFLINE_SAFE", contract)
        self.assertIn("LOCAL_COMPLETE", contract)
        self.assertIn("REMOTE_PUSHED_VERIFY_PENDING", contract)
        self.assertIn("실제 분기", contract)
        self.assertNotIn("git pull --ff-only origin main", contract)
        self.assertIn("최대 3회", contract)
        self.assertIn("blog_pipeline.publishing.repository_sync push", contract)

    def test_all_editorial_contracts_require_varied_cover_art_direction(self):
        for contract_path in (
            EDITOR_CONTRACT,
            GUIDE_CONTRACT,
            SATURDAY_CONTRACT,
            CURIOSITY_CONTRACT,
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
            CURIOSITY_CONTRACT,
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
            CURIOSITY_CONTRACT,
        ):
            contract = contract_path.read_text(encoding="utf-8")

            with self.subTest(contract=contract_path.name):
                self.assertIn("config/search_opportunities.json", contract)
                self.assertIn("editorial.search_intent", contract)
                self.assertIn("foundation", contract)
                self.assertIn("next_step", contract)

    def test_all_editorial_contracts_require_original_value_and_specific_covers(self):
        for contract_path in (
            EDITOR_CONTRACT,
            GUIDE_CONTRACT,
            SATURDAY_CONTRACT,
            CURIOSITY_CONTRACT,
        ):
            contract = contract_path.read_text(encoding="utf-8")

            with self.subTest(contract=contract_path.name):
                self.assertIn("editorial.original_value", contract)
                for field in (
                    "durable_question",
                    "source_gap",
                    "contribution",
                    "proof_method",
                    "reader_outcome",
                    "limits",
                    "editorial_treatment",
                    "focal_subject",
                    "texture_cue",
                    "authenticity_cue",
                ):
                    self.assertIn(f"`{field}`", contract)
                self.assertIn("`images.cover.alt`", contract)
                self.assertIn("15~160자", contract)

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

    def test_friday_contract_owns_sourced_developer_ai_insights(self):
        daily = EDITOR_CONTRACT.read_text(encoding="utf-8")
        contract = SATURDAY_CONTRACT.read_text(encoding="utf-8")

        self.assertIn("SATURDAY_AUTOMATION.md", daily)
        self.assertNotIn("### GitHub 적용 사례형", daily)
        self.assertIn("금요일 09:00 KST", contract)
        self.assertIn("2026-08-28부터 금요일", contract)
        self.assertIn("사용자가 최종 확인 뒤 직접", contract)
        self.assertIn('"publication_mode": "manual_review"', contract)
        self.assertIn("생태계 지도", contract)
        self.assertIn("공식 문서 해설", contract)
        self.assertIn("근거 기반 목록", contract)
        self.assertIn("개발자 커리어 분석", contract)
        self.assertIn("GitHub 스타·버전·최근 활동·라이선스", contract)
        self.assertIn("상황별 선택", contract)
        self.assertIn("검색 지속성 20", contract)
        self.assertIn("개발자 관련성 25", contract)
        self.assertIn("출처 신뢰도 20", contract)
        self.assertIn("원문에 더하는 분석 20", contract)
        self.assertIn("궁금증 유발력 15", contract)
        self.assertIn("검증한 버전·커밋", contract)
        self.assertIn("기대 결과와 실제 결과", contract)
        self.assertIn("임시 디렉터리", contract)
        self.assertIn("의심스러운 설치 스크립트", contract)
        self.assertIn("구조 분석", contract)
        self.assertIn("측정하지 않은 숫자", contract)
        self.assertIn("공식 문서·GitHub 화면의 주석 캡처", contract)
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
        self.assertIn("코드를 이해해야만 효용을 얻는 개발 주제도 허용", contract)
        self.assertIn("개발자와 IT에 관심 있는 독자", contract)
        self.assertIn("공식·원출처 포함 3개 이상의 근거", contract)
        self.assertIn("제목은 `구체적 대상 + 독자가 가진 질문 + 읽고 얻을 판단`", contract)
        self.assertIn("`editorial.reader_walkthrough`", contract)
        self.assertIn("첫 코드보다 앞에 준비물 목록", contract)
        self.assertIn("20줄을 넘는 전체 코드", contract)
        self.assertIn("`easiest_method_considered`", contract)
        self.assertIn("코드는 필수가 아닙니다", contract)
        self.assertIn("`근거와 한계`", contract)
        self.assertIn("`origin`", contract)
        self.assertIn("`imagegen`", contract)
        self.assertIn("결정적 대체 이미지는 발행 준비를 통과하지", contract)

    def test_all_editorial_contracts_require_natural_search_focused_writing(self):
        for path in (
            EDITOR_CONTRACT,
            SATURDAY_CONTRACT,
            GUIDE_CONTRACT,
            CURIOSITY_CONTRACT,
        ):
            with self.subTest(path=path.name):
                contract = path.read_text(encoding="utf-8")
                self.assertIn("핵심 검색어", contract)
                self.assertIn("태그 5~8개", contract)
                self.assertIn("보고서", contract)
                self.assertIn("이번 글에서는", contract)

    def test_friday_contract_matches_the_developer_insight_evidence_schema(self):
        contract = SATURDAY_CONTRACT.read_text(encoding="utf-8")

        for field in (
            "verification",
            "mode",
            "checked_at",
            "scope",
            "method",
            "selection_rule",
            "limitations",
            "source_urls",
            "source_count",
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
