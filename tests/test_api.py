import time
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
import app as web
from estate_agent.storage import Store
from estate_agent.auth import identity
from estate_agent.runtime import run

def test_http_auth_tasks_approval_and_scope(tmp_path,monkeypatch):
    store=Store(tmp_path)
    monkeypatch.setattr(web,'store',store)
    monkeypatch.setattr(web,'run',lambda **kwargs:run(directory=tmp_path,**kwargs))
    monkeypatch.setattr(web,'executor',ThreadPoolExecutor(max_workers=2))
    monkeypatch.setattr(web,'pending',{})
    with TestClient(web.app) as client:
        assert client.get('/api/tasks').status_code==401
        assert client.post('/api/login',json={'username':'chaoyang','password':'bad'}).status_code==401
        assert client.post('/api/login',json={'username':'chaoyang','password':'demo-chaoyang'}).status_code==200
        assert client.post('/api/memory',json={'key':'pref','value':'brief'},headers={'origin':'http://evil.test'}).status_code==403
        assert client.post('/api/tasks',json={'question':'查询','user':'director'}).status_code==422
        res=client.post('/api/tasks',json={'question':'朝阳最近7天带看转成交率分析并创建工单','backend':'bm25'})
        assert res.status_code==202
        url='/api/tasks/'+res.json()['run_id']
        for _ in range(150):
            state=client.get(url).json()
            if state['status']=='waiting': break
            time.sleep(.1)
        assert state['status']=='waiting'
        assert client.post(url+'/resume',json={}).status_code==422
        assert client.post(url+'/resume',json={'value':True}).status_code==202
        for _ in range(150):
            state=client.get(url).json()
            if state['status']=='completed': break
            time.sleep(.1)
        assert state['status']=='completed'
        assert len(client.get('/api/actions').json())==1
        client.post('/api/logout')
        # 单账号环境：登出即未认证，任务详情不可访问
        assert client.get(url).status_code == 401
        assert client.get('/api/actions').status_code == 401
        client.post('/api/logout')
        assert client.get('/api/me').status_code==401
