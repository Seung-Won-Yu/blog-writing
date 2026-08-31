import subprocess
import unittest

from blog_pipeline.publishing.repository_sync import (
    PushStatus,
    is_transient_git_error,
    push_with_retry,
)


def completed(returncode, stderr="", stdout=""):
    return subprocess.CompletedProcess(
        args=["git", "push", "origin", "main"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class RepositorySyncTests(unittest.TestCase):
    def test_transient_network_errors_are_classified_for_retry(self):
        for message in (
            "fatal: unable to access: Could not resolve host: github.com",
            "fatal: unable to access: The requested URL returned error: 503",
            "fatal: unable to access: Failed to connect to github.com",
            "fatal: unable to access: Operation timed out",
        ):
            with self.subTest(message=message):
                self.assertTrue(is_transient_git_error(message))

    def test_auth_and_non_fast_forward_errors_are_not_retried(self):
        for message in (
            "remote: Permission to repository denied",
            "fatal: Authentication failed",
            "! [rejected] main -> main (non-fast-forward)",
        ):
            with self.subTest(message=message):
                self.assertFalse(is_transient_git_error(message))

    def test_dns_failure_is_retried_and_then_succeeds(self):
        results = iter(
            (
                completed(128, "Could not resolve host: github.com"),
                completed(0, stdout="main -> main"),
            )
        )
        commands = []
        delays = []

        def runner(command, cwd):
            commands.append(command)
            return next(results)

        result = push_with_retry(
            remote="origin",
            refspec="main",
            max_attempts=3,
            base_delay=2,
            runner=runner,
            sleep=delays.append,
        )

        self.assertEqual(result.status, PushStatus.PUSHED)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(delays, [2])
        self.assertEqual(commands, [["git", "push", "origin", "main"]] * 2)

    def test_auth_failure_stops_without_retry(self):
        calls = []
        delays = []

        def runner(command, cwd):
            calls.append(command)
            return completed(128, "fatal: Authentication failed")

        result = push_with_retry(
            max_attempts=3,
            runner=runner,
            sleep=delays.append,
        )

        self.assertEqual(result.status, PushStatus.BLOCKED)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(delays, [])

    def test_transient_failure_is_bounded(self):
        calls = []
        delays = []

        def runner(command, cwd):
            calls.append(command)
            return completed(128, "The requested URL returned error: 504")

        result = push_with_retry(
            max_attempts=3,
            base_delay=1.5,
            runner=runner,
            sleep=delays.append,
        )

        self.assertEqual(result.status, PushStatus.TRANSIENT_FAILURE)
        self.assertEqual(result.attempts, 3)
        self.assertEqual(len(calls), 3)
        self.assertEqual(delays, [1.5, 3.0])


if __name__ == "__main__":
    unittest.main()
