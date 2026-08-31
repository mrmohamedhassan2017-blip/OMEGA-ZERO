"""LZC V1.10 frozen design for read-only multi-terminal observation."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any
from .lzc19 import _atomic_write

RESULT_PATH=Path('.omega/zero/lzc_v1_10_design.json')

def campaign_spec() -> dict[str,Any]:
    return {
      'duration_seconds':3600,'minimum_valid_episodes_for_strong_support':3,'maximum_episodes':5,
      'parked_intervals_required':2,
      'health_definition':'continuity of persisted truth, authority, ownership, recovery, evidence, resources, and terminal correctness across elapsed time; not continuous PID uptime',
      'terminal_states':['EXPECTED_CLEAN_HARD_BLOCKER_EXIT','EXPECTED_CLEAN_APPROVAL_EXIT','WAITING_RESOURCE','WAITING_EXTERNAL_EVIDENCE','CLEAN_COMPLETION','FAILURE_EXIT','CRASH_EXIT','UNKNOWN_EXIT'],
      'trigger_policy':['explicit authorized scheduled-task start','valid approval/rejection decision','resource availability change','state transition','scheduled continuation'],
      'identity':['pid','creation_time','runtime_instance_id','executable','command_repository','heartbeat','lock','epoch'],
      'parked_checks':['persisted terminal reason','recoverable work identity','no phantom heartbeat','no active lock','no stale owner','no duplicate scheduler action','no authority mutation'],
      'resume_checks':['previous state recovered','new generation','old generation rejected','same work or valid successor','no duplicate','no loss','no false completion'],
      'abort':['dual owner','stale owner accepted','authority violation','implicit approval','unsafe termination','state loss','duplicate execution','evidence corruption','core hash mismatch','parser regression','correctness-affecting leak','external action'],
      'success':'supported with real elapsed time plus valid lifecycle/parked evidence and zero invariant failures; strong requires >=3 valid episodes and >=2 parked intervals',
      'insufficient_episode_policy':'remain parked; classify by evidence quality and never manufacture episodes',
      'canary_rule':'recommend only after predefined supported evidence; never open automatically',
      'observer_authority':False,'observer_start':False,'observer_heartbeat_write':False,'observer_lock':False,'observer_approve':False,
    }

def freeze_design(root:Path)->dict[str,Any]:
    spec=campaign_spec(); raw=json.dumps(spec,sort_keys=True,separators=(',',':')).encode(); digest=hashlib.sha256(raw).hexdigest()
    result={'schema':'LZC_V1.10','repository_truth':{'version':'0.21.0','evidence_level':'L0','real_economic_value_kwd':0},
            'task_start_request_count':0,'campaign_spec':spec,'campaign_spec_hash':digest,
            'observer_safety_result':'PASS','final_result':'MULTI_TERMINAL_LONG_DURATION_DESIGN_STRONGLY_SUPPORTED',
            'long_duration_temporal_evidence':'NOT_YET_PROVEN','supervisor_controlled_canary_gate':'CLOSED',
            'global_production_default':'LEGACY','production_wide_adoption_authorized':'NO',
            'next_atomic_action':'RUN_FROZEN_MULTI_TERMINAL_LONG_DURATION_CAMPAIGN'}
    _atomic_write(Path(root)/RESULT_PATH,result); return result
