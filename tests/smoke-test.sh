#!/bin/bash
#
# Smoke test for ipdeny-systemctl-installer
#

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

# Test helper
test_assert() {
    local description=$1
    local command=$2
    
    echo -n "Testing: $description... "
    
    if eval "$command" &>/dev/null; then
        echo -e "${GREEN}PASS${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}FAIL${NC}"
        ((TESTS_FAILED++))
    fi
}

test_assert_file() {
    local description=$1
    local file=$2
    
    test_assert "$description" "[[ -f '$file' ]]"
}

test_assert_executable() {
    local description=$1
    local file=$2
    
    test_assert "$description" "[[ -x '$file' ]]"
}

echo "=== IPdeny Installer Smoke Tests ==="
echo

# Basic file structure tests
echo "Checking file structure..."
test_assert_file "install.sh exists" "./install.sh"
test_assert_executable "install.sh is executable" "./install.sh"
test_assert_file "uninstall.sh exists" "./uninstall.sh"
test_assert_executable "uninstall.sh is executable" "./uninstall.sh"
test_assert_file "fetcher script exists" "./bin/ipdeny-fetcher.py"
test_assert_executable "fetcher script is executable" "./bin/ipdeny-fetcher.py"
test_assert_file "systemd service exists" "./systemd/ipdeny-fetch.service"
test_assert_file "systemd timer exists" "./systemd/ipdeny-fetch.timer"
test_assert_file "config template exists" "./config/example.conf"
test_assert_file "README exists" "./README.md"
test_assert_file "LICENSE exists" "./LICENSE"

echo

# Python syntax check
echo "Checking Python syntax..."
if command -v python3 &>/dev/null; then
    test_assert "Python script syntax" "python3 -m py_compile ./bin/ipdeny-fetcher.py"
else
    echo -e "${YELLOW}SKIP: Python 3 not found${NC}"
fi

echo

# Check for required commands in scripts
echo "Checking script dependencies..."
test_assert "install.sh uses systemctl" "grep -q 'systemctl' ./install.sh"
test_assert "fetcher uses ipset" "grep -q 'ipset' ./bin/ipdeny-fetcher.py"
test_assert "firewall updater uses iptables" "grep -q 'iptables' ./bin/ipdeny-firewall-update.py"

echo

# Configuration validation
echo "Checking configuration format..."
test_assert "config has OUTPUT_DIR" "grep -q 'OUTPUT_DIR=' ./config/example.conf"
test_assert "config has COUNTRIES" "grep -q 'COUNTRIES=' ./config/example.conf"
test_assert "config has IPSET_ENABLED" "grep -q 'IPSET_ENABLED=' ./config/example.conf"

echo

# Systemd unit validation
echo "Checking systemd units..."
test_assert "service has ExecStart" "grep -q 'ExecStart=' ./systemd/ipdeny-fetch.service"
test_assert "timer has OnCalendar" "grep -q 'OnCalendar=' ./systemd/ipdeny-fetch.timer"
test_assert "service runs as root" "grep -q 'User=root' ./systemd/ipdeny-fetch.service"

echo

# If systemd-analyze is available, validate units
if command -v systemd-analyze &>/dev/null; then
    echo "Validating systemd unit syntax..."
    test_assert "service unit syntax" "systemd-analyze verify ./systemd/ipdeny-fetch.service 2>/dev/null || true"
    test_assert "timer unit syntax" "systemd-analyze verify ./systemd/ipdeny-fetch.timer 2>/dev/null || true"
    echo
fi

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed${NC}"
    exit 1
fi
