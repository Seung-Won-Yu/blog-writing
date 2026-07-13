import unittest

from visual_direction import motif_for_text


class MotifClassificationTests(unittest.TestCase):
    def test_short_latin_keywords_match_only_at_token_boundaries(self):
        self.assertEqual(motif_for_text("Cloud storage costs fall"), "cloud")
        self.assertEqual(motif_for_text("Average latency improves"), "signal")
        self.assertEqual(motif_for_text("ClickHouse query engine"), "data")
        self.assertEqual(motif_for_text("RAG-based memory retrieval"), "memory")
        self.assertEqual(motif_for_text("New CLI tool"), "code")

    def test_korean_keywords_still_match_inside_compound_words(self):
        self.assertEqual(motif_for_text("통신망 운영 자동화"), "network")
        self.assertEqual(motif_for_text("보안성을 높이는 권한 검토"), "security")

    def test_ai_vendor_names_select_an_agent_scene(self):
        self.assertEqual(motif_for_text("앤트로픽의 활용 가이드"), "agent")
        self.assertEqual(motif_for_text("Anthropic workflow patterns"), "agent")


if __name__ == "__main__":
    unittest.main()
