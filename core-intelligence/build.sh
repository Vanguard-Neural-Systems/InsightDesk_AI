#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — Core Intelligence Build Script (Render)
# Installs system-level dependencies required by aiortc (WebRTC) before
# running pip install.
# ──────────────────────────────────────────────────────────────────────────────
set -e

echo ">>> Installing system dependencies for aiortc (WebRTC)..."
apt-get update -qq
apt-get install -y --no-install-recommends \
  libavdevice-dev \
  libavfilter-dev \
  libopus-dev \
  libvpx-dev \
  libsrtp2-dev \
  pkg-config

echo ">>> Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ">>> Build complete."
