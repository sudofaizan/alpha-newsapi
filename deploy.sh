#!/bin/bash
# deploy.sh — one-shot setup for ff_news.py on Amazon Linux 2
# Usage: bash deploy.sh
# After running, use: python3 ff_news.py [--full | --full-latest | --watch 60 | --json]

set -e
echo "=== AlphaFX NewsAPI deploy ==="

# ── 1. System packages ───────────────────────────────────────────────────────
echo "[1/4] Installing system dependencies..."
sudo yum update -y -q
sudo yum install -y -q python3 python3-pip wget curl unzip \
    atk cups-libs gtk3 libXcomposite libXcursor libXdamage \
    libXext libXi libXrandr libXScrnSaver libXtst pango \
    alsa-lib libdrm libgbm libxkbcommon nss mesa-libgbm \
    xorg-x11-fonts-100dpi xorg-x11-fonts-75dpi \
    xorg-x11-utils xorg-x11-fonts-cyrillic xorg-x11-fonts-Type1 \
    xorg-x11-fonts-misc \
    2>/dev/null || true   # some packages may not exist on all AL2 variants

# ── 2. Python packages ───────────────────────────────────────────────────────
echo "[2/4] Installing Python packages..."
# Ensure pip3 is available (Amazon Linux 2 may not ship it by default)
if ! command -v pip3 &>/dev/null; then
    sudo yum install -y -q python3-pip 2>/dev/null || \
    python3 -m ensurepip --upgrade 2>/dev/null || \
    curl -s https://bootstrap.pypa.io/get-pip.py | sudo python3
fi
pip3 install --quiet playwright

# ── 3. Playwright + Chromium ─────────────────────────────────────────────────
echo "[3/4] Installing Playwright Chromium browser..."
python3 -m playwright install chromium
python3 -m playwright install-deps chromium 2>/dev/null || true

# ── 4. Smoke test ────────────────────────────────────────────────────────────
echo "[4/4] Smoke test..."
python3 -c "from playwright.sync_api import sync_playwright; print('playwright OK')"
python3 -c "import json, re, sys, time, argparse; print('stdlib OK')"

echo ""
echo "=== Deploy complete ==="
echo ""
echo "Usage:"
echo "  python3 ff_news.py                  # latest 5 headlines + preview"
echo "  python3 ff_news.py --full-latest    # latest item, full body, JSON"
echo "  python3 ff_news.py --full           # all items with full body"
echo "  python3 ff_news.py --json           # all items as JSON"
echo "  python3 ff_news.py --watch 60       # poll every 60s, print new items only"
