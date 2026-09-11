import subprocess
import unittest

from blog_pipeline.publishing.repository_sync import preflight


class PreflightTests(unittest.TestCase):
    def check(self, counts="1\t0", dirty="", url=None, fetch_error="", branch="main"):
        calls = []
        def runner(command, cwd):
            calls.append(command)
            args = command[1:]
            out, err, code = "", "", 0
            if args[0] == "status":
                out = dirty
            elif args[0] == "symbolic-ref":
                out = branch
            elif args[0] == "remote":
                out = url or "https://github.com/Seung-Won-Yu/blog-writing.git"
            elif args[0] == "fetch":
                err, code = fetch_error, int(bool(fetch_error))
            elif args[0] == "rev-list":
                out = counts
            return subprocess.CompletedProcess(command, code, out, err)
        result = preflight(runner=runner)
        self.assertFalse(any(c[1] in {"merge", "push", "reset", "rebase"} for c in calls))
        return result, calls

    def test_refreshes_before_compare(self):
        result, calls = self.check()
        self.assertEqual(result["status"], "READY")
        self.assertLess(next(i for i,c in enumerate(calls) if c[1]=="fetch"),
                        next(i for i,c in enumerate(calls) if c[1]=="rev-list"))

    def test_divergence_and_remote_ahead(self):
        for counts, expected in [("1 1", "DIVERGED"), ("0 1", "REMOTE_AHEAD"), ("0 0", "READY")]:
            self.assertEqual(self.check(counts)[0]["status"], expected)

    def test_does_not_trust_cache_after_dns_failure(self):
        result, calls = self.check(fetch_error="Could not resolve host: github.com")
        self.assertEqual(result["reason"], "NETWORK_UNAVAILABLE")
        self.assertFalse(any(c[1] == "rev-list" for c in calls))

    def test_wrong_target_dirty_tree_and_branch_stop_before_fetch(self):
        for options in [{"url": "https://example.com/other.git"}, {"dirty": " M article.json"}, {"branch": "other"}]:
            result, calls = self.check(**options)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertFalse(any(c[1] == "fetch" for c in calls))

    def test_auth_error_not_network_error(self):
        self.assertEqual(self.check(fetch_error="Authentication failed")[0]["reason"], "FETCH_FAILED")

    def test_invalid_comparison_fails_closed(self):
        self.assertEqual(self.check(counts="unexpected")[0]["reason"], "PREFLIGHT_FAILED")
