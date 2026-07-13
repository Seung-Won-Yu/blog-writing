import unittest

from visual_direction import (
    VISUAL_MOTIFS,
    fallback_visual,
    motif_for_text,
    scene_for_text,
    scene_steps,
)


class MotifClassificationTests(unittest.TestCase):
    def test_fallback_visual_uses_the_article_subject_instead_of_a_generic_label(self):
        visual = fallback_visual("인스타 사진 AI 자동 연동이 개인정보 반발로 중단")

        self.assertEqual(visual["subject"], "사진과 AI 연동")
        self.assertIn("사진", visual["hook"])

    def test_does_not_mistake_general_privacy_or_auth_tokens_for_article_scenes(self):
        self.assertEqual(scene_for_text("개인정보 처리방침과 권한 변경"), "security")
        self.assertEqual(scene_for_text("API access token security update"), "security")

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

    def test_every_supported_motif_has_meaningful_three_stage_copy(self):
        for motif in sorted(VISUAL_MOTIFS):
            with self.subTest(motif=motif):
                steps = [part.strip() for part in scene_steps(motif, motif).split("→")]

                self.assertEqual(scene_steps(motif), scene_steps(motif, motif))
                self.assertEqual(len(steps), 3)
                self.assertTrue(all(steps))
                self.assertEqual(len(set(steps)), 3)
                self.assertFalse(any("입력" in part for part in steps))
                self.assertFalse(any("확인" in part for part in steps))


if __name__ == "__main__":
    unittest.main()
