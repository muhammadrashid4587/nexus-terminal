#!/bin/bash
# ═══════════════════════════════════════════════
#  N E X U S  —  Launch Script
# ═══════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
CYAN='\033[38;2;0;212;255m'
GREEN='\033[38;2;0;255;136m'
DIM='\033[2m'
RESET='\033[0m'

echo ""
echo -e "${CYAN}  ▸ NEXUS${RESET} ${DIM}initializing...${RESET}"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "  ${CYAN}✗${RESET} Python3 not found. Please install Python 3.10+"
    exit 1
fi

# Create venv if needed
if [ ! -d ".venv" ]; then
    echo -e "  ${CYAN}▸${RESET} Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install deps if needed
if ! python3 -c "import aiohttp" 2>/dev/null || ! python3 -c "import webview" 2>/dev/null; then
    echo -e "  ${CYAN}▸${RESET} Installing dependencies..."
    pip install -q -r requirements.txt
fi

# Check claude CLI
if ! command -v claude &> /dev/null; then
    echo -e "  ${CYAN}✗${RESET} Claude CLI not found. Install from: https://claude.ai/download"
    exit 1
fi

# Set working directory (default: where the user called from, not script dir)
CALLER_DIR="${NEXUS_CWD:-$(cd - > /dev/null 2>&1 && pwd || echo $HOME)}"
export NEXUS_CWD="${CALLER_DIR}"
export NEXUS_PORT="${NEXUS_PORT:-7777}"

echo -e "  ${GREEN}▸${RESET} All systems go."
echo ""

# Launch — pass --browser flag to skip native window
python3 nexus.py "$@"
