#!/bin/bash
# scripts/backup_qdrant.sh — Qdrant snapshot backup
# Cron registration: 0 2 * * * /path/to/nexus/scripts/backup_qdrant.sh
set -e

QDRANT_URL="http://localhost:6333"
API_KEY="${QDRANT_API_KEY}"
BACKUP_DIR="/backups/qdrant/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

echo "Creating Qdrant snapshot..."
SNAPSHOT=$(curl -s -X POST "${QDRANT_URL}/collections/documents/snapshots" \
    -H "api-key: ${API_KEY}" | jq -r '.result.name')

echo "Downloading snapshot: ${SNAPSHOT}"
curl -s "${QDRANT_URL}/collections/documents/snapshots/${SNAPSHOT}" \
    -H "api-key: ${API_KEY}" \
    -o "${BACKUP_DIR}/${SNAPSHOT}"

echo "Deleting backups older than 7 days..."
find /backups/qdrant -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true

echo "Backup complete: ${BACKUP_DIR}/${SNAPSHOT}"
