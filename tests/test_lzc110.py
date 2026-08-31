import tempfile,unittest
from pathlib import Path
from omega.lzc110 import campaign_spec,freeze_design

class LZC110Tests(unittest.TestCase):
 def test_observer_has_zero_authority(self):
  s=campaign_spec()
  for key in ('observer_authority','observer_start','observer_heartbeat_write','observer_lock','observer_approve'): self.assertFalse(s[key])
 def test_freeze_never_starts_runtime(self):
  with tempfile.TemporaryDirectory() as d:
   r=freeze_design(Path(d)); self.assertEqual(r['task_start_request_count'],0); self.assertEqual(len(r['campaign_spec_hash']),64)

if __name__=='__main__': unittest.main()
