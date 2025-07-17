#!/bin/bash

echo "=== OptiScaler Manager Desktop Integration ==="
echo "Installing desktop entry and creating application launcher..."

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Make all relevant scripts executable
chmod +x "$SCRIPT_DIR/run.sh"
chmod +x "$SCRIPT_DIR/launch-gui.sh"
chmod +x "$SCRIPT_DIR/optiscaler_manager.py"

# Create the local applications directory if needed
mkdir -p ~/.local/share/applications

# Dynamically generate the .desktop entry
cat > ~/.local/share/applications/optiscaler-manager.desktop <<EOL
[Desktop Entry]
Version=1.0
Type=Application
Name=OptiScaler Manager
Comment=Manage OptiScaler installations for Steam games
GenericName=Game Enhancement Manager
Icon=${SCRIPT_DIR}/optiscaler-icon.svg
Exec=bash -c '${SCRIPT_DIR}/launch-gui.sh'
Terminal=false
StartupNotify=true
Categories=Game;Utility;
Keywords=optiscaler;fsr;dlss;steam;gaming;upscaling;
Path=${SCRIPT_DIR}
EOL

# Update the desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database ~/.local/share/applications/
    echo "✓ Desktop database updated"
fi

# Optionally create the icon if it doesn't exist
if [ ! -f "$SCRIPT_DIR/optiscaler-icon.svg" ]; then
    echo "Creating application icon..."
    python3 "$SCRIPT_DIR/create-icon.py"
fi

echo "✓ Desktop entry installed to ~/.local/share/applications/"
echo "✓ OptiScaler Manager should now appear in your application menu"
echo "✓ You can also launch it from: Applications > Games > OptiScaler Manager"
echo ""
echo "To uninstall the desktop entry, run:"
echo "rm ~/.local/share/applications/optiscaler-manager.desktop"
echo "update-desktop-database ~/.local/share/applications/"
