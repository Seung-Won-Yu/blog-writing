import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageChops, ImageDraw

from blog_pipeline.publishing.generate_editorial_images import (
    _arrow,
    draw_scene,
    find_font,
    generate_editorial_images,
    generate_for_day,
    resolve_visual,
)
from blog_pipeline.publishing.visual_direction import VISUAL_MOTIFS


DAY = {
    "date_label": "2026. 7. 13",
    "weekday": "월",
    "editorial": {
        "opening": "AI가 코드를 쓰는 속도보다 결과를 검증하는 힘이 중요해지고 있다.",
        "closing": "도구의 이름보다 내 작업에서 달라지는 지점을 살펴보자.",
        "action": "기사 하나를 골라 내 작업에 적용할 지점을 한 줄로 적어보자.",
    },
    "news": [
        {
            "title_kr": "GitHub Actions에 실행 전 보안 검토 기능 추가",
            "source": "GitHub Changelog",
            "url": "https://example.com/1",
            "blurb_kr": "자동화 변경을 실행 전에 살펴볼 수 있다.",
            "content": [],
        },
        {
            "title_kr": "AI 시대 개발자에게 필요한 검증 습관",
            "source": "요즘IT",
            "url": "https://example.com/2",
            "blurb_kr": "결과를 판단하는 역량이 중요해지고 있다.",
            "content": [],
        },
        {
            "title_kr": "작은 자동화를 오래 운영하는 방법",
            "source": "GeekNews",
            "url": "https://example.com/3",
            "blurb_kr": "실패했을 때 돌아갈 경로를 먼저 만든다.",
            "content": [],
        },
    ],
}


class EditorialImageTests(unittest.TestCase):
    def test_scene_connectors_do_not_draw_presentation_arrowheads(self):
        image = Image.new("RGB", (120, 100), "#000000")
        draw = ImageDraw.Draw(image)

        _arrow(draw, (20, 50), (90, 50), "#FFFFFF", width=8)

        self.assertEqual(image.getpixel((76, 44)), (0, 0, 0))
        self.assertNotEqual(image.getpixel((90, 50)), (0, 0, 0))

    def test_every_generic_motif_draws_a_three_stage_scene_across_the_frame(self):
        for motif in sorted(VISUAL_MOTIFS):
            with self.subTest(motif=motif):
                image = Image.new("RGB", (900, 300), "#000000")
                draw_scene(
                    ImageDraw.Draw(image),
                    motif,
                    motif,
                    (0, 0, 900, 300),
                    foreground="#FFFFFF",
                    accent="#FF7A68",
                    muted="#55D29A",
                )

                for left, right in ((0, 270), (315, 585), (630, 900)):
                    region = image.crop((left, 0, right, 300))
                    background = Image.new("RGB", region.size, "#000000")
                    self.assertIsNotNone(ImageChops.difference(region, background).getbbox())

    def test_maps_article_subjects_to_explanatory_visual_scenes(self):
        day = {
            "news": [
                {
                    "title_kr": "인스타 사진 AI 자동 연동 중단",
                    "blurb_kr": "개인정보 반발 뒤 기능을 멈췄다.",
                },
                {
                    "title_kr": "VS Code와 CLI의 OpenTelemetry export",
                    "blurb_kr": "기업 관측 데이터 관리 기능이다.",
                },
                {
                    "title_kr": "AI 토큰은 데이터센터를 어떻게 여행하는가",
                    "blurb_kr": "요청이 네트워크와 GPU를 지나는 흐름을 설명한다.",
                },
            ]
        }

        visual = resolve_visual(day)

        self.assertEqual(
            [item["scene"] for item in visual["stories"]],
            ["privacy_photo", "observability", "datacenter"],
        )
        self.assertEqual(
            [item["steps"] for item in visual["stories"]],
            [
                "사진 → AI 연동 → 사용자 통제",
                "개발 도구 → 관측 데이터 → 관리",
                "요청 토큰 → 데이터센터 → 응답",
            ],
        )

    def test_maps_model_choice_and_benchmark_limits_to_distinct_scenes(self):
        day = {
            "news": [
                {
                    "title_kr": "메타, 인스타그램 AI 이미지 학습 논란에 3일 만에 철회",
                    "blurb_kr": "사진 데이터 연동과 사용자 통제 문제다.",
                },
                {
                    "title_kr": "GitHub Copilot, 목적별 최적화된 GPT-5.6 모델 3종 도입",
                    "blurb_kr": "속도와 비용에 따라 Sol, Terra, Luna를 선택한다.",
                },
                {
                    "title_kr": "OpenAI가 지적한 SWE-Bench Pro의 코딩 평가 한계",
                    "blurb_kr": "벤치마크 점수와 실제 저장소 작업 사이의 간극을 짚었다.",
                },
            ]
        }

        visual = resolve_visual(day)

        self.assertEqual(
            [item["scene"] for item in visual["stories"]],
            ["privacy_photo", "model_choice", "benchmark_gap"],
        )
        self.assertEqual(
            [item["scene_label"] for item in visual["stories"]],
            ["사진 데이터의 흐름", "세 모델의 선택 기준", "벤치마크와 실제 차이"],
        )

    def test_preserves_article_specific_story_briefs_for_fallback_images(self):
        day = {
            **DAY,
            "visual": {
                "subject": "구체적 기사 장면",
                "hook": "무엇이 실제로 달라졌나?",
                "motif": "security",
                "stories": [
                    {
                        "label": "권한 검토",
                        "scene_label": "휴대폰 사진 한 장과 권한 토글",
                        "steps": "사진 선택 → AI 전송 → 자동 연동 중단",
                    },
                    {
                        "label": "로그 추적",
                        "scene_label": "실행 로그와 권한 범위를 나란히 비교",
                        "steps": "자동 실행 → 로그 기록 → 사람이 추적",
                    },
                ],
            },
        }

        visual = resolve_visual(day)

        self.assertEqual(visual["stories"][0]["label"], "권한 검토")
        self.assertEqual(
            visual["stories"][0]["scene_label"],
            "휴대폰 사진 한 장과 권한 토글",
        )
        self.assertEqual(
            visual["stories"][0]["steps"],
            "사진 선택 → AI 전송 → 자동 연동 중단",
        )
        self.assertEqual(
            visual["stories"][1]["scene_label"],
            "실행 로그와 권한 범위를 나란히 비교",
        )
        self.assertEqual(
            visual["stories"][2]["steps"],
            "변화 감지 → 의미 해석 → 다음 행동",
        )

    def test_keeps_a_short_subject_separate_from_the_curiosity_hook(self):
        day = {
            **DAY,
            "visual": {
                "subject": "인스타 사진 AI",
                "hook": "반발 뒤 자동 연동은 왜 멈췄나?",
                "motif": "security",
            },
        }

        visual = resolve_visual(day)

        self.assertEqual(visual["subject"], "인스타 사진 AI")
        self.assertEqual(visual["hook"], "반발 뒤 자동 연동은 왜 멈췄나?")

    def test_legacy_day_resolves_short_hook_and_story_motifs_without_opening_copy(self):
        visual = resolve_visual(DAY)

        self.assertEqual(visual["motif"], "security")
        self.assertEqual(visual["hook"], "자동화, 어디까지 믿어도 될까?")
        self.assertNotEqual(visual["hook"], DAY["editorial"]["opening"])
        self.assertEqual(len(visual["stories"]), 3)
        self.assertEqual(visual["stories"][0]["label"], "자동화 보안")
        self.assertTrue(all(len(item["label"]) <= 12 for item in visual["stories"]))

    def test_story_motifs_prefer_each_title_before_supporting_summary(self):
        day = {
            "news": [
                {"title_kr": "AI로 통신 산업 재편", "blurb_kr": "네트워크 운영 변화"},
                {"title_kr": "AI 코딩 에이전트의 세션 관리", "blurb_kr": "세션 검색 도구"},
                {"title_kr": "장기 과제를 위한 메모리 에이전트", "blurb_kr": "기억과 검색"},
            ]
        }

        visual = resolve_visual(day)

        self.assertEqual(
            [item["motif"] for item in visual["stories"]],
            ["network", "agent", "memory"],
        )

    def test_every_supported_motif_renders_a_distinct_cover(self):
        font_path = find_font()
        hashes = set()
        with tempfile.TemporaryDirectory() as directory:
            for motif in sorted(VISUAL_MOTIFS):
                day = {
                    **DAY,
                    "visual": {"hook": "기술의 다음 장면은 어디일까?", "motif": motif},
                    "news": [dict(item) for item in DAY["news"]],
                }
                generate_editorial_images(
                    "2026-07-13",
                    day,
                    directory,
                    "https://blog.example/tistory/assets/",
                    font_path=font_path,
                )
                cover = Path(directory, "2026-07-13", "cover.png")
                hashes.add(hashlib.sha256(cover.read_bytes()).hexdigest())

        self.assertEqual(len(hashes), len(VISUAL_MOTIFS))

    def test_generates_deterministic_cover_and_one_story_image_per_news(self):
        font_path = find_font()
        self.assertTrue(Path(font_path).exists())

        with tempfile.TemporaryDirectory() as directory:
            first_day = {**DAY, "news": [dict(item) for item in DAY["news"]]}
            assets = generate_editorial_images(
                "2026-07-13",
                first_day,
                directory,
                "https://blog.example/tistory/assets/",
                font_path=font_path,
            )

            cover = Path(directory, "2026-07-13", "cover.png")
            stories = [
                Path(directory, "2026-07-13", f"story-{index:02d}.png")
                for index in range(1, 4)
            ]
            with Image.open(cover) as image:
                self.assertEqual(image.size, (1200, 630))
                self.assertEqual(image.format, "PNG")
            for story in stories:
                with Image.open(story) as image:
                    self.assertEqual(image.size, (1200, 630))
                    self.assertEqual(image.format, "PNG")

            self.assertEqual(
                set(assets), {"cover", "story_1", "story_2", "story_3"}
            )
            self.assertEqual(
                assets["cover"]["url"],
                "https://blog.example/tistory/assets/2026-07-13/cover.png",
            )
            self.assertIn("코드 변경의 흐름", assets["cover"]["alt"])
            self.assertIn("자동화, 어디까지 믿어도 될까?", assets["cover"]["alt"])
            self.assertIn("자동화 보안", assets["story_1"]["alt"])
            self.assertEqual(
                assets["story_1"]["style"], "text-free-editorial-scene"
            )
            self.assertEqual(
                assets["story_2"]["url"],
                "https://blog.example/tistory/assets/2026-07-13/story-02.png",
            )
            self.assertEqual(first_day["images"], assets)

            first_hash = hashlib.sha256(cover.read_bytes()).hexdigest()
            story_hashes = {hashlib.sha256(path.read_bytes()).hexdigest() for path in stories}
            self.assertEqual(len(story_hashes), 3)
            second_day = {**DAY, "news": [dict(item) for item in DAY["news"]]}
            generate_editorial_images(
                "2026-07-13",
                second_day,
                directory,
                "https://blog.example/tistory/assets/",
                font_path=font_path,
            )
            self.assertEqual(hashlib.sha256(cover.read_bytes()).hexdigest(), first_hash)

    def test_generates_story_images_only_for_actual_news_and_caps_them_at_three(self):
        font_path = find_font()
        four_story_day = {
            **DAY,
            "news": [
                *[dict(item) for item in DAY["news"]],
                {
                    "title_kr": "네 번째 소식은 이미지 대상이 아니다",
                    "source": "공식 블로그",
                    "blurb_kr": "본문에는 남지만 대표 이미지 세트에서는 제외한다.",
                },
            ],
        }

        with tempfile.TemporaryDirectory() as directory:
            assets = generate_editorial_images(
                "2026-07-13",
                four_story_day,
                directory,
                "https://blog.example/assets/",
                font_path=font_path,
            )

            self.assertEqual(
                [key for key in assets if key.startswith("story_")],
                ["story_1", "story_2", "story_3"],
            )
            self.assertFalse(Path(directory, "2026-07-13", "story-04.png").exists())

    def test_deep_story_fallback_generates_one_image_per_visual_brief(self):
        font_path = find_font()
        day = {
            **DAY,
            "format": "lead-story-v1",
            "news": [dict(DAY["news"][0])],
            "visual": {
                "subject": "자동화 보안",
                "hook": "실행 전후에 무엇을 확인할까?",
                "assets": [
                    {"label": "실행 흐름", "steps": "요청 → 실행 → 검증"},
                    {"label": "권한 비교", "steps": "읽기 → 수정 → 승인"},
                    {"label": "위험 대응", "steps": "감지 → 차단 → 복구"},
                ],
            },
        }

        with tempfile.TemporaryDirectory() as directory:
            assets = generate_editorial_images(
                "2026-07-17",
                day,
                directory,
                "https://blog.example/assets/",
                font_path=font_path,
            )

            self.assertEqual(
                list(assets), ["cover", "visual_1", "visual_2", "visual_3"]
            )
            for index in range(1, 4):
                self.assertTrue(
                    Path(directory, "2026-07-17", f"visual-{index:02d}.png").is_file()
                )
                self.assertIn(
                    day["visual"]["assets"][index - 1]["label"],
                    assets[f"visual_{index}"]["alt"],
                )

    def test_deep_story_visual_briefs_are_capped_at_six(self):
        day = {
            **DAY,
            "format": "lead-story-v1",
            "news": [dict(DAY["news"][0])],
            "visual": {
                "assets": [
                    {"label": f"설명 {index}", "steps": "입력 → 검증"}
                    for index in range(1, 9)
                ]
            },
        }

        visual = resolve_visual(day)

        self.assertEqual(len(visual["stories"]), 6)
        self.assertEqual(visual["stories"][-1]["label"], "설명 6")

    def test_stored_day_generation_updates_json_and_refreshes_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            days_dir = root / "days"
            output_dir = root / "assets"
            days_dir.mkdir()
            day_path = days_dir / "2026-07-13.json"
            day_path.write_text(json.dumps(DAY, ensure_ascii=False), encoding="utf-8")

            with patch(
                "blog_pipeline.publishing.export_tistory.write_post"
            ) as write_post:
                assets = generate_for_day(
                    "2026-07-13",
                    days_dir=days_dir,
                    output_dir=output_dir,
                    public_base_url="https://blog.example/assets/",
                )

            stored = json.loads(day_path.read_text(encoding="utf-8"))
            self.assertEqual(stored["images"], assets)
            self.assertTrue((output_dir / "2026-07-13" / "cover.png").exists())
            write_post.assert_called_once()
            self.assertEqual(write_post.call_args.args[0], "2026-07-13")
            self.assertEqual(write_post.call_args.kwargs["day"]["images"], assets)


if __name__ == "__main__":
    unittest.main()
