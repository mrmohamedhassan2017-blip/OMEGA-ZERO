import json
import tempfile
import unittest
from pathlib import Path

from omega.zero_kernel import (EVIDENCE_TYPES, candidate_actions, execute_first_cycle, execute_zeu_stress_baseline, make_evidence,
                               rank_action, validate_economic_truth, zeu_ledger)


class ZeroKernelTests(unittest.TestCase):
    def _root(self, tmp):
        root=Path(tmp); avf=root/".omega"/"avf"; avf.mkdir(parents=True)
        auth={"scope":{"financial_authority_kwd":0,"contacts_used":4,"maximum_qualified_contacts":10},
              "audit":{"qualified_signals":0,"actions_executed":4}}
        (avf/"market_authorization.json").write_text(json.dumps(auth),encoding="utf-8")
        (root/"NEXT_TASK.md").write_text("status: waiting_external_evidence",encoding="utf-8")
        return root

    def test_evidence_types_never_silently_promote(self):
        self.assertEqual({"REAL","DERIVED","SIMULATED","SYNTHETIC","HYPOTHETICAL"},EVIDENCE_TYPES)
        for kind in EVIDENCE_TYPES-{"REAL"}:
            evidence=make_evidence(evidence_id=kind,evidence_type=kind,source="test",subject="s",claim="c",
                                   confidence=.5,independence="INTERNAL",reproducibility="fixture")
            self.assertFalse(evidence["real_world_promotions_allowed"])
            with self.assertRaises(ValueError): validate_economic_truth(evidence,"RECEIVED")

    def test_wait_actions_are_busywork_and_non_executable_actions_cannot_win(self):
        actions=candidate_actions()
        wait=next(x for x in actions if x["id"]=="wait-for-e2-reply")
        invalid=next(x for x in actions if x["id"]=="complete-v030-internally")
        self.assertTrue(wait["busywork"]); self.assertIsNone(wait["eva"])
        self.assertFalse(invalid["executable_now"]); self.assertIsNone(invalid["eva"])

    def test_ranking_requires_all_auditable_components(self):
        with self.assertRaises(ValueError): rank_action({"components":{},"authorized":True,"resources_available":True})
        winner=next(x for x in candidate_actions() if x["eva"] is not None)
        self.assertIn("warning",winner["ranking_model"])

    def test_zeu_is_balanced_simulated_nonmonetary_and_nontransferable(self):
        ledger=zeu_ledger(); entry=ledger["entries"][0]
        self.assertTrue(ledger["balanced"]); self.assertFalse(ledger["real_monetary_value"])
        self.assertTrue(ledger["non_transferable_external"]); self.assertEqual("SIMULATED",entry["evidence_type"])
        self.assertEqual(sum(x["debit"] for x in entry["postings"]),sum(x["credit"] for x in entry["postings"]))

    def test_first_cycle_parks_waiting_branches_executes_and_records_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self._root(tmp); result=execute_first_cycle(root)
            states={x["id"]:x["state"] for x in result["branches"]}
            self.assertEqual("PARKED_WAITING_EXTERNAL",states["e2-01"])
            self.assertEqual("PARKED_WAITING_EXTERNAL",states["v0.30"])
            self.assertEqual("WAITING_AUTHORIZATION",states["inbound-evidence"])
            self.assertEqual("freeze-inbound-install-experiment",result["decision"]["chosen_action"])
            self.assertEqual("OPTION_UNLOCKED",result["decision"]["actual_outcome"])
            self.assertEqual("DERIVED",result["evidence"]["type"])
            self.assertEqual(0,result["real_economic_state"]["verified_value_kwd"])
            self.assertTrue((root/".omega"/"zero"/"decisions.jsonl").exists())

    def test_cycle_is_idempotent_for_append_only_initial_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self._root(tmp); execute_first_cycle(root); execute_first_cycle(root)
            decisions=(root/".omega"/"zero"/"decisions.jsonl").read_text().splitlines()
            evidence=(root/".omega"/"zero"/"evidence.jsonl").read_text().splitlines()
            self.assertEqual(1,len(decisions)); self.assertEqual(1,len(evidence))

    def test_zeu_stress_execution_exposes_failures_without_real_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self._root(tmp); execute_first_cycle(root); result=execute_zeu_stress_baseline(root)
            self.assertEqual("SIMULATED",result["evidence"]["type"])
            self.assertEqual(0,result["real_economic_value_kwd"])
            self.assertTrue(any(x["failure_exposed"] for x in result["results"]))
            self.assertTrue(all(not x["proof_of_viability"] for x in result["results"]))
            self.assertEqual("PARKED_NO_EXECUTABLE_ACTION",result["global_state"])
            state=json.loads((root/".omega"/"zero"/"state.json").read_text())
            kernel=next(x for x in state["branches"] if x["id"]=="zero-agency-kernel")
            self.assertEqual("PARKED_WAITING_TIME",kernel["state"]); self.assertEqual([],kernel["next_executable_actions"])


if __name__=="__main__": unittest.main()
