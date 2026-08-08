import subprocess
import unittest

from blog_pipeline.publishing.sync_main import (
    is_transient_network_error,
    pull_with_retry,
)


def result(returncode, stderr="", stdout=""):
    return subprocess.CompletedProcess(
        args=["git", "pull"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class SyncMainTests(unittest.TestCase):
    def test_retries_dns_failure_then_succeeds(self):
        outcomes = iter(
            [
                result(1, "fatal: unable to access: Could not resolve host: github.com"),
                result(0, stdout="Already up to date.\n"),
            ]
        )
        calls = []
        sleeps = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return next(outcomes)

        returncode = pull_with_retry(
            attempts=3,
            retry_delay=2,
            runner=runner,
            sleeper=sleeps.append,
        )

        self.assertEqual(returncode, 0)
        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, [2])
        self.assertEqual(
            calls[0][0], ["git", "pull", "--ff-only", "origin", "main"]
        )

    def test_does_not_retry_non_fast_forward_failure(self):
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return result(128, "fatal: Not possible to fast-forward, aborting.")

        returncode = pull_with_retry(
            attempts=3,
            retry_delay=0,
            runner=runner,
            sleeper=lambda _delay: None,
        )

        self.assertEqual(returncode, 128)
        self.assertEqual(len(calls), 1)

    def test_stops_after_retry_limit(self):
        calls = []
        sleeps = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return result(1, "fatal: Could not resolve host: github.com")

        returncode = pull_with_retry(
            attempts=3,
            retry_delay=1,
            runner=runner,
            sleeper=sleeps.append,
        )

        self.assertEqual(returncode, 1)
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleeps, [1, 2])

    def test_recognizes_transient_gateway_error(self):
        self.assertTrue(
            is_transient_network_error("The requested URL returned error: 503")
        )


if __name__ == "__main__":
    unittest.main()
