import unittest

from omega.termination import Observation as O, Policy, StopReason, compare_policies, decide, mutate_policy


class TerminationTests(unittest.TestCase):
    def test_distinguishes_all_terminal_reasons(self):
        p = Policy(window=3, restart_budget=0)
        cases = {
            StopReason.GOAL_REACHED: [O(1,1,.2,.01,.05,5)],
            StopReason.RESOURCE_EXHAUSTION: [O(.5,1,.2,.01,.05,0)],
            StopReason.REGRESSION_RISK: [O(.5,1,.2,.3,.05,5)],
            StopReason.EVALUATION_UNCERTAINTY: [O(.5,1,.2,.01,.8,5)],
            StopReason.NO_NOVEL_MUTATIONS: [O(.4,1,0,.01,.1,5)]*3,
            StopReason.DIMINISHING_RETURNS: [O(.4,1,.01,.01,.1,5), O(.401,1,.01,.01,.1,5), O(.402,1,.01,.01,.1,5)],
            StopReason.LOCAL_OPTIMUM: [O(.4,1,.2,.01,.1,5), O(.401,1,.2,.01,.1,5), O(.402,1,.2,.01,.1,5)],
        }
        for reason, history in cases.items():
            self.assertEqual(reason.value, decide(history, p)["reason"])

    def test_local_optimum_gets_bounded_escape_before_stop(self):
        h = [O(.4,1,.2,.01,.1,5), O(.401,1,.2,.01,.1,5), O(.402,1,.2,.01,.1,5)]
        self.assertEqual("DIVERSIFY_RESTART", decide(h, Policy(window=3, restart_budget=1), 0)["action"])
        self.assertEqual(StopReason.LOCAL_OPTIMUM.value, decide(h, Policy(window=3, restart_budget=1), 1)["reason"])

    def test_policy_mutation_cannot_silently_replace_baseline(self):
        fixtures = frozen_fixtures()
        result = mutate_policy(Policy(window=3), fixtures)
        self.assertTrue(result["comparison"]["baseline_unchanged"])
        if result["accepted"]:
            winner = result["comparison"]["results"][0]
            self.assertEqual(0, winner["unsafe_continuations"])

    def test_rejected_policy_mutation_selects_baseline(self):
        baseline = Policy(window=3)
        result = mutate_policy(baseline, frozen_fixtures())
        self.assertFalse(result["accepted"])
        self.assertEqual(baseline, result["selected"])
        self.assertTrue(result["comparison"]["baseline_unchanged"])

    def test_strategies_are_compared_on_frozen_evidence(self):
        policies = [Policy("HYBRID_EVSI", window=3), Policy("RISK_FIRST", window=3, risk_limit=.1),
                    Policy("PATIENCE", window=4, min_gain_per_cost=.001)]
        result = compare_policies(frozen_fixtures(), policies)
        self.assertEqual(3, len(result["results"]))
        self.assertEqual(0, result["results"][0]["unsafe_continuations"])

    def test_continuing_under_evaluation_uncertainty_is_unsafe(self):
        fixture = [{
            "history": [O(.4, 1, .2, .01, .8, 3)],
            "expected": StopReason.EVALUATION_UNCERTAINTY.value,
        }]
        result = compare_policies(fixture, [Policy("OVERCONFIDENT", uncertainty_limit=.9)])
        self.assertEqual(1, result["results"][0]["unsafe_continuations"])
        self.assertLess(result["results"][0]["utility"], 0)

    def test_decision_evidence_captures_policy_and_derived_metrics(self):
        policy = Policy(window=3, risk_limit=.17, restart_budget=1)
        history = [O(.4, 1, .2, .01, .1, 3), O(.401, 1, .3, .01, .1, 3),
                   O(.402, 1, .4, .01, .1, 3)]
        result = decide(history, policy, restarts_used=1)
        evidence = result["evidence"]
        self.assertEqual(.17, evidence["policy"]["risk_limit"])
        self.assertEqual(1, evidence["policy"]["restarts_used"])
        self.assertTrue(evidence["tests_passed"])
        self.assertEqual(.4, evidence["max_novelty"])
        self.assertIn("mean_gain_per_cost", evidence)

    def test_invalid_measurements_fail_closed_with_evidence(self):
        cases = [
            O(float("nan"), 1, .2, .01, .05, 3),
            O(.5, -1, .2, .01, .05, 3),
            O(.5, 1, .2, 1.1, .05, 3),
            O(.5, "unknown", .2, .01, .05, 3),
        ]
        for observation in cases:
            result = decide([observation])
            self.assertEqual(StopReason.EVALUATION_UNCERTAINTY.value, result["reason"])
            self.assertEqual("STOP", result["action"])
            self.assertTrue(result["evidence"]["invalid_measurements"])

    def test_invalid_policy_fails_closed_with_evidence(self):
        cases = [
            (Policy(window=0), 0, "window"),
            (Policy(risk_limit=float("nan")), 0, "risk_limit"),
            (Policy(restart_budget=-1), 0, "restart_budget"),
            (Policy(), -1, "restarts_used"),
        ]
        for policy, restarts_used, invalid_field in cases:
            result = decide([O(.5, 1, .2, .01, .05, 3)], policy, restarts_used)
            self.assertEqual(StopReason.EVALUATION_UNCERTAINTY.value, result["reason"])
            self.assertEqual("STOP", result["action"])
            self.assertIn(invalid_field, result["evidence"]["invalid_policy"])


def frozen_fixtures():
    return [
        {"history":[O(1,1,.2,.01,.05,3)], "expected":StopReason.GOAL_REACHED.value},
        {"history":[O(.4,1,.2,.4,.05,3)], "expected":StopReason.REGRESSION_RISK.value},
        {"history":[O(.4,1,.2,.01,.8,3)], "expected":StopReason.EVALUATION_UNCERTAINTY.value},
        {"history":[O(.3,1,0,.01,.1,3)]*3, "expected":StopReason.NO_NOVEL_MUTATIONS.value},
        {"history":[O(.3,1,.2,.01,.1,3),O(.301,1,.2,.01,.1,3),O(.302,1,.2,.01,.1,3)],
         "expected":StopReason.CONTINUE.value},
    ]


if __name__ == "__main__":
    unittest.main()
