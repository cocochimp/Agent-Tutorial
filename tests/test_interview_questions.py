import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _data():
    path = ROOT / "web" / "interview-questions.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema():
    d = _data()
    cats = set(d["categories"])
    ids = set()
    for q in d["questions"]:
        assert q["category"] in cats, f"{q['id']} 分类 {q['category']} 不在 categories 中"
        assert q["status"] in ("active", "draft")
        assert q["weight"] >= 1
        assert q["question"] and q["answer"]
        assert q["id"] not in ids
        ids.add(q["id"])
    assert "general" in cats


def test_at_least_ten_active():
    d = _data()
    assert sum(1 for q in d["questions"] if q["status"] == "active") >= 10
