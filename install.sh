#!/bin/bash
set -e

# Country Blocker Installer
# Installs ipdeny fetcher with systemd integration and ipset support
#
# Author: Silvester van der Leer (svdleer)
# Repository: https://github.com/svdleer/countryblocker
# License: MIT

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Allow custom install directory via environment variable or first argument
INSTALL_DIR="${1:-${IPDENY_INSTALL_DIR:-/opt/ipdeny}}"
SYSTEMD_DIR="/etc/systemd/system"
CONFIG_DIR="/etc/ipdeny"
DATA_DIR="/var/lib/ipdeny"
LOG_DIR="/var/log"

echo "=== Country Blocker Installer ==="
echo "Install directory: $INSTALL_DIR"
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root${NC}"
   echo "Please run: sudo $0"
   exit 1
fi

# Check system requirements
check_requirements() {
    echo "Checking system requirements..."
    
    # Check for systemd
    if ! command -v systemctl &> /dev/null; then
        echo -e "${RED}Error: systemd not found${NC}"
        exit 1
    fi
    
    # Check for Python 3 and venv
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 not found${NC}"
        echo "Please install Python 3: apt install python3 python3-venv / yum install python3"
        exit 1
    fi
    
    # Check for python3-venv
    if ! python3 -m venv --help &> /dev/null; then
        echo -e "${YELLOW}Warning: python3-venv not found${NC}"
        echo "Installing python3-venv..."
        if command -v apt-get &> /dev/null; then
            apt-get install -y python3-venv
        elif command -v yum &> /dev/null; then
            yum install -y python3-venv
        fi
    fi
    
    # Check for ipset
    if ! command -v ipset &> /dev/null; then
        echo -e "${YELLOW}Warning: ipset not found${NC}"
        echo "ipset is required for firewall integration"
        echo "Install with: apt install ipset / yum install ipset"
        read -p "Continue without ipset? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Check for iptables (optional)
    if ! command -v iptables &> /dev/null; then
        echo -e "${YELLOW}Warning: iptables not found${NC}"
    fi
    
    echo -e "${GREEN}✓ Requirements check passed${NC}"
}

# Create directories
create_directories() {
    echo "Creating directories..."
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$DATA_DIR"
    mkdir -p "$LOG_DIR"
    echo -e "${GREEN}✓ Directories created${NC}"
}

# Install binary and setup venv
install_binary() {
    echo "Installing ipdeny-fetcher, firewall-updater, control tool, and web files..."
    mkdir -p "$INSTALL_DIR/bin"
    mkdir -p "$INSTALL_DIR/web"
    install -m 755 bin/ipdeny-fetcher.py "$INSTALL_DIR/bin/ipdeny-fetcher.py"
    install -m 755 bin/ipdeny-firewall-update.py "$INSTALL_DIR/bin/ipdeny-firewall-update.py"
    install -m 755 bin/ipdeny-ctl.py "$INSTALL_DIR/bin/ipdeny-ctl.py"
    
    # Copy web files
    if [ -d "web" ]; then
        cp -r web/* "$INSTALL_DIR/web/"
        echo -e "${GREEN}✓ Installed web dashboard files${NC}"
    fi
    
    # Copy requirements.txt
    if [ -f "requirements.txt" ]; then
        install -m 644 requirements.txt "$INSTALL_DIR/requirements.txt"
    fi
    
    # Create Python virtual environment
    echo "Creating Python virtual environment..."
    python3 -m venv "$INSTALL_DIR/venv"
    
    # Activate venv and install dependencies (if any)
    if [ -f "$INSTALL_DIR/requirements.txt" ]; then
        "$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade pip
        if [ -s "$INSTALL_DIR/requirements.txt" ]; then
            "$INSTALL_DIR/venv/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"
        fi
    fi
    
    # Create wrapper scripts that use venv
    cat > /usr/local/bin/ipdeny-fetcher << EOF
#!/bin/bash
exec $INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/bin/ipdeny-fetcher.py "\$@"
EOF
    chmod +x /usr/local/bin/ipdeny-fetcher
    
    cat > /usr/local/bin/ipdeny-firewall-update << EOF
#!/bin/bash
exec $INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/bin/ipdeny-firewall-update.py "\$@"
EOF
    chmod +x /usr/local/bin/ipdeny-firewall-update
    
    cat > /usr/local/bin/ipdeny-ctl << EOF
#!/bin/bash
exec $INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/bin/ipdeny-ctl.py "\$@"
EOF
    chmod +x /usr/local/bin/ipdeny-ctl
    
    echo -e "${GREEN}✓ Installed scripts to $INSTALL_DIR/bin/${NC}"
    echo -e "${GREEN}✓ Created Python virtual environment${NC}"
    echo -e "${GREEN}✓ Created wrappers: /usr/local/bin/ipdeny-*${NC}"
}

# Install systemd units
install_systemd() {
    echo "Installing systemd units..."
    install -m 644 systemd/ipdeny-fetch.service "$SYSTEMD_DIR/ipdeny-fetch.service"
    install -m 644 systemd/ipdeny-fetch.timer "$SYSTEMD_DIR/ipdeny-fetch.timer"
    
    # Optional: install standalone firewall-update service
    if [ -f "systemd/ipdeny-firewall-update.service" ]; then
        install -m 644 systemd/ipdeny-firewall-update.service "$SYSTEMD_DIR/ipdeny-firewall-update.service"
    fi
    
    echo -e "${GREEN}✓ Installed systemd units${NC}"
}

# Install configuration
install_config() {
    echo "Installing configuration..."
    if [[ -f "$CONFIG_DIR/ipdeny.conf" ]]; then
        echo -e "${YELLOW}Configuration file already exists: $CONFIG_DIR/ipdeny.conf${NC}"
        echo "Backup created: $CONFIG_DIR/ipdeny.conf.bak"
        cp "$CONFIG_DIR/ipdeny.conf" "$CONFIG_DIR/ipdeny.conf.bak"
    fi
    install -m 644 config/example.conf "$CONFIG_DIR/ipdeny.conf"
    echo -e "${GREEN}✓ Installed configuration${NC}"
}

# Reload systemd
reload_systemd() {
    echo "Reloading systemd daemon..."
    systemctl daemon-reload
    echo -e "${GREEN}✓ Systemd reloaded${NC}"
}

# Enable and start service
enable_service() {
    echo
    read -p "Enable and start ipdeny-fetch.timer? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo "Skipping service enable"
        return
    fi
    
    echo "Enabling ipdeny-fetch.timer..."
    systemctl enable ipdeny-fetch.timer
    systemctl start ipdeny-fetch.timer
    echo -e "${GREEN}✓ Timer enabled and started${NC}"
    
    echo
    echo "Timer status:"
    systemctl status ipdeny-fetch.timer --no-pager || true
}

# Configuration prompt
configure_countries() {
    echo
    echo "=========================================="
    echo "Default Configuration Applied"
    echo "=========================================="
    echo
    echo "Pre-configured countries to block:"
    echo "  🇨🇳 China (cn), 🇭🇰 Hong Kong (hk), 🇮🇳 India (in)"
    echo "  🇰🇷 South Korea (kr), 🇲🇽 Mexico (mx), 🇵🇰 Pakistan (pk)"
    echo "  🇷🇺 Russia (ru), 🇸🇬 Singapore (sg), 🇹🇼 Taiwan (tw), 🇻🇳 Vietnam (vn)"
    echo
    echo "To customize the country list:"
    echo "  sudo nano $CONFIG_DIR/ipdeny.conf"
    echo
    echo "Available country codes: http://www.ipdeny.com/ipblocks/"
    echo
}

# Show next steps
show_next_steps() {
    echo
    echo "=========================================="
    echo "Installation Complete!"
    echo "=========================================="
    echo
    echo -e "${GREEN}✓ Country Blocker installed successfully${NC}"
    echo
    echo "Configuration: $CONFIG_DIR/ipdeny.conf"
    echo "Zone files:    /var/lib/ipdeny/"
    echo "Logs:          /var/log/ipdeny-fetch.log"
    echo
    echo "Quick commands:"
    echo "  • Check status:  ipdeny-ctl status"
    echo "  • View stats:    ipdeny-ctl stats"
    echo "  • First fetch:   sudo ipdeny-fetcher"
    echo "  • Get help:      ipdeny-ctl --help"
    echo
    
    # Ask about web dashboard setup
    echo "=========================================="
    echo "Web Dashboard Setup (Optional)"
    echo "=========================================="
    echo
    echo "Would you like to set up the web dashboard?"
    echo "(Provides a secure web interface to monitor statistics)"
    echo
    read -p "Install web dashboard? [y/N]: " setup_web
    
    if [[ "$setup_web" =~ ^[Yy]$ ]]; then
        echo
        echo "Enter web root path (examples):"
        echo "  • Apache/Nginx: /var/www/html/countryblocker"
        echo "  • Plesk:        /var/www/vhosts/domain.com/httpdocs/countryblocker"
        echo
        read -p "Path: " webroot_path
        
        if [ -n "$webroot_path" ]; then
            echo
            /usr/local/bin/ipdeny-ctl setup-web "$webroot_path"
            
            echo
            read -p "Configure authentication? [Y/n]: " setup_auth
            setup_auth=${setup_auth:-Y}
            
            if [[ "$setup_auth" =~ ^[Yy]$ ]]; then
                echo
                read -p "Username [admin]: " web_user
                web_user=${web_user:-admin}
                /usr/local/bin/ipdeny-ctl setup-auth "$webroot_path" "$web_user"
            fi
            
            # Ask about automatic web stats updates
            echo
            read -p "Enable automatic web statistics updates (every 5 minutes)? [Y/n]: " enable_web_timer
            enable_web_timer=${enable_web_timer:-Y}
            
            if [[ "$enable_web_timer" =~ ^[Yy]$ ]]; then
                echo
                echo "Enabling web statistics timer..."
                systemctl enable ipdeny-web-stats.timer
                systemctl start ipdeny-web-stats.timer
                echo -e "${GREEN}✓ Web statistics timer enabled${NC}"
                echo "Statistics will update every 5 minutes automatically"
            else
                echo
                echo "You can enable automatic updates later with:"
                echo "  sudo systemctl enable ipdeny-web-stats.timer"
                echo "  sudo systemctl start ipdeny-web-stats.timer"
            fi
            
            echo
            echo -e "${GREEN}✓ Web dashboard ready!${NC}"
            echo "Access at: https://your-domain.com/${webroot_path##*/}/"
        fi
    else
        echo
        echo "You can set up the web dashboard later with:"
        echo "  sudo ipdeny-ctl setup-web /path/to/webroot"
    fi
    
    echo
    echo "=========================================="
}

# Main installation
main() {
    check_requirements
    create_directories
    install_binary
    install_systemd
    install_config
    reload_systemd
    enable_service
    configure_countries
    show_next_steps
}

main
