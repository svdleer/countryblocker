# Quick Start Guide

**Author**: [Silvester van der Leer (svdleer)](https://github.com/svdleer)  
**Repository**: [github.com/svdleer/countryblocker](https://github.com/svdleer/countryblocker)

## Easy One-Line Installation

```bash
curl -sSL https://raw.githubusercontent.com/svdleer/countryblocker/main/quick-install.sh | sudo bash
```

That's it! The installer will automatically:
- Install all dependencies (Python 3, ipset, iptables)
- Download and install Country Blocker
- Configure systemd for daily updates
- Set up 10 pre-configured countries
- Install management tool (`ipdeny-ctl`)

## Post-Install Commands

```bash
# Check system status
ipdeny-ctl status

# View detailed statistics
ipdeny-ctl stats

# Run first fetch manually
sudo ipdeny-fetcher

# View firewall rules
ipdeny-ctl list-rules

# Get help
ipdeny-ctl --help
```

## Manual Installation on Ubuntu 22.04+

```bash
# 1. Clone repository
git clone https://github.com/svdleer/countryblocker.git
cd countryblocker

# 2. Install
sudo ./install.sh

# 3. Check status
ipdeny-ctl status
```

# 3. Run (uses pre-configured 10 countries)
sudo ipdeny-fetcher
# Firewall rules are applied automatically!

# 4. Verify
sudo ipset list | grep ipdeny
sudo iptables -L INPUT -n | grep ipdeny
```
```

## Pre-Configured Countries

The installer is pre-configured to block traffic from:
- 🇨🇳 China (cn)
- 🇭🇰 Hong Kong (hk)
- 🇮🇳 India (in)
- 🇰🇷 South Korea (kr)
- 🇲🇽 Mexico (mx)
- 🇵🇰 Pakistan (pk)
- 🇷🇺 Russia (ru)
- 🇸🇬 Singapore (sg)
- 🇹🇼 Taiwan (tw)
- 🇻🇳 Vietnam (vn)

To customize, edit `/etc/ipdeny/ipdeny.conf`

## Key Commands

```bash
# Check service status
systemctl status ipdeny-fetch.timer
systemctl status ipdeny-fetch.service

# View logs
sudo journalctl -u ipdeny-fetch.service -f
sudo tail -f /var/log/ipdeny-fetch.log

## Common Commands

```bash
# Check system status
ipdeny-ctl status

# View statistics
ipdeny-ctl stats

# Manual fetch
sudo ipdeny-fetcher

# Manual firewall update
sudo ipdeny-firewall-update

# List all firewall rules
ipdeny-ctl list-rules

# Stop services
sudo ipdeny-ctl stop

# Start services
sudo ipdeny-ctl start
```

# Show firewall rules
sudo iptables -L INPUT -n -v | grep ipdeny
```

## Testing on macOS

Since this targets Linux/systemd, use Docker:

```bash
# Run Ubuntu container with systemd
docker run -it --privileged \
  -v $(pwd):/workspace \
  ubuntu:latest /bin/bash

# Inside container:
apt update
apt install -y systemd ipset iptables python3
cd /workspace

# Run tests
./tests/smoke-test.sh

# Test installation (dry run)
./install.sh
```

## Integration Examples

### Default Setup (Automatic)

The system automatically manages firewall rules:

```bash
# Just run the fetcher
sudo ipdeny-fetcher

# Firewall rules are automatically applied
# Check rules:
sudo iptables -L INPUT -n -v | grep ipdeny
```

### Block Pre-configured Countries (Already Done!)

```bash
# Already configured in /etc/ipdeny/ipdeny.conf
# Countries: cn hk in kr mx pk ru sg tw vn

# Fetch and create ipsets
sudo ipdeny-fetcher
# Firewall rules applied automatically!
```

### Customize Firewall Action

```bash
# Edit config
sudo nano /etc/ipdeny/ipdeny.conf
# Change: FIREWALL_ACTION="REJECT"  # or "DROP"

# Update firewall
sudo ipdeny-firewall-update
```

### Add Additional Countries

```bash
# Edit config to add more countries
sudo nano /etc/ipdeny/ipdeny.conf
# Add: COUNTRIES="cn hk in kr mx pk ru sg tw vn ir kp"

# Fetch new countries
sudo ipdeny-fetcher
# Firewall rules updated automatically!
```

### Auto-apply rules on system boot

Create `/etc/iptables/ipdeny-rules.sh`:

```bash
#!/bin/bash
# Restore ipdeny firewall rules

for country in cn ru; do
    iptables -A INPUT -m set --match-set ipdeny-${country}-v4 src -j DROP
    ip6tables -A INPUT -m set --match-set ipdeny-${country}-v6 src -j DROP
done
```

Then add to `/etc/rc.local` or create a systemd unit.

## Uninstall

```bash
sudo ./uninstall.sh
```

## Troubleshooting

**Problem**: ipset command not found  
**Solution**: `sudo apt install ipset`

**Problem**: Permission denied  
**Solution**: Run with `sudo`

**Problem**: Set cannot be destroyed  
**Solution**: Remove iptables rules first:
```bash
sudo iptables -D INPUT -m set --match-set ipdeny-cn-v4 src -j DROP
sudo ipset destroy ipdeny-cn-v4
```

**Problem**: No countries configured warning  
**Solution**: This shouldn't happen with the new installer, but if it does:
```bash
sudo nano /etc/ipdeny/ipdeny.conf
# Set: COUNTRIES="cn hk in kr mx pk ru sg tw vn"
```

## More Information

See [README.md](README.md) for complete documentation.
