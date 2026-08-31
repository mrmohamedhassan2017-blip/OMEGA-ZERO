"""Passive, non-authoritative trigger validation and single-wake request plane."""
from __future__ import annotations
import hashlib,json,os,random,time,uuid,subprocess,sys
from xml.sax import saxutils as xmlutils
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
from pathlib import Path
from typing import Any,Callable

SPEC={
 'version':'LZC-V1.15','authority':'NONE','modes':['SHADOW','PASSIVE_PRODUCTION_VALIDATE_ONLY','PASSIVE_PRODUCTION'],
 'trigger_types':['V0_30_EVIDENCE','E2_INBOUND','INBOUND_INSTALL','ZRWVE_PASSIVE_INCIDENT_SUBMISSION','ZRWVE_REAL_INCIDENT_PACKET_RECEIVED','ZRWVE_PUBLIC_INCIDENT_CANDIDATE','PROVIDER_RECOVERY','OWNER_APPROVAL','INTERNAL_READY'],
 'required':['trigger_id','trigger_type','source','source_identity','source_event_id','canonical_event_fingerprint','observed_at','work_id','wake_condition','provenance_class','evidence_reference','authority_requirement','resource_requirement','external_effect','dedupe_key','expiry','verification_requirement'],
 'dedupe':'durable trigger_id+dedupe_key; at-most-one accepted wake','wake':'existing start_scheduled_task only after validation',
 'non_responsibilities':['execute work','approve','external write','host verification','claim completion'],
 'poll_seconds':60,'backoff_seconds':[60,120,300,900],'single_instance':True,
}
SPEC_HASH=hashlib.sha256(json.dumps(SPEC,sort_keys=True,separators=(',',':')).encode()).hexdigest()
TASK_NAME='OMEGA_ZERO_Wake_Plane'
ALLOWED=set(SPEC['trigger_types']); REQUIRED=set(SPEC['required'])

def now()->str:return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')
def _read(path:Path,default:Any):
 try:return json.loads(path.read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError):return default
def _atomic(path:Path,value:Any):
 path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp')
 tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8'); tmp.replace(path)
def sanitize(value:str)->str:
 for token in ('access_token','refresh_token','client_secret','authorization','cookie','api_key'):
  if token in value.lower(): return 'REDACTED_SENSITIVE_ERROR'
 return value[-500:]

@dataclass(frozen=True)
class Trigger:
 trigger_id:str; trigger_type:str; source:str; source_identity:str; observed_at:str; work_id:str
 source_event_id:str; canonical_event_fingerprint:str
 wake_condition:str; provenance_class:str; evidence_reference:str; authority_requirement:str
 resource_requirement:str; external_effect:bool; dedupe_key:str; expiry:str; verification_requirement:str

def parse_trigger(value:Any)->tuple[Trigger|None,str]:
 if not isinstance(value,dict) or not REQUIRED.issubset(value):return None,'INVALID_SCHEMA'
 if any(value.get(k) in (None,'',[],{}) for k in REQUIRED):return None,'MISSING_REQUIRED_FIELD'
 if value.get('trigger_type') not in ALLOWED:return None,'UNKNOWN_TRIGGER_TYPE'
 try:
  observed=datetime.fromisoformat(str(value['observed_at'])); expiry=datetime.fromisoformat(str(value['expiry']))
  if not observed.tzinfo or not expiry.tzinfo:return None,'NAIVE_TIMESTAMP'
  if expiry<=datetime.now(timezone.utc).astimezone():return None,'EXPIRED'
 except ValueError:return None,'INVALID_TIMESTAMP'
 if value['provenance_class'] not in {'INDEPENDENT_EXTERNAL','OWNER_SIGNED','HOST_VERIFIED','INTERNAL_DETERMINISTIC'}:return None,'INVALID_PROVENANCE'
 return Trigger(**{k:value[k] for k in Trigger.__dataclass_fields__}), 'VALID'

class WakePlane:
 def __init__(self,root:Path,mode='SHADOW',wake_fn:Callable[[Path],int]|None=None):
  if mode not in SPEC['modes']: raise ValueError(f'unsupported wake plane mode: {mode}')
  self.root=Path(root); self.base=self.root/'.omega/wake-plane'; self.mode=mode; self.wake_fn=wake_fn
  self.state_path=self.base/'state.json'; self.journal_path=self.base/'journal.jsonl'; self.heartbeat_path=self.base/'heartbeat.json'; self.lock_path=self.base/'lock.json'; self.inbox=self.base/'inbox'
  self.stop_path=self.base/'STOP'
  self.runtime_uuid=uuid.uuid4().hex; self.pid=os.getpid()
 def event(self,kind:str,**data):
  self.base.mkdir(parents=True,exist_ok=True)
  with self.journal_path.open('a',encoding='utf-8') as f:f.write(json.dumps({'timestamp':now(),'event':kind,**data},sort_keys=True)+'\n')
 def acquire(self):
  self.base.mkdir(parents=True,exist_ok=True)
  if self.lock_path.exists():
   old=_read(self.lock_path,{}); old_pid=int(old.get('pid',0) or 0)
   from .supervisor import Supervisor
   if not Supervisor._pid_alive(old_pid):self.event('STALE_LOCK_RECOVERED',old_pid=old_pid);self.lock_path.unlink(missing_ok=True)
  try:fd=os.open(self.lock_path,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
  except FileExistsError:raise RuntimeError('wake plane already locked')
  with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump({'pid':self.pid,'runtime_uuid':self.runtime_uuid,'spec_hash':SPEC_HASH},f)
 def release(self):self.lock_path.unlink(missing_ok=True)
 def heartbeat(self,status='RUNNING',**extra):
  state=_read(self.state_path,{'seen':{},'last_wake':None})
  _atomic(self.heartbeat_path,{'status':status,'pid':self.pid,'runtime_uuid':self.runtime_uuid,'last_heartbeat':now(),'mode':self.mode,'authority':'NONE','spec_hash':SPEC_HASH,'pending_candidates':extra.get('pending',0),'validated_pending':extra.get('validated',0),'last_wake_request':state.get('last_wake'),'resource_health':'BOUNDED'})
 def candidates(self)->list[tuple[Path,Any]]:
  self.inbox.mkdir(parents=True,exist_ok=True); items=[(p,_read(p,{})) for p in sorted(self.inbox.glob('*.json'))]
  from .wake_sources import poll_sources
  source_items,health=poll_sources(self.root);_atomic(self.base/'sources.json',health)
  items.extend((Path('source-'+str(i)+'.json'),value) for i,value in enumerate(source_items))
  return items
 def cycle(self,supervisor_live=False)->dict:
  state=_read(self.state_path,{'seen':{},'canonical_seen':{},'last_wake':None})
  state.setdefault('seen',{}); state.setdefault('canonical_seen',{})
  validated=[]; rejected=[]
  for path,value in self.candidates():
   trigger,reason=parse_trigger(value)
   if not trigger: rejected.append({'file':path.name,'reason':reason}); self.event('TRIGGER_REJECTED',file=path.name,reason=reason); continue
   key=trigger.trigger_id+'|'+trigger.dedupe_key
   canonical_key=trigger.canonical_event_fingerprint
   if key in state['seen']:
    self.event('TRIGGER_DUPLICATE',trigger_id=trigger.trigger_id);continue
   if canonical_key in state['canonical_seen']:
    self.event('CROSS_SOURCE_DUPLICATE',trigger_id=trigger.trigger_id,canonical_event_fingerprint=canonical_key)
    state['seen'][key]={'first_seen':now(),'validated_at':now(),'result':'CROSS_SOURCE_DUPLICATE','trigger':asdict(trigger)}
    continue
   current=(self.root/'NEXT_TASK.md').read_text(encoding='utf-8',errors='replace') if (self.root/'NEXT_TASK.md').exists() else ''
   result='VALIDATED' if trigger.work_id.lower() in current.lower() else 'PENDING_NONCURRENT_WORK'
   state['seen'][key]={'first_seen':now(),'validated_at':now(),'result':result,'trigger':asdict(trigger)}
   state['canonical_seen'][canonical_key]=key
   if result=='VALIDATED':validated.append(trigger);self.event('VALIDATED_TRIGGER',trigger_id=trigger.trigger_id,work_id=trigger.work_id)
   else:self.event('TRIGGER_PARKED_NONCURRENT',trigger_id=trigger.trigger_id,work_id=trigger.work_id)
  wakes=0
  if validated:
   if self.mode=='SHADOW':
    for t in validated:state['seen'][t.trigger_id+'|'+t.dedupe_key]['result']='WOULD_WAKE';self.event('WOULD_WAKE',trigger_id=t.trigger_id)
   elif self.mode=='PASSIVE_PRODUCTION_VALIDATE_ONLY':
    for t in validated:state['seen'][t.trigger_id+'|'+t.dedupe_key]['result']='VALIDATED_NO_WAKE';self.event('VALIDATED_NO_WAKE',trigger_id=t.trigger_id)
   elif not supervisor_live and self.wake_fn:
    chosen=validated[0]
    try:
     pid=self.wake_fn(self.root); wakes=1; state['last_wake']={'trigger_id':chosen.trigger_id,'requested_at':now(),'pid':pid}
     state['seen'][chosen.trigger_id+'|'+chosen.dedupe_key].update({'result':'WAKE_REQUESTED','wake_requested_at':now(),'linked_runtime_pid':pid});self.event('WAKE_REQUEST',trigger_id=chosen.trigger_id,pid=pid)
    except Exception as exc:self.event('WAKE_REQUEST_FAILED',trigger_id=chosen.trigger_id,error=sanitize(str(exc)))
  _atomic(self.state_path,state);self.heartbeat(pending=len(validated),validated=len(validated))
  return {'candidates':len(validated)+len(rejected),'validated':len(validated),'rejected':rejected,'wake_requests':wakes,'mode':self.mode,'authority':'NONE'}
 def run(self,interval=60):
  self.acquire()
  try:
   self.stop_path.unlink(missing_ok=True)
   while not self.stop_path.exists():self.cycle();time.sleep(max(5,interval+random.uniform(-min(5,interval/10),min(5,interval/10))))
  finally:self.heartbeat('STOPPED');self.release()

def status(root:Path)->dict:
 value=_read(Path(root)/'.omega/wake-plane/heartbeat.json',{'status':'STOPPED','authority':'NONE','spec_hash':SPEC_HASH})
 from .supervisor import Supervisor
 alive=Supervisor._pid_alive(int(value.get('pid',0) or 0));value['process_alive']=alive
 if not alive and value.get('status')=='RUNNING':value['status']='STOPPED'
 value['sources']=_read(Path(root)/'.omega/wake-plane/sources.json',{})
 try:
  from .wake_provenance import evaluator_summary
  value['v0_30_independent_evaluator_count']=evaluator_summary(Path(root))['independent_evaluator_count']
 except Exception:
  value['v0_30_independent_evaluator_count']=0
 value['github_inbound_checkpoint']=_read(Path(root)/'.omega/wake-provenance/github_checkpoint.json',{})
 value['gmail_checkpoint']=_read(Path(root)/'.omega/avf/e2_01_monitor_checkpoint.json',{})
 value['last_validated_real_event']=_read(Path(root)/'.omega/wake-plane/state.json',{}).get('last_validated_real_event')
 return value
def history(root:Path,limit=20)->list:
 path=Path(root)/'.omega/wake-plane/journal.jsonl'
 if not path.exists():return []
 out=[]
 for line in path.read_text(encoding='utf-8',errors='replace').splitlines()[-limit:]:
  try:out.append(json.loads(line))
  except json.JSONDecodeError:pass
 return out

def install_shadow(root:Path,mode='SHADOW')->None:
 if os.name!='nt':raise RuntimeError('Windows Task Scheduler required')
 root=Path(root).resolve();base=root/'.omega/wake-plane';base.mkdir(parents=True,exist_ok=True)
 user=subprocess.run(['whoami'],capture_output=True,text=True,check=True,timeout=5).stdout.strip();esc=xmlutils.escape
 xml=f'''<?xml version="1.0" encoding="UTF-16"?><Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"><RegistrationInfo><Description>OMEGA ZERO passive Wake Plane {esc(mode)}</Description></RegistrationInfo><Triggers><LogonTrigger><Enabled>true</Enabled><UserId>{esc(user)}</UserId></LogonTrigger></Triggers><Principals><Principal id="Author"><UserId>{esc(user)}</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals><Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><StartWhenAvailable>true</StartWhenAvailable><AllowStartOnDemand>true</AllowStartOnDemand><Enabled>true</Enabled><Hidden>true</Hidden><ExecutionTimeLimit>PT0S</ExecutionTimeLimit><RestartOnFailure><Interval>PT1M</Interval><Count>5</Count></RestartOnFailure></Settings><Actions Context="Author"><Exec><Command>{esc(str(Path(sys.executable).resolve()))}</Command><Arguments>-m omega.cli wake-plane-run --mode {esc(mode)}</Arguments><WorkingDirectory>{esc(str(root))}</WorkingDirectory></Exec></Actions></Task>'''
 path=base/'scheduled-task.xml';path.write_text(xml,encoding='utf-16')
 cp=subprocess.run(['schtasks','/Create','/TN',TASK_NAME,'/XML',str(path),'/F'],capture_output=True,text=True,timeout=15)
 if cp.returncode:raise RuntimeError(sanitize(cp.stderr or cp.stdout))
def start_task():
 cp=subprocess.run(['schtasks','/Run','/TN',TASK_NAME],capture_output=True,text=True,timeout=15)
 if cp.returncode:raise RuntimeError(sanitize(cp.stderr or cp.stdout))
def stop_task(root:Path):
 base=Path(root)/'.omega/wake-plane';base.mkdir(parents=True,exist_ok=True);(base/'STOP').write_text(now(),encoding='utf-8')
def uninstall_task():
 cp=subprocess.run(['schtasks','/Delete','/TN',TASK_NAME,'/F'],capture_output=True,text=True,timeout=15)
 if cp.returncode:raise RuntimeError(sanitize(cp.stderr or cp.stdout))
