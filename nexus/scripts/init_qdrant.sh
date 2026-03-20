#!/bin/bash
# scripts/init_qdrant.sh — Initialize Qdrant collections + indexes
# Run once after Docker Compose starts
set -e

QDRANT_URL="http://localhost:6333"
API_KEY="${QDRANT_API_KEY:-nexus-qdrant-change-me}"
AUTH_HEADER="api-key: ${API_KEY}"

echo "=== Creating Qdrant collection ==="
curl -s -X PUT "${QDRANT_URL}/collections/documents" \
    -H "Content-Type: application/json" \
    -H "${AUTH_HEADER}" \
    -d '{
        "vectors": {
            "dense": { "size": 1024, "distance": "Cosine", "on_disk": true }
        },
        "sparse_vectors": {
            "sparse": { "modifier": "idf" }
        },
        "optimizers_config": { "indexing_threshold": 20000 },
        "on_disk_payload": true
    }' && echo " -> Collection created"

echo "=== Creating payload indexes ==="
for field in workspace confidential file_type file_hash file_path file_name language chunk_type parent_id; do
    curl -s -X PUT "${QDRANT_URL}/collections/documents/index" \
        -H "Content-Type: application/json" \
        -H "${AUTH_HEADER}" \
        -d "{\"field_name\": \"${field}\", \"field_schema\": \"keyword\"}" \
    && echo " -> ${field} index created"
done

# Bool index
curl -s -X PUT "${QDRANT_URL}/collections/documents/index" \
    -H "Content-Type: application/json" \
    -H "${AUTH_HEADER}" \
    -d '{"field_name": "is_parent", "field_schema": "bool"}' \
&& echo " -> is_parent index created"

# Datetime index
for field in modified_at indexed_at; do
    curl -s -X PUT "${QDRANT_URL}/collections/documents/index" \
        -H "Content-Type: application/json" \
        -H "${AUTH_HEADER}" \
        -d "{\"field_name\": \"${field}\", \"field_schema\": \"datetime\"}" \
    && echo " -> ${field} index created"
done

echo "=== Qdrant initialization complete ==="
