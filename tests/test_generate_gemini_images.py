import base64
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from generate_gemini_images import (
    DEFAULT_GEMINI_IMAGE_MODEL,
    build_image_jobs,
    generate_gemini_images,
    request_gemini_image,
)


DAY = {
    "date_label": "2026. 7. 13.",
    "visual": {
        "subject": "사진 접근 권한",
        "hook": "내 사진은 어디까지 넘어갈까?",
        "motif": "security",
    },
    "editorial": {
        "headline": "사진 AI 자동 연동이 멈춘 이유",
        "opening": "휴대폰 사진 한 장이 편집 도구로 넘어가는 순간을 다룬다.",
    },
    "news": [
        {
            "title_kr": "메타, 인스타그램 사진 AI 자동 연동 철회",
            "source": "AI타임스",
            "blurb_kr": "사진 접근 동의와 사용자 통제가 쟁점이 됐다.",
            "content": [{"t": "p", "text": "사용자가 사진 권한을 어디까지 허용했는지가 핵심이다."}],
        },
        {
            "title_kr": "개발 도구가 실행 기록을 보여주는 방식",
            "source": "GitHub",
            "blurb_kr": "자동화 결과를 로그에서 추적할 수 있게 바뀌었다.",
            "content": [{"t": "p", "text": "실행 로그와 권한 범위를 함께 확인한다."}],
        },
        {
            "title_kr": "데이터센터 전력 사용량을 줄이는 새 구조",
            "source": "공식 블로그",
            "blurb_kr": "서버 처리량과 전력 소비의 균형을 다룬다.",
            "content": [{"t": "p", "text": "서버 랙과 전력 계측값을 비교한다."}],
        },
        {
            "title_kr": "네 번째 소식은 이미지 생성 대상이 아니다",
            "source": "공식 블로그",
            "blurb_kr": "본문에는 남지만 이미지 세트는 최대 네 장이다.",
        },
    ],
    "images": {
        "cover": {
            "url": "https://blog.example/assets/2026-07-13/cover.png",
            "path": "docs/tistory/assets/2026-07-13/cover.png",
            "alt": "사진 접근 권한 대표 이미지",
            "width": 1200,
            "height": 630,
        },
        **{
            f"story_{index}": {
                "url": f"https://blog.example/assets/2026-07-13/story-{index:02d}.png",
                "path": f"docs/tistory/assets/2026-07-13/story-{index:02d}.png",
                "alt": f"기사 {index} 이해 이미지",
                "width": 1200,
                "height": 630,
            }
            for index in range(1, 4)
        },
    },
}


def png_bytes(color="#335577"):
    buffer = io.BytesIO()
    Image.new("RGB", (1024, 576), color).save(buffer, "PNG")
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class GeminiImageClientTests(unittest.TestCase):
    def test_sends_key_only_in_header_and_requests_one_16_by_9_image(self):
        captured = {}
        encoded = base64.b64encode(png_bytes()).decode("ascii")

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse({"output_image": {"type": "image", "data": encoded}})

        result = request_gemini_image(
            "A specific editorial scene",
            "gemini-secret",
            opener=opener,
        )

        self.assertEqual(result, png_bytes())
        self.assertEqual(captured["headers"]["X-goog-api-key"], "gemini-secret")
        self.assertNotIn("gemini-secret", captured["url"])
        self.assertNotIn("gemini-secret", json.dumps(captured["body"]))
        self.assertEqual(captured["body"]["model"], DEFAULT_GEMINI_IMAGE_MODEL)
        self.assertEqual(captured["body"]["response_format"]["aspect_ratio"], "16:9")
        self.assertEqual(captured["body"]["response_format"]["image_size"], "1K")

    def test_builds_article_specific_non_ppt_prompts_and_caps_at_four_images(self):
        jobs = build_image_jobs(DAY)

        self.assertEqual([job["key"] for job in jobs], ["cover", "story_1", "story_2", "story_3"])
        self.assertIn("내 사진은 어디까지 넘어갈까", jobs[0]["prompt"])
        self.assertIn("인스타그램 사진 AI 자동 연동", jobs[1]["prompt"])
        self.assertIn("실행 기록", jobs[2]["prompt"])
        self.assertIn("데이터센터 전력", jobs[3]["prompt"])
        for job in jobs:
            self.assertIn("No text", job["prompt"])
            self.assertIn("not a presentation slide", job["prompt"])
            self.assertIn("untrusted reference data", job["prompt"])

    def test_overwrites_free_fallback_only_after_all_paid_images_succeed(self):
        calls = []

        def image_request(prompt, token, model):
            calls.append((prompt, token, model))
            return png_bytes("#557733")

        with tempfile.TemporaryDirectory() as directory:
            day = json.loads(json.dumps(DAY))
            assets = generate_gemini_images(
                "2026-07-13",
                day,
                token="secret",
                output_dir=directory,
                image_request=image_request,
            )

            self.assertEqual(len(calls), 4)
            self.assertEqual(set(assets), {"cover", "story_1", "story_2", "story_3"})
            self.assertEqual(assets["cover"]["provider"], "gemini")
            self.assertEqual(assets["cover"]["model"], DEFAULT_GEMINI_IMAGE_MODEL)
            self.assertEqual(assets["story_1"]["style"], "ai-editorial-scene")
            with Image.open(Path(directory, "2026-07-13", "cover.png")) as image:
                self.assertEqual(image.size, (1200, 630))

    def test_keeps_existing_fallback_files_when_a_paid_request_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory, "2026-07-13")
            target.mkdir()
            original = png_bytes("#112233")
            for filename in ("cover.png", "story-01.png", "story-02.png", "story-03.png"):
                Path(target, filename).write_bytes(original)
            calls = 0

            def image_request(prompt, token, model):
                nonlocal calls
                calls += 1
                if calls == 3:
                    raise RuntimeError("provider unavailable")
                return png_bytes("#ffffff")

            with self.assertRaisesRegex(RuntimeError, "provider unavailable"):
                generate_gemini_images(
                    "2026-07-13",
                    json.loads(json.dumps(DAY)),
                    token="secret",
                    output_dir=directory,
                    image_request=image_request,
                )

            for filename in ("cover.png", "story-01.png", "story-02.png", "story-03.png"):
                self.assertEqual(Path(target, filename).read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
