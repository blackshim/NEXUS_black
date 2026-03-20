#!/bin/bash
# scripts/setup.sh — NEXUS one-click installation
set -e

echo "=== NEXUS Phase 1 Setup ==="

# 1. Environment variables setup
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Warning: .env file has been created. Please set your API keys:"
    echo "   vi .env"
    exit 1
fi

# 2. Download models
echo "=== Downloading models ==="
bash scripts/download_models.sh

# 3. Start Docker Compose (Qdrant + Redis + Embedding server)
# Ollama runs natively on Windows separately
echo "=== Starting Docker services ==="
docker compose up -d qdrant redis embedding

# 4. Wait for service health checks (max 120 seconds)
echo "=== Waiting for services to be ready ==="
for i in $(seq 1 24); do
    if curl -sf http://localhost:6333/healthz > /dev/null 2>&1 && \
       curl -sf http://localhost:8080/health > /dev/null 2>&1; then
        echo "Qdrant + Embedding server ready"
        break
    fi
    echo "  Waiting... ($((i*5)) seconds)"
    sleep 5
done

# 5. Initialize Qdrant
echo "=== Initializing Qdrant collections ==="
bash scripts/init_qdrant.sh

# 5.5 Start indexing worker (after embedding server is ready)
echo "=== Starting indexing worker ==="
docker compose up -d indexing-worker 2>/dev/null || echo "Indexing worker manual run: cd services/indexing && python worker.py batch /path"

# 6. Check Ollama models (Windows native)
echo "=== Checking Ollama models ==="
if command -v ollama &> /dev/null; then
    ollama list 2>/dev/null || echo "Warning: Ollama is not running. Start it with 'ollama serve'."
    echo "Required model: ollama pull qwen3:4b"
else
    echo "Warning: Ollama is not installed."
    echo "  Windows: https://ollama.ai/download"
    echo "  Linux: curl -fsSL https://ollama.ai/install.sh | sh"
fi

echo ""
echo "NEXUS installation complete!"
echo ""
echo "Access:"
echo "  Qdrant Dashboard: http://localhost:6333/dashboard"
echo "  Embedding Server: http://localhost:8080/health"
echo ""
echo "Next steps:"
echo "  1. Download Ollama model: ollama pull qwen3:4b"
echo "  2. Install OpenClaw: npm install -g openclaw && openclaw onboard"
echo "  3. Index documents: cd services/indexing && python worker.py batch /path/to/docs"
