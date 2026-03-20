#!/bin/bash
# scripts/download_models.sh — Download ONNX models
set -e

MODELS_DIR="./models"
mkdir -p "$MODELS_DIR"

echo "=== Downloading BGE-M3 ONNX (embedding) ==="
if [ ! -d "$MODELS_DIR/bge-m3-onnx" ]; then
    pip install huggingface_hub 2>/dev/null || true
    python -c "
from huggingface_hub import snapshot_download
snapshot_download('BAAI/bge-m3', local_dir='$MODELS_DIR/bge-m3-onnx',
    allow_patterns=['onnx/*', 'tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json'])
"
    echo "BGE-M3 complete"
else
    echo "BGE-M3 already exists, skipping"
fi

echo "=== Downloading Qwen3-Reranker-0.6B ONNX (reranker) ==="
if [ ! -d "$MODELS_DIR/qwen3-reranker-0.6b-onnx" ]; then
    python -c "
from huggingface_hub import snapshot_download
snapshot_download('zhiqing/Qwen3-Reranker-0.6B-ONNX', local_dir='$MODELS_DIR/qwen3-reranker-0.6b-onnx')
"
    echo "Qwen3-Reranker complete"
else
    echo "Qwen3-Reranker already exists, skipping"
fi

echo "=== Model download complete ==="
