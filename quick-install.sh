#!/bin/bash
#
# Country Blocker - Quick Installer
# Downloads and installs the IPdeny systemctl installer from GitHub
#
# Author: Silvester van der Leer (svdleer)
# Repository: https://github.com/svdleer/countryblocker
# License: MIT
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/svdleer/countryblocker/main/quick-install.sh | sudo bash
#   or
#   wget -qO- https://raw.githubusercontent.com/svdleer/countryblocker/main/quick-install.sh | sudo bash
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

REPO_URL="https://github.com/svdleer/countryblocker.git"
INSTALL_DIR="/tmp/countryblocker-install"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Country Blocker - Quick Installer${NC}"
echo -e "${BLUE}================================================${NC}"
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root${NC}"
   echo "Please run with: sudo bash"
   exit 1
fi

# Check system requirements
echo "Checking system requirements..."

# Check for git
if ! command -v git &> /dev/null; then
    echo -e "${YELLOW}Installing git...${NC}"
    if command -v apt-get &> /dev/null; then
        apt-get update -qq
        apt-get install -y git
    elif command -v yum &> /dev/null; then
        yum install -y git
    else
        echo -e "${RED}Error: Cannot install git automatically${NC}"
        echo "Please install git manually and try again"
        exit 1
    fi
fi

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Installing Python 3...${NC}"
    if command -v apt-get &> /dev/null; then
        apt-get install -y python3 python3-venv
    elif command -v yum &> /dev/null; then
        yum install -y python3
    fi
else
    # Check for python3-venv
    if ! python3 -m venv --help &> /dev/null 2>&1; then
        echo -e "${YELLOW}Installing python3-venv...${NC}"
        if command -v apt-get &> /dev/null; then
            apt-get install -y python3-venv
        fi
    fi
fi

# Check for ipset
if ! command -v ipset &> /dev/null; then
    echo -e "${YELLOW}Installing ipset...${NC}"
    if command -v apt-get &> /dev/null; then
        apt-get install -y ipset
    elif command -v yum &> /dev/null; then
        yum install -y ipset
    fi
fi

# Check for iptables
if ! command -v iptables &> /dev/null; then
    echo -e "${YELLOW}Installing iptables...${NC}"
    if command -v apt-get &> /dev/null; then
        apt-get install -y iptables
    elif command -v yum &> /dev/null; then
        yum install -y iptables
    fi
fi

echo -e "${GREEN}✓ All requirements installed${NC}"
echo

# Check if already installed
if [ -x "/usr/local/bin/ipdeny-ctl" ]; then
    echo -e "${YELLOW}Country Blocker is already installed!${NC}"
    echo
    read -p "Do you want to update to the latest version? [Y/n]: " update_choice
    update_choice=${update_choice:-Y}
    
    if [[ "$update_choice" =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Running update...${NC}"
        echo
        /usr/local/bin/ipdeny-ctl update
        exit $?
    else
        echo "Update cancelled."
        exit 0
    fi
fi

echo -e "${GREEN}Starting fresh installation...${NC}"
echo

# Clean up any previous installation attempts

# Clone repository
echo "Downloading Country Blocker from GitHub..."
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
fi

git clone --quiet "$REPO_URL" "$INSTALL_DIR"
echo -e "${GREEN}✓ Downloaded${NC}"
echo

# Run installer
echo "Running installer..."
cd "$INSTALL_DIR"
bash install.sh

# Cleanup
echo
echo "Cleaning up temporary files..."
cd /
rm -rf "$INSTALL_DIR"
echo -e "${GREEN}✓ Cleanup complete${NC}"

echo
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}   Installation Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo
echo "Pre-configured countries:"
echo "  🇨🇳 China, 🇭🇰 Hong Kong, 🇮🇳 India, 🇰🇷 South Korea, 🇲🇽 Mexico"
echo "  🇵🇰 Pakistan, 🇷🇺 Russia, 🇸🇬 Singapore, 🇹🇼 Taiwan, 🇻🇳 Vietnam"
echo -e "${GREEN}Installation complete!${NC}"
echo
echo "Next steps:"
echo "  1. Check status:     ipdeny-ctl status"
echo "  2. Run first fetch:  sudo ipdeny-fetcher"
echo "  3. View statistics:  ipdeny-ctl stats"
echo "  4. Get help:         ipdeny-ctl --help"
echo
echo "To update later, run:  sudo ipdeny-ctl update"
echo
echo "Documentation: https://github.com/svdleer/countryblocker"
