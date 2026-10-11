"""分层可复现评测。500条合成回归项，不冒充真实用户独立Gold集。"""
import argparse
import copy
import json
import math
import sqlite3
import statistics
import tempfile
import time
from pathlib import Path
from estate_agent.auth import identity
from estate_agent.business import DemoError
from estate_agent.data import ROOT, DB, initialize
from estate_agent.intent import understand
from estate_agent.retrieval import search_knowledge
from estate_agent.report import verify_report
from estate_agent.runtime import run
from estate_agent.sql_tools import query_metrics, calculate_metrics, METRICS, guard_sql


def generated_cases():
    cases=[]
    for region in ['朝阳','海淀']:
        for metric, phrase in [('viewing_to_deal','带看转成交率'),('effective_viewing_rate','有效带看占比'),('followup_rate','24小时跟进率')]:
            for days in range(1,21):
                cases.append({'question':f'分析{region}最近{days}天{phrase}变化','region':region,'metric':metric,'days':days})
    return cases


def retrieval_eval(backend):
    cases=json.loads((ROOT/'eval_cases.json').read_text(encoding='utf-8'))
    rows=[]
    for c in cases:
        start=time.perf_counter()
        r=search_knowledge(c['query'],backend=backend,use_cache=False)
        ids=[d['id'] for d in r['evidence']][:5]
        candidates=next((x['rank'] for x in r['stages'] if x['name']=='RRF候选池'),[])
        parents={x[0].rsplit('-C',1)[0] for x in candidates[:20]}
        gold=set(c['gold_ids']);hits=[i for i,x in enumerate(ids,1) if x in gold]
        dcg=sum(1/math.log2(i+1) for i in hits)
        ideal=sum(1/math.log2(i+1) for i in range(1,min(5,len(gold))+1))
        rows.append({**c,'returned':ids,'recall_at_20':len(gold&parents)/len(gold),'recall_at_5':len(gold&set(ids))/len(gold),'mrr_at_5':1/min(hits) if hits else 0,'ndcg_at_5':dcg/ideal,'latency_ms':(time.perf_counter()-start)*1000})
    summary={k:statistics.mean(r[k] for r in rows) for k in ['recall_at_20','recall_at_5','mrr_at_5','ndcg_at_5','latency_ms']}
    return {'cases':rows,'metrics':summary}


def layers():
    user=identity('director');cases=generated_cases();details=[]
    with tempfile.TemporaryDirectory() as folder:
        for i,c in enumerate(cases):
            t=understand(c['question'],user=user)
            details.append({'layer':'intent','case':i,'passed':all(t[k]==c[k] for k in ['metric','region','days'])})
            q=calculate_metrics(query_metrics(t,user))
            num,den,_=METRICS[c['metric']]
            with sqlite3.connect(DB) as con:
                gold=dict(con.execute(f'SELECT d.store_id,1.0*SUM(d.{num})/NULLIF(SUM(d.{den}),0) FROM daily_metrics d JOIN stores s ON s.store_id=d.store_id WHERE s.region=? AND day BETWEEN ? AND ? GROUP BY d.store_id',(t['region'],t['start'],t['end'])))
            details.append({'layer':'sql','case':i,'passed':all(abs(row['current_rate']-gold[row['store_id']])<1e-10 for row in q['rows'])})
            start=time.perf_counter()
            r=run(c['question'],user=user,directory=folder,backend='bm25',strategy='multi' if i%2 else 'single')
            expected=['retrieve_schema','query_metrics','calculate_metrics']
            if q['rows'][0]['delta_pp']<0: expected+=['analyze_funnel']
            expected+=['retrieve_knowledge','generate_report']
            selected=[s['output']['name'] for s in r['trace'] if s['step']=='agent_node' and 'name' in s['output']]
            details.append({'layer':'task','case':i,'passed':r['status']=='completed' and r.get('verification',{}).get('passed',False),'tool_sequence_correct':selected==expected,'repeated_calls':len(selected)-len(set(selected)),'tool_calls':len(selected),'latency_ms':(time.perf_counter()-start)*1000})
            if i%20==0: print(f'Layered eval: {i+1}/120',flush=True)
        baseline=run('朝阳最近7天带看转成交率下降分析',directory=folder,backend='bm25')
        for i in range(80):
            report=copy.deepcopy(baseline['report'])
            kind=i%4
            if kind==0: report['facts'][i%len(report['facts'])]['current_rate']+=.001*(i+1)
            elif kind==1: report['knowledge'][0]['text']+='伪造条款'+str(i)
            elif kind==2: report['period']='错误日期'+str(i)
            else: report['summary']='未经证实的因果结论'+str(i)
            try: verify_report(report,baseline);passed=False
            except DemoError: passed=True
            details.append({'layer':'verifier','case':i,'passed':passed})
        for i in range(54):
            try:
                if i%3==0: understand(f'海淀最近{i//3+1}天带看转成交率',user=identity('chaoyang'))
                elif i%3==1: understand(f'最近{i//3+1}天转化率下降',user=identity('chaoyang'))
                else: guard_sql(f'SELECT secret_{i} FROM stores')
                passed=False
            except DemoError: passed=True
            details.append({'layer':'negative','case':i,'passed':passed})
    metrics={}
    for layer in ['intent','sql','task','verifier','negative']:
        rows=[d for d in details if d['layer']==layer]
        metrics[layer]={'count':len(rows),'passed':sum(bool(r['passed']) for r in rows),'pass_rate':statistics.mean(bool(r['passed']) for r in rows)}
    tasks=[d for d in details if d['layer']=='task']
    metrics['tool_sequence_accuracy']=statistics.mean(r['tool_sequence_correct'] for r in tasks)
    metrics['duplicate_call_ratio']=sum(r['repeated_calls'] for r in tasks)/sum(r['tool_calls'] for r in tasks)
    metrics['task_latency_p95_ms']=sorted(r['latency_ms'] for r in tasks)[math.ceil(len(tasks)*.95)-1]
    return {'metrics':metrics,'details':details,'generated_cases':cases}


def main():
    p=argparse.ArgumentParser();p.add_argument('--quick',action='store_true');p.add_argument('--bm25-only',action='store_true');a=p.parse_args()
    initialize()
    backends=['bm25'] if a.bm25_only else ['bm25','dense','hybrid_no_rerank','hybrid']
    result={'scope':'6条手写检索Gold + 494条参数化合成回归项。检索消融重复使用同一6条，不计作新的独立样本。教学规则模式，不代表DeepSeek质量、生产Faithfulness或原手册指标。','retrieval':{b:retrieval_eval(b) for b in backends}}
    if not a.quick: result['layered']=layers()
    out=ROOT/'output';out.mkdir(exist_ok=True)
    (out/'eval_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'retrieval':{b:r['metrics'] for b,r in result['retrieval'].items()},'layered':result.get('layered',{}).get('metrics',{})},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
