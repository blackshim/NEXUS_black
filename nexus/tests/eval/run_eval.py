"""
NEXUS Search Quality Evaluation Framework

Metrics:
- Recall@K: Proportion of queries where the correct document appears in top K results
- MRR@K: Mean Reciprocal Rank of the correct document
- Answer Hit Rate: Proportion of queries where answer keywords are found in search result text

Usage:
    python run_eval.py [--top-k 5] [--with-rerank] [--verbose]
"""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

QDRANT_URL = "http://localhost:6333"
QDRANT_API_KEY = "nexus-qdrant-change-me"
EMBEDDING_URL = "http://localhost:8080"
COLLECTION = "documents"

http = httpx.Client(timeout=120.0)


def embed_query(query: str) -> dict:
    resp = http.post(
        f"{EMBEDDING_URL}/embed",
        json={
            "texts": [query],
            "instruction": "Represent this sentence for searching relevant passages",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    result = {"dense": data["dense"][0]}
    if data.get("sparse") and data["sparse"]:
        result["sparse"] = data["sparse"][0]
    return result


def rerank(query: str, texts: list[str], top_k: int) -> list[dict]:
    resp = http.post(
        f"{EMBEDDING_URL}/rerank",
        json={"query": query, "documents": texts, "top_k": top_k},
    )
    resp.raise_for_status()
    return resp.json()["results"]


def search_dense(query_vec: list[float], limit: int) -> list[dict]:
    resp = http.post(
        f"{QDRANT_URL}/collections/{COLLECTION}/points/query",
        headers={"api-key": QDRANT_API_KEY, "Content-Type": "application/json"},
        json={
            "query": query_vec,
            "using": "dense",
            "limit": limit,
            "with_payload": True,
        },
    )
    resp.raise_for_status()
    return resp.json()["result"]["points"]


def evaluate(dataset_path: str, top_k: int, with_rerank: bool, verbose: bool):
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"\n{'='*60}")
    print(f"NEXUS Search Quality Evaluation")
    print(f"{'='*60}")
    print(f"Evaluation dataset: {len(dataset)} queries")
    print(f"Top-K: {top_k}")
    print(f"Reranking: {'ON' if with_rerank else 'OFF'}")
    print(f"{'='*60}\n")

    recall_hits = 0
    mrr_sum = 0.0
    answer_hits = 0
    total = len(dataset)
    latencies = []

    for item in dataset:
        qid = item["id"]
        query = item["query"]
        expected_file = item["expected_file"]
        expected_keywords = item.get("expected_answer_contains", [])
        category = item.get("category", "")

        start = time.time()

        # 1. Embedding
        emb = embed_query(query)

        # 2. Dense search
        search_limit = top_k * 2 if with_rerank else top_k
        results = search_dense(emb["dense"], search_limit)

        # 3. Reranking (optional)
        if with_rerank and results:
            texts = [r["payload"]["text"] for r in results]
            reranked = rerank(query, texts, top_k)
            # Reorder based on reranking results
            final_results = []
            for rr in reranked:
                idx = rr["index"]
                final_results.append(results[idx])
            results = final_results
        else:
            results = results[:top_k]

        elapsed = time.time() - start
        latencies.append(elapsed)

        # 4. Recall@K measurement
        found_rank = None
        for rank, pt in enumerate(results, 1):
            file_path = pt["payload"].get("file_path", "")
            if expected_file in file_path:
                found_rank = rank
                break

        recall_hit = found_rank is not None
        if recall_hit:
            recall_hits += 1
            mrr_sum += 1.0 / found_rank

        # 5. Answer Hit Rate (do search results contain answer keywords?)
        all_text = " ".join(r["payload"].get("text", "") for r in results)
        keyword_found = all(kw in all_text for kw in expected_keywords)
        if keyword_found:
            answer_hits += 1

        # Log
        status = "O" if recall_hit else "X"
        answer_status = "O" if keyword_found else "X"
        if verbose:
            print(f"[{qid:2d}] {status} Recall | {answer_status} Answer | {elapsed:.2f}s | [{category}] {query}")
            if found_rank:
                print(f"     -> Correct document rank #{found_rank}: {expected_file}")
            else:
                top_file = results[0]["payload"].get("file_path", "").split("/")[-1].split("\\")[-1] if results else "none"
                print(f"     -> Correct document not found. Top-1: {top_file}")
        else:
            print(f"[{qid:2d}] {status}{answer_status} | {query[:40]}")

    # Result summary
    recall = recall_hits / total
    mrr = mrr_sum / total
    answer_rate = answer_hits / total
    avg_latency = sum(latencies) / len(latencies)

    print(f"\n{'='*60}")
    print(f"Result Summary")
    print(f"{'='*60}")
    print(f"  Recall@{top_k}:        {recall:.1%}  ({recall_hits}/{total})")
    print(f"  MRR@{top_k}:           {mrr:.3f}")
    print(f"  Answer Hit Rate:  {answer_rate:.1%}  ({answer_hits}/{total})")
    print(f"  Avg response time: {avg_latency:.2f}s")
    print(f"{'='*60}")

    # Per-category Recall
    categories = {}
    for item in dataset:
        cat = item.get("category", "other")
        if cat not in categories:
            categories[cat] = {"total": 0, "hits": 0}
        categories[cat]["total"] += 1

    for item in dataset:
        cat = item.get("category", "other")
        emb = embed_query(item["query"])
        results = search_dense(emb["dense"], top_k)
        for pt in results:
            if item["expected_file"] in pt["payload"].get("file_path", ""):
                categories[cat]["hits"] += 1
                break

    print(f"\nPer-category Recall@{top_k}:")
    for cat, data in sorted(categories.items()):
        cat_recall = data["hits"] / data["total"]
        print(f"  {cat:8s}: {cat_recall:.1%} ({data['hits']}/{data['total']})")

    return {"recall": recall, "mrr": mrr, "answer_rate": answer_rate}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NEXUS Search Quality Evaluation")
    parser.add_argument("--top-k", type=int, default=5, help="Top K results (default: 5)")
    parser.add_argument("--with-rerank", action="store_true", help="Enable reranking")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--dataset",
        default=str(Path(__file__).parent / "eval_dataset.json"),
        help="Evaluation dataset path",
    )
    args = parser.parse_args()

    evaluate(args.dataset, args.top_k, args.with_rerank, args.verbose)
