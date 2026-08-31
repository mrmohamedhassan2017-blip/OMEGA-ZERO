import json, tempfile, unittest
from pathlib import Path
from omega.zero_truth import (append_reality_event, claim_status, operate_truth_cycle,
                              validate_reality_event)

class ZeroTruthTests(unittest.TestCase):
    def test_illegal_promotion_rejected(self):
        event={"event_id":"x","timestamp":"t","actor":"OWNER","branch":"b","action":"x","source":"s","evidence_class":"REAL_EXTERNAL_ACTION","independence_class":"OWNER","value_level":"L2","verification_status":"VERIFIED"}
        self.assertFalse(validate_reality_event(event)["valid"])

    def test_claims_require_chain_and_settlement(self):
        self.assertEqual("CLAIM_REJECTED",claim_status("REAL_ECONOMIC_VALUE = 1",[])["status"])
        self.assertEqual("CLAIM_UNPROVEN",claim_status("L3 ACHIEVED",[])["status"])

    def test_cycle_ingests_truth_and_selects_bottleneck(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=operate_truth_cycle(Path(tmp))
            self.assertEqual("independent-evidence-acquisition",result["dominant_bottleneck"]["id"])
            self.assertEqual(3, len(result["failures"]))
            self.assertEqual(0,result["real_economic_value_kwd"]); self.assertEqual("L0",result["current_value_level"])
            self.assertEqual("BUSYWORK_REJECTED",result["removal_options"][-1]["state"])

    def test_no_response_is_not_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=operate_truth_cycle(Path(tmp))
            self.assertEqual("PROPOSED_WORK_ORDER/PARKED_WAITING_EXTERNAL/NO_RESPONSE",result["wo_zero_state"])

if __name__=="__main__": unittest.main()
