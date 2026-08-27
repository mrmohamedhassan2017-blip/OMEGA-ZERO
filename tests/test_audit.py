import unittest

from agent_runtime_audit.audit import audit_agent_events, render_html


class AuditTests(unittest.TestCase):
    def test_complete_lifecycle_passes_without_raw_payloads(self):
        events = [
            {"event": "AGENT_STARTED", "secret": "must-not-appear"},
            {"event": "CHANGES_DETECTED"},
            {"event": "HOST_TEST_STARTED"},
            {"event": "HOST_TEST_PASSED"},
            {"event": "AGENT_COMPLETED"},
        ]
        report = audit_agent_events(events)
        self.assertEqual("PASS", report["assessment"])
        self.assertFalse(report["raw_payloads_included"])
        self.assertNotIn("must-not-appear", str(report))

    def test_html_escapes_event_names(self):
        report = audit_agent_events([{"event": "<script>"}])
        html = render_html(report)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()
