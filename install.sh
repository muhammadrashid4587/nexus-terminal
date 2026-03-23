#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  N E X U S  —  One-Line Installer
#
#  curl -fsSL https://raw.githubusercontent.com/muhammadrashid4587/nexus-terminal/main/install.sh | bash
#
#  Or clone and run:  ./install.sh
# ═══════════════════════════════════════════════════════════

set -e

R='\033[38;2;255;26;26m'
G='\033[38;2;255;215;0m'
D='\033[2m'
X='\033[0m'

echo ""
echo -e "${R}"
echo '  ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗'
echo '  ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝'
echo '  ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗'
echo '  ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║'
echo '  ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║'
echo '  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝'
echo -e "${X}"
echo -e "  ${D}Personal AI Command Center — Installer${X}"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "  ${R}✗${X} Python 3.10+ required. Install from python.org"
    exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "  ${G}✓${X} Python ${PY_VERSION}"

# Check if we're in the nexus directory (local install) or need to clone
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" 2>/dev/null)" && pwd 2>/dev/null || echo "")"

if [ -f "${SCRIPT_DIR}/pyproject.toml" ]; then
    # Local install
    echo -e "  ${R}▸${X} Installing from local source..."
    cd "$SCRIPT_DIR"
    pip install -e ".[dev]" --quiet 2>/dev/null || pip install -e . --quiet
else
    # Remote install via pip
    echo -e "  ${R}▸${X} Installing from PyPI..."
    pip install nexus-terminal --quiet 2>/dev/null || {
        # Fallback: clone from GitHub
        echo -e "  ${R}▸${X} Cloning from GitHub..."
        INSTALL_DIR="$HOME/.nexus/src"
        mkdir -p "$INSTALL_DIR"
        if [ -d "$INSTALL_DIR/nexus-terminal" ]; then
            cd "$INSTALL_DIR/nexus-terminal" && git pull --quiet
        else
            git clone https://github.com/muhammadrashid4587/nexus-terminal.git "$INSTALL_DIR/nexus-terminal"
            cd "$INSTALL_DIR/nexus-terminal"
        fi
        pip install -e . --quiet
    }
fi

echo -e "  ${G}✓${X} NEXUS installed"

# Verify
if command -v nexus &> /dev/null; then
    echo -e "  ${G}✓${X} 'nexus' command available"
else
    echo ""
    echo -e "  ${R}NOTE:${X} Add pip scripts to your PATH if needed:"
    echo -e "  ${D}  export PATH=\"\$(python3 -m site --user-base)/bin:\$PATH\"${X}"
fi

# Check claude
if command -v claude &> /dev/null; then
    echo -e "  ${G}✓${X} Claude CLI found"
else
    echo -e "  ${D}  ! Claude CLI not found (optional — needed for Claude models)${X}"
fi

# Create config dir
mkdir -p "$HOME/.nexus"

echo ""
echo -e "  ${G}━━━ Ready! ━━━${X}"
echo ""
echo -e "  Launch:"
echo -e "    ${R}nexus${X}                     Open in current directory"
echo -e "    ${R}nexus /path/to/project${X}    Open in specific directory"
echo -e "    ${R}nexus --browser${X}           Open in browser"
echo ""
echo -e "  ${D}Config stored in ~/.nexus/${X}"
echo ""
