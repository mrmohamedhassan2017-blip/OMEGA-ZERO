import tempfile
import unittest
from pathlib import Path

from omega.venture_foundry import MISSION_I_TARGET_KWD, advance_e2, audit_agent_events, broker_action, classify_response, economic_ledger, founder_os, gmail_broker_grant, market_barrier, qualify_target, render_agent_audit_html, run_foundry


class VentureFoundryTests(unittest.TestCase):
    def test_e0_e1_portfolio_court_and_experiments_are_reproducible(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=run_foundry(Path(tmp),Path(tmp)/"avf")
            self.assertEqual(20,len(result["portfolio"])); self.assertEqual(5,len(result["finalists"]))
            self.assertEqual(5,len(result["courts"])); self.assertEqual(3,len(result["experiments"]))
            self.assertIn(result["selected_venture"]["current_state"],{"EXPERIMENTING","BUILDING"})
            self.assertTrue(all(x["evidence"] for x in result["portfolio"]))
            self.assertTrue(all(c["judge"]["recommendation"] in {"RUN_EXPERIMENT","WAIT_FOR_EVIDENCE"} for c in result["courts"]))

    def test_no_money_claim_without_evidence(self):
        with self.assertRaisesRegex(ValueError,"provenance"):
            economic_ledger([{"classification":"RECEIVED","amount_kwd":10}])
        ledger=economic_ledger([])
        self.assertEqual(0,ledger["verified_realized_economic_value_kwd"])
        self.assertEqual(MISSION_I_TARGET_KWD,ledger["mission_target_kwd"])

    def test_forecast_is_not_realized_value(self):
        entry={"classification":"FORECAST","amount_kwd":999999,"source":"model","timestamp":"2026-08-27",
               "evidence":"assumption only","venture":"v","verification_status":"ESTIMATED"}
        self.assertEqual(0,economic_ledger([entry])["verified_realized_economic_value_kwd"])

    def test_mvp_audit_excludes_raw_payloads_and_detects_lifecycle_gaps(self):
        report=audit_agent_events([{"event":"AGENT_STARTED","reason":"password=secret"},{"event":"HARD_BLOCKER","payload":"token"}])
        serialized=str(report).lower()
        self.assertEqual("REVIEW",report["assessment"]); self.assertIn("without matching completion"," ".join(report["findings"]))
        self.assertNotIn("password",serialized); self.assertNotIn("secret",serialized); self.assertFalse(report["raw_payloads_included"])
        html=render_agent_audit_html(report); self.assertIn("Agent Runtime Audit",html); self.assertNotIn("token",html)

    def test_e2_preparation_preserves_truth_and_queues_external_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=advance_e2(Path(tmp),Path(tmp)/"e2")
            self.assertEqual("E2_PREPARED_NOT_ACHIEVED",result["gate"])
            self.assertEqual(0,result["verified_external_demand_signals"]); self.assertEqual(0,result["verified_economic_value_kwd"])
            self.assertGreaterEqual(len(result["positioning"]),3); self.assertGreaterEqual(len(result["demand_experiments"]),4)
            self.assertTrue(result["external_action_queue"]); self.assertEqual(0,result["capability_investment_fund"]["balance_kwd"])
            self.assertTrue(all(x["economic_roi"]=="UNVERIFIED" for x in result["capability_frontier"]))

    def test_founder_os_prioritizes_market_contact_and_batches_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=founder_os(Path(tmp),Path(tmp)/"founder")
            self.assertEqual("reachability",result["assumption_graph"]["fatal_upstream_assumption"])
            self.assertEqual("QUEUED",result["external_action_broker"]["status"])
            self.assertEqual(0,result["mission_verified_value_kwd"])
            self.assertEqual(0,result["decision_case"]["minimum_authorization"]["financial_authority_kwd"])
            self.assertEqual([],result["verified_demand_events"])

    def test_credential_possession_never_implies_permission(self):
        identity={"identity_id":"x","credential":"present","authorized":False,"revoked":False,"channels":["c"],"permissions":["SEND"]}
        result=broker_action(identity,{"id":"a","action":"SEND","channel":"c"})
        self.assertEqual("QUEUED",result["status"]); self.assertFalse(result["executed"])
        self.assertFalse(result["audit"]["credential_presence_treated_as_permission"])

    def test_market_controller_requires_qualified_target_and_real_authorization(self):
        target={"target_id":"t1","operates_coding_agents":True,"runtime_responsibility":True,"pain_evidence":"public role description",
                "authority":"CHAMPION","channel_permits_contact":False}
        self.assertFalse(qualify_target(target)["qualified"])
        with tempfile.TemporaryDirectory() as tmp:
            result=market_barrier(Path(tmp),Path(tmp)/"market")
            self.assertEqual("READY_FOR_AUTHORIZATION",result["policy"]["status"])
            self.assertEqual(0,result["market_contact_controller"]["actions_executed"])
            self.assertEqual("DISABLED",result["treasury"]["mode"])
            self.assertEqual([],result["verified_external_signals"])

    def test_delivery_is_not_e2_but_qualified_reply_is(self):
        delivered=classify_response({"signal":"DELIVERED","provenance":"adapter receipt"})
        reply=classify_response({"signal":"QUALIFIED_REPLY","provenance":"signed response","pain_rejection":"not our problem"})
        self.assertFalse(delivered["e2_satisfied"]); self.assertTrue(reply["e2_satisfied"])
        self.assertEqual("not our problem",reply["learning"]["pain_rejection"])

    def test_owner_authorization_without_channel_stays_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); path=root/".omega"/"avf"/"market_authorization.json"; path.parent.mkdir(parents=True)
            path.write_text('{"identity":{"owner_authorized":true},"channel":{"authorized":false}}',encoding="utf-8")
            result=market_barrier(root,root/"out")
            self.assertEqual("AUTHORIZED_PENDING_CHANNEL",result["market_contact_controller"]["state"])
            self.assertEqual(0,result["market_contact_controller"]["actions_executed"])

    def test_gmail_grant_requires_executable_channel_and_qualified_target(self):
        authorization={"experiment_id":"E2-01","status":"E2_EXECUTABLE",
          "identity":{"owner_authorized":True},
          "channel":{"id":"gmail","account":"omega.agent.runtime@gmail.com","authorized":True,"policy_verified":True},
          "scope":{"contacts_used":0,"maximum_qualified_contacts":10,"financial_authority_kwd":0,
                   "message_variants":1,"automated_follow_up":False},
          "frozen_message":{"sha256":"cf4dc2ae69945e079ac2c006b6eb5af12b86da09a4b84b4064cd5121dcbf2a4a"},
          "kill_switch":{"revoked":False}}
        target={"target_id":"t1","operates_coding_agents":True,"runtime_responsibility":True,
                "pain_evidence":"owner-supplied qualification","authority":"CHAMPION","channel_permits_contact":True}
        self.assertTrue(gmail_broker_grant(authorization,target)["authorized"])
        authorization["kill_switch"]["revoked"]=True
        self.assertFalse(gmail_broker_grant(authorization,target)["authorized"])

    def test_market_controller_preserves_verified_executable_channel_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); auth=root/".omega"/"avf"/"market_authorization.json"; auth.parent.mkdir(parents=True)
            auth.write_text('{"status":"E2_EXECUTABLE","identity":{"owner_authorized":true},"channel":{"authorized":true,"policy_verified":true},"audit":{"actions_executed":0}}',encoding="utf-8")
            result=market_barrier(root,root/"out")
            self.assertEqual("E2_EXECUTABLE",result["market_contact_controller"]["state"])
            self.assertEqual(0,result["market_contact_controller"]["actions_executed"])
            self.assertIn("qualified targets",result["market_contact_controller"]["reason"])

    def test_e2_frozen_experiment_is_reused_without_hash_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); out=root/"e2"
            first=advance_e2(root,out)["demand_experiments"]
            second=advance_e2(root,out)["demand_experiments"]
            self.assertEqual(first,second)
            self.assertEqual(first[0]["specification_hash"],second[0]["specification_hash"])


if __name__=="__main__": unittest.main()
