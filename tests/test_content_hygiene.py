import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class ContentHygieneTests(unittest.TestCase):
    def test_saved_articles_do_not_keep_legacy_personal_note_fields(self):
        for path in sorted((ROOT / "data" / "days").glob("*.json")):
            day = json.loads(path.read_text(encoding="utf-8"))
            for article in day.get("news", []):
                self.assertNotIn("author_note", article, path.name)

    def test_copy_ready_html_has_no_automation_disclosure_or_named_notes(self):
        banned = (
            "승원의 메모",
            "개발자 편집자의 체크포인트",
            "초안 생성에 자동화를 사용했습니다",
        )
        for path in sorted((ROOT / "docs" / "tistory").glob("*.html")):
            html = path.read_text(encoding="utf-8")
            for phrase in banned:
                self.assertNotIn(phrase, html, path.name)


if __name__ == "__main__":
    unittest.main()
