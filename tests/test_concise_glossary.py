import unittest
from blog_pipeline.publishing.editorial_quality import _valid_reader_glossary


class ConciseGlossaryTests(unittest.TestCase):
    def test_two_useful_terms_are_enough(self):
        terms = [{"term": "가속도 센서", "meaning": "움직임과 중력의 효과를 전기 신호로 읽는 부품이다."},
                 {"term": "세 축", "meaning": "기기의 좌우와 위아래, 앞뒤를 구분하는 세 방향이다."}]
        self.assertTrue(_valid_reader_glossary({"glossary": terms}))
        self.assertFalse(_valid_reader_glossary({"glossary": terms[:1]}))
        self.assertFalse(_valid_reader_glossary({"glossary": [terms[0], terms[0]]}))
        self.assertFalse(_valid_reader_glossary({"glossary": [terms[0], {"term": "세 축", "meaning": "짧음"}]}))
