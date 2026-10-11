"""真实StateGraph回归，含跨进程恢复与幂等重放。"""
import copy
import json
import shutil
import sqlite3
import subprocess
import sys
from unittest.mock import patch
import pytest
from estate_agent.auth import identity
from estate_agent.business import DemoError, USER
from estate_agent.data import DB, ROOT, initialize
from estate_agent.intent import understand
from estate_agent.retrieval import search_knowledge, allowed_documents
from estate_agent.runtime import run
from estate_agent.report import verify_report
from estate_agent.sql_tools import query_metrics, calculate_metrics, guard_sql, execute_readonly
from estate_agent.storage import Store

QUESTION = '分析朝阳最近7天带看转成交率下降的门店，给出原因和跟进建议'

@pytest.fixture(autouse=True, scope='module')
def data():
    initialize()

@pytest.fixture(autouse=True, scope='module')
def extra_accounts():
    # 生产账号已简化为单一 chaoyang；权限/隔离测试需要额外角色，仅注入测试进程
    from estate_agent import auth
    auth.ACCOUNTS['haidian'] = {"password": "demo-haidian", "role": "region_manager", "regions": ["海淀"]}
    auth.ACCOUNTS['viewer'] = {"password": "demo-viewer", "role": "viewer", "regions": ["朝阳"]}
    yield
    auth.ACCOUNTS.pop('haidian', None)
    auth.ACCOUNTS.pop('viewer', None)

def execute(tmp_path, question=QUESTION, **kwargs):
    return run(question, directory=tmp_path, backend='bm25', **kwargs)

def test_gold(tmp_path):
    r = execute(tmp_path)
    assert r['status'] == 'completed'
    f = r['report']['facts'][0]
    assert f['store_id'] == 'S01'
    assert f['current_rate'] == pytest.approx(29/312)
    assert f['previous_rate'] == pytest.approx(64/310)
    assert r['verification']['passed']

def test_knowledge_no_sql(tmp_path):
    r = execute(tmp_path, '带看转成交率怎么算')
    assert r['status'] == 'completed'
    assert 'query_metrics' not in r['results']

@pytest.mark.parametrize('q,code', [('分析海淀最近7天带看转成交率','PERMISSION_DENIED'),('分析最近100天带看转成交率','INVALID_ARGUMENT'),('删除数据库','PERMISSION_DENIED'),('查询门店收入','UNSUPPORTED_METRIC'),('分析2026-13-01带看转成交率','INVALID_ARGUMENT')])
def test_blocked(tmp_path,q,code):
    assert execute(tmp_path,q)['error']['code'] == code

def test_clarification(tmp_path):
    r = execute(tmp_path, '最近7天转化率下降了')
    assert r['status'] == 'waiting'
    done = run(resume_id=r['run_id'], resume_value='带看转成交率', directory=tmp_path)
    assert done['status'] == 'completed'

def test_cross_process_resume(tmp_path):
    r = execute(tmp_path, pause_after='query_metrics')
    assert r['status'] == 'waiting'
    code = "from estate_agent.runtime import run; import json; r=run(resume_id="+repr(r['run_id'])+",directory="+repr(str(tmp_path))+"); print(json.dumps({'status':r['status'],'queries':sum(t['step']=='query_sql' for t in r['trace'])}))"
    process = subprocess.run([sys.executable,'-X','utf8','-c',code], cwd=ROOT, text=True,capture_output=True,check=True)
    assert json.loads(process.stdout) == {'status':'completed','queries':1}

@pytest.mark.parametrize('strategy',['single','multi'])
def test_approval_idempotency(tmp_path,strategy):
    r = execute(tmp_path,QUESTION+'并创建工单',strategy=strategy)
    assert r['status'] == 'waiting'
    assert not Store(tmp_path).actions(USER.user_id)
    assert run(resume_id=r['run_id'],directory=tmp_path)['status'] == 'waiting'
    done = run(resume_id=r['run_id'],resume_value=True,directory=tmp_path)
    assert done['status'] == 'completed'
    Store(tmp_path).action(done)
    run(resume_id=r['run_id'],resume_value=True,directory=tmp_path)
    assert len(Store(tmp_path).actions(USER.user_id)) == 1

def test_reject(tmp_path):
    r = execute(tmp_path,QUESTION+'并创建工单')
    assert run(resume_id=r['run_id'],resume_value=False,directory=tmp_path)['status'] == 'completed'
    assert not Store(tmp_path).actions(USER.user_id)

def test_readonly_role(tmp_path):
    assert execute(tmp_path,QUESTION+'创建工单',user=identity('viewer'))['error']['code'] == 'PERMISSION_DENIED'

def test_owner_isolation(tmp_path):
    r = execute(tmp_path,pause_after='query_metrics')
    with pytest.raises(DemoError):
        run(resume_id=r['run_id'],directory=tmp_path,user=identity('haidian'))

def test_memory_ttl_scope(tmp_path):
    execute(tmp_path,session_id='shared')
    follow = execute(tmp_path,'它最近14天带看转成交率如何',session_id='shared')
    assert follow['task']['store_id'] == 'S01'
    s = Store(tmp_path)
    assert not s.context('someone-else','shared')['focus']
    s.set_memory(USER.user_id,'preference','简短',-1)
    assert not s.memories(USER.user_id)
    s.clear_memory(USER.user_id,'shared')
    assert not s.context(USER.user_id,'shared')['focus']

@pytest.mark.parametrize('field',['facts','knowledge'])
def test_tamper(tmp_path,field):
    r = execute(tmp_path)
    report = copy.deepcopy(r['report'])
    if field == 'facts': report[field][0]['current_rate'] = .99
    else: report[field][0]['text'] = '没有依据的原因'
    with pytest.raises(DemoError): verify_report(report,r)

def test_tamper_both_state_and_citation(tmp_path):
    r = execute(tmp_path)
    r['results']['retrieve_knowledge']['evidence'][0]['text'] = '篡改源状态'
    r['report']['knowledge'][0]['text'] = '篡改源状态'
    with pytest.raises(DemoError): verify_report(r['report'],r)

@pytest.mark.parametrize('sql',['DROP TABLE stores','SELECT name FROM stores;DELETE FROM stores','SELECT * FROM stores','SELECT name FROM main.stores','SELECT name FROM sqlite_master','SELECT name FROM stores UNION SELECT name FROM stores','SELECT randomblob(1000000) FROM stores','SELECT salary FROM stores','SELECT s.name FROM stores s CROSS JOIN daily_metrics d','SELECT name FROM stores LIMIT -1'])
def test_sql_ast(sql):
    with pytest.raises(DemoError): guard_sql(sql)

def test_row_security_without_where():
    _,rows = execute_readonly('SELECT store_id,name,region FROM stores',{})
    assert len(rows) == 4 and all(r['region']=='朝阳' for r in rows)

def test_incomplete_data(tmp_path):
    path=tmp_path/'partial.db';shutil.copyfile(DB,path)
    con=sqlite3.connect(path)
    con.execute("DELETE FROM daily_metrics WHERE store_id='S01' AND day='2026-09-25'")
    con.commit();con.close()
    with pytest.raises(DemoError,match='不完整'): calculate_metrics(query_metrics(understand(QUESTION),db=path))

def test_zero_denominator(tmp_path):
    path=tmp_path/'zero.db';shutil.copyfile(DB,path)
    con=sqlite3.connect(path)
    con.execute("UPDATE daily_metrics SET viewings=0,deals=0 WHERE store_id='S01'")
    con.commit();con.close()
    r=calculate_metrics(query_metrics(understand(QUESTION),db=path))
    assert next(row for row in r['rows'] if row['store_id']=='S01')['current_rate'] is None

def test_acl_no_evidence():
    r=search_knowledge('薪酬 跟进 带看 72小时',backend='bm25',use_cache=False)
    assert not {d['id'] for d in r['evidence']} & {'PRIVATE-01','OLD-01','HD-01'}
    assert not search_knowledge('量子纠缠火星轨道',backend='bm25')['evidence']

def test_versions():
    from estate_agent.data import read_documents
    docs=read_documents();old={**docs[1],'id':'SUPERSEDED','version':1}
    assert 'SUPERSEDED' not in {d['id'] for d in allowed_documents(docs+[old],'朝阳',USER)}

def test_cancel(tmp_path):
    assert execute(tmp_path,cancel_check=lambda:True)['status']=='cancelled'

def test_transient_retry(tmp_path):
    calls=[]
    def flaky(*a,**kw):
        calls.append(1)
        if len(calls)==1: raise DemoError('SQL_TIMEOUT','模拟超时')
        return query_metrics(*a,**kw)
    with patch('estate_agent.runtime.query_metrics',side_effect=flaky): r=execute(tmp_path)
    assert r['status']=='completed' and len(calls)==2
    assert any(t['step']=='retry_node' for t in r['trace'])

def test_low_confidence(tmp_path):
    with patch('estate_agent.runtime.search_knowledge',return_value={'evidence':[]}): r=execute(tmp_path)
    assert r['status']=='waiting'
    assert '未找到适用制度' in r['markdown']

def test_resume_queued_before_checkpoint(tmp_path):
    from dataclasses import asdict
    Store(tmp_path).put_task({'run_id':'queue-no-checkpoint','user':asdict(USER),'session_id':'queued','question':QUESTION,'mode':'offline','backend':'bm25','status':'queued','trace':[]})
    assert run(resume_id='queue-no-checkpoint',directory=tmp_path)['status']=='completed'
