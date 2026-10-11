"""模型协议替身：只验证编排，不作为DeepSeek质量评测。"""
import copy
import json
from unittest.mock import patch
import pytest
from estate_agent.runtime import run
from estate_agent.intent import rule_intent
from estate_agent.auth import identity
from estate_agent.business import DemoError
from estate_agent.data import initialize

class ScriptedModel:
    model='scripted-test'
    def __init__(self,actions,bad_narrative=False):
        self.actions=iter(actions);self.messages=[];self.bad_narrative=bad_narrative;self.narratives=0
    def stats(self): return {'calls':len(self.messages),'total_tokens':0,'usage':[]}
    def structured(self,instruction,data,schema):
        title=schema.get('title')
        if title=='Intent': return rule_intent(data['question'],data.get('context'),identity('chaoyang'))
        if title=='SQLPlan': return {'metric':data['task']['metric']}
        if title=='Narrative':
            self.narratives+=1
            return {'fact_ids':data['choices']['fact_ids'],'recommendation_ids':['INVENTED'] if self.bad_narrative and self.narratives==1 else data['choices']['recommendation_ids'],'hypothesis_ids':[],'confidence':.9}
        return {'query':data['query']}
    def decide(self,messages):
        self.messages.append(copy.deepcopy(messages));name,args=next(self.actions)
        return {'tool_calls':[{'id':'call_'+str(len(self.messages)),'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]}

ACTIONS=[('retrieve_schema',{}),('query_metrics',{}),('calculate_metrics',{}),('analyze_funnel',{'store_id':'S01'}),('retrieve_knowledge',{'query':'带看转成交率下降 跟进规范'}),('generate_report',{})]

def execute(tmp_path,actions=ACTIONS,**kwargs):
    return run('朝阳最近7天带看转成交率下降分析',mode='llm',client=ScriptedModel(actions,**kwargs),backend='bm25',directory=tmp_path,user=identity('chaoyang'))

def test_model_loop(tmp_path):
    model=ScriptedModel(ACTIONS)
    r=run('朝阳最近7天带看转成交率下降分析',mode='llm',client=model,backend='bm25',directory=tmp_path,user=identity('chaoyang'))
    assert r['status']=='completed'
    assert model.messages[1][-1]['role']=='tool'
    assert 'SQL-01' in json.dumps(model.messages[2],ensure_ascii=False)

def test_repeat(tmp_path):
    r=execute(tmp_path,[('retrieve_schema',{}),('retrieve_schema',{})])
    assert r['error']['code']=='REPEATED_CALL'

def test_bad_tool_schema(tmp_path):
    r=execute(tmp_path,[('analyze_funnel',{'sql':'DROP'})])
    assert r['error']['code']=='MODEL_PROTOCOL_ERROR'

def test_invalid_sequence_replans(tmp_path):
    r=execute(tmp_path,[('analyze_funnel',{'store_id':'S02'})]+ACTIONS)
    assert r['status']=='completed'
    assert any(t['status']=='error' for t in r['trace'])

def test_refinement_once(tmp_path):
    r=execute(tmp_path,bad_narrative=True)
    assert r['status']=='completed' and r['refinement_count']==1
    assert sum(t['step']=='validate' for t in r['trace'])==2

def test_budget_limit(tmp_path):
    from estate_agent.settings import settings
    values=settings();values['max_tool_calls']=2
    with patch('estate_agent.runtime.settings',return_value=values): r=execute(tmp_path)
    assert r['error']['code']=='STEP_LIMIT'
