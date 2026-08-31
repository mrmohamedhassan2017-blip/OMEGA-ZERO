import unittest

from tools.publication_guard import PublicationClass, evaluate_paths


class PublicationGuardTests(unittest.TestCase):
    def assertBlockedAs(self, path, expected):
        finding = evaluate_paths([path])[0]
        self.assertEqual(finding.classification, expected)
        self.assertTrue(finding.blocked)

    def assertAllowedAs(self, path, expected):
        finding = evaluate_paths([path])[0]
        self.assertEqual(finding.classification, expected)
        self.assertFalse(finding.blocked)

    def test_blocks_live_runtime_state(self):
        self.assertBlockedAs(".omega/wake-plane/heartbeat.json", PublicationClass.PRIVATE_RUNTIME)
        self.assertBlockedAs(".omega/task_continuity/checkpoints/task.json", PublicationClass.PRIVATE_RUNTIME)

    def test_blocks_private_evidence_state(self):
        self.assertBlockedAs(
            ".omega/zero/cybersecurity/external_evaluation/v1/results.jsonl",
            PublicationClass.PRIVATE_EVIDENCE,
        )

    def test_blocks_secret_shaped_paths(self):
        self.assertBlockedAs("config/oauth-client.json", PublicationClass.SECRET)
        self.assertBlockedAs("secrets/github-token.txt", PublicationClass.SECRET)
        self.assertBlockedAs("local/session.dpapi", PublicationClass.SECRET)

    def test_allows_known_public_surfaces(self):
        self.assertAllowedAs("omega/public_gateway.py", PublicationClass.PUBLIC_SOURCE)
        self.assertAllowedAs("agent_runtime_audit/audit.py", PublicationClass.PUBLIC_SOURCE)
        self.assertAllowedAs("tests/test_public_gateway.py", PublicationClass.PUBLIC_TEST)
        self.assertAllowedAs("docs/public-gateway/index.html", PublicationClass.PUBLIC_DOC)
        self.assertAllowedAs(".github/workflows/zero-inbound-001.yml", PublicationClass.PUBLIC_GENERATED_SAFE)
        self.assertAllowedAs("README.md", PublicationClass.PUBLIC_DOC)

    def test_unknown_fails_closed(self):
        self.assertBlockedAs("unreviewed-artifact.bin", PublicationClass.UNKNOWN)

    def test_private_deletion_is_allowed_for_remediation(self):
        finding = evaluate_paths(
            [".omega/wake-plane/heartbeat.json"],
            {".omega/wake-plane/heartbeat.json": "D"},
        )[0]
        self.assertEqual(finding.classification, PublicationClass.PRIVATE_RUNTIME)
        self.assertFalse(finding.blocked)


if __name__ == "__main__":
    unittest.main()
