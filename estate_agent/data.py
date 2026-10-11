"""生成可重复的日汇总数据。改这里，再 python app.py --reset-data。"""
import json
import random
import sqlite3
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB = DATA / "business.sqlite3"
AS_OF = date(2026, 9, 28)  # 固定演示时钟，最近7天=9月21日~27日
STORES = [("S01", "望京A店", "朝阳"), ("S02", "朝阳公园店", "朝阳"),
          ("S03", "双井店", "朝阳"), ("S04", "国贸店", "朝阳"),
          ("S05", "中关村店", "海淀"), ("S06", "五道口店", "海淀")]


def initialize(reset=False):
    DATA.mkdir(exist_ok=True)
    if DB.exists() and not reset:
        extend_history()
        return
    rng = random.Random(42)
    with closing(sqlite3.connect(DB)) as con, con:
        con.executescript("""
        DROP TABLE IF EXISTS daily_metrics;
        DROP TABLE IF EXISTS stores;
        CREATE TABLE stores(store_id TEXT PRIMARY KEY, name TEXT, region TEXT);
        CREATE TABLE daily_metrics(
          day TEXT, store_id TEXT, leads INTEGER, viewings INTEGER,
          effective_viewings INTEGER, followups_24h INTEGER, deals INTEGER,
          PRIMARY KEY(day,store_id), FOREIGN KEY(store_id) REFERENCES stores(store_id));
        """)
        con.executemany("INSERT INTO stores VALUES (?,?,?)", STORES)
        for offset in range(28):
            day = AS_OF - timedelta(days=28-offset)
            for i, (sid, _, _) in enumerate(STORES):
                leads = 75 + rng.randint(0, 25) + i * 3
                views = 40 + rng.randint(0, 10)
                affected = sid == "S01" and day >= date(2026, 9, 21)
                effective = round(views * (0.56 if affected else 0.84))
                followups = round(views * (0.47 if affected else 0.90))
                deals = (3 if affected else 8) + rng.randint(0, 2)
                con.execute("INSERT INTO daily_metrics VALUES (?,?,?,?,?,?,?)",
                            (day.isoformat(), sid, leads, views, effective, followups, deals))
    extend_history()


def extend_history():
    """补齐13个月历史以支持上个月、同比；保留原28天种子数据不变。"""
    with closing(sqlite3.connect(DB)) as con, con:
        if con.execute("SELECT MIN(day) FROM daily_metrics").fetchone()[0] <= "2025-08-01":
            return
        rng = random.Random(20260928)
        day = date(2025, 8, 1)
        while day < date(2026, 8, 31):
            for i, (sid, _, _) in enumerate(STORES):
                views = 40+rng.randint(0, 10)
                con.execute("INSERT OR IGNORE INTO daily_metrics VALUES(?,?,?,?,?,?,?)", (
                    day.isoformat(), sid, 75+rng.randint(0, 25)+i*3, views,
                    round(views*.84), round(views*.9), 8+rng.randint(0, 2)))
            day += timedelta(days=1)


def read_documents():
    return json.loads((DATA / "knowledge.json").read_text(encoding="utf-8"))
