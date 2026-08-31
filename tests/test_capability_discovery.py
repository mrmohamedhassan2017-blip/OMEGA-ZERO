import json
import tempfile
import unittest
from pathlib import Path

from omega.capability_discovery import EVIDENCE_CATEGORIES, build_candidates, read_events, run_discovery


class CapabilityDiscoveryTests(unittest.TestCase):
    def test_history_generates_scores_and_frozen_experiment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); log=root/".omega"/"logs"/"events.jsonl"; log.parent.mkdir(parents=True)
            log.write_text("\n".join(json.dumps(x) for x in [
                {"event":"HARD_BLOCKER","reason":"sandbox Python unavailable"},
                {"event":"RUNTIME_RESTART_REQUESTED"},{"event":"SUPERVISOR_RECOVERED"}]),encoding="utf-8")
            out=root/"artifacts"; result=run_discovery(root,out)
            self.assertGreaterEqual(len(result["registry"]["candidates"]),3)
            expected=build_candidates(read_events(root))
            self.assertEqual([(x["id"],x["score"]) for x in expected],
                             [(x["id"],x["score"]) for x in result["registry"]["candidates"]])
            self.assertEqual(64,len(result["experiment"]["specification_hash"]))
            self.assertEqual("CAPABILITY_ACCEPTED",result["outcome"])
            self.assertTrue((out/"self_model.json").exists()); self.assertTrue((out/"capabilities.json").exists())

    def test_evidence_categories_are_permanently_distinct(self):
        self.assertEqual({"VERIFIED_OBJECTIVE_EVIDENCE","INTERNAL_AI_EVALUATION","EXTERNAL_HUMAN_EVIDENCE"},EVIDENCE_CATEGORIES)

    def test_unknown_hunter_only_proposes_experiments(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=run_discovery(Path(tmp),Path(tmp)/"out"); proposals=result["unknown_unknown_proposals"]
            self.assertTrue(proposals); self.assertTrue(all("proposed_experiment" in x for x in proposals))
            self.assertFalse(any("production_change" in x for x in proposals))


if __name__ == "__main__": unittest.main()
