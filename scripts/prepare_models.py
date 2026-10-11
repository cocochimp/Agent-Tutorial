"""下载并真实执行中文Embedding和多语Cross-Encoder；无需GPU。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from estate_agent.data import ROOT
from estate_agent.settings import settings


def main():
    from fastembed import TextEmbedding
    from flashrank import Ranker, RerankRequest
    config = settings()["retrieval"]
    cache = ROOT / "models"
    embedding = TextEmbedding(config["embedding_model"], cache_dir=str(cache / "embedding"), threads=2)
    vectors = list(embedding.embed(["带看后24小时跟进", "门店成交转化率"]))
    print("Embedding shape:", len(vectors), len(vectors[0]), flush=True)
    ranker = Ranker(model_name=config["reranker_model"], cache_dir=str(cache / "reranker"), max_length=256)
    result = ranker.rerank(RerankRequest(query="带看后怎么跟进", passages=[{"id": 1, "text": "带看后24小时记录反馈。"}, {"id": 2, "text": "北京的天气晴朗。"}]))
    print("Cross-encoder:", [(r["id"], float(r["score"])) for r in result], flush=True)


if __name__ == "__main__":
    main()
