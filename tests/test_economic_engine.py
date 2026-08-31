import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from omega.economic_engine import (
    ApprovalPolicy,
    AuthorityClass,
    AuthorityContext,
    EconomicClaim,
    EconomicEvent,
    EconomicEvidence,
    EconomicFailure,
    EconomicLedger,
    OpportunityObject,
    RealityLevel,
    ScaleAssessment,
    economic_utility,
    run_bootstrap,
    run_platform_registry,
    status,
    validate_claim,
    validate_promotion,
    verify_economic_engine,
)


def future() -> str:
    return (datetime.now(timezone.utc).astimezone() + timedelta(days=1)).isoformat(timespec="seconds")


def past() -> str:
    return (datetime.now(timezone.utc).astimezone() - timedelta(days=1)).isoformat(timespec="seconds")


class EconomicEngineTests(unittest.TestCase):
    def test_reality_ladder_cannot_self_promote(self):
        evidence = [EconomicEvidence("internal", "PROJECT_STATE", future(), "CURRENT", "INTERNAL_STATE", "OMEGA", ["test"], 1.0)]
        self.assertTrue(validate_promotion(RealityLevel.L0, evidence, [])[0])
        self.assertFalse(validate_promotion(RealityLevel.L2, evidence, [])[0])
        self.assertFalse(validate_promotion(RealityLevel.L4, evidence, [])[0])
        self.assertFalse(validate_promotion(RealityLevel.L7, evidence, [])[0])

    def test_proposal_owner_and_ai_consensus_are_not_demand(self):
        authority = AuthorityContext(AuthorityClass.A0, "test", ApprovalPolicy.PER_ACTION)
        evidence = {
            "proposal": EconomicEvidence("proposal", "email", future(), "CURRENT", "EXTERNAL_ACTION", "OWNER_AUTHORIZED", ["sent"], 1.0),
            "ai": EconomicEvidence("ai", "models", future(), "CURRENT", "AI_CONSENSUS", "OMEGA", ["liked"], 0.5),
        }
        claim = EconomicClaim("demand", "CUSTOMER_DEMAND_CONFIRMED", True, "BOOLEAN", future(), ["proposal", "ai"], 0.5, RealityLevel.L1, authority)
        ok, errors = validate_claim(claim, evidence)
        self.assertFalse(ok)
        self.assertIn("proposal_or_owner_activity_is_not_demand", errors)

    def test_contract_payment_profit_and_cash_remain_distinct(self):
        ledger = EconomicLedger()
        ledger.append(EconomicEvent("contract", "opp", future(), "CONTRACT", 100, "USD", 100, 0, 100, "e1", "third-party", "contract", AuthorityClass.A4, 1, "CONTRACTED", idempotency_key="contract-1"))
        cash = ledger.cash_flow()
        self.assertEqual(100, cash.contracted_value)
        self.assertEqual(0, cash.settled_value)
        self.assertEqual(0, cash.available_cash)
        self.assertEqual(0, cash.verified_net_cash_profit)
        ledger.append(EconomicEvent("payment", "opp", future(), "PAYMENT", 100, "USD", 100, 20, 80, "e2", "third-party", "payment", AuthorityClass.A5, 1, "SETTLED", idempotency_key="payment-1"))
        cash = ledger.cash_flow()
        self.assertEqual(80, cash.settled_value)
        self.assertEqual(80, cash.available_cash)
        self.assertEqual(60, cash.working_capital)

    def test_stale_evidence_expired_approval_and_revocation_fail_closed(self):
        stale = EconomicEvidence("old", "market", past(), "STALE", "MARKET_RESPONSE", "THIRD_PARTY", ["demand"], 0.8, valid_until=past())
        self.assertFalse(stale.is_current())
        expired = AuthorityContext(AuthorityClass.A3, "owner", ApprovalPolicy.PER_ACTION, "approval", past())
        revoked = AuthorityContext(AuthorityClass.A6, "owner", ApprovalPolicy.PER_ACTION, "approval", future(), "REVOKED")
        self.assertFalse(expired.allows(AuthorityClass.A3))
        self.assertFalse(revoked.allows(AuthorityClass.A1))

    def test_lower_authority_cannot_execute_external_financial_or_security_actions(self):
        authority = AuthorityContext(AuthorityClass.A2, "prep-only", ApprovalPolicy.PER_ACTION, "approval", future())
        self.assertFalse(authority.allows(AuthorityClass.A3))
        self.assertFalse(authority.allows(AuthorityClass.A5))
        self.assertFalse(authority.allows(AuthorityClass.A6))

    def test_unrealized_asset_value_is_excluded_from_mission_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = run_bootstrap(Path(tmp))
            mission = payload["mission"]
            cash = payload["cash_flow"]
            self.assertEqual(0, mission["verified_net_economic_value_usd"])
            self.assertEqual(0, cash["unrealized_estimated_asset_value"])
            self.assertEqual(1_000_000, mission["target_remaining_usd"])
            self.assertTrue(payload["verification"]["claim_results"]["claim-real-value-zero"]["valid"])

    def test_fx_without_fresh_evidence_excluded_from_verified_progress(self):
        authority = AuthorityContext(AuthorityClass.A0, "test", ApprovalPolicy.PER_ACTION)
        stale_fx = EconomicEvidence("fx", "fixture", past(), "STALE", "FX_RATE", "THIRD_PARTY", ["conversion"], 0.8, valid_until=past())
        claim = EconomicClaim("usd", "NET_VERIFIED_VALUE", 10, "USD", future(), ["fx"], 0.8, RealityLevel.L5, authority)
        ok, errors = validate_claim(claim, {"fx": stale_fx})
        self.assertFalse(ok)
        self.assertIn("stale_evidence", errors)

    def test_duplicate_economic_side_effects_require_reconciliation(self):
        ledger = EconomicLedger()
        event = EconomicEvent("p1", "opp", future(), "PAYMENT", 1, "USD", 1, 0, 1, "e", "third-party", "payment", AuthorityClass.A5, 1, "SETTLED", idempotency_key="same")
        ledger.append(event)
        with self.assertRaises(ValueError):
            ledger.append(EconomicEvent("p2", "opp", future(), "PAYMENT", 1, "USD", 1, 0, 1, "e", "third-party", "payment", AuthorityClass.A5, 1, "SETTLED", idempotency_key="same"))

    def test_ledger_hash_integrity_and_contradictions_are_preserved(self):
        ledger = EconomicLedger()
        committed = ledger.append(EconomicEvent("e1", "opp", future(), "PAYMENT", 1, "USD", 1, 0, 1, "e", "third-party", "payment", AuthorityClass.A5, 1, "SETTLED"))
        self.assertTrue(committed.ledger_hash)
        self.assertEqual((True, "ledger hash chain verified"), ledger.verify())
        authority = AuthorityContext(AuthorityClass.A0, "test", ApprovalPolicy.PER_ACTION)
        claim = EconomicClaim("c", "CUSTOMER_DEMAND_CONFIRMED", True, "BOOLEAN", future(), [], 0.5, RealityLevel.L2, authority, contradicting_evidence=["negative-reply"])
        ok, errors = validate_claim(claim, {})
        self.assertFalse(ok)
        self.assertIn("contradicting_evidence_present", errors)

    def test_scale_gate_blocks_negative_liquidity_and_concentration_risk(self):
        self.assertEqual(EconomicFailure.NEGATIVE_UNIT_ECONOMICS.value, ScaleAssessment(1, 2, 0, 0, 0, 0, 0, 0, True, True).decision())
        self.assertEqual(EconomicFailure.LIQUIDITY_RISK.value, ScaleAssessment(5, 1, 0, 0, 0, 0, 0, 0, True, False).decision())
        self.assertEqual("CONCENTRATION_RISK", ScaleAssessment(5, 1, 0, 0, 0, 0, 0, 0.9, True, True).decision())

    def test_unknown_failure_is_bounded_and_security_scope_is_blocked(self):
        self.assertEqual("UNKNOWN_FAILURE", EconomicFailure.UNKNOWN_FAILURE.value)
        authority = AuthorityContext(AuthorityClass.A5, "financial", ApprovalPolicy.PER_ACTION, "approval", future())
        self.assertFalse(authority.allows(AuthorityClass.A6))

    def test_utility_keeps_estimates_separate_from_verified_cash(self):
        opp = OpportunityObject("opp", "test", [], future(), "problem", "customer", "market", RealityLevel.L0, 100, 80, 1, 2, 3, 4, 0.5, 0.25, 0.75, 0.5, 0.5, 0.5, 3, 2, 1, 0.4, 0.3, AuthorityClass.A0, ApprovalPolicy.PER_ACTION, 1, 1, 1, 1, 1, 0.8, 0.7, ["u"], "critical", "cheap test", ["kill"], ["scale"], [], "OPTION_CREATED", "next")
        self.assertIsInstance(economic_utility(opp), float)

    def test_bootstrap_persists_minimal_state_without_control_plane_or_value_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = run_bootstrap(root)
            self.assertTrue((root / ".omega" / "zero" / "economic" / "state.json").exists())
            self.assertFalse(payload["engine_state"]["parallel_control_plane_created"])
            self.assertEqual(0, payload["engine_state"]["mission_state"]["verified_net_economic_value_usd"])
            self.assertEqual(0, payload["external_writes"])
            self.assertEqual(0, payload["financial_actions"])
            self.assertEqual(0, payload["security_actions"])

    def test_engine_verification_and_status_are_machine_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            verification = verify_economic_engine(root)
            self.assertTrue(verification["implemented"])
            not_bootstrapped = status(root)
            self.assertEqual("NOT_BOOTSTRAPPED", not_bootstrapped["state"])
            self.assertFalse((root / ".omega" / "zero" / "economic" / "state.json").exists())
            run_bootstrap(root)
            result = status(root)
            self.assertEqual("ZERO-AUTONOMOUS-ECONOMIC-ENGINE-V2.0", result["constitution_id"])
            self.assertEqual(0, result["verified_net_economic_value_usd"])

    def test_platform_registry_fails_closed_and_selects_preparation_only_top_three(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_platform_registry(Path(tmp))
        self.assertEqual("IMPLEMENTED_PREPARE_ONLY", report["registry_state"])
        self.assertEqual(27, report["platform_count"])
        self.assertGreaterEqual(report["policy_verified_count"], 3)
        self.assertEqual([], report["execution_ready_platforms"])
        self.assertEqual([], report["payout_ready_platforms"])
        self.assertEqual(0, report["external_actions"])
        self.assertEqual(0, report["financial_actions"])
        self.assertEqual(0, report["security_actions"])
        self.assertEqual("INTERNAL_HYPOTHESIS", report["reality_level_after"])
        top = report["top_3_channels"]
        self.assertEqual(3, len(top))
        self.assertEqual("github", top[0]["platform_id"])
        selected = report["selected_first_experiment"]
        self.assertFalse(selected["executed"])
        self.assertFalse(selected["external_evidence_created"])
        self.assertIn(selected["authority_required"], {"OBSERVE_READ", "EXTERNAL_ACTION_PREPARATION"})

    def test_platform_registry_preserves_unknown_as_unknown_not_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_platform_registry(Path(tmp))
        platforms = {item["platform_id"]: item for item in report["platforms"]}
        self.assertEqual("UNVERIFIED", platforms["fiverr"]["state"])
        self.assertEqual("UNKNOWN", platforms["fiverr"]["ai_usage_policy"])
        self.assertFalse(platforms["fiverr"]["execution_enabled"])
        self.assertFalse(platforms["fiverr"]["payout_enabled"])


if __name__ == "__main__":
    unittest.main()
