#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/siemens-s7-1200-plcopen-builder.desktop"
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Siemens S7-1200 PLCopen XML Builder
Comment=Build PLCopen TC6 XML with Siemens S7-1200 hardware metadata
Exec=$PROJECT_DIR/run.sh
Path=$PROJECT_DIR
Terminal=false
Categories=Development;Engineering;
StartupNotify=true
EOF
chmod +x "$DESKTOP_FILE"
echo "Installed $DESKTOP_FILE"
