# Country Blocker (IPdeny Systemctl Installer)

Automated installation and management of [ipdeny.com](http://www.ipdeny.com/) IP blocklists with systemd, ipset, and iptables integration.

**Author**: [Silvester van der Leer (svdleer)](https://github.com/svdleer)  
**Repository**: [github.com/svdleer/countryblocker](https://github.com/svdleer/countryblocker)  
**License**: MIT

**Target Platform**: Ubuntu 22.04+ (compatible with other systemd-based Linux distributions)

**Default Configuration**: Pre-configured to block traffic from China, Hong Kong, India, South Korea, Mexico, Pakistan, Russia, Singapore, Taiwan, and Vietnam.

## 🚀 Quick Install (One-Line)

Install directly from GitHub on your Ubuntu server:

```bash
curl -sSL https://raw.githubusercontent.com/svdleer/countryblocker/main/quick-install.sh | sudo bash
```

Or using wget:

```bash
wget -qO- https://raw.githubusercontent.com/svdleer/countryblocker/main/quick-install.sh | sudo bash
```

This will:
- ✅ Install all dependencies (Python 3, ipset, iptables)
- ✅ Clone the repository
- ✅ Run the installer
- ✅ Configure systemd timer for daily updates
- ✅ Set up 10 pre-configured countries to block
- ✅ Install management tool: `ipdeny-ctl`

## Features

- **Automated Downloads**: Fetches country-based IP blocklists from ipdeny.com
- **systemd Integration**: Runs as a systemd service with configurable timer
- **ipset Support**: Efficient IP list management using ipset (hash:net)
- **iptables Ready**: Easy integration with existing iptables/ip6tables rules
- **Atomic Updates**: Safe ipset swap/flush operations without firewall disruption
- **IPv4 + IPv6**: Full support for both protocol versions
- **Logging**: Comprehensive logging to syslog and file
- **Configurable**: Easy configuration via `/etc/ipdeny/ipdeny.conf`

## Requirements

- Ubuntu 22.04+ (or any Linux with systemd)
- Python 3.6+
- `ipset` (for efficient blocklist management)
- `iptables` / `ip6tables` (for firewall integration)
- Root/sudo privileges

### Install Requirements (Ubuntu)
```bash
sudo apt update
sudo apt install python3 ipset iptables
```

**Other Distributions:**

For RHEL/CentOS/Fedora:
```bash
sudo yum install python3 ipset iptables
```

## Quick Start

### Method 1: One-Line Install (Recommended)

```bash
curl -sSL https://raw.githubusercontent.com/svdleer/countryblocker/main/quick-install.sh | sudo bash
```

### Method 2: Manual Install

```bash
git clone https://github.com/svdleer/countryblocker.git
cd countryblocker
sudo ./install.sh

# Or install to custom location:
sudo ./install.sh /usr/local/ipdeny
# Or set environment variable:
sudo IPDENY_INSTALL_DIR=/usr/local/ipdeny ./install.sh
```

## Updating

To update to the latest version:

### ⚡ Recommended: Use Built-in Update Command

```bash
sudo ipdeny-ctl update
```

This will:
- ✅ Download latest version from GitHub
- ✅ Update all scripts (fetcher, firewall-update, ctl)
- ✅ Update web dashboard files
- ✅ Update systemd units
- ✅ **Preserve your configuration** in `/etc/ipdeny/`
- ✅ **Preserve your data** in `/var/lib/ipdeny/`
- ✅ Keep all ipsets and firewall rules

### 🔄 Alternative: Re-run Quick Installer

```bash
curl -sSL https://raw.githubusercontent.com/svdleer/countryblocker/main/quick-install.sh | sudo bash
```

The quick installer now **detects existing installations** and offers to update:

```bash
Country Blocker is already installed!

Do you want to update to the latest version? [Y/n]: y
Running update...
✓ Update complete!
```

### 📋 Example Update Output
```bash
$ sudo ipdeny-ctl update

=== Country Blocker Update ===

Updating to latest version from GitHub...

1. Downloading latest version...
   ✓ Downloaded

2. Backing up configuration...
   ✓ Backed up to /etc/ipdeny.backup

3. Updating scripts...
   ✓ Updated ipdeny-fetcher.py
   ✓ Updated ipdeny-firewall-update.py
   ✓ Updated ipdeny-ctl.py

4. Updating web files...
   ✓ Updated web/index.php
   ✓ Updated web/.htaccess

5. Updating systemd units...
   ✓ Updated ipdeny-fetch.service
   ✓ Updated ipdeny-fetch.timer
   ✓ Updated ipdeny-web-stats.timer

6. Reloading systemd...
   ✓ Reloaded

✓ Update complete!

Updated components:
  - ipdeny-fetcher
  - ipdeny-firewall-update
  - ipdeny-ctl
  - Web dashboard
  - Systemd units

Your configuration and data were preserved.

Recommended: Restart services
  sudo systemctl restart ipdeny-fetch.timer
  sudo systemctl restart ipdeny-web-stats.timer
```

### Alternative: Manual Update

```bash
cd /path/to/countryblocker
git pull origin main
sudo ./install.sh
```

### Option 3: Update Scripts Only

If you only want to update the fetcher and firewall scripts:

```bash
# Download latest versions
sudo curl -o /opt/ipdeny/bin/ipdeny-fetcher.py \
  https://raw.githubusercontent.com/svdleer/countryblocker/main/bin/ipdeny-fetcher.py
sudo curl -o /opt/ipdeny/bin/ipdeny-firewall-update.py \
  https://raw.githubusercontent.com/svdleer/countryblocker/main/bin/ipdeny-firewall-update.py

# Make executable
sudo chmod +x /opt/ipdeny/bin/*.py

# Restart services
sudo systemctl daemon-reload
sudo systemctl restart ipdeny-fetch.service
```

**Note:** Your configuration (`/etc/ipdeny/ipdeny.conf`), data (`/var/lib/ipdeny`), and ipsets are preserved during updates.

The installer will:
- Install the fetcher script to `/opt/ipdeny/bin/`
- Create Python virtual environment at `/opt/ipdeny/venv/`
- Create wrapper script at `/usr/local/bin/ipdeny-fetcher`
- Install systemd units to `/etc/systemd/system/`
- Create configuration at `/etc/ipdeny/ipdeny.conf`
- Enable and start the daily update timer

**Default countries blocked**: China (cn), Hong Kong (hk), India (in), South Korea (kr), Mexico (mx), Pakistan (pk), Russia (ru), Singapore (sg), Taiwan (tw), Vietnam (vn)

### 2. Configure (Optional)

The installer comes pre-configured with common countries to block. To customize:

```bash
sudo nano /etc/ipdeny/ipdeny.conf
```

Example configuration:
```bash
# Pre-configured countries (you can modify this list)
COUNTRIES="cn hk in kr mx pk ru sg tw vn"
FETCH_IPV4="true"
FETCH_IPV6="true"
IPSET_ENABLED="true"
```

Available country codes: [ipdeny.com/ipblocks](http://www.ipdeny.com/ipblocks/)

### 3. Run Initial Fetch

```bash
sudo ipdeny-fetcher
# or: sudo /opt/ipdeny/bin/ipdeny-fetcher.py
```

This will:
- Download zone files for configured countries (default: cn, hk, in, kr, mx, pk, ru, sg, tw, vn)
- Create ipsets (e.g., `ipdeny-cn-v4`, `ipdeny-cn-v6`)
- Populate ipsets with IP ranges (using atomic swap)
- Flush old entries and update with new data
- Save zone files to `/var/lib/ipdeny/`
- **Automatically apply iptables rules** for all ipsets

### 4. Verify Firewall Rules

```bash
# Check iptables rules
sudo iptables -L INPUT -n -v | grep ipdeny
sudo ip6tables -L INPUT -n -v | grep ipdeny

# Check which IPs are being blocked
sudo ipset list ipdeny-cn-v4 | head -20
```

The firewall rules are automatically managed - you don't need to run the examples script anymore!

## Management Tool: ipdeny-ctl

A comprehensive control tool for managing Country Blocker:

```bash
# Show system status
ipdeny-ctl status

# Show detailed statistics per ipset
ipdeny-ctl stats

# List all firewall rules
ipdeny-ctl list-rules

# Flush all ipsets (clear IPs, keep structure)
sudo ipdeny-ctl flush

# Remove all firewall rules
sudo ipdeny-ctl remove-rules

# Stop services
sudo ipdeny-ctl stop

# Start services
sudo ipdeny-ctl start

# Generate web dashboard statistics
sudo ipdeny-ctl update-web

# Deploy web dashboard to webroot
sudo ipdeny-ctl setup-web /var/www/html/countryblocker

# Complete uninstall (interactive)
sudo ipdeny-ctl uninstall
```

## Web Dashboard

A secure, responsive PHP dashboard for monitoring Country Blocker status in real-time.

### Features

- 📊 Real-time statistics with auto-refresh
- 🔒 Secure read-only design with security headers
- 📱 Mobile-friendly responsive layout
- 🎨 Modern gradient interface
- 🛡️ HTTP Basic Auth support (recommended)
- 🔐 Automatic authentication setup

### Security Features

**Built-in Security:**
- ✅ Read-only dashboard (no write operations)
- ✅ No user input processing
- ✅ Security headers (CSP, X-Frame-Options, XSS Protection)
- ✅ Sensitive file protection (.htpasswd, stats.json)
- ✅ HTTPS enforcement (optional)

**Authentication (Recommended):**
- ✅ HTTP Basic Authentication
- ✅ Password-protected access
- ✅ Configurable usernames
- ✅ One-command setup

### Quick Setup

```bash
# 1. Deploy to your webroot (auto-detects correct user/group)
sudo ipdeny-ctl setup-web /var/www/html/countryblocker

# Automatically:
# - Detects and sets correct user:group (www-data, domain user, etc)
# - Sets proper permissions (755/644)
# - Creates default .htpasswd with credentials: ipdeny / stats
# - Enables authentication in .htaccess

# ⚠️ IMPORTANT: Change default password immediately!
sudo ipdeny-ctl setup-auth /var/www/html/countryblocker ipdeny
# Enter new password when prompted

# Or create a different admin user:
sudo ipdeny-ctl setup-auth /var/www/html/countryblocker admin

# 2. Generate statistics
sudo ipdeny-ctl update-web

# 3. Enable automatic updates (every 5 minutes)
sudo systemctl enable ipdeny-web-stats.timer
sudo systemctl start ipdeny-web-stats.timer

# 4. For Plesk servers (same process)
sudo ipdeny-ctl setup-web /var/www/vhosts/yourdomain.com/httpdocs/countryblocker
sudo ipdeny-ctl setup-auth /var/www/vhosts/yourdomain.com/httpdocs/countryblocker admin

# 5. Access dashboard
# Visit: https://your-domain.com/countryblocker/
# Default: ipdeny / stats (change this!)
```

**🔐 Default Credentials:**
- Username: `ipdeny`
- Password: `stats`
- **⚠️ CHANGE THESE IMMEDIATELY!** Use `setup-auth` command.

**Note**: The installer will prompt you to enable automatic web statistics updates during installation.

**Note**: The installer will prompt you to enable automatic web statistics updates during installation.

### Example Output

```bash
$ ipdeny-ctl status
=== Country Blocker Status ===

Systemd Services:
  ✓ ipdeny-fetch.service: active
  ✓ ipdeny-fetch.timer: active

ipsets: 20 total
  IPv4: 10
  IPv6: 10

Firewall Rules:
  IPv4: 10 rules
  IPv6: 10 rules

Blocked Countries (10): cn, hk, in, kr, mx, pk, ru, sg, tw, vn
```

```bash
$ ipdeny-ctl stats
=== ipset Statistics ===

Name                      Entries      Memory          Refs     Hits (pkts)     Blocked        
---------------------------------------------------------------------------------------------------------
ipdeny-cn-v4              8234         401KB           1        12,543          45.2MB         
ipdeny-cn-v6              3045         166KB           1        892             3.1MB          
ipdeny-hk-v4              892          47KB            1        45              156KB          
...
---------------------------------------------------------------------------------------------------------
Total IP entries: 125,432
Total blocked packets: 45,892
Total blocked traffic: 156.8MB
```

### Automatic Firewall Management

The system automatically manages your firewall rules:

1. **Fetch**: `ipdeny-fetcher` downloads IP lists and updates ipsets
2. **Update**: `ipdeny-firewall-update` automatically runs after fetcher completes
3. **Sync**: Adds iptables rules for new ipsets, removes rules for deleted ipsets
4. **Daily**: Timer runs both scripts daily at 3 AM

You don't need to manually manage iptables rules - the system handles everything automatically!

### ipset Integration

The fetcher uses **atomic swap operations** to update ipsets without disrupting active firewall rules:

1. Creates a temporary ipset (`ipdeny-cn-v4-tmp`)
2. Populates it with new IP ranges
3. Swaps/renames to the active name (`ipdeny-cn-v4`)
4. iptables rules continue working seamlessly

### Existing iptables Compatibility

The system is designed to **work alongside your existing iptables rules**:
- Uses ipset matching (`-m set --match-set`)
- Never modifies existing iptables chains
- Safe to add/remove rules manually
- Examples show integration with INPUT/FORWARD chains

### ipset Flush and Destroy

The fetcher handles ipset lifecycle carefully:
- **Flush**: Clears all IPs from a set (safe even when in use by iptables) - logged as "cleared all entries"
- **Destroy**: Removes the set completely (may fail if referenced by iptables)
- **Auto-flush**: Enabled by default (`IPSET_AUTO_FLUSH="true"`)
- **Atomic updates**: Uses temporary sets and swap to avoid disruption

If you need to manually manage ipsets:
```bash
# List all ipdeny ipsets
sudo ipset list | grep ipdeny

# Flush a specific ipset
sudo ipset flush ipdeny-cn-v4

# Destroy (remove iptables rules first)
sudo iptables -D INPUT -m set --match-set ipdeny-cn-v4 src -j DROP
sudo ipset destroy ipdeny-cn-v4
```

## Usage

### Manual Firewall Update

If you need to manually update firewall rules:

```bash
sudo ipdeny-firewall-update
```

This will sync iptables rules with current ipsets.

### Check Service Status

```bash
# Check timer status
systemctl status ipdeny-fetch.timer

# Check last run
systemctl status ipdeny-fetch.service

# View logs
sudo journalctl -u ipdeny-fetch.service -f
sudo tail -f /var/log/ipdeny-fetch.log
```

### Manual Fetch

```bash
sudo ipdeny-fetcher
# or: sudo /opt/ipdeny/bin/ipdeny-fetcher.py
```

### List ipsets

```bash
sudo ipset list | grep ipdeny
```

### Show Statistics

```bash
# Show number of IPs in each set
for set in $(sudo ipset list -n | grep ipdeny); do
    echo -n "$set: "
    sudo ipset list $set | grep "Number of entries:" | awk '{print $4}'
done
```

### Apply/Remove Firewall Rules

```bash
# Apply blocking rules
sudo ./examples/apply-firewall-rules.sh apply

# Remove blocking rules
sudo ./examples/apply-firewall-rules.sh remove

# Show current rules
sudo ./examples/apply-firewall-rules.sh show
```

## Configuration Reference

Configuration file: `/etc/ipdeny/ipdeny.conf`

| Option | Default | Description |
|--------|---------|-------------|
| `OUTPUT_DIR` | `/var/lib/ipdeny` | Directory for zone files |
| `COUNTRIES` | `"cn hk in kr mx pk ru sg tw vn"` | Space-separated country codes |
| `FETCH_IPV4` | `true` | Download IPv4 lists |
| `FETCH_IPV6` | `true` | Download IPv6 lists |
| `IPSET_ENABLED` | `true` | Create and populate ipsets |
| `IPSET_PREFIX` | `ipdeny` | Prefix for ipset names |
| `IPSET_AUTO_FLUSH` | `true` | Flush ipsets before updating |
| `IPSET_HASHSIZE` | `4096` | ipset hash table size |
| `IPSET_MAXELEM` | `65536` | Maximum elements per ipset |
| `HTTP_TIMEOUT` | `30` | HTTP request timeout in seconds |
| `HTTP_RETRIES` | `3` | Number of retry attempts for failed downloads |
| `HTTP_RETRY_DELAY` | `5` | Base delay between retries (exponential backoff) |
| `FIREWALL_ENABLED` | `true` | Automatically update iptables rules |
| `FIREWALL_ACTION` | `DROP` | Action for matched packets (DROP/REJECT) |
| `FIREWALL_CHAIN` | `INPUT` | iptables chain to use |
| `LOG_FILE` | `/var/log/ipdeny-fetch.log` | Log file path |
| `LOG_LEVEL` | `INFO` | Logging level |

## Systemd Timer

The timer runs daily at 3 AM (with 1-hour randomization):

```bash
# Check next run time
systemctl list-timers ipdeny-fetch.timer

# Run immediately
sudo systemctl start ipdeny-fetch.service

# Disable automatic updates
sudo systemctl disable ipdeny-fetch.timer
sudo systemctl stop ipdeny-fetch.timer
```

## Advanced Examples

### Block Multiple Countries

The default configuration blocks 10 countries. To add more:

```bash
# /etc/ipdeny/ipdeny.conf
COUNTRIES="cn hk in kr mx pk ru sg tw vn ir kp"  # Added Iran and North Korea
```

### Allow Specific Countries (Whitelist)

```bash
# Fetch country lists
COUNTRIES="us ca gb de fr"

# Use ACCEPT instead of DROP in iptables
iptables -A INPUT -m set --match-set ipdeny-us-v4 src -j ACCEPT
iptables -A INPUT -j DROP  # Drop everything else
```

### Custom ipset Parameters

For large blocklists (e.g., China ~8000 ranges):
```bash
IPSET_HASHSIZE="8192"
IPSET_MAXELEM="131072"
```

### Integration with nftables

```bash
# Create set in nftables
sudo nft add table inet filter
sudo nft add set inet filter ipdeny_cn { type ipv4_addr\; flags interval\; }

# Import from zone file
cat /var/lib/ipdeny/cn-v4.zone | while read ip; do
    sudo nft add element inet filter ipdeny_cn { $ip }
done

# Block traffic
sudo nft add rule inet filter input ip saddr @ipdeny_cn drop
```

## Testing (macOS/Non-Linux)

Since this targets Linux/systemd, test in a container or VM:

```bash
# Docker (with systemd support)
docker run -it --privileged -v $(pwd):/workspace \
    ubuntu:latest /bin/bash

# Inside container:
apt update && apt install -y systemd ipset iptables python3
cd /workspace
./tests/smoke-test.sh
```

## Troubleshooting

### ipset: Set cannot be destroyed (in use)

The ipset is referenced by iptables rules. Remove iptables rules first:
```bash
sudo iptables -L INPUT -n --line-numbers | grep ipdeny
sudo iptables -D INPUT <line_number>
sudo ipset destroy ipdeny-cn-v4
```

### Permission Denied

Ensure running as root:
```bash
sudo /usr/local/bin/ipdeny-fetcher.py
```

### No Countries Configured

This shouldn't happen with the new installer, but if you see this warning:

```bash
sudo nano /etc/ipdeny/ipdeny.conf
# Restore: COUNTRIES="cn hk in kr mx pk ru sg tw vn"
```

### Download Failures (503 Service Unavailable)

The fetcher includes retry logic with exponential backoff:

```bash
# Default: 3 retries with 5-second base delay
# Retry 1: wait 5 seconds
# Retry 2: wait 10 seconds  
# Retry 3: wait 15 seconds
```

To adjust retry settings:
```bash
sudo nano /etc/ipdeny/ipdeny.conf
HTTP_RETRIES="5"        # More attempts
HTTP_RETRY_DELAY="10"   # Longer delays
HTTP_TIMEOUT="60"       # Longer timeout
```

If ipdeny.com is down, the fetcher will log errors but won't disrupt existing ipsets or firewall rules.

### Download Failures

Check network connectivity:
```bash
curl http://www.ipdeny.com/ipblocks/data/aggregated/cn-aggregated.zone
```

## Security Considerations

- **Root Privileges**: Required for ipset/iptables operations
- **Systemd Hardening**: Service uses `ProtectSystem=strict` and `PrivateTmp=yes`
- **Zone File Integrity**: Consider adding MD5 checksum validation (future enhancement)
- **False Positives**: Blocking entire countries may affect legitimate traffic (VPNs, CDNs)
- **Maintenance**: Keep lists updated (daily timer recommended)

## Uninstall

```bash
sudo ./uninstall.sh
```

This will:
- Stop and disable systemd units
- Remove installed files
- Optionally remove ipsets
- Optionally remove configuration and data

## Development

### Run Tests

```bash
./tests/smoke-test.sh
```

### Build Package

```bash
make package
```

### Project Structure

```
.
├── bin/
│   ├── ipdeny-fetcher.py           # Fetches IP lists and updates ipsets
│   ├── ipdeny-firewall-update.py   # Updates iptables rules automatically
│   └── ipdeny-ctl.py               # Management and control tool
├── config/
│   └── example.conf                # Configuration template
├── systemd/
│   ├── ipdeny-fetch.service        # Main service (runs fetcher + firewall update)
│   ├── ipdeny-fetch.timer          # Timer for daily updates
│   └── ipdeny-firewall-update.service  # Standalone firewall update service
├── tests/
│   └── smoke-test.sh               # Basic validation tests
├── requirements.txt                # Python dependencies (minimal)
├── install.sh                      # Installation script
├── uninstall.sh                    # Uninstallation script
├── quick-install.sh                # One-line installer
├── Makefile                        # Build automation
└── README.md                       # This file
```

## Installation Paths

```
/opt/ipdeny/
├── bin/
│   └── ipdeny-fetcher.py            # Main fetcher script
├── venv/                            # Python virtual environment
└── requirements.txt                 # Python dependencies

/usr/local/bin/
└── ipdeny-fetcher                   # Wrapper script (uses venv)

/etc/systemd/system/
├── ipdeny-fetch.service         # Systemd service unit
└── ipdeny-fetch.timer           # Systemd timer unit

/etc/ipdeny/
└── ipdeny.conf                  # Configuration

/var/lib/ipdeny/
├── cn-v4.zone                   # Downloaded zone files
├── cn-v6.zone
└── ... (for each configured country)

/var/log/
└── ipdeny-fetch.log             # Log file
```

## Support

For issues, questions, or contributions:
- 🐛 Report bugs: https://github.com/svdleer/countryblocker/issues
- 💡 Feature requests: https://github.com/svdleer/countryblocker/issues
- 🔧 Pull requests: https://github.com/svdleer/countryblocker/pulls

## License

MIT License - see [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Silvester van der Leer (svdleer)

## Author

**Silvester van der Leer**
- GitHub: [@svdleer](https://github.com/svdleer)
- Repository: [github.com/svdleer/countryblocker](https://github.com/svdleer/countryblocker)

## Acknowledgments

- IP blocklists provided by [ipdeny.com](http://www.ipdeny.com/)
- Built with Python, ipset, and iptables


## Credits

- IP blocklists: [ipdeny.com](http://www.ipdeny.com/)
- Maintained by the community

## See Also

- [ipdeny.com](http://www.ipdeny.com/) - IP blocklist provider
- [ipset man page](http://ipset.netfilter.org/) - ipset documentation
- [iptables tutorial](https://www.netfilter.org/documentation/) - Netfilter documentation
