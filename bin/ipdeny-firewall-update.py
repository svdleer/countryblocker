#!/usr/bin/env python3
"""
IPdeny Firewall Updater
Automatically applies iptables rules for all ipdeny ipsets
Runs after ipdeny-fetcher to keep firewall rules in sync

Author: Silvester van der Leer (svdleer)
Repository: https://github.com/svdleer/countryblocker
License: MIT
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from typing import List, Tuple

# Configuration
CONFIG_FILE = '/etc/ipdeny/ipdeny.conf'
LOG_FILE = '/var/log/ipdeny-fetch.log'

# Default configuration
DEFAULT_CONFIG = {
    'IPSET_PREFIX': 'ipdeny',
    'COUNTRIES': '',
    'FIREWALL_ACTION': 'DROP',  # DROP or REJECT
    'FIREWALL_CHAIN': 'INPUT',  # INPUT, FORWARD, or custom
    'FIREWALL_ENABLED': 'true',
    'LOG_LEVEL': 'INFO',
}


class FirewallUpdater:
    def __init__(self, config_file: str = CONFIG_FILE):
        self.config = self.load_config(config_file)
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
    def load_config(self, config_file: str) -> dict:
        """Load configuration from file with defaults"""
        config = DEFAULT_CONFIG.copy()
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Strip comments from value (everything after #)
                        value = value.split('#')[0].strip()
                        # Remove quotes
                        value = value.strip('"').strip("'")
                        config[key.strip()] = value
        
        return config
    
    def setup_logging(self):
        """Configure logging"""
        log_level = getattr(logging, self.config['LOG_LEVEL'], logging.INFO)
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        log_file = LOG_FILE
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def run_command(self, cmd: List[str]) -> Tuple[int, str, str]:
        """Execute shell command and return exit code, stdout, stderr"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)
    
    def get_ipdeny_ipsets(self) -> List[str]:
        """Get list of all ipdeny ipsets"""
        prefix = self.config['IPSET_PREFIX']
        returncode, stdout, stderr = self.run_command(['ipset', 'list', '-n'])
        
        if returncode != 0:
            self.logger.error(f"Failed to list ipsets: {stderr}")
            return []
        
        ipsets = []
        for line in stdout.split('\n'):
            setname = line.strip()
            if setname.startswith(f"{prefix}-"):
                ipsets.append(setname)
        
        return ipsets
    
    def rule_exists(self, chain: str, setname: str, action: str, ipv6: bool = False) -> bool:
        """Check if iptables rule exists"""
        cmd = ['ip6tables' if ipv6 else 'iptables', '-C', chain, '-m', 'set', 
               '--match-set', setname, 'src', '-j', action, '-m', 'comment',
               '--comment', f'Country blocker: {setname}']
        
        returncode, _, _ = self.run_command(cmd)
        return returncode == 0
    
    def add_rule(self, chain: str, setname: str, action: str, ipv6: bool = False) -> bool:
        """Add iptables rule"""
        iptables = 'ip6tables' if ipv6 else 'iptables'
        
        # Check if rule already exists
        if self.rule_exists(chain, setname, action, ipv6):
            self.logger.debug(f"Rule for {setname} already exists in {iptables}")
            return True
        
        # Add rule
        cmd = [iptables, '-A', chain, '-m', 'set', '--match-set', setname, 'src',
               '-j', action, '-m', 'comment', '--comment', f'Country blocker: {setname}']
        
        returncode, stdout, stderr = self.run_command(cmd)
        if returncode != 0:
            self.logger.error(f"Failed to add {iptables} rule for {setname}: {stderr}")
            return False
        
        self.logger.info(f"Added {iptables} rule: {setname} -> {action}")
        return True
    
    def remove_orphaned_rules(self, chain: str, active_ipsets: List[str], action: str) -> int:
        """Remove iptables rules for ipsets that no longer exist"""
        removed = 0
        
        for ipv6 in [False, True]:
            iptables = 'ip6tables' if ipv6 else 'iptables'
            
            # List rules with line numbers
            cmd = [iptables, '-L', chain, '-n', '--line-numbers']
            returncode, stdout, stderr = self.run_command(cmd)
            
            if returncode != 0:
                continue
            
            # Parse output to find ipdeny rules
            lines = stdout.split('\n')
            rules_to_delete = []
            
            for line in lines:
                if 'Country blocker:' in line or 'ipdeny-' in line:
                    # Extract set name from rule
                    for setname in active_ipsets:
                        if setname in line:
                            break
                    else:
                        # This is an orphaned rule - extract line number
                        parts = line.split()
                        if parts and parts[0].isdigit():
                            rules_to_delete.append(int(parts[0]))
            
            # Delete rules in reverse order (highest line number first)
            for line_num in sorted(rules_to_delete, reverse=True):
                cmd = [iptables, '-D', chain, str(line_num)]
                returncode, _, stderr = self.run_command(cmd)
                if returncode == 0:
                    removed += 1
                    self.logger.info(f"Removed orphaned {iptables} rule at line {line_num}")
        
        return removed
    
    def update_firewall(self) -> bool:
        """Update firewall rules for all ipdeny ipsets"""
        if self.config['FIREWALL_ENABLED'].lower() != 'true':
            self.logger.info("Firewall updates disabled in configuration")
            return True
        
        self.logger.info("=== Firewall Updater Started ===")
        
        # Check if running as root
        if os.geteuid() != 0:
            self.logger.error("Firewall updates require root privileges")
            return False
        
        # Get configuration
        action = self.config['FIREWALL_ACTION']
        chain = self.config['FIREWALL_CHAIN']
        
        # Get all ipdeny ipsets
        ipsets = self.get_ipdeny_ipsets()
        
        if not ipsets:
            self.logger.warning("No ipdeny ipsets found")
            return True
        
        self.logger.info(f"Found {len(ipsets)} ipdeny ipsets")
        
        # Add rules for each ipset
        success_count = 0
        for setname in ipsets:
            ipv6 = '-v6' in setname
            if self.add_rule(chain, setname, action, ipv6):
                success_count += 1
        
        # Remove orphaned rules
        removed = self.remove_orphaned_rules(chain, ipsets, action)
        if removed > 0:
            self.logger.info(f"Removed {removed} orphaned rules")
        
        self.logger.info(f"=== Firewall Updater Completed: {success_count}/{len(ipsets)} rules active ===")
        return success_count == len(ipsets)


def main():
    try:
        updater = FirewallUpdater()
        success = updater.update_firewall()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
