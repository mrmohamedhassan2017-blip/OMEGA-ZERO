import json, tempfile, unittest
from pathlib import Path
from omega.lzc19d import freeze_episode

class LZC19DTests(unittest.TestCase):
    def test_freeze_does_not_upgrade_missing_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); p=root/'.omega/zero'; p.mkdir(parents=True)
            (p/'lzc_v1_9b_result.json').write_text(json.dumps({'start_request_count':1,'heartbeat_writer_count':1,'heartbeat_advance_sample_count':1,'fresh_heartbeat_sample_count':2,'unsafe_process_terminations':0,'core_api_spec_hash_valid':True}), encoding='utf-8')
            r=freeze_episode(root)
            self.assertEqual(r['final_result'],'HARD_BLOCKER_HEALTH_EPISODE_WITH_ISSUES')
            self.assertEqual(r['live_identity_valid'],'UNKNOWN'); self.assertEqual(r['additional_starts'],0)

if __name__=='__main__': unittest.main()
