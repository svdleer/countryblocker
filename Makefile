.PHONY: all install uninstall test clean package help

PREFIX ?= /usr/local
SYSTEMD_DIR ?= /etc/systemd/system
DESTDIR ?=

VERSION := 1.0.0
PACKAGE_NAME := ipdeny-systemctl-installer-$(VERSION)

help:
	@echo "IPdeny Systemctl Installer - Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install     - Install ipdeny fetcher and systemd units"
	@echo "  uninstall   - Remove ipdeny fetcher and systemd units"
	@echo "  test        - Run smoke tests"
	@echo "  package     - Create distribution tarball"
	@echo "  clean       - Remove build artifacts"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "Usage:"
	@echo "  sudo make install"
	@echo "  sudo make uninstall"
	@echo "  make test"
	@echo ""

install:
	@echo "Running installer..."
	@./install.sh

uninstall:
	@echo "Running uninstaller..."
	@./uninstall.sh

test:
	@echo "Running smoke tests..."
	@./tests/smoke-test.sh

package: clean
	@echo "Creating package: $(PACKAGE_NAME).tar.gz"
	@mkdir -p dist
	@mkdir -p $(PACKAGE_NAME)
	@cp -r bin config examples systemd tests $(PACKAGE_NAME)/
	@cp install.sh uninstall.sh README.md LICENSE Makefile $(PACKAGE_NAME)/
	@chmod +x $(PACKAGE_NAME)/install.sh
	@chmod +x $(PACKAGE_NAME)/uninstall.sh
	@chmod +x $(PACKAGE_NAME)/bin/ipdeny-fetcher.py
	@chmod +x $(PACKAGE_NAME)/tests/smoke-test.sh
	@chmod +x $(PACKAGE_NAME)/examples/apply-firewall-rules.sh
	@tar czf dist/$(PACKAGE_NAME).tar.gz $(PACKAGE_NAME)
	@rm -rf $(PACKAGE_NAME)
	@echo "Package created: dist/$(PACKAGE_NAME).tar.gz"
	@ls -lh dist/$(PACKAGE_NAME).tar.gz

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf dist/
	@rm -rf ipdeny-systemctl-installer-*/
	@rm -f *.tar.gz
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@echo "Clean complete"

all: test
