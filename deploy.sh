#!/bin/bash
# deploy.sh — one-shot setup for ff_news.py on Amazon Linux 2
# Usage: bash deploy.sh
# After running, use: python3 ff_news.py [--full | --full-latest | --watch 60 | --json]

set -e
echo "=== AlphaFX NewsAPI deploy ==="

# ── 1. pip3 ──────────────────────────────────────────────────────────────────
echo "[1/4] Installing pip3..."
if ! command -v pip3 &>/dev/null; then
    curl -s https://bootstrap.pypa.io/get-pip.py | sudo python3
fi

# ── 2. Playwright Python package ─────────────────────────────────────────────
echo "[2/4] Installing Playwright..."
pip3 install --quiet playwright

# ── 3. Chromium + all system deps ────────────────────────────────────────────
echo "[3/4] Installing Chromium + system dependencies..."

PKGS="atk at-spi2-atk at-spi2-core cups-libs gtk3 \
      libXcomposite libXcursor libXdamage libXext \
      libXi libXrandr libXScrnSaver libXtst \
      pango mesa-libgbm nss nspr alsa-lib libdrm libxkbcommon \
      xorg-x11-fonts-Type1 xorg-x11-fonts-misc"

if command -v dnf &>/dev/null; then
    # Amazon Linux 2023
    sudo dnf install -y $PKGS 2>/dev/null || true
else
    # Amazon Linux 2 — enable EPEL first for libXcomposite etc.
    sudo amazon-linux-extras install epel -y 2>/dev/null || true
    sudo yum install -y $PKGS 2>/dev/null || true
fi

# Install Playwright's Chromium binary
python3 -m playwright install chromium

# ── 4. Smoke test ────────────────────────────────────────────────────────────
echo "[4/4] Smoke test..."
python3 -c "from playwright.sync_api import sync_playwright; print('playwright OK')"

echo ""
echo "=== Deploy complete ==="
echo ""
echo "Usage:"
echo "  python3 ff_news.py                  # latest 5 headlines + preview"
echo "  python3 ff_news.py --full-latest    # latest item, full body, JSON"
echo "  python3 ff_news.py --full           # all items with full body"
echo "  python3 ff_news.py --json           # all items as JSON"
echo "  python3 ff_news.py --watch 60       # poll every 60s, print new items only"
