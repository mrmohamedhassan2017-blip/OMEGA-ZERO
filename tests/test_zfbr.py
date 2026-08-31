import tempfile
import unittest
from pathlib import Path

from omega.zfbr import block, classify, freeze, operate_zfbr, resume, verify_frozen


class ZFBRTests(unittest.TestCase):
    def test_freeze_hash_and_resume_gate(self):
        unit = freeze("x", "test", {"case": 1})
        self.assertTrue(verify_frozen(unit)); block(unit, classify("PROCESS_TIMEOUT", summary="bounded"))
        self.assertEqual("REPAIR_REQUIRED", unit.state)
        self.assertEqual("READY", resume(unit, blocker_resolved=True).state)

    def test_blocker_classes_remain_distinct(self):
        self.assertEqual("RESOURCE_QUOTA", classify("PROVIDER_FAILURE", resource="QUOTA")["blocker_class"])
        self.assertEqual("FILE_READ_PERMISSION", classify("FILE_ACCESS", permission="READ")["blocker_class"])
        self.assertEqual("AUTH_FAILURE", classify("AUTH_FAILURE")["blocker_class"])

    def test_corrupted_spec_stops_without_rehashing(self):
        unit = freeze("x", "test", {"case": 1}); unit.frozen_spec["case"] = 2
        out = resume(unit, blocker_resolved=True)
        self.assertEqual("INTEGRITY_FAILURE", out.state); self.assertEqual("FROZEN_SPEC_INTEGRITY_FAILURE", out.blocker_class)

    def test_freeze_detaches_mutable_input(self):
        spec = {"nested": {"value": 1}}
        unit = freeze("x", "test", spec); spec["nested"]["value"] = 2
        self.assertTrue(verify_frozen(unit))

    def test_authority_resource_and_epoch_gates_prevent_resume(self):
        unit = freeze("x", "test", {"case": 1}); block(unit, classify("RESOURCE_QUOTA", summary="quota"))
        self.assertEqual("WAITING_AUTH", resume(unit, blocker_resolved=True, authority_valid=False).state)
        self.assertEqual("WAITING_RESOURCE", resume(unit, blocker_resolved=True, resources_valid=False).state)
        self.assertEqual("PARK_FOR_REPAIR", resume(unit, blocker_resolved=True, current_epoch=99).state)

    def test_reference_cycle_persists_and_preserves_boundaries(self):
        with tempfile.TemporaryDirectory() as folder:
            result = operate_zfbr(Path(folder))
        self.assertEqual("RESOURCE_QUOTA", result["provider_quota_fixture"]["blocker_class"])
        self.assertFalse(result["provider_quota_fixture"]["provider_rotation"])
        self.assertTrue(result["frozen_spec_failure_fixture"]["stopped"])
        self.assertTrue(result["waiting_branch_result"]["branch_parks_locally"])


if __name__ == "__main__": unittest.main()
