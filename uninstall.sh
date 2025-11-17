#!/bin/bash
set -e

#!/bin/bash
set -e

# Country Blocker Uninstaller
# Removes ipdeny fetcher and all components
#
# Author: Silvester van der Leer (svdleer)
# Repository: https://github.com/svdleer/countryblocker
# License: MIT

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="/opt/ipdeny"
SYSTEMD_DIR="/etc/systemd/system"
CONFIG_DIR="/etc/ipdeny"
DATA_DIR="/var/lib/ipdeny"

echo "=== IPdeny Systemctl Uninstaller ==="
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root${NC}"
   exit 1
fi

# Stop and disable systemd services
stop_services() {
    echo "Stopping and disabling services..."
    systemctl stop ipdeny-fetch.timer ipdeny-fetch.service ipdeny-web-stats.timer ipdeny-web-stats.service 2>/dev/null || true
    systemctl disable ipdeny-fetch.timer ipdeny-fetch.service ipdeny-web-stats.timer ipdeny-web-stats.service 2>/dev/null || true
    echo -e "${GREEN}✓ Services stopped and disabled${NC}"
}

# Remove systemd units
remove_systemd() {
    echo "Removing systemd units..."
    rm -f "$SYSTEMD_DIR/ipdeny-fetch.service"
    rm -f "$SYSTEMD_DIR/ipdeny-fetch.timer"
    rm -f "$SYSTEMD_DIR/ipdeny-firewall-update.service"
    rm -f "$SYSTEMD_DIR/ipdeny-web-stats.service"
    rm -f "$SYSTEMD_DIR/ipdeny-web-stats.timer"
    systemctl daemon-reload
    echo -e "${GREEN}✓ Systemd units removed${NC}"
}

# Remove binary
remove_binary() {
    echo "Removing binary..."
    rm -f "$INSTALL_DIR/bin/ipdeny-fetcher.py"
    rm -f "$INSTALL_DIR/bin/ipdeny-firewall-update.py"
    rm -f "$INSTALL_DIR/bin/ipdeny-ctl.py"
    rm -f "$INSTALL_DIR/requirements.txt"
    rm -f /usr/local/bin/ipdeny-fetcher
    rm -f /usr/local/bin/ipdeny-firewall-update
    rm -f /usr/local/bin/ipdeny-ctl
    
    # Remove venv
    if [ -d "$INSTALL_DIR/venv" ]; then
        rm -rf "$INSTALL_DIR/venv"
        echo "Removed Python virtual environment"
    fi
    
    # Remove install directory if empty
    if [ -d "$INSTALL_DIR" ]; then
        rmdir "$INSTALL_DIR/bin" 2>/dev/null || true
        rmdir "$INSTALL_DIR" 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✓ Binary removed${NC}"
}

# Remove ipsets
remove_ipsets() {
    if ! command -v ipset &> /dev/null; then
        return
    fi
    
    echo "Checking for ipdeny ipsets..."
    ipsets=$(ipset list -n | grep "^ipdeny-" || true)
    
    if [[ -z "$ipsets" ]]; then
        echo "No ipdeny ipsets found"
        return
    fi
    
    echo "Found ipsets:"
    echo "$ipsets"
    echo
    read -p "Remove all ipdeny ipsets? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "$ipsets" | while read -r setname; do
            echo "Destroying ipset: $setname"
            ipset flush "$setname" 2>/dev/null || true
            ipset destroy "$setname" 2>/dev/null || true
        done
        echo -e "${GREEN}✓ ipsets removed${NC}"
    else
        echo "Skipping ipset removal"
    fi
}

# Remove data and config
remove_data() {
    echo
    read -p "Remove configuration ($CONFIG_DIR)? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$CONFIG_DIR"
        echo -e "${GREEN}✓ Configuration removed${NC}"
    fi
    
    echo
    read -p "Remove data directory ($DATA_DIR)? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$DATA_DIR"
        echo -e "${GREEN}✓ Data directory removed${NC}"
    fi
}

# Main uninstallation
main() {
    stop_services
    remove_systemd
    remove_binary
    remove_ipsets
    remove_data
    
    echo
    echo -e "${GREEN}=========================================="
    echo "Uninstallation Complete!"
    echo "==========================================${NC}"
    echo
    echo "Note: Log file /var/log/ipdeny-fetch.log not removed"
    echo "Remove manually if desired: sudo rm /var/log/ipdeny-fetch.log"
    echo
}

main
