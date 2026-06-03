#!/bin/bash
# YT AI Editor — macOS Installer
# Double-click this file in Finder to run, or: bash install_mac.command

set -e
cd "$(dirname "$0")"

echo "============================================================"
echo " YT AI Editor — macOS Installer"
echo "============================================================"
echo

# ── Python check ──────────────────────────────────────────────
check_python() {
    for cmd in python3 python3.12 python3.11 python3.10; do
        if command -v "$cmd" &>/dev/null; then
            ver=$("$cmd" --version 2>&1 | awk '{print $2}')
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON=$(check_python) || {
    echo "[ERROR] Python 3.10+ not found."
    echo "  Install via Homebrew:  brew install python"
    echo "  Or download from https://python.org"
    echo
    read -p "Press Enter to exit..."
    exit 1
}
echo "[OK] Python found: $($PYTHON --version)"

# ── FFmpeg check ──────────────────────────────────────────────
if ! command -v ffmpeg &>/dev/null; then
    echo
    echo "[WARNING] FFmpeg not found."
    echo "  Install via Homebrew:  brew install ffmpeg"
    echo "  Recording will not work without FFmpeg."
    echo "  You can still use the Process page with existing video files."
    echo
    read -p "Continue anyway? (y/n): " CONT
    [[ "${CONT,,}" != "y" ]] && exit 1
else
    echo "[OK] FFmpeg found."
fi

# ── Virtual environment ───────────────────────────────────────
if [ ! -d ".venv" ]; then
    echo
    echo "Creating virtual environment..."
    $PYTHON -m venv .venv
    echo "[OK] Virtual environment created."
else
    echo "[OK] Virtual environment already exists."
fi

source .venv/bin/activate

# ── Dependencies ──────────────────────────────────────────────
echo
echo "Installing dependencies (this may take a few minutes)..."
pip install --upgrade pip --quiet
pip install -r requirements.txt
echo "[OK] Dependencies installed."

# ── .env template ─────────────────────────────────────────────
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo "[OK] Created .env from template. Edit it with your API key."
fi

# ── Output directories ────────────────────────────────────────
python -c "from src.utils.config import get_settings; get_settings().ensure_dirs()" 2>/dev/null || true

# ── Launch script ─────────────────────────────────────────────
cat > launch_mac.command << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
python app.py
EOF
chmod +x launch_mac.command
echo "[OK] Created launch_mac.command"

# ── macOS permissions reminder ────────────────────────────────
echo
echo "============================================================"
echo " Installation complete!"
echo "============================================================"
echo
echo " Next steps:"
echo "   1. Edit .env and add your ANTHROPIC_API_KEY"
echo "   2. Double-click launch_mac.command to start the app"
echo "      (or run: source .venv/bin/activate && python app.py)"
echo "   3. The browser opens automatically at http://localhost:8080"
echo
echo " macOS permissions you may need to grant:"
echo "   - Screen Recording: System Settings → Privacy → Screen Recording"
echo "   - Camera: System Settings → Privacy → Camera"
echo "   - Microphone: System Settings → Privacy → Microphone"
echo
echo " See SETUP.md for YouTube upload and webcam setup."
echo
read -p "Press Enter to close this window..."
