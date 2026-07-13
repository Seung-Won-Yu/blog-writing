import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from generate_editorial_images import find_font, generate_editorial_images


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
    def test_generates_deterministic_cover_and_flow_pngs(self):
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
            flow = Path(directory, "2026-07-13", "flow.png")
            with Image.open(cover) as image:
                self.assertEqual(image.size, (1200, 630))
                self.assertEqual(image.format, "PNG")
            with Image.open(flow) as image:
                self.assertEqual(image.size, (1200, 675))
                self.assertEqual(image.format, "PNG")

            self.assertEqual(set(assets), {"cover", "flow"})
            self.assertEqual(
                assets["cover"]["url"],
                "https://blog.example/tistory/assets/2026-07-13/cover.png",
            )
            self.assertEqual(first_day["images"], assets)

            first_hash = hashlib.sha256(cover.read_bytes()).hexdigest()
            second_day = {**DAY, "news": [dict(item) for item in DAY["news"]]}
            generate_editorial_images(
                "2026-07-13",
                second_day,
                directory,
                "https://blog.example/tistory/assets/",
                font_path=font_path,
            )
            self.assertEqual(hashlib.sha256(cover.read_bytes()).hexdigest(), first_hash)


if __name__ == "__main__":
    unittest.main()
