#!/usr/bin/env bash
set -euo pipefail

echo "=== Vetra — Veterinary Clinic AI Assistant ==="
echo ""

cd "$(dirname "$0")"

echo "[1/3] Creating Python virtual environment..."
uv sync --reinstall-package openai-agents

echo ""
echo "[2/3] Seeding ChromaDB drug interaction database..."
uv run python -c "
from knowledge import create_vetra_knowledge_base
import chromadb
print('✓ ChromaDB drug interaction database ready')
print('  Database location: ./vetra_chroma')
"

echo ""
echo "[3/3] Setup complete!"
echo ""
echo "To run Vetra in CLI mode:"
echo "  export OPENAI_API_KEY='sk-...'"
echo "  uv run python demo.py --cli"
echo ""
echo "To run Vetra as WhatsApp server:"
echo "  export OPENAI_API_KEY='sk-...'"
echo "  export AK_WHATSAPP__VERIFY_TOKEN='...'"
echo "  export AK_WHATSAPP__ACCESS_TOKEN='...'"
echo "  export AK_WHATSAPP__PHONE_NUMBER_ID='...'"
echo "  uv run python demo.py"
