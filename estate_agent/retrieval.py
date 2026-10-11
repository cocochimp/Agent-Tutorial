"""Dense+BM25→RRF→CrossEncoder→Authority/Validity→MMR→DynamicTopK。"""
import hashlib
import atexit
import json
import math
import re
import threading
import uuid
from collections import Counter
from .business import USER, DemoError
from .data import AS_OF, ROOT, read_documents
from .graph_rag import graph_lookup
from .settings import settings
from .storage import Cache, Store

# 本地 ONNX 模型与 Qdrant 客户端在进程内复用；锁保护初始化、索引和精排调用。
# Qdrant 本地目录不能被多个进程同时占用，完整评测应与网页服务分开运行。
LOCK = threading.RLock()
_embedding = _ranker = _vector_db = _index_fingerprint = None


@atexit.register
def close_vectors():
    global _vector_db, _index_fingerprint
    if _vector_db is not None:
        _vector_db.close()
        _vector_db = _index_fingerprint = None


# 无外部分词服务的中文二元切分：例如“带看成交”得到“带看/看成/成交”。
# 英文与数字按连续词提取，供 BM25 与后续 Jaccard 去重共同使用。
def tokenize(text):
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    for part in re.findall(r"[\u4e00-\u9fff]+", text):
        tokens.extend(part[i:i+2] for i in range(max(1, len(part)-1)))
    return tokens


# 检索前先确定可见文档：地区、角色、有效期都必须满足。
# 同一 family 只保留适用候选中版本最高的一条，避免新旧规范同时被引用。
def allowed_documents(docs, region, user):
    if region not in user.regions:
        raise DemoError("PERMISSION_DENIED", "知识检索地区越权。")
    roles = {user.role} | ({"region_manager"} if user.role in ("director", "viewer") else set())
    candidates = [d for d in docs if roles.intersection(d["roles"]) and d["region"] in (region, "all")
                  and d["valid_from"] <= AS_OF.isoformat() <= d["valid_to"]]
    versions = {}
    for doc in candidates:
        family = doc.get("family", doc["id"])
        if family not in versions or doc.get("version", 1) > versions[family].get("version", 1):
            versions[family] = doc
    return list(versions.values())


# 子段参与召回，parent 保留完整制度条款。命中短句后仍能回取完整依据，
# 同时保留 child ID，用于解释到底是哪句话匹配了问题。
def chunks(docs):
    return [{"id": f'{d["id"]}-C{i+1}', "parent": d, "text": d["title"]+" · "+d["section"]+"："+s.strip()}
            for d in docs for i, s in enumerate(re.split(r"[。；]", d["text"])) if s.strip()]


# 词法召回：tf 表示词在当前段落出现次数，df 表示多少段落包含该词。
# 公式同时考虑词的重要性与段落长度，输出 (子段位置, 分数) 的降序列表。
def bm25(query, items):
    counts = [Counter(tokenize(c["text"])) for c in items]
    average = sum(sum(c.values()) for c in counts)/max(1, len(counts))
    scores = []
    for i, count in enumerate(counts):
        score = 0.0
        for word in set(tokenize(query)):
            tf, df = count[word], sum(word in c for c in counts)
            if tf:
                score += math.log(1+(len(counts)-df+.5)/(df+.5))*tf*2.5/(tf+1.5*(.25+.75*sum(count.values())/max(average, 1)))
        if score > 0:
            scores.append((i, score))
    return sorted(scores, key=lambda x: x[1], reverse=True)


# 两个模型分工不同：Embedding 把文本转成向量，Cross-Encoder 对问题/段落配对打分。
# 它们在本地 CPU 运行，与选择工具的 DeepSeek API 互相独立。
def models():
    global _embedding, _ranker
    config = settings()["retrieval"]
    with LOCK:
        if _embedding is None:
            from fastembed import TextEmbedding
            _embedding = TextEmbedding(config["embedding_model"], cache_dir=str(ROOT/"models"/"embedding"), threads=2)
        if _ranker is None:
            from flashrank import Ranker
            _ranker = Ranker(model_name=config["reranker_model"], cache_dir=str(ROOT/"models"/"reranker"), max_length=256)
    return _embedding, _ranker


def dense_rank(query, permitted, all_items):
    global _vector_db, _index_fingerprint
    from qdrant_client import QdrantClient, models as qm
    embedding, _ = models()
    fingerprint = hashlib.sha256(json.dumps(all_items, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    with LOCK:
        if _vector_db is None:
            _vector_db = QdrantClient(path=str(ROOT/"state"/"vectors"))
        # 文档内容指纹变化时重建索引。索引可以包含完整知识库，
        # 但每次查询必须使用允许的 child ID 过滤，不能先返回再隐藏。
        if _index_fingerprint != fingerprint:
            vectors = list(embedding.embed([c["text"] for c in all_items]))
            if _vector_db.collection_exists("knowledge"):
                _vector_db.delete_collection("knowledge")
            _vector_db.create_collection("knowledge", vectors_config=qm.VectorParams(size=len(vectors[0]), distance=qm.Distance.COSINE))
            _vector_db.upsert("knowledge", points=[qm.PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL, c["id"])), vector=v.tolist(),
                payload={"child_id": c["id"], "parent_id": c["parent"]["id"]}) for c, v in zip(all_items, vectors)])
            _index_fingerprint = fingerprint
        vector = list(embedding.query_embed(query))[0]
        # Qdrant在向量检索前施加允许的chunk ID过滤；未授权chunk不会返回。
        hits = _vector_db.query_points("knowledge", query=vector.tolist(), query_filter=qm.Filter(must=[
            qm.FieldCondition(key="child_id", match=qm.MatchAny(any=[c["id"] for c in permitted]))]), limit=min(20, len(permitted))).points
        positions = {c["id"]: i for i, c in enumerate(permitted)}
        return [(positions[p.payload["child_id"]], float(p.score)) for p in hits]


def rewrite_query(query, client=None, hypothetical=False):
    if client:
        prompt = "生成检索关键词，保留指标与制度编号，不回答问题。" if not hypothetical else "生成假设文档的检索关键词，仅用来检索，不能当作事实证据。"
        return client.structured(prompt, {"query": query}, {"type": "object", "properties": {"query": {"type": "string"}},
                                 "required": ["query"], "additionalProperties": False})["query"][:500]
    rewritten = query
    for old, new in {"转化": "带看 成交", "回访": "跟进", "卖不动": "成交 下降", "计算": "指标 口径"}.items():
        if old in query:
            rewritten += " "+new
    return rewritten


# 返回契约：evidence 是报告可引用的证据，stages 是检索各阶段的可观测记录。
# backend 决定消融方式；规则模式也调用此函数，RAG 并不依赖 DeepSeek 才能执行。
def search_knowledge(query, region="朝阳", user=USER, documents=None, backend=None, client=None, graph=False, use_cache=True):
    config = settings()["retrieval"]
    backend = backend or config["backend"]
    if backend not in ("hybrid", "dense", "bm25", "hybrid_no_rerank"):
        raise DemoError("INVALID_ARGUMENT", "未知检索模式。")
    docs = documents if documents is not None else read_documents()
    allowed = allowed_documents(docs, region, user)
    items = chunks(allowed)
    base = {"query": query, "evidence": [], "candidate_count": len(items), "method": backend, "stages": [], "cache_hit": False}
    if not items:
        return base
    # 缓存键包含用户/角色/地区、文档内容、模型与检索配置。
    # 不能只用 query 做键，否则其他身份可能命中不属于自己的证据。
    key = hashlib.sha256(json.dumps([query, region, user.user_id, user.role, docs, config, backend, graph, getattr(client, "model", None), "estate-v2.0"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    cache = Cache(Store(), settings()["cache"])
    if use_cache and (cached := cache.get(key)):
        return {**cached, "cache_hit": True}
    # 查询改写补充检索词，不直接回答问题；仍只允许引用知识库里的原文。
    rewritten = rewrite_query(query, client)
    sparse = bm25(rewritten, items)
    dense = dense_rank(rewritten, items, chunks(docs)) if backend != "bm25" else []
    base["stages"] = [{"name": "ACL/版本/有效期预过滤", "parents": len(allowed)}, {"name": "Query Rewrite", "query": rewritten},
                      {"name": "BM25", "rank": [[items[i]["id"], s] for i, s in sparse[:20]]},
                      {"name": "Dense", "rank": [[items[i]["id"], s] for i, s in dense]}]
    # HyDE 仅在词法召回为空时补救。模型生成的是检索线索，绝不作为 evidence。
    if not sparse and client and config["hyde_on_empty"]:
        hypothetical = rewrite_query(query, client, hypothetical=True)
        sparse = bm25(hypothetical, items)
        if dense:
            dense = dense_rank(hypothetical, items, chunks(docs))
        base["stages"].append({"name": "HyDE补救（仅用于检索）", "query": hypothetical})
    # RRF 按名次融合：两个检索器的原始分数不可直接比较，
    # 改用 1/(60+排名) 累加，奖励两路都排在前面的候选。
    fused = Counter()
    for ranking in ([dense] if backend == "dense" else [sparse, dense]):
        for position, (idx, _) in enumerate(ranking[:config["candidate_k"]], 1):
            fused[idx] += 1/(60+position)
    if graph:
        base["graph"] = graph_lookup(query, {d["id"] for d in allowed})
        for i, item in enumerate(items):
            if item["parent"]["id"] in base["graph"]["document_ids"]:
                fused[i] += .005
    candidates = fused.most_common(config["candidate_k"])
    base["stages"].append({"name": "RRF候选池", "rank": [[items[i]["id"], score] for i, score in candidates]})
    if not candidates:
        return base
    # 只有完整 hybrid 做 Cross-Encoder 精排。其他模式用归一化融合分数作消融，
    # 这些分数服务于排序，不能解释为事实正确的概率。
    if backend == "hybrid":
        from flashrank import RerankRequest
        _, ranker = models()
        with LOCK:
            ranked = ranker.rerank(RerankRequest(query=query, passages=[{"id": i, "text": items[i]["text"]} for i, _ in candidates]))
        scores = [(int(r["id"]), float(r["score"])) for r in ranked]
    else:
        maximum = max(score for _, score in candidates)
        scores = [(i, score/maximum) for i, score in candidates]
    base["stages"].append({"name": "Cross-Encoder" if backend == "hybrid" else "Ablation未启用精排", "rank": [[items[i]["id"], s] for i, s in scores]})
    candidates = [(i, score) for i, score in scores if score >= config["min_rerank_score"]]
    # MMR 平衡相关性与冗余：本项目用中文词项 Jaccard 衡量重复程度。
    # 父条款只选一次，并裁掉过低分项，因此最后不一定正好达到 top_k。
    selected, seen = [], set()
    while candidates and len(selected) < config["top_k"]:
        def mmr(pair):
            idx, relevance = pair
            tokens = set(tokenize(items[idx]["text"]))
            redundancy = max((len(tokens & set(tokenize(items[j]["text"])))/max(1, len(tokens | set(tokenize(items[j]["text"])))) for j, _ in selected), default=0)
            authority = items[idx]["parent"].get("authority", .8)
            return config["mmr_lambda"]*(relevance*.9+authority*.1)-(1-config["mmr_lambda"])*redundancy
        best = max(candidates, key=mmr)
        candidates.remove(best)
        i, score = best
        parent = items[i]["parent"]
        if parent["id"] in seen or (selected and score < selected[0][1]*.12):
            continue
        selected.append(best)
        seen.add(parent["id"])
    # 把选中的子段映射回父条款，附上命中片段与分数。报告的引用来自这里，
    # 不来自查询改写文本，也不来自模型自行编写的答案。
    base["evidence"] = [{**items[i]["parent"], "child_id": items[i]["id"], "matched_excerpt": items[i]["text"],
                         "rerank_score": score, "rrf_score": fused[i]} for i, score in selected]
    base["stages"].append({"name": "Authority + MMR + DynamicTopK", "selected": len(selected), "threshold": config["min_rerank_score"]})
    base["rewritten_query"] = rewritten
    base["model_versions"] = {"embedding": config["embedding_model"] if dense else None, "reranker": config["reranker_model"] if backend == "hybrid" else None}
    if use_cache:
        cache.put(key, base)
    return base
