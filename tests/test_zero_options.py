import json
import tempfile
import unittest
from pathlib import Path

from omega.zero_kernel import generate_inbound_options, operate_option_creation_cycle, score_option


class ZeroOptionTests(unittest.TestCase):
    def test_at_least_five_distinct_lawful_external_truth_paths(self):
        options=generate_inbound_options()
        self.assertGreaterEqual(len(options),5); self.assertEqual(len(options),len({x["id"] for x in options}))
        self.assertTrue(all(x["lawful"] and x["external_truth_surface"] and x["kill_condition"] for x in options))

    def test_options_expose_required_cost_risk_authority_and_evsi(self):
        for option in generate_inbound_options():
            for key in ("future_action_unlocked","expected_mission_value","evsi","authority_required","resources_required",
                        "cost","risk","reversibility","external_truth_surface","kill_condition","state"):
                self.assertIn(key,option)

    def test_winner_is_computed_not_fixed_by_identifier(self):
        option=generate_inbound_options()[0].copy(); option["id"]="different-id"; option["components"]=dict(option["components"])
        option["components"]["expected_mission_value"]=0
        rescored=score_option(option)
        self.assertNotEqual(generate_inbound_options()[0]["score"],rescored["score"])

    def test_busywork_without_truth_surface_is_rejected(self):
        option=generate_inbound_options()[0].copy(); option["external_truth_surface"]=""
        rejected=score_option(option)
        self.assertEqual("OPTION_REJECTED",rejected["state"]); self.assertTrue(rejected["busywork"])

    def test_cycle_executes_local_winner_and_creates_one_authority_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); zero=root/".omega"/"zero"; avf=root/".omega"/"avf"; zero.mkdir(parents=True); avf.mkdir(parents=True)
            (zero/"state.json").write_text(json.dumps({"global_state":"PARKED_NO_EXECUTABLE_ACTION","branches":[
                {"id":"e2-01","state":"PARKED_WAITING_EXTERNAL"},{"id":"v0.30","state":"PARKED_WAITING_EXTERNAL"},
                {"id":"inbound-evidence","state":"WAITING_AUTHORIZATION"}]}),encoding="utf-8")
            (zero/"decisions.jsonl").write_text("",encoding="utf-8"); (zero/"evidence.jsonl").write_text("",encoding="utf-8")
            (avf/"agent-runtime-audit.json").write_text('{"private":false}',encoding="utf-8")
            result=operate_option_creation_cycle(root)
            self.assertTrue(result["execution"]["executed"]); self.assertFalse(result["decision"]["external_action_performed"])
            self.assertEqual("DERIVED",result["evidence"]["type"]); self.assertEqual(0,result["real_economic_value_kwd"])
            self.assertEqual("AUTHORITY_REQUIRED",result["authority_case"]["status"])
            self.assertTrue((zero/"inbound_evidence_kit.json").exists())


if __name__=="__main__": unittest.main()
