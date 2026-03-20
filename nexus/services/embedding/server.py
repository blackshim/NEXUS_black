"""
NEXUS Embedding + Reranker Server
- /embed: Text -> Dense + Sparse vector conversion
- /rerank: query + documents -> relevance score reranking
- /health: Health check
"""

import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nexus-embedding")

# === Configuration ===
EMBEDDING_MODEL_PATH = os.environ.get("EMBEDDING_MODEL_PATH", "/models/bge-m3")
RERANKER_MODEL_PATH = os.environ.get("RERANKER_MODEL_PATH", "/models/reranker")
MAX_BATCH_SIZE = int(os.environ.get("MAX_BATCH_SIZE", "32"))
MAX_SEQ_LENGTH = 512
RERANKER_MAX_LENGTH = 2048  # For Qwen3 reranker


# === Model Holder ===
class Models:
    embed_session: ort.InferenceSession | None = None
    embed_tokenizer: Tokenizer | None = None
    rerank_session: ort.InferenceSession | None = None
    rerank_tokenizer: Tokenizer | None = None
    embed_dim: int = 1024  # BGE-M3 dense dim
    # Qwen3 reranker specific
    rerank_prefix: str = ""
    rerank_suffix: str = ""
    rerank_prefix_tokens: list = []
    rerank_suffix_tokens: list = []
    token_true_id: int = 0
    token_false_id: int = 0
    is_qwen3_reranker: bool = False


models = Models()


def load_onnx_model(model_dir: str) -> tuple[ort.InferenceSession, Tokenizer]:
    """Load ONNX model and tokenizer."""
    model_path = Path(model_dir)

    # Find ONNX file
    onnx_file = None
    for candidate in ["model.onnx", "model_optimized.onnx", "onnx/model.onnx"]:
        p = model_path / candidate
        if p.exists():
            onnx_file = str(p)
            break
    if not onnx_file:
        # Find any .onnx file
        onnx_files = list(model_path.rglob("*.onnx"))
        if onnx_files:
            onnx_file = str(onnx_files[0])
        else:
            raise FileNotFoundError(f"No .onnx file found in {model_dir}")

    # Load tokenizer
    tokenizer_path = model_path / "tokenizer.json"
    if not tokenizer_path.exists():
        # Search parent directories as well
        for p in model_path.rglob("tokenizer.json"):
            tokenizer_path = p
            break
    if not tokenizer_path.exists():
        raise FileNotFoundError(f"No tokenizer.json found in {model_dir}")

    logger.info(f"Loading ONNX model: {onnx_file}")
    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    opts.inter_op_num_threads = 4
    opts.intra_op_num_threads = 4
    session = ort.InferenceSession(onnx_file, opts, providers=["CPUExecutionProvider"])

    logger.info(f"Loading tokenizer: {tokenizer_path}")
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    tokenizer.enable_truncation(max_length=MAX_SEQ_LENGTH)
    tokenizer.enable_padding(length=MAX_SEQ_LENGTH)

    return session, tokenizer


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models on server start."""
    logger.info("=== NEXUS Embedding Server Starting ===")

    # Load embedding model
    if Path(EMBEDDING_MODEL_PATH).exists():
        models.embed_session, models.embed_tokenizer = load_onnx_model(
            EMBEDDING_MODEL_PATH
        )
        # Check dense dim
        output_names = [o.name for o in models.embed_session.get_outputs()]
        logger.info(f"Embedding model outputs: {output_names}")
        logger.info("Embedding model loaded successfully")
    else:
        logger.warning(f"Embedding model not found at {EMBEDDING_MODEL_PATH}")

    # Load reranker model
    if Path(RERANKER_MODEL_PATH).exists():
        reranker_config = Path(RERANKER_MODEL_PATH) / "config.json"
        # Detect Qwen3 reranker
        is_qwen3 = False
        if reranker_config.exists():
            import json
            with open(reranker_config) as f:
                cfg = json.load(f)
            is_qwen3 = "qwen" in cfg.get("model_type", "").lower()

        if is_qwen3:
            # Qwen3 reranker: separate loading (left padding, prompt format)
            onnx_file = str(Path(RERANKER_MODEL_PATH) / "model.onnx")
            opts = ort.SessionOptions()
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            opts.inter_op_num_threads = 4
            opts.intra_op_num_threads = 4
            models.rerank_session = ort.InferenceSession(
                onnx_file, opts, providers=["CPUExecutionProvider"]
            )
            tokenizer_path = Path(RERANKER_MODEL_PATH) / "tokenizer.json"
            models.rerank_tokenizer = Tokenizer.from_file(str(tokenizer_path))

            # Qwen3 prompt construction
            models.is_qwen3_reranker = True
            models.rerank_prefix = '<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. Note that the answer can only be "yes" or "no".<|im_end|>\n<|im_start|>user\n'
            models.rerank_suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
            models.rerank_prefix_tokens = models.rerank_tokenizer.encode(
                models.rerank_prefix, add_special_tokens=False
            ).ids
            models.rerank_suffix_tokens = models.rerank_tokenizer.encode(
                models.rerank_suffix, add_special_tokens=False
            ).ids
            # yes/no token IDs
            models.token_true_id = models.rerank_tokenizer.token_to_id("yes") or 9693
            models.token_false_id = models.rerank_tokenizer.token_to_id("no") or 2753
            logger.info(f"Qwen3 reranker loaded (yes={models.token_true_id}, no={models.token_false_id})")
        else:
            # Standard cross-encoder
            models.rerank_session, models.rerank_tokenizer = load_onnx_model(
                RERANKER_MODEL_PATH
            )
        logger.info("Reranker model loaded successfully")
    else:
        logger.warning(f"Reranker model not found at {RERANKER_MODEL_PATH}")

    yield
    logger.info("=== NEXUS Embedding Server Shutting Down ===")


app = FastAPI(title="NEXUS Embedding Server", lifespan=lifespan)


# === Schema ===
class EmbedRequest(BaseModel):
    texts: list[str]
    instruction: str = ""  # Query instruction for BGE-M3


class EmbedResponse(BaseModel):
    dense: list[list[float]]
    # sparse is in Qdrant SparseVector format: indices + values
    sparse: list[dict]


class RerankRequest(BaseModel):
    query: str
    documents: list[str]
    top_k: int = 5


class RerankResult(BaseModel):
    index: int
    score: float
    text: str


class RerankResponse(BaseModel):
    results: list[RerankResult]


class HealthResponse(BaseModel):
    status: str
    embedding_loaded: bool
    reranker_loaded: bool


# === Helpers ===
def tokenize_batch(
    tokenizer: Tokenizer, texts: list[str]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Tokenize text and convert to ONNX input format."""
    encodings = tokenizer.encode_batch(texts)
    input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
    attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
    token_type_ids = np.zeros_like(input_ids, dtype=np.int64)
    return input_ids, attention_mask, token_type_ids


def extract_sparse(
    input_ids: np.ndarray, attention_mask: np.ndarray, token_weights: np.ndarray
) -> list[dict]:
    """Extract sparse vectors from token weights (for lexical matching)."""
    results = []
    for i in range(input_ids.shape[0]):
        token_map: dict[int, float] = {}
        for j in range(input_ids.shape[1]):
            if attention_mask[i][j] == 0:
                continue
            tid = int(input_ids[i][j])
            # Exclude special tokens (CLS=101, SEP=102, PAD=0)
            if tid in (0, 101, 102):
                continue
            w = float(token_weights[i][j])
            if w > 0:
                # Use max value if same token appears multiple times
                if tid not in token_map or w > token_map[tid]:
                    token_map[tid] = w
        indices = sorted(token_map.keys())
        values = [token_map[k] for k in indices]
        results.append({"indices": indices, "values": values})
    return results


def mean_pooling(
    last_hidden_state: np.ndarray, attention_mask: np.ndarray
) -> np.ndarray:
    """Mean pooling with attention mask."""
    mask_expanded = np.expand_dims(attention_mask, axis=-1).astype(np.float32)
    sum_embeddings = np.sum(last_hidden_state * mask_expanded, axis=1)
    sum_mask = np.clip(mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)
    return sum_embeddings / sum_mask


def normalize(vectors: np.ndarray) -> np.ndarray:
    """L2 normalization."""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.clip(norms, a_min=1e-9, a_max=None)
    return vectors / norms


# === Endpoints ===
@app.post("/embed", response_model=EmbedResponse)
async def embed(req: EmbedRequest):
    if models.embed_session is None:
        raise HTTPException(503, "Embedding model not loaded")
    if len(req.texts) > MAX_BATCH_SIZE:
        raise HTTPException(400, f"Batch size exceeds maximum ({MAX_BATCH_SIZE})")
    if not req.texts:
        return EmbedResponse(dense=[], sparse=[])

    # Add instruction prefix (for BGE-M3 query)
    texts = req.texts
    if req.instruction:
        texts = [f"{req.instruction}: {t}" for t in texts]

    input_ids, attention_mask, token_type_ids = tokenize_batch(
        models.embed_tokenizer, texts
    )

    inputs = {"input_ids": input_ids, "attention_mask": attention_mask}
    # Only for models that require token_type_ids
    input_names = [inp.name for inp in models.embed_session.get_inputs()]
    if "token_type_ids" in input_names:
        inputs["token_type_ids"] = token_type_ids

    outputs = models.embed_session.run(None, inputs)

    # BGE-M3 ONNX: first output is last_hidden_state
    last_hidden = outputs[0]

    # Dense: mean pooling + L2 normalize
    dense_vecs = normalize(mean_pooling(last_hidden, attention_mask))

    # Sparse: token weight based (using norm of last_hidden as weight)
    token_weights = np.linalg.norm(last_hidden, axis=-1)
    sparse_vecs = extract_sparse(input_ids, attention_mask, token_weights)

    return EmbedResponse(
        dense=dense_vecs.tolist(),
        sparse=sparse_vecs,
    )


@app.post("/rerank", response_model=RerankResponse)
async def rerank(req: RerankRequest):
    if models.rerank_session is None:
        raise HTTPException(503, "Reranker model not loaded")
    if not req.documents:
        return RerankResponse(results=[])

    if models.is_qwen3_reranker:
        scores = _rerank_qwen3(req.query, req.documents)
    else:
        scores = _rerank_cross_encoder(req.query, req.documents)

    # Sort by score in descending order
    indexed = [(i, s, req.documents[i]) for i, s in enumerate(scores)]
    indexed.sort(key=lambda x: x[1], reverse=True)

    results = [
        RerankResult(index=idx, score=score, text=text)
        for idx, score, text in indexed[: req.top_k]
    ]

    return RerankResponse(results=results)


def _rerank_qwen3(query: str, documents: list[str]) -> list[float]:
    """Qwen3 LLM-based reranking: compute score from yes/no probability.

    Memory management: process documents one at a time and run GC after each to prevent OOM.
    """
    import gc

    instruction = "Given a web search query, retrieve relevant passages that answer the query"
    all_scores = []
    max_doc_chars = 1500  # Document text length limit (OOM prevention)

    for doc in documents:
        # Limit document length
        truncated_doc = doc[:max_doc_chars] if len(doc) > max_doc_chars else doc

        text = f"<Instruct>: {instruction}\n<Query>: {query}\n<Document>: {truncated_doc}"
        full = models.rerank_prefix + text + models.rerank_suffix

        # Tokenize (single document)
        enc = models.rerank_tokenizer.encode(full, add_special_tokens=False)
        ids = enc.ids[-RERANKER_MAX_LENGTH:]
        seq_len = len(ids)

        input_ids = np.array([ids], dtype=np.int64)
        attention_mask = np.ones((1, seq_len), dtype=np.int64)
        position_ids = np.arange(seq_len, dtype=np.int64).reshape(1, -1)

        # Inference -- extract yes/no logits from last token only
        logits_np = models.rerank_session.run(
            ["logits"],
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "position_ids": position_ids,
            },
        )[0]

        # Extract yes/no probability only, immediately release remaining logits
        last_logit = logits_np[0, -1, :].astype(np.float32)
        true_score = float(last_logit[models.token_true_id])
        false_score = float(last_logit[models.token_false_id])
        del logits_np, last_logit

        # softmax
        max_s = max(true_score, false_score)
        exp_true = np.exp(true_score - max_s)
        exp_false = np.exp(false_score - max_s)
        yes_prob = float(exp_true / (exp_true + exp_false))

        all_scores.append(yes_prob)

        # GC after each document
        gc.collect()

    return all_scores


def _rerank_cross_encoder(query: str, documents: list[str]) -> list[float]:
    """Standard cross-encoder reranking."""
    scores = []
    for batch_start in range(0, len(documents), MAX_BATCH_SIZE):
        batch_docs = documents[batch_start : batch_start + MAX_BATCH_SIZE]

        encodings = []
        for doc in batch_docs:
            enc = models.rerank_tokenizer.encode(query, doc)
            encodings.append(enc)

        input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)

        inputs = {"input_ids": input_ids, "attention_mask": attention_mask}
        input_names = [inp.name for inp in models.rerank_session.get_inputs()]
        if "token_type_ids" in input_names:
            token_type_ids = np.array([e.type_ids for e in encodings], dtype=np.int64)
            inputs["token_type_ids"] = token_type_ids

        output = models.rerank_session.run(None, inputs)
        logits = output[0]
        if logits.shape[-1] == 1:
            batch_scores = logits.squeeze(-1).tolist()
        else:
            exp = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
            softmax = exp / exp.sum(axis=-1, keepdims=True)
            batch_scores = softmax[:, 1].tolist()

        scores.extend(batch_scores)

    return scores


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        embedding_loaded=models.embed_session is not None,
        reranker_loaded=models.rerank_session is not None,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
