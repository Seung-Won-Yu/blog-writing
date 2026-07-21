import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

from blog_pipeline.publishing.daily_guard import (
    find_recent_duplicates,
    find_recent_draft_duplicates,
    inspect_daily_state,
    inspect_draft_state,
)


class DailyGuardTests(unittest.TestCase):
    def test_final_saturday_guard_blocks_recent_repository_and_primary_query(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous_day = "2026-07-25"
            previous_id = f"{previous_day}-automation"
            self.write_json(
                root / "data" / "automation_cases" / f"{previous_day}.json",
                {
                    "draft_id": previous_id,
                    "publish_date": previous_day,
                    "content_type": "automation_case",
                    "primary_query": "n8n 실패 워크플로 알림 자동화",
                    "verification": {
                        "problem_lane": "워크플로",
                        "tool_brand": "n8n",
                    },
                    "news": [
                        {
                            "title_kr": "n8n 실패 알림",
                            "url": "https://github.com/n8n-io/n8n/releases/tag/v2",
                        }
                    ],
                },
            )
            self.write_json(
                root / "docs" / "tistory" / f"{previous_id}.json",
                {
                    "draft_id": previous_id,
                    "publish_date": previous_day,
                    "content_type": "automation_case",
                    "source": f"data/automation_cases/{previous_day}.json",
                    "publish_ready": True,
                },
            )
            current = {
                "editorial": {"topic_key": "different-topic"},
                "primary_query": "n8n 워크플로 실패 알림 만들기",
                "verification": {
                    "problem_lane": "서버 운영",
                    "tool_brand": "Community Tool",
                },
                "news": [
                    {
                        "title_kr": "별도 서버 운영 실험",
                        "url": "https://github.com/n8n-io/n8n/issues/99999",
                    }
                ],
            }

            duplicates = find_recent_draft_duplicates(
                "2026-08-01-automation",
                current,
                root=root,
                window_days=90,
            )

        self.assertTrue(
            {item["reason"] for item in duplicates}
            & {"same_repository", "similar_primary_query"}
        )

    def test_preview_must_embed_the_current_final_adfit_fragment(self):
        from blog_pipeline.publishing.build_copy_page import render_preview_page
        from blog_pipeline.publishing.daily_guard import preview_artifact_reasons

        with tempfile.TemporaryDirectory() as directory:
            preview = Path(directory) / "preview.html"
            current = (
                '<article class="daily-digest-post">current'
                '<figure data-ad-vendor="adfit"></figure></article>'
            )
            meta = {
                "title": "현재 글",
                "category": "데일리IT뉴스",
                "publish_date": "2026-07-19",
                "content_label": "뉴스 심층글",
            }
            preview.write_text(
                '<!doctype html><article class="daily-digest-post">old</article>',
                encoding="utf-8",
            )

            stale = preview_artifact_reasons(preview, current, meta)
            preview.write_text(
                render_preview_page(meta, current), encoding="utf-8"
            )
            fresh = preview_artifact_reasons(preview, current, meta)
            preview.write_text(
                "<!doctype html><main>"
                f"<!--{current}-->"
                '<article class="daily-digest-post">stale visible</article>'
                "</main>",
                encoding="utf-8",
            )
            hidden_canonical = preview_artifact_reasons(preview, current, meta)

        self.assertEqual(stale, ["stale_preview_artifact"])
        self.assertEqual(fresh, [])
        self.assertEqual(hidden_canonical, ["stale_preview_artifact"])

    def test_future_guard_malformed_nested_objects_fail_closed(self):
        from tests.test_editorial_quality import valid_daily_source

        for label, mutate in (
            ("editorial_boolean", lambda source: source.update({"editorial": True})),
            ("news_item_boolean", lambda source: source.update({"news": [True]})),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = valid_daily_source("2026-07-19")
                mutate(source)
                self.write_json(root / "data" / "days" / "2026-07-19.json", source)
                self.write_json(root / "docs" / "tistory" / "2026-07-19.json", {})

                result = inspect_draft_state("2026-07-19", root=root, window_days=60)

                self.assertEqual(result["status"], "PARTIAL")
                self.assertTrue(result["reasons"])

    def test_ci_uses_ninety_day_duplicate_window_for_automation(self):
        from blog_pipeline.publishing.daily_guard import inspect_publish_ready_drafts

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_json(
                root / "data" / "days" / "2026-07-25.json",
                {"draft_id": "2026-07-25", "publish_date": "2026-07-25"},
            )
            self.write_json(
                root / "data" / "automation_cases" / "2026-07-25.json",
                {
                    "draft_id": "2026-07-25-automation",
                    "publish_date": "2026-07-25",
                    "content_type": "automation_case",
                },
            )
            windows = {}

            def inspect(draft_id, **kwargs):
                windows[draft_id] = kwargs["window_days"]
                return {"draft_id": draft_id, "status": "COMPLETE", "reasons": []}

            with patch(
                "blog_pipeline.publishing.daily_guard.inspect_draft_state",
                side_effect=inspect,
            ):
                result = inspect_publish_ready_drafts(root=root)

        self.assertEqual(result["failures"], [])
        self.assertEqual(windows["2026-07-25"], 60)
        self.assertEqual(windows["2026-07-25-automation"], 90)

    def write_explanatory_png(self, path, variant=0):
        image = Image.new("RGB", (1200, 630), "#f5f1e8")
        draw = ImageDraw.Draw(image)
        offset = 40 * (variant % 4)
        draw.rounded_rectangle(
            (70 + offset, 90, 500 + offset, 540),
            radius=30,
            fill="#2f6f5f",
        )
        draw.rounded_rectangle(
            (690 - offset, 150, 1130 - offset, 500),
            radius=30,
            fill="#d89b45",
        )
        draw.line((500 + offset, 315, 690 - offset, 315), fill="#1f2933", width=18)
        image.save(path, "PNG")

    def test_future_legacy_three_story_format_cannot_skip_strict_quality(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day_id = "2026-07-19"
            self.write_json(
                root / "data" / "days" / f"{day_id}.json",
                {
                    "news": [
                        {"title_kr": "첫 번째", "url": "https://example.com/1"},
                        {"title_kr": "두 번째", "url": "https://example.com/2"},
                        {"title_kr": "세 번째", "url": "https://example.com/3"},
                    ]
                },
            )

            result = inspect_draft_state(day_id, root=root)

        self.assertIn("quality_identity", result["reasons"])

    def test_inline_style_detection_ignores_plain_code_text_but_blocks_attributes(self):
        from blog_pipeline.publishing.daily_guard import has_inline_post_style

        self.assertFalse(
            has_inline_post_style(
                '<pre><code>element.style = "color: red"; style=demo</code></pre>'
            )
        )
        self.assertTrue(has_inline_post_style('<p style="color:red">text</p>'))
        self.assertTrue(has_inline_post_style('<style>.post { color:red; }</style>'))

    def write_json(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def write_canonical_preview(self, preview_path, meta_path, fragment):
        from blog_pipeline.publishing.build_copy_page import render_preview_page

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.write_text(
            render_preview_page(meta, fragment),
            encoding="utf-8",
        )

    def test_future_daily_can_reach_complete_through_optimize_export_and_guard(self):
        from blog_pipeline.publishing.export_tistory import write_post
        from blog_pipeline.publishing.optimize_images import optimize_draft_images
        from tests.test_editorial_quality import valid_daily_source

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day_id = "2026-07-19"
            source = valid_daily_source(day_id)
            asset_dir = root / "docs" / "tistory" / "assets" / day_id
            asset_dir.mkdir(parents=True)
            filenames = {
                "cover": "대표-적용조건-비교.png",
                "visual_1": "변경전-변경후-흐름.png",
                "visual_2": "확인절차-결과신호.png",
            }
            for index, (kind, filename) in enumerate(filenames.items()):
                path = asset_dir / filename
                self.write_explanatory_png(path, index)
                source["images"][kind].update(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "url": f"https://example.com/assets/{day_id}/{filename}",
                    }
                )
            source_path = root / "data" / "days" / f"{day_id}.json"
            self.write_json(source_path, source)

            optimize_draft_images(day_id, root=root)
            stored = json.loads(source_path.read_text(encoding="utf-8"))
            out = root / "docs" / "tistory"
            with patch(
                "blog_pipeline.publishing.export_tistory.HERE", root
            ), patch(
                "blog_pipeline.publishing.export_tistory.OUT_DIR", out
            ):
                write_post(day_id, day=stored)
            preview = root / "docs" / "preview" / f"{day_id}.html"
            final_fragment = (out / f"{day_id}-adfit.html").read_text(
                encoding="utf-8"
            )
            self.write_canonical_preview(
                preview,
                out / f"{day_id}.json",
                final_fragment,
            )

            result = inspect_draft_state(day_id, root=root, window_days=60)

        self.assertEqual(result["status"], "COMPLETE", result["reasons"])
        self.assertEqual(result["reasons"], [])

    def test_future_guard_binds_canonical_source_to_images_body_and_adfit(self):
        from blog_pipeline.publishing.export_tistory import (
            TISTORY_ADFIT_MARKER,
            write_post,
        )
        from blog_pipeline.publishing.optimize_images import optimize_draft_images
        from tests.test_editorial_quality import valid_daily_source

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day_id = "2026-07-19"
            source = valid_daily_source(day_id)
            asset_dir = root / "docs" / "tistory" / "assets" / day_id
            asset_dir.mkdir(parents=True)
            for index, kind in enumerate(("cover", "visual_1", "visual_2")):
                path = asset_dir / f"{index + 1}번-{kind}-설명이미지.png"
                self.write_explanatory_png(path, index)
                source["images"][kind].update(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "url": f"https://example.com/assets/{day_id}/{path.name}",
                    }
                )
            source_path = root / "data" / "days" / f"{day_id}.json"
            self.write_json(source_path, source)
            optimize_draft_images(day_id, root=root)
            stored = json.loads(source_path.read_text(encoding="utf-8"))
            out = root / "docs" / "tistory"
            with patch(
                "blog_pipeline.publishing.export_tistory.HERE", root
            ), patch(
                "blog_pipeline.publishing.export_tistory.OUT_DIR", out
            ):
                write_post(day_id, day=stored)
            preview = root / "docs" / "preview" / f"{day_id}.html"
            final_fragment = (out / f"{day_id}-adfit.html").read_text(
                encoding="utf-8"
            )
            self.write_canonical_preview(
                preview,
                out / f"{day_id}.json",
                final_fragment,
            )

            original_meta = json.loads(
                (out / f"{day_id}.json").read_text(encoding="utf-8")
            )
            tampered_meta = copy.deepcopy(original_meta)
            tampered_meta["image_assets"][0]["url"] = "https://evil.example/cover.webp"
            tampered_meta["image_assets"][0]["alt"] = "본문과 무관한 이미지"
            self.write_json(out / f"{day_id}.json", tampered_meta)
            image_result = inspect_draft_state(day_id, root=root, window_days=60)

            self.write_json(out / f"{day_id}.json", original_meta)
            body_path = out / f"{day_id}.html"
            adfit_path = out / f"{day_id}-adfit.html"
            tampered_body = body_path.read_text(encoding="utf-8").replace(
                "일반 사용자가 확인할 새 기능 변경",
                "검증되지 않은 다른 주장",
                1,
            )
            tampered_adfit = tampered_body.replace(
                '<div class="digest-ad-break" data-digest-ad-break="true"></div>',
                TISTORY_ADFIT_MARKER,
                1,
            )
            body_path.write_text(tampered_body, encoding="utf-8")
            adfit_path.write_text(tampered_adfit, encoding="utf-8")
            forged_meta = copy.deepcopy(original_meta)
            forged_meta["html_sha256"] = hashlib.sha256(
                body_path.read_bytes()
            ).hexdigest()
            forged_meta["adfit_sha256"] = hashlib.sha256(
                adfit_path.read_bytes()
            ).hexdigest()
            self.write_json(out / f"{day_id}.json", forged_meta)
            self.write_canonical_preview(
                preview,
                out / f"{day_id}.json",
                tampered_adfit,
            )
            body_result = inspect_draft_state(day_id, root=root, window_days=60)

        self.assertIn("invalid_publish_metadata", image_result["reasons"])
        self.assertIn("stale_html_artifact", body_result["reasons"])
        self.assertIn("stale_adfit_artifact", body_result["reasons"])

    def test_future_saturday_can_reach_complete_with_real_execution_evidence(self):
        from blog_pipeline.publishing.export_tistory import write_post
        from blog_pipeline.publishing.optimize_images import optimize_draft_images
        from tests.test_editorial_quality import valid_automation_source

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day_id = "2026-07-25"
            draft_id = f"{day_id}-automation"
            source = valid_automation_source(day_id)
            asset_dir = root / "docs" / "tistory" / "assets" / draft_id
            asset_dir.mkdir(parents=True)
            filenames = {
                "cover": "메일첨부-날짜폴더-자동정리.png",
                "visual_1": "실행전-테스트파일-캡처.png",
                "visual_2": "자동정리-처리흐름-도식.png",
                "visual_3": "실행후-성공실패-결과.png",
            }
            for index, (kind, filename) in enumerate(filenames.items()):
                path = asset_dir / filename
                self.write_explanatory_png(path, index)
                source["images"][kind].update(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "url": f"https://example.com/assets/{draft_id}/{filename}",
                    }
                )
            source_path = root / "data" / "automation_cases" / f"{day_id}.json"
            self.write_json(source_path, source)

            optimize_draft_images(draft_id, root=root)
            stored = json.loads(source_path.read_text(encoding="utf-8"))
            out = root / "docs" / "tistory"
            with patch(
                "blog_pipeline.publishing.export_tistory.HERE", root
            ), patch(
                "blog_pipeline.publishing.export_tistory.OUT_DIR", out
            ):
                write_post(draft_id, day=stored)
            preview = root / "docs" / "preview" / f"{draft_id}.html"
            final_fragment = (out / f"{draft_id}-adfit.html").read_text(
                encoding="utf-8"
            )
            self.write_canonical_preview(
                preview,
                out / f"{draft_id}.json",
                final_fragment,
            )

            result = inspect_draft_state(draft_id, root=root, window_days=90)

        self.assertEqual(result["status"], "COMPLETE", result["reasons"])
        self.assertEqual(result["reasons"], [])

    def test_artifact_freshness_rejects_changed_source_and_adfit_copy(self):
        from blog_pipeline.publishing.daily_guard import artifact_freshness_reasons

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.json"
            html = root / "post.html"
            adfit = root / "post-adfit.html"
            source.write_text('{"version": 1}', encoding="utf-8")
            html.write_text("<article>current body</article>", encoding="utf-8")
            adfit.write_text(
                '<article>current body<figure data-ad-vendor="adfit"></figure></article>',
                encoding="utf-8",
            )
            digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            meta = {
                "source_sha256": digest(source),
                "html_sha256": digest(html),
                "adfit_sha256": digest(adfit),
            }

            self.assertEqual(
                artifact_freshness_reasons(source, meta, html, adfit), []
            )
            source.write_text('{"version": 2}', encoding="utf-8")
            adfit.write_text(
                '<article>stale other body<figure data-ad-vendor="adfit"></figure></article>',
                encoding="utf-8",
            )
            reasons = artifact_freshness_reasons(source, meta, html, adfit)

        self.assertIn("stale_source_export", reasons)
        self.assertIn("stale_adfit_artifact", reasons)

    def test_all_publish_ready_scan_fails_on_a_partial_future_draft(self):
        from blog_pipeline.publishing.daily_guard import inspect_publish_ready_drafts

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_json(
                root / "docs" / "tistory" / "2026-07-19.json",
                {
                    "draft_id": "2026-07-19",
                    "publish_date": "2026-07-19",
                    "content_type": "daily_news",
                    "publish_ready": True,
                },
            )
            with patch(
                "blog_pipeline.publishing.daily_guard.inspect_draft_state",
                return_value={
                    "draft_id": "2026-07-19",
                    "status": "PARTIAL",
                    "reasons": ["quality_depth"],
                },
            ):
                result = inspect_publish_ready_drafts(root=root)

        self.assertEqual(result["checked"], 1)
        self.assertEqual(result["failures"][0]["draft_id"], "2026-07-19")

    def test_ci_scan_does_not_ignore_future_sources_or_not_ready_metadata(self):
        from blog_pipeline.publishing.daily_guard import inspect_publish_ready_drafts

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_json(
                root / "data" / "days" / "2026-07-19.json",
                {"draft_id": "2026-07-19", "publish_date": "2026-07-19"},
            )
            self.write_json(
                root / "docs" / "tistory" / "2026-07-20.json",
                {
                    "draft_id": "2026-07-20",
                    "publish_date": "2026-07-20",
                    "content_type": "daily_news",
                    "publish_ready": False,
                },
            )
            with patch(
                "blog_pipeline.publishing.daily_guard.inspect_draft_state",
                side_effect=lambda draft_id, **_kwargs: {
                    "draft_id": draft_id,
                    "status": "PARTIAL",
                    "reasons": ["not_publish_ready"],
                },
            ):
                result = inspect_publish_ready_drafts(root=root)

        self.assertEqual(result["checked"], 2)
        self.assertEqual(
            {item["draft_id"] for item in result["failures"]},
            {"2026-07-19", "2026-07-20"},
        )

    def test_daily_complete_and_saturday_automation_new_are_independent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = "2026-07-11"
            self.write_json(
                root / "data" / "days" / f"{day}.json",
                {
                    "news": [
                        {"title_kr": "첫 뉴스", "url": "https://example.com/1"},
                        {"title_kr": "둘째 뉴스", "url": "https://example.com/2"},
                        {"title_kr": "셋째 뉴스", "url": "https://example.com/3"},
                    ]
                },
            )
            self.write_json(
                root / "docs" / "tistory" / f"{day}.json",
                {
                    "publish_ready": True,
                    "image_assets": [
                        {"kind": "cover"},
                        {"kind": "story_1"},
                        {"kind": "story_2"},
                        {"kind": "story_3"},
                    ],
                },
            )
            body = (
                '<article class="daily-digest-post">'
                '<section id="digest-news-1" class="digest-news-card">1</section>'
                '<section id="digest-news-2" class="digest-news-card">2</section>'
                '<section id="digest-news-3" class="digest-news-card">3</section>'
                "</article>"
            )
            tistory = root / "docs" / "tistory"
            (tistory / f"{day}.html").write_text(body, encoding="utf-8")
            (tistory / f"{day}-adfit.html").write_text(
                body.replace(
                    '<section id="digest-news-2"',
                    '<figure data-ad-vendor="adfit"></figure><section id="digest-news-2"',
                ),
                encoding="utf-8",
            )
            preview = root / "docs" / "preview"
            preview.mkdir(parents=True)
            (preview / f"{day}.html").write_text(body, encoding="utf-8")

            daily_before = inspect_daily_state(day, root=root)
            automation = inspect_draft_state(f"{day}-automation", root=root)
            daily_after = inspect_daily_state(day, root=root)

        self.assertEqual(daily_before["status"], "COMPLETE")
        self.assertEqual(automation["status"], "NEW")
        self.assertEqual(automation["draft_id"], f"{day}-automation")
        self.assertEqual(daily_after, daily_before)

    def test_saturday_automation_requires_at_least_three_explanatory_visuals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = "2026-07-18"
            self.write_json(
                root / "data" / "automation_cases" / f"{day}.json",
                {
                    "draft_id": f"{day}-automation",
                    "publish_date": day,
                    "content_type": "automation_case",
                    "content_label": "업무자동화 실험",
                    "format": "lead-story-v1",
                    "primary_query": "반복 보고서 자동화",
                    "images": {
                        "cover": {},
                        "visual_1": {},
                        "visual_2": {},
                    },
                    "news": [
                        {
                            "title_kr": "반복 보고서 자동화 실험",
                            "references": [
                                {
                                    "kind": "official",
                                    "title": "공식 문서",
                                    "url": "https://example.com/docs",
                                },
                                {
                                    "kind": "independent",
                                    "title": "보조 자료",
                                    "url": "https://example.net/guide",
                                },
                            ],
                            "content": [
                                {"t": "h", "text": "문제"},
                                {"t": "visual", "image": "visual_1"},
                                {"t": "h", "text": "준비"},
                                {"t": "p", "text": "환경"},
                                {"t": "ad_break"},
                                {"t": "h", "text": "실행"},
                                {"t": "visual", "image": "visual_2"},
                                {"t": "h", "text": "결과"},
                            ],
                        }
                    ],
                    "related_posts": [
                        {
                            "title": "관련 1",
                            "url": "https://won0322.tistory.com/120",
                        },
                        {
                            "title": "관련 2",
                            "url": "https://won0322.tistory.com/121",
                        },
                    ],
                },
            )

            result = inspect_draft_state(f"{day}-automation", root=root)

        self.assertIn("lead_explanatory_visuals", result["reasons"])

    def test_saturday_visual_quality_rejects_deterministic_fallback_images(self):
        from blog_pipeline.publishing import daily_guard

        source = {
            "visual": {
                "assets": [
                    {"origin": "capture", "evidence_type": "screenshot"},
                    {
                        "origin": "deterministic_fallback",
                        "evidence_type": "diagram",
                    },
                    {
                        "origin": "imagegen",
                        "evidence_type": "diagram",
                        "generation_prompt": "버튼 이름 불일치와 수정 전후를 보여 주는 장면",
                        "generation_model": "gpt-image",
                    },
                ]
            },
            "images": {
                "cover": {"origin": "imagegen"},
                "visual_1": {"origin": "capture"},
                "visual_2": {
                    "origin": "deterministic_fallback",
                    "style": "text-free-editorial-scene",
                },
                "visual_3": {"origin": "imagegen"},
            },
        }

        reasons = daily_guard._automation_visual_quality_reasons(source)

        self.assertIn("automation_fallback_image", reasons)

    def test_saturday_visual_quality_accepts_capture_and_imagegen_explanations(self):
        from blog_pipeline.publishing import daily_guard

        source = {
            "visual": {
                "assets": [
                    {"origin": "capture", "evidence_type": "screenshot"},
                    {
                        "origin": "imagegen",
                        "evidence_type": "diagram",
                        "generation_prompt": "메일 첨부파일이 날짜별 폴더로 이동하는 실제 물체 중심 흐름",
                        "generation_model": "gpt-image",
                    },
                    {
                        "origin": "annotated_capture",
                        "evidence_type": "screenshot",
                    },
                ]
            },
            "images": {
                "cover": {"origin": "imagegen"},
                "visual_1": {"origin": "capture"},
                "visual_2": {"origin": "imagegen"},
                "visual_3": {"origin": "annotated_capture"},
            },
        }

        reasons = daily_guard._automation_visual_quality_reasons(source)

        self.assertEqual(reasons, [])

    def test_saturday_visual_quality_rejects_an_unbriefed_extra_fallback_image(self):
        from blog_pipeline.publishing import daily_guard

        source = {
            "visual": {
                "assets": [
                    {"origin": "capture", "evidence_type": "screenshot"},
                    {
                        "origin": "imagegen",
                        "evidence_type": "diagram",
                        "generation_prompt": "폴더 정리 전후를 보여 주는 장면",
                        "generation_model": "gpt-image",
                    },
                ]
            },
            "images": {
                "cover": {"origin": "imagegen"},
                "visual_1": {"origin": "capture"},
                "visual_2": {"origin": "imagegen"},
                "visual_3": {
                    "origin": "deterministic_fallback",
                    "style": "text-free-editorial-scene",
                },
            },
        }

        reasons = daily_guard._automation_visual_quality_reasons(source)

        self.assertIn("automation_image_provenance", reasons)
        self.assertIn("automation_fallback_image", reasons)

    def test_saturday_guard_rejects_mismatched_publish_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = "2026-07-18"
            draft_id = f"{day}-automation"
            self.write_json(
                root / "data" / "automation_cases" / f"{day}.json",
                {
                    "draft_id": draft_id,
                    "publish_date": day,
                    "content_type": "automation_case",
                    "content_label": "업무자동화 실험",
                    "news": [],
                },
            )
            self.write_json(
                root / "docs" / "tistory" / f"{draft_id}.json",
                {
                    "draft_id": day,
                    "publish_date": day,
                    "content_type": "daily_news",
                    "content_label": "뉴스 심층글",
                    "source": f"data/days/{day}.json",
                    "publish_ready": True,
                },
            )

            result = inspect_draft_state(draft_id, root=root)

        self.assertIn("invalid_publish_identity", result["reasons"])
        self.assertIn("invalid_publish_source", result["reasons"])

    def test_complete_day_stops_a_second_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = "2026-07-14"
            self.write_json(
                root / "data" / "days" / f"{day}.json",
                {
                    "news": [
                        {"title_kr": "첫 뉴스", "url": "https://example.com/1"},
                        {"title_kr": "둘째 뉴스", "url": "https://example.com/2"},
                        {"title_kr": "셋째 뉴스", "url": "https://example.com/3"},
                    ]
                },
            )
            self.write_json(
                root / "docs" / "tistory" / f"{day}.json",
                {
                    "publish_ready": True,
                    "image_assets": [
                        {"kind": "cover"},
                        {"kind": "story_1"},
                        {"kind": "story_2"},
                        {"kind": "story_3"},
                    ],
                },
            )
            html = (
                '<article class="daily-digest-post">'
                '<section id="digest-news-1" class="digest-news-card">1</section>'
                '<section id="digest-news-2" class="digest-news-card">2</section>'
                '<section id="digest-news-3" class="digest-news-card">3</section>'
                "</article>"
            )
            tistory = root / "docs" / "tistory"
            (tistory / f"{day}.html").write_text(html, encoding="utf-8")
            (tistory / f"{day}-adfit.html").write_text(
                html.replace(
                    '<section id="digest-news-2"',
                    '<figure data-ad-vendor="adfit"></figure><section id="digest-news-2"',
                ),
                encoding="utf-8",
            )
            preview = root / "docs" / "preview"
            preview.mkdir(parents=True)
            (preview / f"{day}.html").write_text(html, encoding="utf-8")

            result = inspect_daily_state(day, root=root)

        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["duplicates"], [])

    def test_existing_source_without_outputs_is_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_json(
                root / "data" / "days" / "2026-07-14.json",
                {"news": [{"title_kr": "작성 중", "url": "https://example.com/1"}]},
            )

            result = inspect_daily_state("2026-07-14", root=root)

        self.assertEqual(result["status"], "PARTIAL")
        self.assertIn("news_count", result["reasons"])
        self.assertIn("missing_publish_meta", result["reasons"])

    def test_new_daily_runs_require_the_webp_image_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_json(
                root / "data" / "days" / "2026-07-16.json",
                {
                    "generation": {"provider": "codex-agent"},
                    "news": [
                        {"title_kr": "첫 뉴스", "url": "https://example.com/1"},
                        {"title_kr": "둘째 뉴스", "url": "https://example.com/2"},
                        {"title_kr": "셋째 뉴스", "url": "https://example.com/3"},
                    ],
                },
            )

            result = inspect_daily_state("2026-07-16", root=root)

        self.assertIn("missing_image_policy", result["reasons"])

    def test_invalid_new_day_json_reports_partial_instead_of_crashing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "data" / "days" / "2026-07-16.json"
            path.parent.mkdir(parents=True)
            path.write_text("{invalid", encoding="utf-8")

            result = inspect_daily_state("2026-07-16", root=root)

        self.assertEqual(result["status"], "PARTIAL")
        self.assertIn("missing_or_invalid_source", result["reasons"])
        self.assertIn("invalid_image_manifest", result["reasons"])

    def test_complete_deep_story_accepts_one_news_and_variable_explanatory_visuals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = "2026-07-17"
            asset_dir = root / "docs" / "tistory" / "assets" / day
            asset_dir.mkdir(parents=True)
            images = {}
            for kind in ("cover", "visual_1", "visual_2"):
                path = asset_dir / f"{kind}.webp"
                Image.new("RGB", (1200, 630), "#23483c").save(path, "WEBP")
                images[kind] = {
                    "path": path.relative_to(root).as_posix(),
                    "url": f"https://blog.example/{kind}.webp",
                }
            content = [
                {"t": "h", "text": "무슨 일이 있었나"},
                {"t": "p", "text": "핵심 사실"},
                {"t": "visual", "image": "visual_1", "caption": "흐름도"},
                {"t": "h", "text": "무엇이 다른가"},
                {"t": "table", "headers": ["구분", "변경"], "rows": [["전", "후"]]},
                {"t": "ad_break"},
                {"t": "h", "text": "무슨 의미인가"},
                {"t": "p", "text": "실제 영향"},
                {"t": "visual", "image": "visual_2", "caption": "비교 도식"},
                {"t": "h", "text": "무엇을 확인할까"},
                {"t": "p", "text": "권한 범위를 확인한다."},
                {"t": "p", "text": "실행 로그를 남긴다."},
                {"t": "p", "text": "리뷰 책임자를 정한다."},
            ]
            source = {
                "schema_version": 3,
                "format": "lead-story-v1",
                "primary_query": "GitHub Copilot agent mode",
                "generation": {"provider": "codex-agent", "image_policy": "webp-v1"},
                "images": images,
                "news": [
                    {
                        "title_kr": "GitHub Copilot 에이전트 모드 변경",
                        "url": "https://github.blog/example",
                        "references": [
                            {"kind": "official", "title": "공식", "url": "https://github.blog/example"},
                            {"kind": "independent", "title": "분석", "url": "https://security.example/analysis"},
                        ],
                        "content": content,
                    }
                ],
                "related_posts": [
                    {"title": "관련 글 1", "url": "https://won0322.tistory.com/120"},
                    {"title": "관련 글 2", "url": "https://won0322.tistory.com/121"},
                ],
            }
            self.write_json(root / "data" / "days" / f"{day}.json", source)
            self.write_json(
                root / "docs" / "tistory" / f"{day}.json",
                {
                    "publish_ready": True,
                    "image_assets": [{"kind": kind} for kind in images],
                },
            )
            html = (
                '<article class="daily-digest-post" data-digest-version="3">'
                '<section id="digest-news-1" class="digest-news-card digest-lead-story">1</section>'
                '<div data-digest-ad-break="true"></div>'
                '<section class="digest-lead-continuation">2</section></article>'
            )
            tistory = root / "docs" / "tistory"
            (tistory / f"{day}.html").write_text(html, encoding="utf-8")
            (tistory / f"{day}-adfit.html").write_text(
                html.replace(
                    '<div data-digest-ad-break="true"></div>',
                    '<figure data-ad-vendor="adfit"></figure>',
                ),
                encoding="utf-8",
            )
            preview = root / "docs" / "preview"
            preview.mkdir(parents=True)
            (preview / f"{day}.html").write_text(html, encoding="utf-8")

            result = inspect_daily_state(day, root=root)

        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["reasons"], [])

    def test_deep_story_rejects_missing_research_visuals_and_internal_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = "2026-07-17"
            self.write_json(
                root / "data" / "days" / f"{day}.json",
                {
                    "format": "lead-story-v1",
                    "primary_query": "AI agent",
                    "news": [{"title_kr": "심층 글", "content": [{"t": "ad_break"}]}],
                },
            )

            result = inspect_daily_state(day, root=root)

        self.assertIn("lead_references", result["reasons"])
        self.assertIn("lead_explanatory_visuals", result["reasons"])
        self.assertIn("related_posts", result["reasons"])

    def test_deep_story_rejects_a_declared_visual_that_is_not_used_in_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = "2026-07-17"
            content = [
                {"t": "h", "text": "변화"},
                {"t": "p", "text": "사실"},
                {"t": "visual", "image": "visual_1"},
                {"t": "h", "text": "비교"},
                {"t": "p", "text": "차이"},
                {"t": "ad_break"},
                {"t": "h", "text": "영향"},
                {"t": "visual", "image": "visual_2"},
                {"t": "h", "text": "확인"},
                {"t": "p", "text": "검토"},
                {"t": "p", "text": "테스트"},
                {"t": "p", "text": "승인"},
                {"t": "p", "text": "복구"},
            ]
            self.write_json(
                root / "data" / "days" / f"{day}.json",
                {
                    "format": "lead-story-v1",
                    "primary_query": "의존성 업데이트",
                    "images": {
                        "cover": {},
                        "visual_1": {},
                        "visual_2": {},
                        "visual_3": {},
                    },
                    "news": [
                        {
                            "title_kr": "심층 글",
                            "references": [
                                {"kind": "official", "title": "공식", "url": "https://example.com/official"},
                                {"kind": "independent", "title": "분석", "url": "https://example.net/analysis"},
                            ],
                            "content": content,
                        }
                    ],
                    "related_posts": [
                        {"title": "관련 1", "url": "https://won0322.tistory.com/120"},
                        {"title": "관련 2", "url": "https://won0322.tistory.com/121"},
                    ],
                },
            )

            result = inspect_daily_state(day, root=root)

        self.assertIn("lead_explanatory_visuals", result["reasons"])

    def test_deep_story_does_not_count_non_http_research_or_related_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = "2026-07-17"
            content = [
                {"t": "h", "text": "변화"},
                {"t": "p", "text": "사실"},
                {"t": "visual", "image": "visual_1"},
                {"t": "h", "text": "비교"},
                {"t": "p", "text": "차이"},
                {"t": "ad_break"},
                {"t": "h", "text": "영향"},
                {"t": "visual", "image": "visual_2"},
                {"t": "h", "text": "확인"},
                {"t": "p", "text": "검토"},
                {"t": "p", "text": "테스트"},
                {"t": "p", "text": "승인"},
                {"t": "p", "text": "복구"},
            ]
            self.write_json(
                root / "data" / "days" / f"{day}.json",
                {
                    "format": "lead-story-v1",
                    "primary_query": "의존성 업데이트",
                    "images": {"cover": {}, "visual_1": {}, "visual_2": {}},
                    "news": [
                        {
                            "title_kr": "심층 글",
                            "references": [
                                {"kind": "official", "title": "위험", "url": "javascript:alert(1)"},
                                {"kind": "documentation", "title": "내부", "url": "/docs/local"},
                            ],
                            "content": content,
                        }
                    ],
                    "related_posts": [
                        {"title": "위험 1", "url": "data:text/html,bad"},
                        {"title": "위험 2", "url": "javascript:alert(2)"},
                    ],
                },
            )

            result = inspect_daily_state(day, root=root)

        self.assertIn("lead_references", result["reasons"])
        self.assertIn("related_posts", result["reasons"])

    def test_deep_story_rejects_related_posts_outside_the_tistory_blog(self):
        source = {
            "format": "lead-story-v1",
            "primary_query": "Cloudflare 캐시 설정",
            "images": {"cover": {}, "visual_1": {}, "visual_2": {}},
            "news": [
                {
                    "title_kr": "Cloudflare 캐시 설정법",
                    "references": [
                        {
                            "kind": "official",
                            "title": "공식 발표",
                            "url": "https://blog.cloudflare.com/example",
                        },
                        {
                            "kind": "documentation",
                            "title": "공식 문서",
                            "url": "https://developers.cloudflare.com/example",
                        },
                    ],
                    "content": [
                        {"t": "h", "text": "변화"},
                        {"t": "visual", "image": "visual_1"},
                        {"t": "h", "text": "비교"},
                        {"t": "p", "text": "차이"},
                        {"t": "ad_break"},
                        {"t": "h", "text": "설정"},
                        {"t": "visual", "image": "visual_2"},
                        {"t": "h", "text": "확인"},
                    ],
                }
            ],
            "related_posts": [
                {
                    "title": "외부 미리보기 1",
                    "url": "https://seung-won-yu.github.io/blog-writing/tistory/1.html",
                },
                {
                    "title": "외부 미리보기 2",
                    "url": "https://example.com/post",
                },
            ],
        }

        from blog_pipeline.publishing.daily_guard import _lead_source_reasons

        self.assertIn("related_posts", _lead_source_reasons(source))

    def test_deep_story_rejects_unpublished_tistory_post_ids(self):
        from blog_pipeline.publishing.daily_guard import _lead_source_reasons

        source = {
            "primary_query": "공개 글 링크 검증",
            "news": [{"references": [{"title": "공식", "url": "https://example.com", "kind": "official"}], "content": [{"t": "h"}] * 4 + [{"t": "visual", "image": "visual_1"}, {"t": "visual", "image": "visual_2"}, {"t": "ad_break"}]}],
            "images": {"visual_1": {}, "visual_2": {}},
            "related_posts": [
                {"title": "실제 공개 글", "url": "https://won0322.tistory.com/132"},
                {"title": "존재하지 않는 글", "url": "https://won0322.tistory.com/999999"},
            ],
        }

        self.assertIn("related_posts", _lead_source_reasons(source))

    def test_new_deep_story_requires_visual_logic_and_product_ui_evidence(self):
        source = {
            "format": "lead-story-v1",
            "primary_query": "Cloudflare 리전 힌트 설정 방법",
            "visual": {
                "assets": [
                    {
                        "label": "설정 흐름",
                        "scene_label": ["원본", "리전"],
                        "steps": "원본 확인 → 리전 설정",
                        "curiosity_hook": "어디서 설정할까?",
                        "evidence_type": "diagram",
                        "logic_type": "conditional",
                    },
                    {
                        "label": "설정 결과",
                        "scene_label": ["캐시", "로그"],
                        "steps": "설정 → 확인",
                        "curiosity_hook": "작동했는지 어떻게 알까?",
                        "evidence_type": "diagram",
                        "logic_type": "flow",
                    },
                ]
            },
            "images": {"cover": {}, "visual_1": {}, "visual_2": {}},
            "news": [
                {
                    "title_kr": "Cloudflare 리전 힌트 설정법",
                    "references": [
                        {
                            "kind": "official",
                            "title": "공식 발표",
                            "url": "https://blog.cloudflare.com/example",
                        },
                        {
                            "kind": "documentation",
                            "title": "공식 문서",
                            "url": "https://developers.cloudflare.com/example",
                        },
                    ],
                    "content": [
                        {"t": "h", "text": "변화"},
                        {"t": "visual", "image": "visual_1"},
                        {"t": "h", "text": "비교"},
                        {"t": "p", "text": "차이"},
                        {"t": "ad_break"},
                        {"t": "h", "text": "설정"},
                        {"t": "visual", "image": "visual_2"},
                        {"t": "h", "text": "확인"},
                    ],
                }
            ],
            "related_posts": [
                {"title": "관련 1", "url": "https://won0322.tistory.com/120"},
                {"title": "관련 2", "url": "https://won0322.tistory.com/121"},
            ],
        }

        from blog_pipeline.publishing.daily_guard import _lead_source_reasons

        reasons = _lead_source_reasons(source, require_visual_evidence=True)

        self.assertIn("lead_visual_briefs", reasons)
        self.assertIn("lead_product_ui_evidence", reasons)

    def test_new_deep_story_accepts_conditional_brief_and_real_ui_screenshot(self):
        source = {
            "format": "lead-story-v1",
            "primary_query": "Cloudflare 리전 힌트 설정 방법",
            "visual": {
                "assets": [
                    {
                        "label": "조건부 흐름",
                        "scene_label": ["원본", "리전"],
                        "steps": "설정 / DNS 변경 시 재확인",
                        "curiosity_hook": "언제 다시 확인할까?",
                        "evidence_type": "diagram",
                        "logic_type": "conditional",
                        "condition": "DNS 또는 IP를 변경한 경우",
                    },
                    {
                        "label": "실제 설정 화면",
                        "scene_label": ["Provider", "Region"],
                        "steps": "원본 선택 → 리전 선택",
                        "curiosity_hook": "어디서 설정할까?",
                        "evidence_type": "screenshot",
                        "logic_type": "evidence",
                        "source_url": "https://blog.cloudflare.com/example",
                    },
                ]
            },
            "images": {"cover": {}, "visual_1": {}, "visual_2": {}},
            "news": [
                {
                    "title_kr": "Cloudflare 리전 힌트 설정법",
                    "references": [
                        {
                            "kind": "official",
                            "title": "공식 발표",
                            "url": "https://blog.cloudflare.com/example",
                        },
                        {
                            "kind": "documentation",
                            "title": "공식 문서",
                            "url": "https://developers.cloudflare.com/example",
                        },
                    ],
                    "content": [
                        {"t": "h", "text": "변화"},
                        {"t": "visual", "image": "visual_1"},
                        {"t": "h", "text": "비교"},
                        {"t": "p", "text": "차이"},
                        {"t": "ad_break"},
                        {"t": "h", "text": "설정"},
                        {"t": "visual", "image": "visual_2"},
                        {"t": "h", "text": "확인"},
                    ],
                }
            ],
            "related_posts": [
                {"title": "관련 1", "url": "https://won0322.tistory.com/120"},
                {"title": "관련 2", "url": "https://won0322.tistory.com/121"},
            ],
        }

        from blog_pipeline.publishing.daily_guard import _lead_source_reasons

        reasons = _lead_source_reasons(source, require_visual_evidence=True)

        self.assertNotIn("lead_visual_briefs", reasons)
        self.assertNotIn("lead_product_ui_evidence", reasons)

    def test_deep_story_caps_explanatory_visuals_at_six(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = "2026-07-17"
            content = [
                {"t": "h", "text": "변화"},
                {"t": "p", "text": "사실"},
                {"t": "visual", "image": "visual_1"},
                {"t": "visual", "image": "visual_2"},
                {"t": "h", "text": "비교"},
                {"t": "p", "text": "차이"},
                {"t": "visual", "image": "visual_3"},
                {"t": "ad_break"},
                {"t": "h", "text": "영향"},
                {"t": "visual", "image": "visual_4"},
                {"t": "visual", "image": "visual_5"},
                {"t": "p", "text": "검토"},
                {"t": "h", "text": "확인"},
                {"t": "visual", "image": "visual_6"},
                {"t": "visual", "image": "visual_7"},
                {"t": "p", "text": "테스트"},
                {"t": "p", "text": "승인"},
                {"t": "p", "text": "복구"},
            ]
            self.write_json(
                root / "data" / "days" / f"{day}.json",
                {
                    "format": "lead-story-v1",
                    "primary_query": "의존성 업데이트",
                    "images": {
                        "cover": {},
                        **{f"visual_{index}": {} for index in range(1, 8)},
                    },
                    "news": [
                        {
                            "title_kr": "심층 글",
                            "references": [
                                {"kind": "official", "title": "공식", "url": "https://example.com/official"},
                                {"kind": "independent", "title": "분석", "url": "https://example.net/analysis"},
                            ],
                            "content": content,
                        }
                    ],
                    "related_posts": [
                        {"title": "관련 1", "url": "https://won0322.tistory.com/120"},
                        {"title": "관련 2", "url": "https://won0322.tistory.com/121"},
                    ],
                },
            )

            result = inspect_daily_state(day, root=root)

        self.assertIn("lead_explanatory_visuals", result["reasons"])

    def test_blocks_same_canonical_url_from_recent_days(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_json(
                root / "data" / "days" / "2026-07-13.json",
                {
                    "news": [
                        {
                            "title_kr": "인스타 사진 AI 연동 중단",
                            "url": "https://example.com/story?utm_source=rss&id=7",
                        }
                    ]
                },
            )
            current = {
                "news": [
                    {
                        "title_kr": "메타, 인스타 사진 AI 자동 연동 철회",
                        "url": "https://example.com/story?id=7&utm_medium=feed",
                    }
                ]
            }

            duplicates = find_recent_duplicates(
                "2026-07-14", current, root=root, window_days=14
            )

        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["reason"], "same_url")
        self.assertEqual(duplicates[0]["previous_day"], "2026-07-13")

    def test_blocks_a_nearly_identical_title_on_a_different_url(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_json(
                root / "data" / "days" / "2026-07-10.json",
                {
                    "news": [
                        {
                            "title_kr": "GitHub CodeQL, AI 시스템 프롬프트 인젝션 탐지 추가",
                            "url": "https://example.com/old",
                        }
                    ]
                },
            )
            current = {
                "news": [
                    {
                        "title_kr": "GitHub CodeQL AI 시스템 프롬프트 인젝션 탐지 추가",
                        "url": "https://example.com/new",
                    }
                ]
            }

            duplicates = find_recent_duplicates(
                "2026-07-14", current, root=root, window_days=14
            )

        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["reason"], "similar_title")

    def test_blocks_paraphrased_same_topic_key_and_recent_entity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_json(
                root / "data" / "days" / "2026-07-18.json",
                {
                    "editorial": {
                        "topic_key": "cloud-cache-routing",
                        "entities": ["Cloudflare"],
                    },
                    "news": [
                        {
                            "title_kr": "대륙별 캐시 경로가 달라진 배경",
                            "url": "https://example.com/old",
                        }
                    ],
                },
            )
            same_topic = {
                "editorial": {
                    "topic_key": "cloud-cache-routing",
                    "entities": ["Other Brand"],
                },
                "news": [
                    {
                        "title_kr": "원본 요청 경로 선택 기준을 다시 살펴보기",
                        "url": "https://example.net/new",
                    }
                ],
            }
            same_entity = {
                "editorial": {
                    "topic_key": "wordpress-patch",
                    "entities": ["Cloudflare", "WordPress"],
                },
                "news": [
                    {
                        "title_kr": "워드프레스 패치와 앞단 방어의 차이",
                        "url": "https://example.org/patch",
                    }
                ],
            }

            topic_duplicates = find_recent_duplicates(
                "2026-07-19", same_topic, root=root, window_days=60
            )
            entity_duplicates = find_recent_duplicates(
                "2026-07-19", same_entity, root=root, window_days=60
            )

        self.assertEqual(topic_duplicates[0]["reason"], "same_topic_key")
        self.assertEqual(entity_duplicates[0]["reason"], "recent_entity")

    def test_saturday_rotation_only_uses_previous_publish_ready_cases(self):
        from blog_pipeline.publishing.daily_guard import find_recent_draft_duplicates

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous_day = "2026-07-25"
            previous_id = f"{previous_day}-automation"
            self.write_json(
                root / "data" / "automation_cases" / f"{previous_day}.json",
                {
                    "draft_id": previous_id,
                    "publish_date": previous_day,
                    "content_type": "automation_case",
                    "verification": {
                        "problem_lane": "이메일·문서",
                        "tool_brand": "Python",
                    },
                    "news": [
                        {
                            "title_kr": "메일 첨부파일 정리",
                            "url": "https://example.com/previous",
                        }
                    ],
                },
            )
            current = {
                "verification": {
                    "problem_lane": "이메일·문서",
                    "tool_brand": "Other Tool",
                },
                "news": [
                    {
                        "title_kr": "반복 수신함 규칙 만들기",
                        "url": "https://example.net/current",
                    }
                ],
            }

            incomplete = find_recent_draft_duplicates(
                "2026-08-01-automation", current, root=root, window_days=90
            )
            self.write_json(
                root / "docs" / "tistory" / f"{previous_id}.json",
                {
                    "draft_id": previous_id,
                    "publish_date": previous_day,
                    "content_type": "automation_case",
                    "source": f"data/automation_cases/{previous_day}.json",
                    "publish_ready": True,
                },
            )
            complete = find_recent_draft_duplicates(
                "2026-08-01-automation", current, root=root, window_days=90
            )

        self.assertEqual(incomplete, [])
        self.assertEqual(complete[0]["reason"], "recent_problem_lane")


if __name__ == "__main__":
    unittest.main()
