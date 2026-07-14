import unittest

from blog_pipeline.publishing.quiz_bank import QUIZ_BANK, select_quiz


class QuizBankTests(unittest.TestCase):
    def test_every_question_has_one_unambiguous_zero_based_answer(self):
        allowed_categories = {
            "소프트웨어 설계",
            "소프트웨어 개발",
            "데이터베이스 구축",
            "프로그래밍 언어 활용",
            "정보시스템 구축관리",
        }

        self.assertGreaterEqual(len(QUIZ_BANK), 10)
        for quiz in QUIZ_BANK:
            self.assertIn(quiz["category"], allowed_categories)
            self.assertEqual(len(quiz["options"]), 4)
            self.assertEqual(len(set(quiz["options"])), 4)
            self.assertIn(quiz["answer"], range(4))
            self.assertTrue(quiz["question"])
            self.assertTrue(quiz["explain_kr"])

    def test_selection_is_deterministic_and_skips_a_recent_question(self):
        selected = select_quiz("2026-07-13", recent_questions=[])
        repeated = select_quiz("2026-07-13", recent_questions=[])
        next_quiz = select_quiz(
            "2026-07-13", recent_questions=[selected["question"]]
        )

        self.assertEqual(selected, repeated)
        self.assertNotEqual(next_quiz["question"], selected["question"])
        selected["options"][0] = "호출자가 바꾼 값"
        self.assertNotEqual(
            select_quiz("2026-07-13", recent_questions=[])["options"][0],
            "호출자가 바꾼 값",
        )

    def test_daily_selection_varies_the_correct_answer_position(self):
        answer_positions = set()
        correct_by_question = {
            quiz["question"]: quiz["options"][quiz["answer"]] for quiz in QUIZ_BANK
        }
        for day in range(1, 21):
            selected = select_quiz(f"2026-07-{day:02d}", recent_questions=[])
            answer_positions.add(selected["answer"])
            self.assertEqual(
                selected["options"][selected["answer"]],
                correct_by_question[selected["question"]],
            )

        self.assertGreaterEqual(len(answer_positions), 3)

    def test_exhausted_bank_uses_least_recently_seen_question(self):
        history = []
        previous = ""
        for day in range(1, 31):
            selected = select_quiz(f"2026-07-{day:02d}", history)
            self.assertNotEqual(selected["question"], previous)
            history.append(selected["question"])
            previous = selected["question"]


if __name__ == "__main__":
    unittest.main()
