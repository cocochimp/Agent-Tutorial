"""FastAPI登录、异步任务、状态流、审批/澄清/重启恢复与CLI。"""
import argparse
import asyncio
import json
import re
import threading
import uuid
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from estate_agent.auth import identity, login
from estate_agent.business import DemoError
from estate_agent.data import ROOT, initialize
from estate_agent.llm import ModelClient
from estate_agent.runtime import run, build_graph
from estate_agent.settings import settings
from estate_agent.storage import Store

DEFAULT_QUESTION = "分析朝阳最近7天带看转成交率下降的门店，给出原因和跟进建议"
@asynccontextmanager
async def lifespan(app):
    initialize()
    yield
    executor.shutdown(wait=True)
    from estate_agent.retrieval import close_vectors
    close_vectors()


app = FastAPI(title="经营分析Agent · LangGraph", version="2.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(ROOT/"web")), name="static")
app.mount("/guide", StaticFiles(directory=str(ROOT/"docs")), name="guide")
store = Store()
executor = ThreadPoolExecutor(max_workers=settings()["max_workers"])
pending = {}
cancellations = {}
job_lock = threading.Lock()


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginBody(Body):
    username: str
    password: str


class RunBody(Body):
    question: str = Field(min_length=1, max_length=2000)
    mode: str = "offline"
    session_id: str = Field(default="default", pattern=r"^[\w-]{1,64}$")
    backend: str = "hybrid"
    graph_rag: bool = False
    strategy: str = "single"
    pause_after: str | None = None


class ResumeBody(Body):
    value: bool | str | None = None


class MemoryBody(Body):
    key: str = Field(pattern=r"^[\w-]{1,40}$")
    value: str = Field(max_length=500)


@app.middleware("http")
async def same_origin(request, call_next):
    if request.method in ("POST", "PUT", "DELETE"):
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "跨域写入请求未开放"}, status_code=403)
    return await call_next(request)


def current_user(request):
    username = store.lookup_login(request.cookies.get("estate_session", ""))
    if not username:
        raise HTTPException(401, "请先登录演示账号。")
    return identity(username)


@app.get("/")
def index():
    return FileResponse(ROOT/"web"/"index.html", headers={"Cache-Control": "no-store"})


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@app.get("/api/health")
def health():
    try:
        ModelClient()
        configured = True
    except DemoError:
        configured = False
    return {"ok": True, "version": "2.0.0", "runtime": "LangGraph StateGraph / SQLite Checkpointer", "model_configured": configured}


@app.post("/api/login")
def sign_in(body: LoginBody, response: Response):
    try:
        token, user = login(body.username, body.password, store)
    except DemoError as exc:
        raise HTTPException(401, str(exc))
    response.set_cookie("estate_session", token, httponly=True, samesite="strict", max_age=86400)
    return user


@app.post("/api/logout")
def sign_out(request: Request, response: Response):
    # 删除服务端登录记录，旧cookie不能继续访问。
    import hashlib
    token_hash = hashlib.sha256(request.cookies.get("estate_session", "").encode()).hexdigest()
    with store.connect() as con:
        con.execute("DELETE FROM logins WHERE token_hash=?", (token_hash,))
    response.delete_cookie("estate_session")
    return {"ok": True}


@app.get("/api/me")
def me(request: Request):
    return asdict(current_user(request))


@app.get("/api/session")
def session_status(request: Request):
    username = store.lookup_login(request.cookies.get("estate_session", ""))
    return {"user": asdict(identity(username)) if username else None}


def submit(user, kwargs, run_id=None):
    with job_lock:
        for old in [key for key, future in pending.items() if future.done()]:
            pending.pop(old, None)
            cancellations.pop(old, None)
        active = sum(not f.done() for f in pending.values())
        if active >= settings()["max_pending_tasks"]:
            raise HTTPException(429, "任务队列已满，请稍后重试。")
        key = run_id or uuid.uuid4().hex[:12]
        if key in pending and not pending[key].done():
            raise HTTPException(409, "该任务正在执行，不能重复恢复。")
        cancel = threading.Event()
        cancellations[key] = cancel
        if not run_id:
            store.put_task({**kwargs, "run_id": key, "user": asdict(user), "status": "queued", "trace": []})
        else:
            value = store.get_task(key, user.user_id)
            value["status"] = "queued"
            store.put_task(value)
        pending[key] = executor.submit(run, user=user, run_id=key, cancel_check=cancel.is_set, **kwargs)
    return {"run_id": key, "status": "queued"}


@app.post("/api/tasks", status_code=202)
# 请求处理只负责校验、登记和提交后台执行，避免 HTTP 请求一直等模型返回。
# user 来自登录 cookie；不接受前端自称的角色或数据权限。
def create_task(body: RunBody, request: Request):
    user = current_user(request)
    if body.mode not in ("offline", "llm") or body.backend not in ("hybrid", "bm25", "dense", "hybrid_no_rerank") or body.strategy not in ("single", "multi"):
        raise HTTPException(400, "未知模式或检索设置。")
    return submit(user, body.model_dump())


def owned_task(run_id, user):
    value = store.get_task(run_id, user.user_id)
    if not value:
        raise HTTPException(404, "任务不存在或无权查看。")
    with job_lock:
        active = run_id in pending and not pending[run_id].done()
    if value["status"] in ("running", "queued") and not active:
        value["status"] = "interrupted"
    return value


@app.get("/api/tasks")
def task_list(request: Request):
    return store.list_tasks(current_user(request).user_id)


@app.get("/api/tasks/{run_id}")
def task_status(run_id: str, request: Request):
    return owned_task(run_id, current_user(request))


@app.get("/api/tasks/{run_id}/events")
# SSE 持续发送任务快照；每次读取都经过任务归属检查。
# 前端 watch() 收到快照后调用 render() 更新图、Trace 和报告。
async def task_events(run_id: str, request: Request):
    user = current_user(request)
    owned_task(run_id, user)
    async def events():
        previous = None
        for _ in range(600):
            if await request.is_disconnected():
                return
            value = owned_task(run_id, user)
            payload = json.dumps(value, ensure_ascii=False)
            if payload != previous:
                yield "data: "+payload+"\n\n"
                previous = payload
            if value["status"] not in ("running", "queued"):
                return
            await asyncio.sleep(.5)
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.post("/api/tasks/{run_id}/resume", status_code=202)
def resume_task(run_id: str, body: ResumeBody, request: Request):
    user = current_user(request)
    value = owned_task(run_id, user)
    if value["status"] not in ("waiting", "interrupted", "failed"):
        raise HTTPException(409, "任务不处于可恢复状态。")
    for item in value.get("interrupts", []):
        if item["kind"] == "approval" and not isinstance(body.value, bool):
            raise HTTPException(422, "需要明确选择批准或拒绝。")
        if item["kind"] == "clarification" and (not isinstance(body.value, str) or not body.value.strip()):
            raise HTTPException(422, "请输入澄清内容。")
    return submit(user, {"resume_id": run_id, "resume_value": body.value}, run_id)


@app.post("/api/tasks/{run_id}/cancel")
def cancel_task(run_id: str, request: Request):
    owned_task(run_id, current_user(request))
    if run_id in cancellations:
        cancellations[run_id].set()
    return {"status": "cancel_requested", "message": "正在进行的外部调用结束后，在下一节点取消。"}


@app.get("/api/actions")
def list_actions(request: Request):
    return store.actions(current_user(request).user_id)


@app.get("/api/memory/{session_id}")
def memory(session_id: str, request: Request):
    user = current_user(request)
    return {"session": store.context(user.user_id, session_id), "preferences": store.memories(user.user_id)}


@app.post("/api/memory")
def remember(body: MemoryBody, request: Request):
    user = current_user(request)
    store.set_memory(user.user_id, body.key, body.value, settings()["long_memory_ttl_seconds"])
    return {"ok": True}


@app.delete("/api/memory/{session_id}")
def forget(session_id: str, request: Request):
    store.clear_memory(current_user(request).user_id, session_id)
    return {"ok": True}


@app.get("/api/graph")
def graph_definition(strategy: str = "single"):
    if strategy not in ("single", "multi"):
        raise HTTPException(400, "未知编排模式")
    from estate_agent.diagram import svg_graph
    graph = build_graph(None, store, strategy=strategy)
    return {"mermaid": graph.get_graph().draw_mermaid(), "svg": svg_graph(graph)}


@app.get("/manual")
def manual():
    from urllib.parse import quote
    return RedirectResponse("/guide/"+quote("能力对照说明书.html"))


def main():
    parser = argparse.ArgumentParser(description="LangGraph经营分析Agent")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--ask", nargs="?", const=DEFAULT_QUESTION)
    parser.add_argument("--mode", choices=["offline", "llm"], default="offline")
    parser.add_argument("--backend", choices=["hybrid", "bm25", "dense", "hybrid_no_rerank"], default=None)
    parser.add_argument("--strategy", choices=["single", "multi"], default="single")
    parser.add_argument("--user", default="chaoyang", choices=["chaoyang", "haidian", "director", "viewer"])
    parser.add_argument("--session", default="cli")
    parser.add_argument("--resume")
    parser.add_argument("--answer")
    parser.add_argument("--approve", choices=["yes", "no"])
    parser.add_argument("--pause-after", choices=list(__import__('estate_agent.runtime', fromlist=['TOOL_NODES']).TOOL_NODES))
    parser.add_argument("--reset-data", action="store_true")
    parser.add_argument("--graph-rag", action="store_true")
    args = parser.parse_args()
    initialize(args.reset_data)
    if args.ask is not None or args.resume:
        value = args.answer if args.answer is not None else args.approve == "yes" if args.approve is not None else None
        result = run(args.ask or "", mode=args.mode, resume_id=args.resume, resume_value=value, pause_after=args.pause_after,
                     user=identity(args.user), session_id=args.session, backend=args.backend, graph_rag=args.graph_rag, strategy=args.strategy)
        print(result.get("markdown") or json.dumps(result.get("error", result.get("interrupts", [])), ensure_ascii=False, indent=2))
        print("Task:", result["run_id"], "Status:", result["status"])
        return 0 if result["status"] in ("completed", "waiting") else 1
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
