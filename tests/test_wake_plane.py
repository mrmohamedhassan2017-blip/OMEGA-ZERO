import json,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from omega.wake_plane import WakePlane,parse_trigger,SPEC_HASH,sanitize,status

def trigger(**over):
 now=datetime.now(timezone.utc); value={'trigger_id':'t1','trigger_type':'INTERNAL_READY','source':'fixture','source_identity':'host','source_event_id':'fixture:t1','canonical_event_fingerprint':'fixture-fp-1','observed_at':now.isoformat(),'work_id':'w1','wake_condition':'ready','provenance_class':'INTERNAL_DETERMINISTIC','evidence_reference':'fixture:1','authority_requirement':'NONE','resource_requirement':'HOST','external_effect':False,'dedupe_key':'d1','expiry':(now+timedelta(hours=1)).isoformat(),'verification_requirement':'host'};value.update(over);return value
class WakePlaneTests(unittest.TestCase):
 def test_schema_and_expiry_fail_closed(self):
  self.assertEqual(parse_trigger({})[1],'INVALID_SCHEMA');self.assertEqual(parse_trigger(trigger(expiry=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()))[1],'EXPIRED')
 def test_shadow_never_wakes(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'NEXT_TASK.md').write_text('w1');p=root/'.omega/wake-plane/inbox';p.mkdir(parents=True);(p/'t.json').write_text(json.dumps(trigger()))
   calls=[];r=WakePlane(root,'SHADOW',lambda r:calls.append(r)).cycle();self.assertEqual(r['wake_requests'],0);self.assertEqual(calls,[])
 def test_production_single_wake_and_dedupe(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'NEXT_TASK.md').write_text('w1');p=root/'.omega/wake-plane/inbox';p.mkdir(parents=True);(p/'t.json').write_text(json.dumps(trigger()))
   calls=[];wp=WakePlane(root,'PASSIVE_PRODUCTION',lambda r:calls.append(r) or 42);self.assertEqual(wp.cycle()['wake_requests'],1);self.assertEqual(wp.cycle()['wake_requests'],0);self.assertEqual(len(calls),1)
 def test_coalesces_simultaneous_triggers(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'NEXT_TASK.md').write_text('w1');p=root/'.omega/wake-plane/inbox';p.mkdir(parents=True)
   (p/'a.json').write_text(json.dumps(trigger()));(p/'b.json').write_text(json.dumps(trigger(trigger_id='t2',dedupe_key='d2')))
   calls=[];r=WakePlane(root,'PASSIVE_PRODUCTION',lambda x:calls.append(1) or 7).cycle();self.assertEqual(r['wake_requests'],1);self.assertEqual(len(calls),1)
 def test_supervisor_live_prevents_wake(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'NEXT_TASK.md').write_text('w1');p=root/'.omega/wake-plane/inbox';p.mkdir(parents=True);(p/'t.json').write_text(json.dumps(trigger()))
   self.assertEqual(WakePlane(root,'PASSIVE_PRODUCTION',lambda r:1).cycle(supervisor_live=True)['wake_requests'],0)
 def test_validate_only_never_wakes(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'NEXT_TASK.md').write_text('w1');p=root/'.omega/wake-plane/inbox';p.mkdir(parents=True);(p/'t.json').write_text(json.dumps(trigger()))
   calls=[];result=WakePlane(root,'PASSIVE_PRODUCTION_VALIDATE_ONLY',lambda r:calls.append(r)).cycle()
   self.assertEqual(result['wake_requests'],0);self.assertEqual(calls,[])
 def test_secret_sanitization(self):self.assertEqual(sanitize('client_secret=oops'),'REDACTED_SENSITIVE_ERROR')
 def test_noncurrent_work_is_parked_without_wake(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'NEXT_TASK.md').write_text('different');p=root/'.omega/wake-plane/inbox';p.mkdir(parents=True);(p/'t.json').write_text(json.dumps(trigger()))
   calls=[];r=WakePlane(root,'PASSIVE_PRODUCTION',lambda x:calls.append(1)).cycle();self.assertEqual(r['wake_requests'],0);self.assertEqual(calls,[])
 def test_spec_hash_frozen(self):self.assertEqual(len(SPEC_HASH),64)
 def test_passive_intake_trigger_types_are_registered(self):
  self.assertEqual(parse_trigger(trigger(trigger_type='ZRWVE_PASSIVE_INCIDENT_SUBMISSION'))[1],'VALID')
  self.assertEqual(parse_trigger(trigger(trigger_type='ZRWVE_REAL_INCIDENT_PACKET_RECEIVED'))[1],'VALID')
  self.assertEqual(parse_trigger(trigger(trigger_type='ZRWVE_PUBLIC_INCIDENT_CANDIDATE'))[1],'VALID')
 def test_cross_source_fingerprint_is_deduped(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'NEXT_TASK.md').write_text('w1');p=root/'.omega/wake-plane/inbox';p.mkdir(parents=True)
   (p/'a.json').write_text(json.dumps(trigger(trigger_id='a',dedupe_key='a')))
   (p/'b.json').write_text(json.dumps(trigger(trigger_id='b',dedupe_key='b')))
   wp=WakePlane(root,'SHADOW');result=wp.cycle();self.assertEqual(result['validated'],1)
   self.assertTrue(any(e.get('event')=='CROSS_SOURCE_DUPLICATE' for e in __import__('omega.wake_plane',fromlist=['history']).history(root)))
 def test_status_never_reports_dead_pid_running(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'.omega/wake-plane';p.mkdir(parents=True);(p/'heartbeat.json').write_text(json.dumps({'status':'RUNNING','pid':999999,'authority':'NONE'}))
   self.assertEqual(status(root)['status'],'STOPPED')
if __name__=='__main__':unittest.main()
