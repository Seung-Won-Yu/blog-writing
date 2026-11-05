import unittest
from unittest.mock import patch
from urllib.request import Request

from blog_pipeline.publishing.public_article import validate_url, parse_article, PublicRedirects, main


class PublicArticleTests(unittest.TestCase):
    def test_private_login_external_and_non_numeric_urls_are_rejected(self):
        for url in ('http://won0322.tistory.com/214','https://won0322.tistory.com/manage/posts','https://won0322.tistory.com/214?login=1','https://example.org/214','https://won0322.tistory.com:443/214'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    def test_only_public_article_body_is_extracted_without_scripts_or_sidebar(self):
        body='실제 공개 글에서 읽어야 하는 문단과 설명입니다. '*10
        html=f'<title>공개 제목</title><nav>제외</nav><div class="tt_article_useless_p_margin contents_style"><article><h2>확인 순서</h2><p>{body}</p><script>SECRET_SCRIPT</script><div>마지막 문단</div></article></div><aside>SIDEBAR</aside>'
        parsed=parse_article(html,'https://won0322.tistory.com/214')
        self.assertEqual(parsed['title'],'공개 제목')
        self.assertIn(body.strip(),parsed['text'])
        self.assertNotIn('SECRET_SCRIPT',parsed['text'])
        self.assertNotIn('SIDEBAR',parsed['text'])

    def test_login_or_soft_error_page_never_counts_as_a_public_comparison(self):
        with self.assertRaises(ValueError):
            parse_article('<title>로그인</title><p>로그인하세요</p>','https://won0322.tistory.com/214')

    def test_redirects_cannot_change_article_or_enter_login(self):
        handler=PublicRedirects();req=Request('https://won0322.tistory.com/214')
        for url in ('https://accounts.kakao.com/login','https://won0322.tistory.com/221'):
            with self.assertRaises(ValueError):
                handler.redirect_request(req,None,302,'redirect',{},url)

    def test_raw_evidence_inside_repository_is_rejected_before_network(self):
        with patch('blog_pipeline.publishing.public_article.fetch_article') as fetch:
            with self.assertRaises(SystemExit):
                main(['--url','https://won0322.tistory.com/214','--output','reports/raw-public.json'])
            fetch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
