#!/usr/bin/env python3
"""
IPdeny Fetcher - Downloads and manages IP blocklists from ipdeny.com
Integrates with ipset for efficient firewall management

Author: Silvester van der Leer (svdleer)
Repository: https://github.com/svdleer/countryblocker
License: MIT
"""

import os
import sys
import logging
import subprocess
import hashlib
import urllib.request
import urllib.error
import time
from pathlib import Path
from typing import List, Tuple, Optional

# Default configuration
DEFAULT_CONFIG = {
    'OUTPUT_DIR': '/var/lib/ipdeny',
    'COUNTRIES': '',
    'FETCH_IPV4': 'true',
    'FETCH_IPV6': 'true',
    'IPV4_BASE_URL': 'http://www.ipdeny.com/ipblocks/data/aggregated',
    'IPV6_BASE_URL': 'http://www.ipdeny.com/ipv6/ipaddresses/aggregated',
    'LOG_FILE': '/var/log/ipdeny-fetch.log',
    'LOG_LEVEL': 'INFO',
    'IPSET_ENABLED': 'true',
    'IPSET_PREFIX': 'ipdeny',
    'IPSET_AUTO_FLUSH': 'true',
    'IPSET_HASHSIZE': '4096',
    'IPSET_MAXELEM': '65536',
    'HTTP_TIMEOUT': '30',
    'HTTP_RETRIES': '3',
    'HTTP_RETRY_DELAY': '5',
}

CONFIG_FILE = '/etc/ipdeny/ipdeny.conf'


class IPdenyFetcher:
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
        """Configure logging to file and console"""
        log_level = getattr(logging, self.config['LOG_LEVEL'], logging.INFO)
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # File handler
        log_file = self.config['LOG_FILE']
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
    
    def ipset_exists(self, name: str) -> bool:
        """Check if ipset exists"""
        returncode, _, _ = self.run_command(['ipset', 'list', name])
        return returncode == 0
    
    def create_ipset(self, name: str, family: str = 'inet') -> bool:
        """Create ipset with optimal parameters"""
        if self.ipset_exists(name):
            self.logger.debug(f"ipset {name} already exists")
            return True
        
        hashsize = self.config['IPSET_HASHSIZE']
        maxelem = self.config['IPSET_MAXELEM']
        
        cmd = [
            'ipset', 'create', name,
            'hash:net',
            'family', family,
            'hashsize', hashsize,
            'maxelem', maxelem
        ]
        
        returncode, stdout, stderr = self.run_command(cmd)
        if returncode != 0:
            self.logger.error(f"Failed to create ipset {name}: {stderr}")
            return False
        
        self.logger.info(f"Created ipset: {name}")
        return True
    
    def flush_ipset(self, name: str, force: bool = False) -> bool:
        """Flush ipset entries. Use force=True to ensure flush even if set doesn't exist."""
        if not self.ipset_exists(name):
            if force:
                self.logger.warning(f"ipset {name} does not exist, skipping flush")
            return True
        
        returncode, stdout, stderr = self.run_command(['ipset', 'flush', name])
        if returncode != 0:
            self.logger.error(f"Failed to flush ipset {name}: {stderr}")
            return False
        
        self.logger.info(f"Flushed ipset: {name} (cleared all entries)")
        return True
    
    def flush_all_ipdeny_ipsets(self) -> int:
        """Flush all ipdeny-prefixed ipsets. Returns number of sets flushed."""
        prefix = self.config['IPSET_PREFIX']
        flushed = 0
        
        # List all ipsets
        returncode, stdout, stderr = self.run_command(['ipset', 'list', '-n'])
        if returncode != 0:
            self.logger.error(f"Failed to list ipsets: {stderr}")
            return 0
        
        # Filter for ipdeny sets
        for line in stdout.split('\n'):
            setname = line.strip()
            if setname.startswith(f"{prefix}-"):
                if self.flush_ipset(setname):
                    flushed += 1
        
        self.logger.info(f"Flushed {flushed} ipdeny ipsets")
        return flushed
    
    def destroy_ipset(self, name: str, flush_first: bool = True) -> bool:
        """Destroy ipset"""
        if not self.ipset_exists(name):
            return True
        
        # Optionally flush first
        if flush_first:
            self.flush_ipset(name)
        
        returncode, stdout, stderr = self.run_command(['ipset', 'destroy', name])
        if returncode != 0:
            # This is expected when ipset is in use by iptables - not an error
            if "in use by a kernel component" in stderr:
                self.logger.debug(f"ipset {name} in use by iptables (expected, safe to ignore)")
            else:
                self.logger.warning(f"Failed to destroy ipset {name}: {stderr}")
            return False
        
        self.logger.info(f"Destroyed ipset: {name}")
        return True
    
    def populate_ipset_from_file(self, ipset_name: str, zone_file: str) -> bool:
        """Add IPs from zone file to ipset using atomic swap"""
        temp_name = f"{ipset_name}-tmp"
        
        # Get family from ipset name
        family = 'inet6' if '-v6' in ipset_name else 'inet'
        
        # Create temporary ipset
        if not self.create_ipset(temp_name, family):
            return False
        
        # Populate temporary ipset
        try:
            with open(zone_file, 'r') as f:
                for line in f:
                    ip = line.strip()
                    if ip and not ip.startswith('#'):
                        cmd = ['ipset', 'add', temp_name, ip, '-exist']
                        returncode, _, stderr = self.run_command(cmd)
                        if returncode != 0:
                            self.logger.warning(f"Failed to add {ip} to {temp_name}: {stderr}")
        except Exception as e:
            self.logger.error(f"Error reading {zone_file}: {e}")
            self.destroy_ipset(temp_name)
            return False
        
        # Atomic swap: try to replace existing ipset
        if self.ipset_exists(ipset_name):
            # Flush old set first
            self.flush_ipset(ipset_name)
            # Try to destroy (may fail if in use by iptables - that's OK)
            self.destroy_ipset(ipset_name, flush_first=False)  # Already flushed above
        
        # Rename temp to final name
        returncode, stdout, stderr = self.run_command(['ipset', 'rename', temp_name, ipset_name])
        if returncode != 0:
            # Rename can fail if target exists and is in use - this is normal
            self.logger.debug(f"Rename failed (expected if ipset in use): {stderr}")
            
            # If target still exists, use swap instead (atomic update)
            if self.ipset_exists(ipset_name):
                # Swap temp with existing (atomic operation)
                returncode, stdout, stderr = self.run_command(['ipset', 'swap', temp_name, ipset_name])
                if returncode != 0:
                    self.logger.error(f"Failed to swap ipsets: {stderr}")
                    self.destroy_ipset(temp_name)
                    return False
                
                # Clean up temp set
                self.destroy_ipset(temp_name)
            else:
                # Target was destroyed, create new and swap
                if not self.create_ipset(ipset_name, family):
                    self.destroy_ipset(temp_name)
                    return False
                
                self.run_command(['ipset', 'swap', temp_name, ipset_name])
                self.destroy_ipset(temp_name)
        
        self.logger.info(f"Populated ipset {ipset_name} from {zone_file}")
        return True
    
    def download_zone(self, country: str, ipv4: bool = True) -> Optional[str]:
        """Download zone file for country with retry logic"""
        output_dir = Path(self.config['OUTPUT_DIR'])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        version = 'v4' if ipv4 else 'v6'
        zone_file = output_dir / f"{country}-{version}.zone"
        
        base_url = self.config['IPV4_BASE_URL'] if ipv4 else self.config['IPV6_BASE_URL']
        url = f"{base_url}/{country}-aggregated.zone"
        
        timeout = int(self.config.get('HTTP_TIMEOUT', 30))
        max_retries = int(self.config.get('HTTP_RETRIES', 3))
        retry_delay = int(self.config.get('HTTP_RETRY_DELAY', 5))
        
        for attempt in range(1, max_retries + 1):
            try:
                self.logger.info(f"Downloading {url}... (attempt {attempt}/{max_retries})")
                with urllib.request.urlopen(url, timeout=timeout) as response:
                    data = response.read()
                    
                    # Write to file
                    with open(zone_file, 'wb') as f:
                        f.write(data)
                    
                    self.logger.info(f"Downloaded {zone_file} ({len(data)} bytes)")
                    return str(zone_file)
                    
            except urllib.error.HTTPError as e:
                if e.code in [503, 502, 504]:  # Temporary server errors
                    if attempt < max_retries:
                        wait_time = retry_delay * attempt  # Exponential backoff
                        self.logger.warning(f"HTTP {e.code} {e.reason} - retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                self.logger.error(f"HTTP error downloading {url}: {e.code} {e.reason}")
            except urllib.error.URLError as e:
                if attempt < max_retries:
                    wait_time = retry_delay * attempt
                    self.logger.warning(f"URL error: {e.reason} - retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                self.logger.error(f"URL error downloading {url}: {e.reason}")
            except Exception as e:
                if attempt < max_retries:
                    wait_time = retry_delay * attempt
                    self.logger.warning(f"Error: {e} - retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                self.logger.error(f"Error downloading {url}: {e}")
        
        self.logger.error(f"Failed to download {url} after {max_retries} attempts")
        return None
    
    def process_country(self, country: str) -> bool:
        """Download and process zone files for a country"""
        self.logger.info(f"Processing country: {country}")
        success = True
        
        ipset_enabled = self.config['IPSET_ENABLED'].lower() == 'true'
        prefix = self.config['IPSET_PREFIX']
        
        # IPv4
        if self.config['FETCH_IPV4'].lower() == 'true':
            zone_file = self.download_zone(country, ipv4=True)
            if zone_file:
                if ipset_enabled:
                    ipset_name = f"{prefix}-{country}-v4"
                    if not self.populate_ipset_from_file(ipset_name, zone_file):
                        success = False
            else:
                success = False
        
        # IPv6
        if self.config['FETCH_IPV6'].lower() == 'true':
            zone_file = self.download_zone(country, ipv4=False)
            if zone_file:
                if ipset_enabled:
                    ipset_name = f"{prefix}-{country}-v6"
                    if not self.populate_ipset_from_file(ipset_name, zone_file):
                        success = False
            else:
                success = False
        
        return success
    
    def run(self):
        """Main execution"""
        self.logger.info("=== IPdeny Fetcher Started ===")
        
        countries = self.config['COUNTRIES'].split()
        if not countries:
            self.logger.warning("No countries configured in COUNTRIES setting")
            self.logger.info("Edit /etc/ipdeny/ipdeny.conf and add country codes")
            return 0
        
        # Check if running as root (required for ipset)
        if os.geteuid() != 0 and self.config['IPSET_ENABLED'].lower() == 'true':
            self.logger.error("ipset operations require root privileges")
            return 1
        
        success_count = 0
        fail_count = 0
        
        for country in countries:
            if self.process_country(country.lower()):
                success_count += 1
            else:
                fail_count += 1
        
        self.logger.info(f"=== IPdeny Fetcher Completed: {success_count} succeeded, {fail_count} failed ===")
        return 0 if fail_count == 0 else 1


def main():
    try:
        fetcher = IPdenyFetcher()
        return fetcher.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
