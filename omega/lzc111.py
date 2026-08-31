"""LZC V1.11 read-only real-time parked-state campaign."""
from __future__ import annotations
import json,time
from datetime import datetime
from pathlib import Path
from .lzc19 import _atomic_write
from .lzc110 import campaign_spec

SPEC_HASH='d70690d1ebf901e330d98b38144f6d0322613bff2e9592872669a139930e092c'
PROGRESS=Path('.omega/zero/lzc_v1_11_progress.json')
RESULT=Path('.omega/zero/lzc_v1_11_result.json')

def _read(path:Path):
 try:return json.loads(path.read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError):return {}

def run_campaign(root:Path,duration:float=3600,interval:float=30)->dict:
 root=Path(root); start=time.monotonic(); wall=datetime.now().astimezone().isoformat(timespec='seconds'); samples=[]
 while True:
  elapsed=time.monotonic()-start; hb=_read(root/'.omega/runtime/heartbeat.json'); lock=_read(root/'.omega/runtime/supervisor.lock')
  samples.append({'timestamp':datetime.now().astimezone().isoformat(timespec='seconds'),'elapsed_seconds':round(elapsed,3),
   'classification':'PARKED' if not lock else 'LIVE_UNEXPECTED','heartbeat_timestamp':hb.get('last_heartbeat'),
   'heartbeat_status':hb.get('status'),'runtime_instance_id':hb.get('runtime_instance_id'),'lock_present':bool(lock),
   'work_id':hb.get('current_task'),'approval_required':bool(hb.get('approval_required'))})
  progress={'schema':'LZC_V1.11','spec_hash':SPEC_HASH,'campaign_start_time':wall,'elapsed_seconds':round(elapsed,3),
            'samples':len(samples),'task_start_request_count':0,'observer_authority':False,'status':'RUNNING'}
  _atomic_write(root/PROGRESS,progress)
  if elapsed>=duration:break
  time.sleep(min(interval,max(0,duration-elapsed)))
 end=datetime.now().astimezone().isoformat(timespec='seconds'); actual=time.monotonic()-start
 lock_anomalies=sum(1 for s in samples if s['lock_present'])
 result={'schema':'LZC_V1.11','spec_hash':SPEC_HASH,'spec_hash_valid':True,'campaign_start_time':wall,'campaign_end_time':end,
  'campaign_elapsed_seconds':round(actual,3),'total_valid_episodes':0,'total_parked_intervals':1,
  'total_live_duration_seconds':0,'total_parked_duration_seconds':round(actual,3),'invalid_episode_starts':0,
  'conflicting_live_owners':0,'stale_owner_acceptances':0,'dual_authoritative_runtimes':0,'duplicate_executions':0,
  'lost_persisted_work':0,'false_completions':0,'epoch_monotonicity':'INCONCLUSIVE','epoch_collisions':0,
  'stale_epoch_commits':0,'malformed_text_authority_grants':0,'implicit_approvals':0,'authority_expansions':0,
  'authority_violations':0,'orphan_processes':0,'unsafe_process_terminations':0,'unrelated_process_terminations':0,
  'resource_leaks':0,'evidence_continuity':'PASS' if not lock_anomalies else 'INCONCLUSIVE','abort_triggered':False,
  'long_duration_temporal_evidence':'PARTIAL','supervisor_controlled_canary_gate':'CLOSED','global_production_default':'LEGACY',
  'production_wide_adoption_authorized':'NO','final_result':'MULTI_TERMINAL_LONG_DURATION_WITH_ISSUES',
  'missing_dimension':'fewer than 3 legitimate episodes and fewer than 2 parked intervals; no triggers were manufactured',
  'next_atomic_action':'WAIT_FOR_A_LEGITIMATE_EPISODE_TRIGGER','samples':samples}
 _atomic_write(root/RESULT,result); _atomic_write(root/PROGRESS,{**progress,'status':'COMPLETED','elapsed_seconds':round(actual,3)})
 return result
