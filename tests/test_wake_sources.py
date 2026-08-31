import json,tempfile,unittest
from pathlib import Path
from omega.wake_sources import poll_sources
from omega.wake_provenance import (GithubResponse, TrustedSourceObservation,
                                    digest, ingest_v030_submission,
                                    evaluator_summary)

class WakeSourceTests(unittest.TestCase):
 def base(self,root):
  (root/'.omega/avf').mkdir(parents=True);(root/'.omega/runtime').mkdir(parents=True);(root/'NEXT_TASK.md').write_text('V0.30 External Evaluator Evidence Collection')
 def test_e2_metadata_normalizes_without_body(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.base(root);(root/'.omega/avf/e2_01_reply_events.jsonl').write_text(json.dumps({'gmail_message_id':'m1','classification':'NEGATIVE','raw':'secret body'})+'\n')
   events,health=poll_sources(root);self.assertEqual(len(events),1);self.assertNotIn('secret body',json.dumps(events));self.assertTrue(health['gmail_e2']['production_ready'])
 def test_v030_fails_closed_without_independence_provenance(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.base(root);events,health=poll_sources(root);self.assertEqual(health['v0_30_evaluator']['health'],'BLOCKED');self.assertFalse(health['v0_30_evaluator']['production_ready'])
 def test_inactive_provider_is_dormant(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.base(root);(root/'.omega/runtime/provider_checkpoint.json').write_text(json.dumps({'status':'WAITING_RESOURCE','task_id':'x','branch':'other'}));_,h=poll_sources(root);self.assertEqual(h['provider_recovery']['health'],'DORMANT')
 def test_malformed_approval_never_normalizes(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.base(root);p=root/'.omega/runtime/approval_decisions';p.mkdir();(p/'bad.json').write_text('{}');events,h=poll_sources(root);self.assertEqual(events,[]);self.assertEqual(h['owner_approval']['candidate_count'],0)
 def test_ready_queue_routes_exact_work(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.base(root);(root/'.omega/runtime/work_queue.jsonl').write_text(json.dumps({'work_id':'V0.30','state':'READY','authority_valid':True,'resources_available':True})+'\n');events,h=poll_sources(root);self.assertEqual(events[0]['work_id'],'V0.30');self.assertTrue(h['internal_queue']['production_ready'])
 def test_github_public_external_event_is_journaled(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.base(root);cfg=root/'.omega/wake-provenance';cfg.mkdir(parents=True)
   (cfg/'config.json').write_text(json.dumps({'github':{'enabled':True,'repository':'mrmohamedhassan2017-blip/agent-runtime-audit','owner_login':'mrmohamedhassan2017-blip'}}))
   def fake(url,etag):
    if url.endswith('/agent-runtime-audit'):
     return GithubResponse(200,{'etag':'repo-1'}, {'full_name':'mrmohamedhassan2017-blip/agent-runtime-audit','owner':{'login':'mrmohamedhassan2017-blip','id':313155572}})
    return GithubResponse(200,{'etag':'issues-1','x-ratelimit-remaining':'59'},[{'id':77,'number':1,'title':'repro','body':'details','created_at':'2026-08-29T00:00:00Z','updated_at':'2026-08-29T00:00:00Z','html_url':'https://github.com/mrmohamedhassan2017-blip/agent-runtime-audit/issues/1','user':{'login':'external-dev','id':999,'type':'User'}}])
   events,health=poll_sources(root,github_fetcher=fake,force_github=True)
   self.assertEqual(len(events),1);self.assertEqual(events[0]['trigger_type'],'INBOUND_INSTALL')
   self.assertEqual(health['github_inbound']['health'],'ACTIVE');self.assertTrue(health['github_inbound']['production_ready'])
   self.assertEqual(health['github_inbound']['candidate_count'],1)
 def test_passive_issue_form_routes_qualified_stage1_without_inbound_contamination(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.base(root);cfg=root/'.omega/wake-provenance';cfg.mkdir(parents=True)
   (cfg/'config.json').write_text(json.dumps({'github':{'enabled':True,'repository':'mrmohamedhassan2017-blip/agent-runtime-audit','owner_login':'mrmohamedhassan2017-blip','passive_incident_intake':{'enabled':True,'read_only':True}}}))
   body='''### Firsthand operational experience
I_HAVE_FIRSTHAND_EXPERIENCE
### Stack / orchestrator
sanitized workflow engine
### Incident class
AMBIGUOUS_PERSISTED_STATE
### Real incident exists
YES
### Incident relevance summary
A retry exposed conflicting checkpoint and downstream-effect state.
### Sanitized reconstruction
YES
### Sanitization declaration
- [x] I_WILL_NOT_SHARE_RESTRICTED_DATA
### Public attribution preference
PSEUDONYMOUS_IN_REPORT
### Stage 2 incident packet (optional JSON)
'''
   def fake(url,etag):
    if url.endswith('/agent-runtime-audit'): return GithubResponse(200,{}, {'full_name':'mrmohamedhassan2017-blip/agent-runtime-audit','owner':{'login':'mrmohamedhassan2017-blip','id':313155572}})
    return GithubResponse(200,{},[{'id':88,'number':8,'title':'[incident-intake] sanitized case','body':body,'created_at':'2026-08-29T00:00:00Z','updated_at':'2026-08-29T00:01:00Z','html_url':'https://github.com/mrmohamedhassan2017-blip/agent-runtime-audit/issues/8','user':{'login':'external-operator','id':888,'type':'User'}}])
   first,health=poll_sources(root,github_fetcher=fake,force_github=True)
   second,_=poll_sources(root,github_fetcher=fake,force_github=True)
   self.assertEqual([e['trigger_type'] for e in first],['ZRWVE_PASSIVE_INCIDENT_SUBMISSION'])
   self.assertEqual(second,[]);self.assertFalse(health['github_inbound']['real_trigger_present'])
   self.assertTrue(health['zrwve_passive_intake']['production_ready']);self.assertEqual(health['zrwve_passive_intake']['stage1_qualified_count'],1)
   records,_=__import__('omega.wake_provenance',fromlist=['read_chain']).read_chain(cfg/'zrwve_passive_incident_intake.jsonl')
   self.assertEqual(len(records),1);self.assertFalse(records[0]['raw_content_stored']);self.assertNotIn('checkpoint and downstream',json.dumps(records).lower())
 def test_passive_route_remains_ready_on_cached_poll(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.base(root);cfg=root/'.omega/wake-provenance';cfg.mkdir(parents=True)
   (cfg/'config.json').write_text(json.dumps({'github':{'enabled':True,'repository':'mrmohamedhassan2017-blip/agent-runtime-audit','owner_login':'mrmohamedhassan2017-blip','passive_incident_intake':{'enabled':True,'read_only':True}}}))
   def fake(url,etag):
    if url.endswith('/agent-runtime-audit'): return GithubResponse(200,{}, {'full_name':'mrmohamedhassan2017-blip/agent-runtime-audit','owner':{'login':'mrmohamedhassan2017-blip','id':313155572}})
    return GithubResponse(200,{},[])
   poll_sources(root,github_fetcher=fake,force_github=True)
   events,health=poll_sources(root,github_fetcher=lambda *_: self.fail('cached poll performed network'))
   self.assertEqual(events,[]);self.assertTrue(health['zrwve_passive_intake']['production_ready'])
   self.assertTrue(health['zrwve_passive_intake']['route_registered'])
 def test_passive_issue_form_secret_is_rejected_without_wake_or_raw_storage(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.base(root);cfg=root/'.omega/wake-provenance';cfg.mkdir(parents=True)
   (cfg/'config.json').write_text(json.dumps({'github':{'enabled':True,'repository':'mrmohamedhassan2017-blip/agent-runtime-audit','owner_login':'mrmohamedhassan2017-blip','passive_incident_intake':{'enabled':True,'read_only':True}}}))
   fake_token='ghp_'+'1'*30
   body=f'''### Firsthand operational experience
I_HAVE_FIRSTHAND_EXPERIENCE
### Stack / orchestrator
Airflow
### Incident class
AMBIGUOUS_PERSISTED_STATE
### Real incident exists
YES
### Incident relevance summary
{fake_token} leaked into the report.
### Sanitized reconstruction
YES
### Sanitization declaration
- [x] I_WILL_NOT_SHARE_RESTRICTED_DATA
### Public attribution preference
PUBLIC_GITHUB_IDENTITY
### Stage 2 incident packet (optional JSON)
'''
   def fake(url,etag):
    if url.endswith('/agent-runtime-audit'): return GithubResponse(200,{}, {'full_name':'mrmohamedhassan2017-blip/agent-runtime-audit','owner':{'login':'mrmohamedhassan2017-blip','id':313155572}})
    return GithubResponse(200,{},[{'id':89,'number':9,'title':'[incident-intake] unsafe','body':body,'created_at':'2026-08-29T00:00:00Z','updated_at':'2026-08-29T00:01:00Z','html_url':'https://github.com/mrmohamedhassan2017-blip/agent-runtime-audit/issues/9','user':{'login':'external-operator','id':889,'type':'User'}}])
   events,health=poll_sources(root,github_fetcher=fake,force_github=True)
   self.assertEqual(events,[]);self.assertEqual(health['zrwve_passive_intake']['stage1_qualified_count'],0)
   text=(cfg/'zrwve_passive_incident_intake.jsonl').read_text()
   self.assertNotIn('ghp_',text);self.assertIn('REJECTED_SECRET_OR_PRIVATE_CONTENT',text)
 def test_github_owner_and_bot_are_negative_evidence_only(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.base(root);cfg=root/'.omega/wake-provenance';cfg.mkdir(parents=True)
   (cfg/'config.json').write_text(json.dumps({'github':{'enabled':True,'repository':'mrmohamedhassan2017-blip/agent-runtime-audit','owner_login':'mrmohamedhassan2017-blip'}}))
   def fake(url,etag):
    if url.endswith('/agent-runtime-audit'):
     return GithubResponse(200,{}, {'full_name':'mrmohamedhassan2017-blip/agent-runtime-audit','owner':{'login':'mrmohamedhassan2017-blip','id':313155572}})
    return GithubResponse(200,{},[
      {'id':1,'number':1,'title':'owner','body':'','created_at':'2026-08-29T00:00:00Z','html_url':'https://github.com/mrmohamedhassan2017-blip/agent-runtime-audit/issues/1','user':{'login':'mrmohamedhassan2017-blip','id':313155572,'type':'User'}},
      {'id':2,'number':2,'title':'bot','body':'','created_at':'2026-08-29T00:00:01Z','html_url':'https://github.com/mrmohamedhassan2017-blip/agent-runtime-audit/issues/2','user':{'login':'dependabot[bot]','id':2,'type':'Bot'}}])
   events,health=poll_sources(root,github_fetcher=fake,force_github=True)
   self.assertEqual(events,[]);self.assertEqual(health['github_inbound']['candidate_count'],2)
   records,_=__import__('omega.wake_provenance',fromlist=['read_chain']).read_chain(cfg/'github_inbound.jsonl')
   self.assertEqual({r['independence_status'] for r in records},{'PROVEN_NON_INDEPENDENT'})
 def test_github_restart_dedupe(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.base(root);cfg=root/'.omega/wake-provenance';cfg.mkdir(parents=True)
   (cfg/'config.json').write_text(json.dumps({'github':{'enabled':True,'repository':'mrmohamedhassan2017-blip/agent-runtime-audit','owner_login':'mrmohamedhassan2017-blip'}}))
   def fake(url,etag):
    if url.endswith('/agent-runtime-audit'): return GithubResponse(200,{}, {'full_name':'mrmohamedhassan2017-blip/agent-runtime-audit','owner':{'login':'mrmohamedhassan2017-blip','id':313155572}})
    return GithubResponse(200,{},[{'id':7,'number':7,'title':'x','body':'','created_at':'2026-08-29T00:00:00Z','html_url':'https://github.com/mrmohamedhassan2017-blip/agent-runtime-audit/issues/7','user':{'login':'external','id':7,'type':'User'}}])
   first,_=poll_sources(root,github_fetcher=fake,force_github=True);second,_=poll_sources(root,github_fetcher=fake,force_github=True)
   self.assertEqual(len(first),1);self.assertEqual(len(second),0)
 def test_github_rate_limit_is_degraded_and_checkpointed(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.base(root);cfg=root/'.omega/wake-provenance';cfg.mkdir(parents=True)
   (cfg/'config.json').write_text(json.dumps({'github':{'enabled':True,'repository':'mrmohamedhassan2017-blip/agent-runtime-audit','owner_login':'mrmohamedhassan2017-blip'}}))
   def fake(url,etag): return GithubResponse(429,{'x-ratelimit-reset':'999'},None)
   events,health=poll_sources(root,github_fetcher=fake,force_github=True)
   self.assertEqual(events,[]);self.assertEqual(health['github_inbound']['health'],'DEGRADED');self.assertEqual(health['github_inbound']['last_error_class'],'RATE_LIMITED')
   self.assertTrue((cfg/'github_checkpoint.json').exists())
 def test_reality_watch_uses_existing_source_cycle_and_emits_structured_trigger(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.base(root);cfg=root/'.omega/wake-provenance';cfg.mkdir(parents=True)
   (cfg/'config.json').write_text(json.dumps({'reality_watch':{'enabled':True,'read_only':True,'target':'T2','mode':'ACTIVE_READ_ONLY','external_write':False}}))
   def fake(url,etag):
    project='apache/airflow' if 'apache/airflow' in url else 'PrefectHQ/prefect'
    return GithubResponse(200,{},[{'id':71,'number':7,'title':'Retry after partial downstream commit duplicates effect','body':'A failed workflow was retried after a partial downstream side effect. The task state remained running and the operator could not tell whether the transaction committed before manually resuming the flow.','created_at':'2026-08-29T00:00:00Z','updated_at':'2026-08-29T00:01:00Z','html_url':f'https://github.com/{project}/issues/7','user':{'login':'external-operator','id':771,'type':'User'}}])
   events,health=poll_sources(root,reality_fetcher=fake,force_reality=True)
   public=[event for event in events if event['trigger_type']=='ZRWVE_PUBLIC_INCIDENT_CANDIDATE']
   self.assertEqual(len(public),1);self.assertEqual(public[0]['external_effect'],False)
   self.assertEqual(health['zrwve_public_reality_watch']['health'],'ACTIVE')
   self.assertEqual(health['zrwve_public_reality_watch']['external_writes'],0)
   self.assertNotIn('partial downstream',json.dumps(public).lower())
 def test_v030_raw_assertion_is_rejected_and_trusted_unknown_stays_unknown(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.base(root)
   payload={'format':'omega.blind-evaluation-result','format_version':1,'submission_id':'s1','evaluator_session_id':'session-1','evaluation_id':'e1'}
   payload['payload_sha256']=digest({k:v for k,v in payload.items()})
   with self.assertRaises(TypeError):ingest_v030_submission(root,payload,{'source_verified':True})
   obs=TrustedSourceObservation('GITHUB_PUBLIC_API','display','', 'User','https://x','x','2026-08-29T00:00:00Z',None,None,True,'test','fp')
   rec=ingest_v030_submission(root,payload,obs)
   self.assertEqual(rec['independence_status'],'UNKNOWN');self.assertEqual(evaluator_summary(root)['independent_evaluator_count'],0)
 def test_v030_counts_two_verified_actor_identities_only(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.base(root)
   for index,actor in enumerate(('actor-a','actor-b'),1):
    payload={'format':'omega.blind-evaluation-result','format_version':1,'submission_id':f's{index}','evaluator_session_id':f'session-{index}','evaluation_id':f'e{index}'}
    payload['payload_sha256']=digest({k:v for k,v in payload.items()})
    obs=TrustedSourceObservation('GITHUB_PUBLIC_API',actor,str(index),'User',f'https://github.com/ext/repo/issues/{index}',f'event-{index}','2026-08-29T00:00:00Z',False,False,True,'immutable actor id',f'fp-{index}')
    ingest_v030_submission(root,payload,obs)
   self.assertEqual(evaluator_summary(root)['independent_evaluator_count'],2)
if __name__=='__main__':unittest.main()
