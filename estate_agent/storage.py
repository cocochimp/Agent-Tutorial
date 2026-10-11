"""持久化任务、会话记忆、审批业务记录与TTL缓存。所有读取带用户作用域。"""
import hashlib
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from .data import ROOT

STATE_DIR = ROOT / "state"


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class Store:
    def __init__(self, directory=STATE_DIR):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "application.sqlite3"
        with self.connect() as con:
            con.executescript('''
            CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,user_id TEXT,session_id TEXT,status TEXT,body TEXT,updated REAL);
            CREATE TABLE IF NOT EXISTS conversations(user_id TEXT,session_id TEXT,body TEXT,expires REAL,PRIMARY KEY(user_id,session_id));
            CREATE TABLE IF NOT EXISTS memories(user_id TEXT,key TEXT,value TEXT,expires REAL,PRIMARY KEY(user_id,key));
            CREATE TABLE IF NOT EXISTS actions(id TEXT PRIMARY KEY,user_id TEXT,run_id TEXT,kind TEXT,payload TEXT,created REAL);
            CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY,value TEXT,expires REAL);
            CREATE TABLE IF NOT EXISTS logins(token_hash TEXT PRIMARY KEY,user_id TEXT,expires REAL);
            CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,user_id TEXT,event TEXT,details TEXT,created REAL);
            ''')

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.path, timeout=15)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        try:
            yield con
            con.commit()
        finally:
            con.close()

    def put_task(self, state):
        with self.connect() as con:
            con.execute("INSERT OR REPLACE INTO tasks VALUES(?,?,?,?,?,?)", (
                state["run_id"], state["user"]["user_id"], state["session_id"], state["status"], encode(state), time.time()))

    def get_task(self, run_id, user_id):
        with self.connect() as con:
            row = con.execute("SELECT body FROM tasks WHERE id=? AND user_id=?", (run_id, user_id)).fetchone()
        return json.loads(row[0]) if row else None

    def list_tasks(self, user_id):
        with self.connect() as con:
            return [dict(r) for r in con.execute("SELECT id,session_id,status,updated FROM tasks WHERE user_id=? ORDER BY updated DESC LIMIT 40", (user_id,))]

    # 会话键同时包含 user_id 和 session_id；即使两个用户使用相同会话名也不会串话。
    # 过期会话不用于补全问题，避免很久以前的门店对象影响本轮理解。
    def context(self, user_id, session_id):
        with self.connect() as con:
            row = con.execute("SELECT body FROM conversations WHERE user_id=? AND session_id=? AND expires>?", (user_id, session_id, time.time())).fetchone()
        return json.loads(row[0]) if row else {"recent": [], "summary": "", "focus": {}}

    # 保存精简摘要、最近轮次与关注门店，不无限累积原始模型对话。
    # focus 供下一轮“它/这家店”指代消解使用，和当前任务的检查点用途不同。
    def remember_turn(self, state, ttl=86400):
        context = self.context(state["user"]["user_id"], state["session_id"])
        report = state.get("report", {})
        context["recent"].append({"question": state["question"][:1000], "answer": report.get("summary", "")[:500]})
        if len(context["recent"]) > 4:
            old = context["recent"].pop(0)
            context["summary"] = (context["summary"] + "\n" + old["question"][:100] + " → " + old["answer"][:150])[-1500:]
        rows = state.get("results", {}).get("query_metrics", {}).get("rows", [])
        context["focus"] = {"store_id": rows[0]["store_id"] if rows else context["focus"].get("store_id"),
                            "region": state["task"]["region"], "metric": state["task"]["metric"]}
        with self.connect() as con:
            con.execute("INSERT OR REPLACE INTO conversations VALUES(?,?,?,?)", (state["user"]["user_id"], state["session_id"], encode(context), time.time()+ttl))

    # 长期偏好由用户显式保存，按账号隔离并设置过期时间；不会自动推测个人偏好。
    def set_memory(self, user_id, key, value, ttl):
        with self.connect() as con:
            con.execute("INSERT OR REPLACE INTO memories VALUES(?,?,?,?)", (user_id, key, value[:500], time.time()+ttl))

    def memories(self, user_id):
        with self.connect() as con:
            return {r[0]: r[1] for r in con.execute("SELECT key,value FROM memories WHERE user_id=? AND expires>?", (user_id, time.time()))}

    def clear_memory(self, user_id, session_id):
        with self.connect() as con:
            con.execute("DELETE FROM conversations WHERE user_id=? AND session_id=?", (user_id, session_id))
            con.execute("DELETE FROM memories WHERE user_id=?", (user_id,))

    # 幂等键绑定任务与动作类型。先前已成功写入但尚未保存下一检查点时，
    # 重试 INSERT OR IGNORE 不会产生第二张工单，随后返回同一条已存在的记录。
    def action(self, state):
        # 一个run只能执行一次审批后的动作；断点重放也不会创建重复记录。
        key = hashlib.sha256((state["run_id"] + ":" + state["task"]["action"]).encode()).hexdigest()[:24]
        payload = {"title": state["report"]["summary"], "evidence_ids": [d["id"] for d in state["report"]["knowledge"]],
                   "report": state["markdown"], "destination": "本地演示工单/通知收件箱"}
        with self.connect() as con:
            con.execute("INSERT OR IGNORE INTO actions VALUES(?,?,?,?,?,?)", (key, state["user"]["user_id"], state["run_id"], state["task"]["action"], encode(payload), time.time()))
        return {"id": key, "kind": state["task"]["action"], "status": "created", "destination": payload["destination"]}

    def actions(self, user_id):
        with self.connect() as con:
            return [{**dict(r), "payload": json.loads(r["payload"])} for r in con.execute("SELECT * FROM actions WHERE user_id=? ORDER BY created DESC LIMIT 30", (user_id,))]

    def audit(self, user_id, event, details):
        with self.connect() as con:
            con.execute("INSERT INTO audit(user_id,event,details,created) VALUES(?,?,?,?)", (user_id, event, encode(details), time.time()))

    def cache_get(self, key):
        with self.connect() as con:
            row = con.execute("SELECT value FROM cache WHERE key=? AND expires>?", (key, time.time())).fetchone()
        return json.loads(row[0]) if row else None

    def cache_put(self, key, value, ttl):
        with self.connect() as con:
            con.execute("INSERT OR REPLACE INTO cache VALUES(?,?,?)", (key, encode(value), time.time()+ttl))

    def login(self, user_id):
        token = secrets.token_urlsafe(32)
        with self.connect() as con:
            con.execute("INSERT INTO logins VALUES(?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), user_id, time.time()+86400))
        return token

    def lookup_login(self, token):
        with self.connect() as con:
            row = con.execute("SELECT user_id FROM logins WHERE token_hash=? AND expires>?", (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
        return row[0] if row else None


class Cache:
    def __init__(self, store, config):
        self.store, self.config = store, config
        self.redis = None
        self.backend = "sqlite"
        if config["backend"] == "redis":
            import redis
            self.redis = redis.Redis.from_url(config["redis_url"], socket_timeout=2, decode_responses=True)
            self.redis.ping()  # 配置Redis却不可用时显式失败，不假称在使用Redis。
            self.backend = "redis"

    def get(self, key):
        if self.redis:
            value = self.redis.get("estate:"+key)
            return json.loads(value) if value else None
        return self.store.cache_get(key)

    def put(self, key, value):
        ttl = self.config["ttl_seconds"]
        if self.redis:
            self.redis.setex("estate:"+key, ttl, encode(value))
        else:
            self.store.cache_put(key, value, ttl)
