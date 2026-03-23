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

# ── Install pipx if needed ──
if ! command -v pipx &> /dev/null; then
    echo -e "  ${R}▸${X} Installing pipx..."
    if command -v brew &> /dev/null; then
        brew install pipx --quiet 2>/dev/null
        pipx ensurepath 2>/dev/null
    else
        python3 -m pip install --user pipx 2>/dev/null || {
            echo -e "  ${R}✗${X} Could not install pipx. Install manually: brew install pipx"
            exit 1
        }
        python3 -m pipx ensurepath 2>/dev/null
    fi
    # Reload PATH
    export PATH="$HOME/.local/bin:$PATH"
fi
echo -e "  ${G}✓${X} pipx ready"

# ── Check if local source or remote ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" 2>/dev/null)" && pwd 2>/dev/null || echo "")"

if [ -f "${SCRIPT_DIR}/pyproject.toml" ]; then
    echo -e "  ${R}▸${X} Installing from local source..."
    cd "$SCRIPT_DIR"
    pipx install -e . --force 2>/dev/null || pipx install . --force
else
    echo -e "  ${R}▸${X} Installing from GitHub..."
    pipx install "git+https://github.com/muhammadrashid4587/nexus-terminal.git" --force
fi

echo -e "  ${G}✓${X} NEXUS installed"

# ── Inject extra deps that pipx might miss ──
pipx inject nexus-terminal pywebview psutil 2>/dev/null || true

# Verify
if command -v nexus &> /dev/null; then
    echo -e "  ${G}✓${X} 'nexus' command available"
else
    export PATH="$HOME/.local/bin:$PATH"
    if command -v nexus &> /dev/null; then
        echo -e "  ${G}✓${X} 'nexus' command available"
        echo -e "  ${R}NOTE:${X} Add this to your ~/.zshrc:"
        echo -e "  ${D}  export PATH=\"\$HOME/.local/bin:\$PATH\"${X}"
    else
        echo -e "  ${R}!${X} Run: ${G}export PATH=\"\$HOME/.local/bin:\$PATH\"${X}"
    fi
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
echo -e "    ${R}nexus${X}                     Native window"
echo -e "    ${R}nexus -i${X}                  Inline (current terminal)"
echo -e "    ${R}nexus --browser${X}           Browser"
echo ""
echo -e "  ${D}Config: ~/.nexus/${X}"
echo ""
