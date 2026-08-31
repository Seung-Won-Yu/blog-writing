import json
import unittest
from datetime import datetime
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

    def test_published_project_archives_use_the_actual_publication_identity(self):
        archive_dir = ROOT / "data" / "project_logs" / "published"
        for path in sorted(archive_dir.glob("*.json")):
            archived = json.loads(path.read_text(encoding="utf-8"))
            published_day = path.stem
            actual_published_at = datetime.fromisoformat(
                archived["actual_published_at"]
            )

            self.assertEqual(archived.get("archive_status"), "published", path.name)
            self.assertEqual(archived.get("publication_mode"), "published", path.name)
            self.assertEqual(archived.get("publish_date"), published_day, path.name)
            self.assertEqual(
                archived.get("draft_id"), f"{published_day}-project", path.name
            )
            self.assertEqual(actual_published_at.date().isoformat(), published_day)
            self.assertEqual(
                archived.get("scheduled_at"), archived.get("actual_published_at")
            )

    def test_project_html_has_an_active_source_or_a_published_revision_source(self):
        active_ids = {
            f"{path.stem}-project"
            for path in (ROOT / "data" / "project_logs").glob("*.json")
        }
        revision_ids = set()
        for meta_path in (ROOT / "docs" / "tistory").glob(
            "*-project-revision.json"
        ):
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            source = ROOT / str(meta.get("source") or "")
            if (
                meta.get("artifact_type") == "published_revision"
                and meta.get("draft_id") == meta_path.stem
                and source.parent
                == ROOT / "data" / "project_logs" / "published"
                and source.is_file()
            ):
                revision_ids.add(meta_path.stem)
        allowed_ids = active_ids | revision_ids
        allowed_tistory_names = {
            name
            for draft_id in allowed_ids
            for name in (
                f"{draft_id}.html",
                f"{draft_id}-adfit.html",
                f"{draft_id}-after-ad.html",
                f"{draft_id}-before-ad.html",
            )
        }
        for path in (ROOT / "docs" / "tistory").glob("*-project*.html"):
            self.assertIn(path.name, allowed_tistory_names, path.name)
        for path in (ROOT / "docs" / "preview").glob("*-project*.html"):
            self.assertIn(path.stem, allowed_ids, path.name)


if __name__ == "__main__":
    unittest.main()
