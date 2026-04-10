#!/usr/bin/env bash
# Clean historical thread data before deploying thread isolation.
# This removes checkpoint DBs, memory.json, and .langgraph_api/ state
# so the system starts fresh with per-user ownership mappings.

set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "$0")/../backend" && pwd)"

echo "Cleaning thread data in $BACKEND_DIR ..."

# Checkpoint database files
for f in checkpoints.db checkpoints.db-wal checkpoints.db-shm; do
  target="$BACKEND_DIR/.deer-flow/$f"
  if [ -f "$target" ]; then
    rm -f "$target"
    echo "  Deleted $target"
  fi
done

# Memory file
if [ -f "$BACKEND_DIR/.deer-flow/memory.json" ]; then
  rm -f "$BACKEND_DIR/.deer-flow/memory.json"
  echo "  Deleted $BACKEND_DIR/.deer-flow/memory.json"
fi

# LangGraph API state directory
if [ -d "$BACKEND_DIR/.langgraph_api" ]; then
  rm -rf "$BACKEND_DIR/.langgraph_api"
  echo "  Deleted $BACKEND_DIR/.langgraph_api/"
fi

echo "Done."
