#!/usr/bin/env python3
"""
ipdeny-ctl - Control tool for Country Blocker
Manage ipsets, firewall rules, and system status

Author: Silvester van der Leer (svdleer)
Repository: https://github.com/svdleer/countryblocker
License: MIT
"""

import os
import sys
import subprocess
import argparse
from typing import List, Tuple, Dict
from pathlib import Path

CONFIG_FILE = '/etc/ipdeny/ipdeny.conf'
CONFIG_DIR = '/etc/ipdeny'
INSTALL_DIR = '/opt/ipdeny'
SYSTEMD_DIR = '/etc/systemd/system'


class IPdenyControl:
    def __init__(self):
        self.config = self.load_config()
        
    def load_config(self) -> dict:
        """Load configuration"""
        config = {'IPSET_PREFIX': 'ipdeny'}
        
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        value = value.split('#')[0].strip().strip('"').strip("'")
                        config[key.strip()] = value
        
        return config
    
    def run_command(self, cmd: List[str]) -> Tuple[int, str, str]:
        """Execute command"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)
    
    def get_ipsets(self) -> List[str]:
        """Get all ipdeny ipsets"""
        prefix = self.config['IPSET_PREFIX']
        returncode, stdout, _ = self.run_command(['ipset', 'list', '-n'])
        
        if returncode != 0:
            return []
        
        return [line.strip() for line in stdout.split('\n') 
                if line.strip().startswith(f"{prefix}-")]
    
    def get_ipset_stats(self, setname: str) -> Dict[str, str]:
        """Get statistics for an ipset"""
        returncode, stdout, _ = self.run_command(['ipset', 'list', setname])
        
        if returncode != 0:
            return {}
        
        stats = {'name': setname}
        for line in stdout.split('\n'):
            if 'Number of entries:' in line:
                stats['entries'] = line.split(':')[1].strip()
            elif 'Size in memory:' in line:
                stats['memory'] = line.split(':')[1].strip()
            elif 'References:' in line:
                stats['references'] = line.split(':')[1].strip()
        
        return stats
    
    def get_iptables_rule_stats(self, setname: str) -> Dict[str, int]:
        """Get packet and byte counts for a specific ipset from iptables"""
        stats = {'packets': 0, 'bytes': 0}
        
        # Check both IPv4 and IPv6
        for iptables, ipv6 in [('iptables', False), ('ip6tables', True)]:
            # Only check the appropriate table for the ipset type
            if ('-v6' in setname and not ipv6) or ('-v4' in setname and ipv6):
                continue
            
            cmd = [iptables, '-L', 'INPUT', '-n', '-v', '-x']
            returncode, stdout, _ = self.run_command(cmd)
            
            if returncode != 0:
                continue
            
            # Parse output for matching set
            for line in stdout.split('\n'):
                if setname in line and 'match-set' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            stats['packets'] += int(parts[0])
                            stats['bytes'] += int(parts[1])
                        except (ValueError, IndexError):
                            pass
        
        return stats
    
    def format_bytes(self, bytes_val: int) -> str:
        """Format bytes in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f}{unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f}PB"
    
    def get_iptables_rules(self, ipv6: bool = False) -> List[str]:
        """Get iptables rules containing ipdeny"""
        cmd = ['ip6tables' if ipv6 else 'iptables', '-L', 'INPUT', '-n', '-v', '--line-numbers']
        returncode, stdout, _ = self.run_command(cmd)
        
        if returncode != 0:
            return []
        
        rules = []
        for line in stdout.split('\n'):
            if 'ipdeny-' in line:
                rules.append(line.strip())
        
        return rules
    
    def cmd_status(self):
        """Show system status"""
        print("=== Country Blocker Status ===\n")
        
        # Check if running as root
        if os.geteuid() != 0:
            print("⚠️  Not running as root - some information may be unavailable\n")
        
        # Systemd services
        print("Systemd Services:")
        for service in ['ipdeny-fetch.service', 'ipdeny-fetch.timer', 'ipdeny-web-stats.timer']:
            returncode, stdout, _ = self.run_command(['systemctl', 'is-active', service])
            status = stdout.strip()
            symbol = "✓" if status == "active" else "✗"
            print(f"  {symbol} {service}: {status}")
        
        print()
        
        # ipsets
        ipsets = self.get_ipsets()
        print(f"ipsets: {len(ipsets)} total")
        if ipsets:
            ipv4_sets = [s for s in ipsets if '-v4' in s]
            ipv6_sets = [s for s in ipsets if '-v6' in s]
            print(f"  IPv4: {len(ipv4_sets)}")
            print(f"  IPv6: {len(ipv6_sets)}")
        
        print()
        
        # Firewall rules
        rules_v4 = self.get_iptables_rules(ipv6=False)
        rules_v6 = self.get_iptables_rules(ipv6=True)
        print(f"Firewall Rules:")
        print(f"  IPv4: {len(rules_v4)} rules")
        print(f"  IPv6: {len(rules_v6)} rules")
        
        print()
        
        # Countries
        countries = set()
        for ipset in ipsets:
            # Extract country code from ipdeny-XX-v4/v6
            parts = ipset.split('-')
            if len(parts) >= 2:
                countries.add(parts[1])
        
        if countries:
            print(f"Blocked Countries ({len(countries)}): {', '.join(sorted(countries))}")
    
    def cmd_stats(self):
        """Show detailed statistics"""
        print("=== ipset Statistics ===\n")
        
        ipsets = self.get_ipsets()
        if not ipsets:
            print("No ipsets found")
            return
        
        print(f"{'Name':<25} {'Entries':<12} {'Memory':<15} {'Refs':<8} {'Hits (pkts)':<15} {'Blocked':<15}")
        print("-" * 105)
        
        total_entries = 0
        total_packets = 0
        total_bytes = 0
        
        for setname in sorted(ipsets):
            stats = self.get_ipset_stats(setname)
            rule_stats = self.get_iptables_rule_stats(setname)
            
            if stats:
                entries = stats.get('entries', 'N/A')
                memory = stats.get('memory', 'N/A')
                refs = stats.get('references', 'N/A')
                packets = rule_stats.get('packets', 0)
                bytes_val = rule_stats.get('bytes', 0)
                
                packets_str = f"{packets:,}" if packets > 0 else "0"
                bytes_str = self.format_bytes(bytes_val) if bytes_val > 0 else "0B"
                
                print(f"{setname:<25} {entries:<12} {memory:<15} {refs:<8} {packets_str:<15} {bytes_str:<15}")
                
                try:
                    total_entries += int(entries)
                except:
                    pass
                
                total_packets += packets
                total_bytes += bytes_val
        
        print("-" * 105)
        print(f"Total IP entries: {total_entries:,}")
        print(f"Total blocked packets: {total_packets:,}")
        print(f"Total blocked traffic: {self.format_bytes(total_bytes)}")
    
    def cmd_list_rules(self):
        """List firewall rules"""
        print("=== Firewall Rules ===\n")
        
        print("IPv4 Rules:")
        rules = self.get_iptables_rules(ipv6=False)
        if rules:
            for rule in rules:
                print(f"  {rule}")
        else:
            print("  No rules found")
        
        print()
        
        print("IPv6 Rules:")
        rules = self.get_iptables_rules(ipv6=True)
        if rules:
            for rule in rules:
                print(f"  {rule}")
        else:
            print("  No rules found")
    
    def cmd_flush_ipsets(self):
        """Flush all ipdeny ipsets"""
        if os.geteuid() != 0:
            print("Error: This command requires root privileges")
            return 1
        
        ipsets = self.get_ipsets()
        if not ipsets:
            print("No ipsets to flush")
            return 0
        
        print(f"Flushing {len(ipsets)} ipsets...")
        
        flushed = 0
        for setname in ipsets:
            returncode, _, stderr = self.run_command(['ipset', 'flush', setname])
            if returncode == 0:
                print(f"  ✓ Flushed {setname}")
                flushed += 1
            else:
                print(f"  ✗ Failed to flush {setname}: {stderr}")
        
        print(f"\nFlushed {flushed}/{len(ipsets)} ipsets")
        return 0
    
    def cmd_remove_rules(self):
        """Remove all firewall rules"""
        if os.geteuid() != 0:
            print("Error: This command requires root privileges")
            return 1
        
        print("Removing firewall rules...")
        removed = 0
        
        # Remove IPv4 rules
        for iptables, ipv6 in [('iptables', False), ('ip6tables', True)]:
            while True:
                # Get rules with line numbers
                returncode, stdout, _ = self.run_command([iptables, '-L', 'INPUT', '-n', '--line-numbers'])
                if returncode != 0:
                    break
                
                # Find first ipdeny rule
                line_num = None
                for line in stdout.split('\n'):
                    if 'ipdeny-' in line:
                        parts = line.split()
                        if parts:
                            try:
                                line_num = int(parts[0])
                                break
                            except:
                                pass
                
                if line_num is None:
                    break
                
                # Delete rule by line number
                returncode, _, stderr = self.run_command([iptables, '-D', 'INPUT', str(line_num)])
                if returncode == 0:
                    print(f"  ✓ Removed {iptables} rule #{line_num}")
                    removed += 1
                else:
                    print(f"  ✗ Failed to remove rule: {stderr}")
                    break
        
        print(f"\nRemoved {removed} firewall rules")
        return 0
    
    def cmd_stop(self):
        """Stop and disable services"""
        if os.geteuid() != 0:
            print("Error: This command requires root privileges")
            return 1
        
        print("Stopping Country Blocker services...")
        
        services = ['ipdeny-fetch.timer', 'ipdeny-fetch.service']
        for service in services:
            # Stop
            returncode, _, _ = self.run_command(['systemctl', 'stop', service])
            if returncode == 0:
                print(f"  ✓ Stopped {service}")
            
            # Disable
            returncode, _, _ = self.run_command(['systemctl', 'disable', service])
            if returncode == 0:
                print(f"  ✓ Disabled {service}")
        
        print("\nServices stopped and disabled")
        return 0
    
    def cmd_start(self):
        """Start and enable services"""
        if os.geteuid() != 0:
            print("Error: This command requires root privileges")
            return 1
        
        print("Starting Country Blocker services...")
        
        services = ['ipdeny-fetch.timer', 'ipdeny-fetch.service']
        for service in services:
            # Enable
            returncode, _, _ = self.run_command(['systemctl', 'enable', service])
            if returncode == 0:
                print(f"  ✓ Enabled {service}")
            
            # Start (only timer, service is triggered by timer)
            if 'timer' in service:
                returncode, _, _ = self.run_command(['systemctl', 'start', service])
                if returncode == 0:
                    print(f"  ✓ Started {service}")
        
        print("\nServices started and enabled")
        return 0
    
    def cmd_uninstall(self):
        """Uninstall Country Blocker"""
        if os.geteuid() != 0:
            print("Error: This command requires root privileges")
            return 1
        
        print("⚠️  This will uninstall Country Blocker")
        print("The following will be removed:")
        print(f"  - ipsets and firewall rules")
        print(f"  - Systemd services")
        print(f"  - Binaries in {INSTALL_DIR}")
        print(f"  - Configuration (optional)")
        print()
        
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled")
            return 0
        
        # Stop services
        print("\nStopping services...")
        self.cmd_stop()
        
        # Remove firewall rules
        print("\nRemoving firewall rules...")
        self.cmd_remove_rules()
        
        # Destroy ipsets
        print("\nDestroying ipsets...")
        ipsets = self.get_ipsets()
        for setname in ipsets:
            self.run_command(['ipset', 'destroy', setname])
            print(f"  ✓ Destroyed {setname}")
        
        # Remove systemd units
        print("\nRemoving systemd units...")
        for service in ['ipdeny-fetch.service', 'ipdeny-fetch.timer', 'ipdeny-firewall-update.service']:
            path = f"{SYSTEMD_DIR}/{service}"
            if os.path.exists(path):
                os.remove(path)
                print(f"  ✓ Removed {service}")
        
        self.run_command(['systemctl', 'daemon-reload'])
        
        # Remove binaries
        print("\nRemoving binaries...")
        if os.path.exists(INSTALL_DIR):
            self.run_command(['rm', '-rf', INSTALL_DIR])
            print(f"  ✓ Removed {INSTALL_DIR}")
        
        for wrapper in ['/usr/local/bin/ipdeny-fetcher', '/usr/local/bin/ipdeny-firewall-update', '/usr/local/bin/ipdeny-ctl']:
            if os.path.exists(wrapper):
                os.remove(wrapper)
                print(f"  ✓ Removed {wrapper}")
        
        # Ask about config
        response = input("\nRemove configuration in /etc/ipdeny? [y/N]: ")
        if response.lower() == 'y':
            self.run_command(['rm', '-rf', '/etc/ipdeny'])
            print("  ✓ Removed configuration")
        
        # Ask about data
        response = input("Remove zone files in /var/lib/ipdeny? [y/N]: ")
        if response.lower() == 'y':
            self.run_command(['rm', '-rf', '/var/lib/ipdeny'])
            print("  ✓ Removed zone files")
        
        print("\n✓ Country Blocker uninstalled")
        return 0
    
    def cmd_update_web(self):
        """Generate JSON stats file for web dashboard"""
        import json
        import glob
        
        print("Generating web statistics...")
        
        ipsets = self.get_ipsets()
        if not ipsets:
            print("No ipsets found")
            return 1
        
        # Collect data
        ipsets_data = []
        total_entries = 0
        total_packets = 0
        total_bytes = 0
        countries = set()
        ipv4_count = 0
        ipv6_count = 0
        
        for setname in sorted(ipsets):
            stats = self.get_ipset_stats(setname)
            rule_stats = self.get_iptables_rule_stats(setname)
            
            if stats:
                # Extract country code
                parts = setname.split('-')
                country = parts[1] if len(parts) >= 2 else 'unknown'
                iptype = 'v4' if '-v4' in setname else 'v6'
                
                countries.add(country)
                if iptype == 'v4':
                    ipv4_count += 1
                else:
                    ipv6_count += 1
                
                entries = int(stats.get('entries', 0))
                packets = rule_stats.get('packets', 0)
                bytes_val = rule_stats.get('bytes', 0)
                
                total_entries += entries
                total_packets += packets
                total_bytes += bytes_val
                
                ipsets_data.append({
                    'name': setname,
                    'country': country,
                    'type': iptype,
                    'entries': entries,
                    'memory': stats.get('memory', 'N/A'),
                    'packets': packets,
                    'traffic': self.format_bytes(bytes_val)
                })
        
        # Build JSON data
        data = {
            'timestamp': int(__import__('time').time()),
            'summary': {
                'total_countries': len(countries),
                'total_entries': total_entries,
                'total_packets': total_packets,
                'total_traffic': self.format_bytes(total_bytes),
                'ipv4_sets': ipv4_count,
                'ipv6_sets': ipv6_count
            },
            'ipsets': ipsets_data
        }
        
        # Write JSON file to system location
        stats_file = '/var/lib/ipdeny/stats.json'
        try:
            with open(stats_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Set permissions for web server
            os.chmod(stats_file, 0o644)
            
            print(f"✓ Statistics written to {stats_file}")
            print(f"  Countries: {len(countries)}")
            print(f"  Total entries: {total_entries:,}")
            print(f"  Total packets blocked: {total_packets:,}")
            print(f"  Total traffic blocked: {self.format_bytes(total_bytes)}")
            
            # Copy stats.json to all web dashboard installations (for Plesk/open_basedir compatibility)
            import shutil
            web_dirs = []
            
            # Find all index.php files that contain "Country Blocker"
            for pattern in ['/var/www/*/index.php', '/var/www/*/httpdocs/index.php',
                           '/var/www/*/*/index.php',  # /var/www/html/countryblock/index.php
                           '/home/*/public_html/index.php', 
                           '/home/httpd/vhosts/*/httpdocs/index.php',
                           '/home/httpd/vhosts/*/httpdocs/*/index.php']:  # Plesk subdirectories
                for php_file in glob.glob(pattern):
                    try:
                        with open(php_file, 'r') as f:
                            if 'Country Blocker' in f.read(500):  # Check first 500 chars
                                web_dir = os.path.dirname(php_file)
                                web_dirs.append(web_dir)
                    except:
                        pass
            
            if web_dirs:
                print(f"\n  Copying stats.json to {len(web_dirs)} web dashboard(s):")
                for web_dir in web_dirs:
                    try:
                        web_stats = os.path.join(web_dir, 'stats.json')
                        shutil.copy2(stats_file, web_stats)
                        os.chmod(web_stats, 0o644)
                        
                        # Set correct ownership based on web directory
                        web_user = self.detect_web_user(web_dir)
                        web_group = self.detect_web_group(web_dir, web_user)
                        self.run_command(['chown', f'{web_user}:{web_group}', web_stats])
                        
                        print(f"    ✓ {web_dir} ({web_user}:{web_group})")
                    except Exception as e:
                        print(f"    ✗ {web_dir}: {e}")
            
            return 0
        except Exception as e:
            print(f"Error writing statistics: {e}")
            return 1
    
    def cmd_setup_web(self, webroot: str):
        """Setup web dashboard in specified directory"""
        if os.geteuid() != 0:
            print("Error: This command requires root privileges")
            return 1
        
        print(f"Setting up web dashboard in {webroot}...")
        
        # Check if source files exist
        source_dir = f"{INSTALL_DIR}/web"
        if not os.path.exists(source_dir):
            # Try relative to script location
            script_dir = os.path.dirname(os.path.abspath(__file__))
            source_dir = os.path.join(os.path.dirname(script_dir), 'web')
        
        if not os.path.exists(source_dir):
            print(f"Error: Web files not found. Expected at {source_dir}")
            return 1
        
        # Detect web server user and group
        web_user = self.detect_web_user(webroot)
        web_group = self.detect_web_group(webroot, web_user)
        
        print(f"Detected web server user: {web_user}:{web_group}")
        
        # Create target directory
        os.makedirs(webroot, exist_ok=True)
        
        # Copy files
        import shutil
        for item in os.listdir(source_dir):
            src = os.path.join(source_dir, item)
            dst = os.path.join(webroot, item)
            
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                print(f"  ✓ Copied {item}")
        
        # Copy default .htpasswd if .htpasswd.example exists and target doesn't have .htpasswd
        htpasswd_example = os.path.join(source_dir, '.htpasswd.example')
        htpasswd_target = os.path.join(webroot, '.htpasswd')
        
        if os.path.exists(htpasswd_example) and not os.path.exists(htpasswd_target):
            shutil.copy2(htpasswd_example, htpasswd_target)
            os.chmod(htpasswd_target, 0o640)
            self.run_command(['chown', f'{web_user}:{web_group}', htpasswd_target])
            print(f"  ✓ Created default .htpasswd (user: ipdeny, pass: stats)")
            print(f"  ⚠️  WARNING: Change default password with: sudo ipdeny-ctl setup-auth {webroot} ipdeny")
        
        # Set ownership and permissions
        print(f"\nSetting ownership to {web_user}:{web_group}...")
        self.run_command(['chown', '-R', f'{web_user}:{web_group}', webroot])
        
        print("Setting permissions...")
        self.run_command(['chmod', '755', webroot])
        self.run_command(['find', webroot, '-type', 'f', '-exec', 'chmod', '644', '{}', ';'])
        
        # Make stats.json readable by web server
        stats_file = '/var/lib/ipdeny/stats.json'
        if os.path.exists(stats_file):
            self.run_command(['chmod', '644', stats_file])
            print(f"✓ Made {stats_file} readable by web server")
        
        print(f"\n✓ Web dashboard installed to {webroot}")
        print(f"✓ Ownership: {web_user}:{web_group}")
        print(f"✓ Permissions: 755 (directory), 644 (files)")
        print("\nNext steps:")
        print(f"  1. Generate stats: sudo ipdeny-ctl update-web")
        print(f"  2. Setup auth:     sudo ipdeny-ctl setup-auth {webroot} admin")
        print(f"  3. Access at:      http://your-domain.com{webroot.replace('/var/www/html', '').replace('/var/www/vhosts', '')}/")
        
        return 0
    
    def detect_web_user(self, webroot: str) -> str:
        """Detect appropriate web server user based on path"""
        import pwd
        import os
        
        # Walk up directory tree to find first existing non-root owned directory
        try:
            check_path = webroot
            # Keep going up until we find an existing directory
            while check_path and check_path != '/':
                if os.path.exists(check_path):
                    stat_info = os.stat(check_path)
                    owner = pwd.getpwuid(stat_info.st_uid).pw_name
                    # Only use if it's not root (found actual user directory)
                    if owner != 'root':
                        return owner
                # Go up one level
                check_path = os.path.dirname(check_path)
        except:
            pass
        
        # Check if it's a Plesk path
        if '/vhosts/' in webroot:
            # Extract domain from path: /home/httpd/vhosts/domain.com/... or /var/www/vhosts/domain.com/...
            parts = webroot.split('/vhosts/')[1].split('/')
            if parts:
                domain = parts[0]
                # In Plesk, check if user exists for domain
                # Try domain name as username
                try:
                    pwd.getpwnam(domain)
                    return domain
                except KeyError:
                    pass
                
                # Try domain without TLD (e.g., 'example' from 'example.com')
                domain_short = domain.split('.')[0]
                try:
                    pwd.getpwnam(domain_short)
                    return domain_short
                except KeyError:
                    pass
        
        # Check if it's under a user's home directory
        if webroot.startswith('/home/'):
            parts = webroot.split('/')[2:3]  # Get username from /home/username/...
            if parts:
                username = parts[0]
                try:
                    pwd.getpwnam(username)
                    return username
                except KeyError:
                    pass
        
        # Check common web server users
        for user in ['www-data', 'apache', 'nginx', 'httpd']:
            try:
                pwd.getpwnam(user)
                return user
            except KeyError:
                pass
        
        # Fallback to current directory owner if it exists
        if os.path.exists(webroot):
            import stat
            st = os.stat(webroot)
            try:
                return pwd.getpwuid(st.st_uid).pw_name
            except:
                pass
        
        # Default fallback
        return 'www-data'
    
    def detect_web_group(self, webroot: str, web_user: str) -> str:
        """Detect appropriate web server group based on path and user"""
        import grp
        
        # Check if it's a Plesk path - Plesk uses 'psacln' group
        if '/vhosts/' in webroot:
            try:
                grp.getgrnam('psacln')
                return 'psacln'
            except KeyError:
                pass
        
        # Try to use the same name as user (common for most setups)
        try:
            grp.getgrnam(web_user)
            return web_user
        except KeyError:
            pass
        
        # Check common web server groups
        for group in ['www-data', 'apache', 'nginx', 'httpd']:
            try:
                grp.getgrnam(group)
                return group
            except KeyError:
                pass
        
        # Fallback to current directory group owner if it exists
        if os.path.exists(webroot):
            import stat
            st = os.stat(webroot)
            try:
                return grp.getgrgid(st.st_gid).gr_name
            except:
                pass
        
        # Default fallback
        return web_user
    
    def cmd_setup_auth(self, webroot: str, username: str = 'admin'):
        """Setup HTTP Basic Authentication for web dashboard"""
        if os.geteuid() != 0:
            print("Error: This command requires root privileges")
            return 1
        
        import subprocess
        import getpass
        
        print(f"Setting up HTTP Basic Authentication for {webroot}...")
        
        # Check if webroot exists
        if not os.path.exists(webroot):
            print(f"Error: Directory {webroot} does not exist")
            print("Run setup-web first: sudo ipdeny-ctl setup-web /path/to/webroot")
            return 1
        
        # Check if htpasswd is available
        returncode, _, _ = self.run_command(['which', 'htpasswd'])
        if returncode != 0:
            print("Error: htpasswd not found. Install apache2-utils:")
            print("  Ubuntu/Debian: sudo apt install apache2-utils")
            print("  RHEL/CentOS:   sudo yum install httpd-tools")
            return 1
        
        # Get password
        print(f"\nCreate password for user: {username}")
        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Confirm password: ")
        
        if password != password_confirm:
            print("Error: Passwords do not match")
            return 1
        
        if len(password) < 8:
            print("Error: Password must be at least 8 characters")
            return 1
        
        # Create .htpasswd file
        htpasswd_file = '/var/www/.htpasswd'
        
        # Use htpasswd command to create/update password file
        process = subprocess.Popen(
            ['htpasswd', '-cB', htpasswd_file, username],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=f"{password}\n{password}\n")
        
        if process.returncode != 0:
            print(f"Error creating password file: {stderr}")
            return 1
        
        # Set permissions
        os.chmod(htpasswd_file, 0o640)
        self.run_command(['chown', 'root:www-data', htpasswd_file])
        
        print(f"✓ Created password file: {htpasswd_file}")
        
        # Update .htaccess
        htaccess_file = os.path.join(webroot, '.htaccess')
        if os.path.exists(htaccess_file):
            with open(htaccess_file, 'r') as f:
                content = f.read()
            
            # Uncomment auth lines
            content = content.replace('# AuthType Basic', 'AuthType Basic')
            content = content.replace('# AuthName', 'AuthName')
            content = content.replace('# AuthUserFile', 'AuthUserFile')
            content = content.replace('# Require valid-user', 'Require valid-user')
            
            # Update AuthUserFile path
            if '/var/www/.htpasswd' not in content:
                content = content.replace('AuthUserFile /path/to/.htpasswd', f'AuthUserFile {htpasswd_file}')
            
            with open(htaccess_file, 'w') as f:
                f.write(content)
            
            print(f"✓ Updated {htaccess_file}")
        
        print("\n✓ Authentication configured!")
        print(f"\nCredentials:")
        print(f"  Username: {username}")
        print(f"  Password: [hidden]")
        print(f"\nAccess your dashboard - you will be prompted for credentials.")
        
        return 0
    
    def cmd_update(self):
        """Update Country Blocker to latest version from GitHub"""
        if os.geteuid() != 0:
            print("Error: This command requires root privileges")
            return 1
        
        import tempfile
        import shutil
        
        print("=== Country Blocker Update ===\n")
        print("Updating to latest version from GitHub...")
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Clone latest version
            print("\n1. Downloading latest version...")
            returncode, stdout, stderr = self.run_command([
                'git', 'clone', '--depth', '1',
                'https://github.com/svdleer/countryblocker.git',
                temp_dir
            ])
            
            if returncode != 0:
                print(f"Error downloading: {stderr}")
                return 1
            
            print("   ✓ Downloaded")
            
            # Backup current config
            print("\n2. Backing up configuration...")
            config_backup = None
            if os.path.exists(CONFIG_DIR):
                config_backup = f"{CONFIG_DIR}.backup"
                shutil.copytree(CONFIG_DIR, config_backup, dirs_exist_ok=True)
                print(f"   ✓ Backed up to {config_backup}")
            
            # Update scripts
            print("\n3. Updating scripts...")
            for script in ['ipdeny-fetcher.py', 'ipdeny-firewall-update.py', 'ipdeny-ctl.py']:
                src = os.path.join(temp_dir, 'bin', script)
                dst = os.path.join(INSTALL_DIR, 'bin', script)
                if os.path.exists(src):
                    shutil.copy2(src, dst)
                    os.chmod(dst, 0o755)
                    print(f"   ✓ Updated {script}")
            
            # Update web files
            print("\n4. Updating web files...")
            web_src = os.path.join(temp_dir, 'web')
            web_dst = os.path.join(INSTALL_DIR, 'web')
            if os.path.exists(web_src):
                os.makedirs(web_dst, exist_ok=True)
                for item in os.listdir(web_src):
                    src = os.path.join(web_src, item)
                    dst = os.path.join(web_dst, item)
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
                        print(f"   ✓ Updated web/{item}")
            
            # Update systemd units
            print("\n5. Updating systemd units...")
            for unit in ['ipdeny-fetch.service', 'ipdeny-fetch.timer', 
                        'ipdeny-firewall-update.service', 'ipdeny-web-stats.service', 
                        'ipdeny-web-stats.timer']:
                src = os.path.join(temp_dir, 'systemd', unit)
                dst = os.path.join(SYSTEMD_DIR, unit)
                if os.path.exists(src):
                    shutil.copy2(src, dst)
                    os.chmod(dst, 0o644)
                    print(f"   ✓ Updated {unit}")
            
            # Reload systemd
            print("\n6. Reloading systemd...")
            self.run_command(['systemctl', 'daemon-reload'])
            print("   ✓ Reloaded")
            
            # Update deployed web dashboards
            print("\n7. Updating deployed web dashboards...")
            import glob
            web_dirs = []
            
            # Find all index.php files that contain "Country Blocker"
            for pattern in ['/var/www/*/index.php', '/var/www/*/httpdocs/index.php',
                           '/var/www/*/*/index.php',  # /var/www/html/countryblock/index.php
                           '/home/*/public_html/index.php', 
                           '/home/httpd/vhosts/*/httpdocs/index.php',
                           '/home/httpd/vhosts/*/httpdocs/*/index.php']:  # Plesk subdirectories
                for php_file in glob.glob(pattern):
                    try:
                        with open(php_file, 'r') as f:
                            if 'Country Blocker' in f.read(500):
                                web_dir = os.path.dirname(php_file)
                                web_dirs.append(web_dir)
                    except:
                        pass
            
            if web_dirs:
                print(f"   Found {len(web_dirs)} deployed dashboard(s)")
                web_src = os.path.join(INSTALL_DIR, 'web', 'index.php')
                for web_dir in web_dirs:
                    try:
                        web_dst = os.path.join(web_dir, 'index.php')
                        shutil.copy2(web_src, web_dst)
                        os.chmod(web_dst, 0o644)
                        
                        # Set correct ownership
                        web_user = self.detect_web_user(web_dir)
                        web_group = self.detect_web_group(web_dir, web_user)
                        self.run_command(['chown', f'{web_user}:{web_group}', web_dst])
                        
                        print(f"   ✓ Updated {web_dir}")
                    except Exception as e:
                        print(f"   ✗ {web_dir}: {e}")
            else:
                print("   No deployed dashboards found")
            
            # Restore config if it was backed up
            if config_backup and os.path.exists(config_backup):
                print("\n8. Restoring configuration...")
                # Config is preserved, just remove backup
                shutil.rmtree(config_backup)
                print("   ✓ Configuration preserved")
            
            print("\n✓ Update complete!")
            print("\nUpdated components:")
            print("  - ipdeny-fetcher")
            print("  - ipdeny-firewall-update")
            print("  - ipdeny-ctl")
            print("  - Web dashboard")
            print("  - Systemd units")
            print("\nYour configuration and data were preserved.")
            print("\nRecommended: Restart services")
            print("  sudo systemctl restart ipdeny-fetch.timer")
            print("  sudo systemctl restart ipdeny-web-stats.timer")
            
            return 0
            
        except Exception as e:
            print(f"\nError during update: {e}")
            return 1
        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


def main():
    parser = argparse.ArgumentParser(
        description='Country Blocker Control Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  status        Show system status (services, ipsets, rules)
  stats         Show detailed ipset statistics
  list-rules    List all firewall rules
  flush         Flush all ipsets (clear entries, keep structure)
  remove-rules  Remove all firewall rules
  start         Start and enable services
  stop          Stop and disable services
  uninstall     Completely uninstall Country Blocker
  update-web    Generate JSON statistics for web dashboard
  setup-web     Deploy web dashboard to specified directory
  setup-auth    Configure HTTP Basic Authentication for dashboard
  update        Update Country Blocker to latest version from GitHub

Examples:
  ipdeny-ctl status              # Show current status
  ipdeny-ctl stats               # Show ipset statistics
  sudo ipdeny-ctl flush          # Flush all ipsets
  sudo ipdeny-ctl remove-rules   # Remove firewall rules
  sudo ipdeny-ctl stop           # Stop services
  sudo ipdeny-ctl update         # Update to latest version
  sudo ipdeny-ctl update-web     # Generate web stats
  sudo ipdeny-ctl setup-web /var/www/html/countryblocker  # Deploy dashboard
  sudo ipdeny-ctl setup-auth /var/www/html/countryblocker admin  # Setup authentication
  sudo ipdeny-ctl uninstall      # Complete uninstall
"""
    )
    
    parser.add_argument('command', 
                       choices=['status', 'stats', 'list-rules', 'flush', 'remove-rules', 'start', 'stop', 'uninstall', 'update-web', 'setup-web', 'setup-auth', 'update'],
                       help='Command to execute')
    
    parser.add_argument('path', nargs='?', help='Path for setup-web command')
    parser.add_argument('username', nargs='?', default='admin', help='Username for setup-auth command')
    
    args = parser.parse_args()
    
    ctl = IPdenyControl()
    
    commands = {
        'status': ctl.cmd_status,
        'stats': ctl.cmd_stats,
        'list-rules': ctl.cmd_list_rules,
        'flush': ctl.cmd_flush_ipsets,
        'remove-rules': ctl.cmd_remove_rules,
        'start': ctl.cmd_start,
        'stop': ctl.cmd_stop,
        'uninstall': ctl.cmd_uninstall,
        'update-web': ctl.cmd_update_web,
        'setup-web': lambda: ctl.cmd_setup_web(args.path) if args.path else print("Error: setup-web requires a path argument"),
        'setup-auth': lambda: ctl.cmd_setup_auth(args.path, args.username) if args.path else print("Error: setup-auth requires a path argument"),
        'update': ctl.cmd_update,
    }
    
    try:
        return commands[args.command]()
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main() or 0)
