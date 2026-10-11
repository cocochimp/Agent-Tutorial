"""小型知识图谱扩展：仅返回已通过权限检查的证据关系。"""
import json
from .data import ROOT


def graph_lookup(query, permitted_ids):
    graph = json.loads((ROOT/"data"/"relations.json").read_text(encoding="utf-8"))
    starts = {n["id"] for n in graph["nodes"] if any(w in query for w in n["keywords"])}
    visited, frontier, edges = set(starts), set(starts), []
    for _ in range(2):
        following = set()
        for edge in graph["edges"]:
            if edge["from"] in frontier and edge["document"] in permitted_ids:
                edges.append(edge)
                following.add(edge["to"])
        frontier = following-visited
        visited |= following
    return {"matched_entities": sorted(starts), "edges": edges, "document_ids": sorted({e["document"] for e in edges})}
