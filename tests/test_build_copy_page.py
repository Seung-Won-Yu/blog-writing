import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from blog_pipeline.publishing.build_copy_page import (
    SKIN_CSS_PATH,
    apply_refresh_handoffs,
    draft_work_date,
    json_for_script,
    load_drafts,
    render,
    safe_image_assets,
    scheduled_label,
    sort_drafts,
    valid_refresh_date,
    write_preview_pages,
)


class CopyPageTests(unittest.TestCase):
    def test_refresh_completion_date_sorts_old_article_before_yesterday_new_draft(self):
        original = {
            "draft_id": "2026-08-08-automation",
            "source": "data/automation_cases/2026-08-08.json",
            "publish_date": "2026-08-08", "publish_ready": False,
            "scheduled_at": "2026-08-08T09:00:00+09:00",
        }
        yesterday = {"draft_id": "2026-10-12", "publish_date": "2026-10-12"}
        plan = {"refresh_queue": [{
            "draft_id": original["draft_id"], "source": original["source"],
            "page_url": "https://won0322.tistory.com/197",
            "status": "ready_for_review", "refreshed_on": "2026-10-13",
        }]}
        checked = apply_refresh_handoffs([yesterday, original], plan)
        self.assertEqual(checked[0]["draft_id"], original["draft_id"])
        self.assertEqual(draft_work_date(checked[0]), "2026-10-13")
        self.assertEqual(checked[0]["publish_date"], "2026-08-08")
        self.assertEqual(checked[0]["scheduled_at"], original["scheduled_at"])
        self.assertFalse(checked[0]["publish_ready"])
        self.assertNotIn("refreshed_on", original)
        self.assertEqual(apply_refresh_handoffs([yesterday, original], plan), checked)

    def test_mixed_new_and_refreshed_drafts_sort_by_work_date_not_type(self):
        drafts = [
            {"draft_id": "old", "publish_date": "2026-08-08", "refreshed_on": "2026-10-13"},
            {"draft_id": "newer", "publish_date": "2026-10-14"},
            {"draft_id": "new", "publish_date": "2026-10-12"},
            {"draft_id": "older", "publish_date": "2026-09-03", "refreshed_on": "2026-10-11"},
        ]
        self.assertEqual(
            [item["draft_id"] for item in sort_drafts(drafts)],
            ["newer", "old", "new", "older"],
        )

    def test_work_date_ties_are_deterministic_and_do_not_mutate_input(self):
        drafts = [
            {"draft_id": "a", "publish_date": "2026-10-13", "scheduled_at": "09:00"},
            {"draft_id": "c", "publish_date": "2026-08-08", "refreshed_on": "2026-10-13"},
            {"draft_id": "b", "publish_date": "2026-10-13", "scheduled_at": "09:00"},
        ]
        self.assertEqual([d["draft_id"] for d in sort_drafts(drafts)], ["b", "a", "c"])
        self.assertEqual([d["draft_id"] for d in drafts], ["a", "c", "b"])

    def test_refresh_date_must_be_an_explicit_canonical_calendar_date(self):
        for value in [None, 20261013, "", "20261013", "2026-1-3", "2026-02-30",
                      "2026-10-13T09:00:00+09:00", "<script>", " 2026-10-13"]:
            with self.subTest(value=value):
                self.assertEqual(valid_refresh_date(value), "")
                self.assertEqual(draft_work_date({
                    "publish_date": "2026-08-08", "refreshed_on": value,
                }), "2026-08-08")
        self.assertEqual(valid_refresh_date("2026-10-13"), "2026-10-13")

    def test_missing_or_invalid_completion_date_keeps_original_order(self):
        old = {"draft_id": "2026-09-03", "publish_date": "2026-09-03",
               "source": "data/days/2026-09-03.json"}
        newer = {"draft_id": "2026-10-12", "publish_date": "2026-10-12"}
        for refreshed_on in [None, "2026-02-30"]:
            with self.subTest(refreshed_on=refreshed_on):
                checked = apply_refresh_handoffs([old, newer], {"refresh_queue": [{
                    "draft_id": old["draft_id"], "source": old["source"],
                    "page_url": "https://won0322.tistory.com/221", "status": "published",
                    "refreshed_on": refreshed_on,
                }]})
                self.assertEqual(checked[0]["draft_id"], newer["draft_id"])
                self.assertIn("replacement_target_url", checked[1])
                self.assertNotIn("refreshed_on", checked[1])

    def test_render_groups_and_defaults_to_refresh_date_but_keeps_original_identity(self):
        old = {"draft_id": "2026-08-08-automation", "publish_date": "2026-08-08",
               "refreshed_on": "2026-10-13", "title": "기존 글 수정본"}
        new = {"draft_id": "2026-10-12", "publish_date": "2026-10-12"}
        page = render([new, old])
        self.assertIn('const latest = "2026-08-08-automation";', page)
        self.assertLess(page.index('2026-10-13 · 1건'), page.index('2026-10-12 · 1건'))
        self.assertIn('data-draft-id="2026-08-08-automation"', page)
        self.assertIn('기존 글 보완 · 최초 발행 2026-08-08', page)
        self.assertIn('"publish_date": "2026-08-08"', page)
        self.assertIn('id="workDate"', page)
        self.assertNotIn('data-draft-id="2026-10-13"', page)

    def test_completed_refresh_is_labeled_as_replacement_without_bypassing_qa(self):
        original = {
            "draft_id": "2026-09-03", "source": "data/days/2026-09-03.json",
            "publish_ready": False, "publish_date": "2026-09-03",
        }
        checked = apply_refresh_handoffs([original], {"refresh_queue": [{
            "draft_id": "2026-09-03", "source": "data/days/2026-09-03.json",
            "page_url": "https://won0322.tistory.com/221", "status": "ready_for_review",
        }]})
        self.assertEqual(checked[0]["replacement_target_url"], "https://won0322.tistory.com/221")
        self.assertIn("본문 교체", checked[0]["scheduled_label"])
        self.assertFalse(checked[0]["publish_ready"])
        self.assertEqual(checked[0]["publish_date"], "2026-09-03")
        self.assertNotIn("replacement_target_url", original)

    def test_planned_or_invalid_target_does_not_claim_a_completed_refresh(self):
        draft = {"draft_id": "2026-09-03", "source": "data/days/2026-09-03.json"}
        for status, url, source in [
            ("planned", "https://won0322.tistory.com/221", draft["source"]),
            ("in_progress", "https://won0322.tistory.com/221", draft["source"]),
            ("ready_for_review", "https://example.com/221", draft["source"]),
            ("ready_for_review", "https://won0322.tistory.com/221", "data/days/2026-09-04.json"),
        ]:
            with self.subTest(status=status, url=url):
                checked = apply_refresh_handoffs([draft], {"refresh_queue": [{
                    "draft_id": draft["draft_id"], "source": source,
                    "page_url": url, "status": status, "refreshed_on": "2026-10-13",
                }]})
                self.assertNotIn("replacement_target_url", checked[0])
                self.assertNotIn("refreshed_on", checked[0])

    def test_deep_link_can_only_select_a_known_draft(self):
        page = render([])
        self.assertIn('new URLSearchParams(window.location.search).get("draft")', page)
        self.assertIn("byId.has(requestedDraft) ? requestedDraft : latest", page)
        self.assertIn("기존 글 교체용", page)

    def test_preview_uses_repository_assets_before_public_deploy(self):
        from blog_pipeline.publishing.build_copy_page import render_preview_page

        page = render_preview_page(
            {"title": "미리보기"},
            '<img src="https://seung-won-yu.github.io/blog-writing/tistory/assets/2026-07-19/example.webp">',
        )

        self.assertIn('src="../tistory/assets/2026-07-19/example.webp"', page)
        self.assertNotIn(
            'src="https://seung-won-yu.github.io/blog-writing/tistory/assets/',
            page,
        )

    def test_manual_extra_schedule_is_labeled_as_immediate_publish(self):
        self.assertEqual(
            scheduled_label(
                "2026-07-19T18:40:00+09:00", publication_mode="manual_extra"
            ),
            "즉시 발행 · 2026. 7. 19. (일) 18:40",
        )

    def test_manual_review_hides_internal_production_time(self):
        self.assertEqual(
            scheduled_label(
                "2026-08-28T09:00:00+09:00", publication_mode="manual_review"
            ),
            "1차 검수 완료 · 티스토리에서 직접 발행",
        )

    def test_published_revision_is_labeled_as_a_body_replacement(self):
        self.assertEqual(
            scheduled_label("", publication_mode="published_revision"),
            "공개 글 수정본 · 티스토리에서 본문 교체",
        )

    def test_copy_page_loads_a_published_project_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tistory = root / "docs" / "tistory"
            published = root / "data" / "project_logs" / "published"
            tistory.mkdir(parents=True)
            published.mkdir(parents=True)
            source = {
                "draft_id": "2026-08-25-project",
                "publish_date": "2026-08-25",
                "content_type": "project_log",
                "content_label": "프로젝트 제작기",
            }
            (published / "2026-08-25.json").write_text(
                json.dumps(source, ensure_ascii=False), encoding="utf-8"
            )
            artifact = "2026-08-25-project-revision"
            (tistory / f"{artifact}.html").write_text("draft", encoding="utf-8")
            (tistory / f"{artifact}.json").write_text(
                json.dumps(
                    {
                        "artifact_type": "published_revision",
                        "draft_id": artifact,
                        "revision_of": "2026-08-25-project",
                        "publish_date": "2026-08-25",
                        "content_type": "project_log",
                        "content_label": "프로젝트 제작기 수정본",
                        "publication_mode": "published_revision",
                        "source": "data/project_logs/published/2026-08-25.json",
                        "title": "좋은 주식은 어떻게 고를까?",
                        "publish_ready": True,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch("blog_pipeline.publishing.build_copy_page.ROOT", root), patch(
                "blog_pipeline.publishing.build_copy_page.TISTORY_DIR", tistory
            ):
                drafts = load_drafts()

        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0]["artifact_type"], "published_revision")
        self.assertEqual(
            drafts[0]["scheduled_label"],
            "공개 글 수정본 · 티스토리에서 본문 교체",
        )

    def test_copy_page_uses_ninety_day_guard_for_saturday_automation(self):
        from blog_pipeline.publishing.build_copy_page import apply_guard_results

        drafts = [
            {
                "draft_id": "2026-07-25",
                "publish_date": "2026-07-25",
                "content_type": "daily_news",
                "publish_ready": True,
            },
            {
                "draft_id": "2026-07-25-automation",
                "publish_date": "2026-07-25",
                "content_type": "automation_case",
                "content_label": "업무자동화 실험",
                "publish_ready": True,
            },
        ]
        windows = {}

        def inspect(draft_id, **kwargs):
            windows[draft_id] = kwargs["window_days"]
            return {"status": "COMPLETE", "reasons": []}

        with patch(
            "blog_pipeline.publishing.daily_guard.inspect_draft_state",
            side_effect=inspect,
        ):
            checked = apply_guard_results(drafts, root=Path("/tmp/example"))

        self.assertTrue(all(draft["publish_ready"] for draft in checked))
        self.assertEqual(windows["2026-07-25"], 60)
        self.assertEqual(windows["2026-07-25-automation"], 90)

    def test_copy_page_uses_long_guard_window_for_project_series(self):
        from blog_pipeline.publishing.build_copy_page import apply_guard_results

        drafts = [
            {
                "draft_id": "2026-08-29-project",
                "publish_date": "2026-08-29",
                "content_type": "project_log",
                "content_label": "프로젝트 제작기",
                "publish_ready": True,
            }
        ]

        with patch(
            "blog_pipeline.publishing.daily_guard.inspect_draft_state",
            return_value={"status": "COMPLETE", "reasons": []},
        ) as inspect:
            checked = apply_guard_results(drafts, root=Path("/tmp/example"))

        self.assertTrue(checked[0]["publish_ready"])
        self.assertEqual(inspect.call_args.kwargs["window_days"], 365)

    def test_copy_page_uses_long_guard_window_for_curiosity_articles(self):
        from blog_pipeline.publishing.build_copy_page import apply_guard_results

        drafts = [
            {
                "draft_id": "2026-09-01",
                "publish_date": "2026-09-01",
                "content_type": "daily_news",
                "content_label": "궁금한 IT 원리",
                "publish_ready": True,
            }
        ]

        with patch(
            "blog_pipeline.publishing.daily_guard.inspect_draft_state",
            return_value={"status": "COMPLETE", "reasons": []},
        ) as inspect:
            checked = apply_guard_results(drafts, root=Path("/tmp/example"))

        self.assertTrue(checked[0]["publish_ready"])
        self.assertEqual(inspect.call_args.kwargs["window_days"], 365)

    def test_copy_page_disables_a_publish_ready_draft_when_guard_is_partial(self):
        from blog_pipeline.publishing.build_copy_page import apply_guard_results

        drafts = [
            {
                "draft_id": "2026-07-19",
                "publish_date": "2026-07-19",
                "publish_ready": True,
            }
        ]
        with patch(
            "blog_pipeline.publishing.daily_guard.inspect_draft_state",
            return_value={
                "status": "PARTIAL",
                "reasons": ["quality_depth", "stale_export"],
            },
        ):
            checked = apply_guard_results(drafts, root=Path("/tmp/example"))

        self.assertFalse(checked[0]["publish_ready"])
        self.assertEqual(
            checked[0]["quality_reasons"], ["quality_depth", "stale_export"]
        )
        self.assertIn("quality_reasons", render(checked))

    def test_rejects_non_http_image_links_before_they_reach_download_controls(self):
        assets = safe_image_assets(
            [
                {"kind": "cover", "url": "javascript:alert(1)"},
                {"kind": "visual_1", "url": "data:text/html,bad"},
                {"kind": "visual_2", "url": "https://example.com/safe.webp"},
            ]
        )

        self.assertEqual(
            assets,
            [
                {
                    "kind": "visual_2",
                    "url": "https://example.com/safe.webp",
                }
            ],
        )
        page = render([])
        self.assertIn('["http:", "https:"].includes(url.protocol)', page)

    def test_same_date_previews_keep_news_and_automation_bodies_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tistory = root / "tistory"
            preview = root / "preview"
            tistory.mkdir()
            (tistory / "2026-07-18.html").write_text(
                "<article>뉴스 전용 본문</article>", encoding="utf-8"
            )
            (tistory / "2026-07-18-automation.html").write_text(
                "<article>자동화 전용 본문</article>", encoding="utf-8"
            )
            drafts = [
                {
                    "draft_id": "2026-07-18",
                    "publish_date": "2026-07-18",
                    "content_label": "뉴스 심층글",
                    "title": "뉴스",
                },
                {
                    "draft_id": "2026-07-18-automation",
                    "publish_date": "2026-07-18",
                    "content_label": "업무자동화 실험",
                    "title": "자동화",
                },
            ]

            with patch(
                "blog_pipeline.publishing.build_copy_page.TISTORY_DIR", tistory
            ), patch(
                "blog_pipeline.publishing.build_copy_page.PREVIEW_DIR", preview
            ):
                write_preview_pages(drafts)

            daily = (preview / "2026-07-18.html").read_text(encoding="utf-8")
            automation = (preview / "2026-07-18-automation.html").read_text(
                encoding="utf-8"
            )

        self.assertIn("뉴스 전용 본문", daily)
        self.assertNotIn("자동화 전용 본문", daily)
        self.assertIn("자동화 전용 본문", automation)
        self.assertNotIn("뉴스 전용 본문", automation)

    def test_preview_prefers_the_same_adfit_fragment_used_for_final_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tistory = root / "tistory"
            preview = root / "preview"
            tistory.mkdir()
            (tistory / "2026-07-19.html").write_text(
                "<article>광고 전 기본 본문</article>", encoding="utf-8"
            )
            (tistory / "2026-07-19-adfit.html").write_text(
                '<article>최종 본문<figure data-ke-type="revenue"></figure></article>',
                encoding="utf-8",
            )

            with patch(
                "blog_pipeline.publishing.build_copy_page.TISTORY_DIR", tistory
            ), patch(
                "blog_pipeline.publishing.build_copy_page.PREVIEW_DIR", preview
            ):
                write_preview_pages(
                    [{"draft_id": "2026-07-19", "title": "미리보기"}]
                )

            page = (preview / "2026-07-19.html").read_text(encoding="utf-8")

        self.assertIn("최종 본문", page)
        self.assertIn('data-ke-type="revenue"', page)
        self.assertNotIn("광고 전 기본 본문", page)

    def test_groups_news_and_automation_drafts_for_the_same_saturday(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tistory = root / "docs" / "tistory"
            days = root / "data" / "days"
            automation_cases = root / "data" / "automation_cases"
            tistory.mkdir(parents=True)
            days.mkdir(parents=True)
            automation_cases.mkdir(parents=True)
            (days / "2026-07-18.json").write_text("{}", encoding="utf-8")
            (automation_cases / "2026-07-18.json").write_text(
                "{}", encoding="utf-8"
            )
            rows = (
                (
                    "2026-07-18",
                    "data/days/2026-07-18.json",
                    "daily_news",
                    "뉴스 심층글",
                    "2026-07-18T09:00:00+09:00",
                ),
                (
                    "2026-07-18-automation",
                    "data/automation_cases/2026-07-18.json",
                    "automation_case",
                    "업무자동화 실험",
                    "2026-07-18T18:00:00+09:00",
                ),
            )
            for draft_id, source, content_type, content_label, scheduled_at in rows:
                (tistory / f"{draft_id}.html").write_text(
                    "<article>draft</article>", encoding="utf-8"
                )
                (tistory / f"{draft_id}.json").write_text(
                    json.dumps(
                        {
                            "draft_id": draft_id,
                            "publish_date": "2026-07-18",
                            "content_type": content_type,
                            "content_label": content_label,
                            "scheduled_at": scheduled_at,
                            "title": content_label,
                            "source": source,
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )

            with patch("blog_pipeline.publishing.build_copy_page.ROOT", root), patch(
                "blog_pipeline.publishing.build_copy_page.TISTORY_DIR", tistory
            ):
                drafts = load_drafts()
            page = render(drafts)

        self.assertEqual(len(drafts), 2)
        self.assertEqual(
            {item["day"] for item in drafts},
            {"2026-07-18", "2026-07-18-automation"},
        )
        self.assertEqual({item["publish_date"] for item in drafts}, {"2026-07-18"})
        self.assertIn("2026-07-18 · 2건", page)
        self.assertIn("뉴스 심층글", page)
        self.assertIn("업무자동화 실험", page)
        self.assertIn("발행 방식", page)
        self.assertIn('data-draft-id="2026-07-18"', page)
        self.assertIn('data-draft-id="2026-07-18-automation"', page)
        self.assertIn("const byId = new Map", page)
        self.assertNotIn("const byDay = new Map", page)
        self.assertNotIn("button.dataset.day", page)

    def test_copy_page_hides_legacy_drafts_without_local_source_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tistory = root / "docs" / "tistory"
            days = root / "data" / "days"
            tistory.mkdir(parents=True)
            days.mkdir(parents=True)
            for day in ("2026-07-12", "2026-07-13"):
                (tistory / f"{day}.html").write_text("draft", encoding="utf-8")
                (tistory / f"{day}.json").write_text(
                    json.dumps({"title": day, "source": f"data/days/{day}.json"}),
                    encoding="utf-8",
                )
            (days / "2026-07-13.json").write_text("{}", encoding="utf-8")

            with patch("blog_pipeline.publishing.build_copy_page.ROOT", root), patch(
                "blog_pipeline.publishing.build_copy_page.TISTORY_DIR", tistory
            ):
                drafts = load_drafts()

        self.assertEqual([item["day"] for item in drafts], ["2026-07-13"])

    def test_copy_page_rejects_metadata_whose_id_differs_from_its_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tistory = root / "docs" / "tistory"
            days = root / "data" / "days"
            automation = root / "data" / "automation_cases"
            tistory.mkdir(parents=True)
            days.mkdir(parents=True)
            automation.mkdir(parents=True)
            (days / "2026-07-18.json").write_text("{}", encoding="utf-8")
            (automation / "2026-07-18.json").write_text("{}", encoding="utf-8")
            (tistory / "2026-07-18-automation.html").write_text(
                "draft", encoding="utf-8"
            )
            (tistory / "2026-07-18-automation.json").write_text(
                json.dumps(
                    {
                        "draft_id": "2026-07-18",
                        "source": "data/days/2026-07-18.json",
                    }
                ),
                encoding="utf-8",
            )

            with patch("blog_pipeline.publishing.build_copy_page.ROOT", root), patch(
                "blog_pipeline.publishing.build_copy_page.TISTORY_DIR", tistory
            ):
                drafts = load_drafts()

        self.assertEqual(drafts, [])

    def test_explains_the_minimal_daily_publish_flow(self):
        html = render([])

        self.assertIn('name="robots" content="noindex,nofollow,noarchive"', html)
        self.assertIn("오늘 글 발행 준비", html)
        self.assertIn("월·수·금은 새 글, 화·목은 기존 글 개선", html)
        self.assertIn("CONTENT_GROWTH_TRIAL.md", html)
        self.assertIn("토요일 프로젝트 글", html)
        self.assertNotIn("수요일 개발 가이드", html)
        self.assertIn("HTML 모드에 한 번 붙여넣고", html)
        self.assertNotIn("Run workflow", html)
        self.assertNotIn("tistory-draft.yml", html)
        self.assertNotIn("조이한", html)
        self.assertIn('role="status"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn('href="integration.html"', html)
        self.assertIn("보강글 HTML 조립", html)
        self.assertIn("독자 품질", html)
        self.assertIn("이해도 ", html)
        self.assertIn("가독성 ", html)
        self.assertIn("understanding >= 8.5 && readability >= 8.5", html)

    def test_shows_ready_skin_contract_without_claiming_remote_deployment(self):
        page = render(
            [],
            skin_contract={
                "status": "COMPLETE",
                "version": "project-reader-v1",
                "sha256": "b04fa6c54c841a8fbb347876560585f6",
                "reasons": [],
            },
        )

        self.assertIn("발행 스킨 준비 완료", page)
        self.assertIn("project-reader-v1", page)
        self.assertIn("CSS b04fa6c54c84", page)
        self.assertIn("스킨 변경 시 티스토리에 다시 적용", page)
        self.assertNotIn("티스토리 적용 완료", page)

    def test_warns_when_skin_contract_is_not_ready(self):
        page = render(
            [],
            skin_contract={
                "status": "PARTIAL",
                "version": "project-reader-v1",
                "sha256": "",
                "reasons": ["stale_preview_skin_css"],
            },
        )

        self.assertIn("발행 중지 · 스킨 계약 확인 필요", page)
        self.assertIn("stale_preview_skin_css", page)
        self.assertIn('class="skin-contract is-error"', page)

    def test_draft_buttons_expose_selected_state_and_fetch_recovery(self):
        html = render(
            [
                {
                    "day": "2026-07-13",
                    "title": "오늘의 초안",
                    "title_candidates": [],
                    "category": "데일리IT뉴스",
                    "tags": "AI",
                    "meta_description": "설명",
                    "key_summary": [],
                    "publish_checklist": [],
                    "image_assets": [],
                    "source": "data/days/2026-07-13.json",
                    "source_page": "",
                    "html_path": "tistory/2026-07-13.html",
                    "preview_path": "preview/2026-07-13.html",
                    "meta_path": "tistory/2026-07-13.json",
                    "generation_provider": "gemini",
                    "publish_ready": True,
                }
            ]
        )

        self.assertIn('aria-pressed="false"', html)
        self.assertIn('button.setAttribute("aria-pressed"', html)
        self.assertIn("초안을 불러오지 못했습니다", html)
        self.assertIn("let selectionRevision = 0;", html)
        self.assertIn("const revision = ++selectionRevision;", html)
        self.assertIn("if (revision !== selectionRevision) return;", html)
        self.assertIn('for="htmlCode"', html)
        self.assertIn('copyText(currentFinalHtml, "최종 HTML")', html)
        self.assertIn("최종 HTML 복사", html)
        self.assertIn("기본모드로 다시 전환하지 마세요", html)
        self.assertIn('id="adMarkup"', html)
        self.assertIn('id="buildFinalButton"', html)
        self.assertIn("function buildFinalHtml(showMessage = true)", html)
        self.assertIn("function extractRevenueMarkup(value)", html)
        self.assertIn("function isFinalHtmlStructurallyValid(value)", html)
        self.assertIn('document.createElement("textarea")', html)
        self.assertIn('document.execCommand("copy")', html)
        self.assertIn('helper.setSelectionRange(0, helper.value.length)', html)
        self.assertIn("복사에 실패했습니다", html)

    def test_final_html_validation_accepts_deep_story_and_digest_layouts(self):
        html = render([])

        self.assertIn(
            'const nextSection = parsed.querySelector(".digest-lead-continuation") || news[1];',
            html,
        )
        self.assertIn(
            "articles.length !== 1 || news.length < 1 || ads.length !== 1 || !nextSection",
            html,
        )
        self.assertIn("ads[0].compareDocumentPosition(nextSection)", html)
        self.assertNotIn("news.length !== 3", html)

    def test_allows_publish_ready_copy_without_required_manual_review(self):
        html = render([])

        self.assertNotIn('id="editorNote"', html)
        self.assertNotIn('id="verificationNote"', html)
        self.assertNotIn('id="sourceChecked"', html)
        self.assertNotIn('id="relatedUrl"', html)
        self.assertIn('id="finalCopyButton"', html)
        self.assertIn('data-copy="final" disabled', html)
        self.assertIn('id="htmlCode" spellcheck="false" readonly', html)
        self.assertNotIn("검수 완료 후 HTML 코드가 표시됩니다.", html)
        self.assertNotIn("function buildAuthorNoteHtml()", html)
        self.assertNotIn('class="digest-author-note"', html)
        self.assertIn("function isDraftCopyReady()", html)
        self.assertNotIn("editorNote.length >= 40", html)
        self.assertNotIn("verificationNote.length >= 40", html)
        self.assertNotIn("Boolean(els.sourceChecked.checked)", html)
        self.assertIn("current.publish_ready", html)
        self.assertIn("currentBaseHtml", html)
        self.assertIn("최종 HTML 준비 완료", html)
        self.assertNotIn("메모는 선택", html)
        self.assertIn("발행 보류", html)

    def test_shows_only_information_needed_to_publish(self):
        html = render([])

        self.assertIn("추천 제목", html)
        self.assertIn("카테고리", html)
        self.assertIn("태그", html)
        self.assertIn("대표 이미지", html)
        self.assertIn("광고 HTML 태그", html)
        self.assertNotIn("검색형 제목 후보", html)
        self.assertNotIn("오늘의 핵심 요약", html)
        self.assertNotIn("발행 체크리스트", html)
        self.assertNotIn("운영 정보 전체 복사", html)
        self.assertNotIn("첫 문단/메타", html)
        self.assertNotIn("데이터 경로", html)

    def test_loads_generation_readiness_from_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tistory = root / "docs" / "tistory"
            days = root / "data" / "days"
            tistory.mkdir(parents=True)
            days.mkdir(parents=True)
            (tistory / "2026-07-13.html").write_text("draft", encoding="utf-8")
            (tistory / "2026-07-13.json").write_text(
                json.dumps(
                    {
                        "title": "오늘의 초안",
                        "source": "data/days/2026-07-13.json",
                        "generation_provider": "gemini",
                        "publish_ready": True,
                    }
                ),
                encoding="utf-8",
            )
            (days / "2026-07-13.json").write_text("{}", encoding="utf-8")

            with patch("blog_pipeline.publishing.build_copy_page.ROOT", root), patch(
                "blog_pipeline.publishing.build_copy_page.TISTORY_DIR", tistory
            ):
                draft = load_drafts()[0]

        self.assertEqual(draft["generation_provider"], "gemini")
        self.assertTrue(draft["publish_ready"])

    def test_selects_named_cover_and_escapes_payload_for_script_context(self):
        unsafe = "뉴스 </script><script>alert(1)</script> & 흐름\u2028다음"
        encoded = json_for_script({"title": unsafe})
        self.assertNotIn("</script>", encoded)
        self.assertNotIn("<script>", encoded)
        self.assertNotIn("\u2028", encoded)
        self.assertIn("\\u003c/script\\u003e", encoded)

        html = render([])
        self.assertIn('asset.kind === "cover"', html)
        self.assertIn('aspect-ratio: 1200 / 630', html)
        self.assertIn("els.coverPreview.alt =", html)
        self.assertNotIn('asset.kind === "flow"', html)
        self.assertNotIn('asset.kind.startsWith("story_")', html)
        self.assertNotIn("본문 1번 이미지 열기", html)

    def test_body_preview_toggles_inline_next_to_copy_button(self):
        html = render([])

        self.assertIn(
            '<button class="btn" type="button" id="previewButton" aria-expanded="false" aria-controls="previewPane" disabled>본문 미리보기</button>',
            html,
        )
        self.assertLess(html.index('id="previewButton"'), html.index('data-copy="final"'))
        self.assertIn(
            '<section class="preview-pane" id="previewPane" aria-label="블로그 본문 미리보기" hidden>',
            html,
        )
        self.assertIn(
            '<iframe class="preview-frame" id="previewFrame" title="블로그 본문 미리보기" sandbox="allow-same-origin" referrerpolicy="no-referrer"></iframe>',
            html,
        )
        self.assertIn('currentPreviewPath = draft.preview_path + "?v=" + Date.now();', html)
        self.assertIn('els.previewFrame.setAttribute("src", currentPreviewPath);', html)
        self.assertIn('showingPreview && !els.previewFrame.hasAttribute("src")', html)
        self.assertIn('els.previewButton.addEventListener("click"', html)
        self.assertNotIn('els.previewFrame.addEventListener("load"', html)
        self.assertNotIn("updatePreviewNote", html)
        self.assertIn('els.previewPane.hidden = !showingPreview;', html)
        self.assertIn('els.htmlCode.hidden = showingPreview;', html)
        self.assertIn('els.previewButton.textContent = showingPreview', html)
        self.assertIn('els.previewButton.setAttribute("aria-expanded"', html)
        self.assertNotIn("previewDialog", html)
        self.assertNotIn("showModal", html)
        self.assertIn(".action-row {", html)
        self.assertIn(".preview-pane {", html)
        self.assertIn("textarea[hidden], .preview-pane[hidden] { display: none; }", html)
        self.assertLess(
            html.index('<div class="status" id="status"'),
            html.index('<section class="preview-pane" id="previewPane"'),
        )

    def test_writes_a_utf8_script_blocked_standalone_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tistory = root / "tistory"
            preview = root / "preview"
            tistory.mkdir()
            (tistory / "2026-07-13.html").write_text(
                '<article><h2>한글 제목</h2><script>alert("x")</script></article>',
                encoding="utf-8",
            )
            drafts = [
                {
                    "day": "2026-07-13",
                    "title": "한글 제목",
                    "html_path": "tistory/2026-07-13.html",
                    "preview_path": "preview/2026-07-13.html",
                }
            ]

            with patch(
                "blog_pipeline.publishing.build_copy_page.TISTORY_DIR", tistory
            ), patch(
                "blog_pipeline.publishing.build_copy_page.PREVIEW_DIR", preview
            ):
                write_preview_pages(drafts)

            page = (preview / "2026-07-13.html").read_text(encoding="utf-8")
            shared_skin = (preview / "tistory-style.css").read_text(encoding="utf-8")

        self.assertIn('<meta charset="utf-8">', page)
        self.assertIn('name="robots" content="noindex,nofollow,noarchive"', page)
        self.assertIn('Content-Security-Policy', page)
        self.assertIn("script-src 'none'", page)
        self.assertIn("style-src 'self' 'unsafe-inline'", page)
        self.assertIn('<link rel="stylesheet" href="tistory-style.css">', page)
        self.assertIn("body.preview-page { height: auto;", page)
        self.assertIn("한글 제목 · 본문 미리보기", page)
        self.assertEqual(SKIN_CSS_PATH.name, "style.css")
        self.assertIn('<body id="tt-body-page"', page)
        self.assertIn('<div class="post-cover">', page)
        self.assertIn('<section id="container">', page)
        self.assertIn('<div class="content-wrap">', page)
        self.assertIn('<article id="content">', page)
        self.assertIn('<div class="entry-content" id="article-view">', page)
        self.assertIn(
            '<div class="tt_article_useless_p_margin contents_style">', page
        )
        self.assertNotIn('<main class="entry-content">', page)
        self.assertNotIn(
            ".entry-content { width: min(760px, 100%);", page
        )
        self.assertIn("--sw-content: 720px", shared_skin)
        self.assertIn(
            ".entry-content > .tt_article_useless_p_margin > .daily-digest-post",
            shared_skin,
        )
        self.assertIn("<article><h2>한글 제목</h2>", page)
        self.assertEqual(page.count("<article><h2>한글 제목</h2>"), 1)


if __name__ == "__main__":
    unittest.main()
