#!/bin/bash
#
# Install systemd services for persistent server management
#
# This script installs systemd service files that allow the backend and frontend
# to run persistently, survive reboots, and auto-restart on crash.
#
# Usage:
#   sudo ./scripts/install-services.sh install    # Install and enable services
#   sudo ./scripts/install-services.sh uninstall  # Disable and remove services
#

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_DIR="/etc/systemd/system"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

install_services() {
    log_info "Installing systemd services..."

    # Copy service files
    cp "$PROJECT_ROOT/scripts/systemd/basketball-backend.service" "$SYSTEMD_DIR/"
    cp "$PROJECT_ROOT/scripts/systemd/basketball-frontend.service" "$SYSTEMD_DIR/"

    # Reload systemd
    systemctl daemon-reload

    # Enable services (start on boot)
    systemctl enable basketball-backend.service
    systemctl enable basketball-frontend.service

    log_info "Services installed and enabled."
    echo ""
    echo "To start the servers:"
    echo "  sudo systemctl start basketball-backend"
    echo "  sudo systemctl start basketball-frontend"
    echo ""
    echo "Or use the server script:"
    echo "  ./scripts/server.sh start"
    echo ""
    echo "The servers will now:"
    echo "  - Auto-start on system boot"
    echo "  - Auto-restart if they crash"
    echo "  - Persist after terminal/tmux shutdown"
}

uninstall_services() {
    log_info "Uninstalling systemd services..."

    # Stop services if running
    systemctl stop basketball-backend.service 2>/dev/null || true
    systemctl stop basketball-frontend.service 2>/dev/null || true

    # Disable services
    systemctl disable basketball-backend.service 2>/dev/null || true
    systemctl disable basketball-frontend.service 2>/dev/null || true

    # Remove service files
    rm -f "$SYSTEMD_DIR/basketball-backend.service"
    rm -f "$SYSTEMD_DIR/basketball-frontend.service"

    # Reload systemd
    systemctl daemon-reload

    log_info "Services uninstalled."
}

case "$1" in
    install)
        if [ "$EUID" -ne 0 ]; then
            log_error "Please run as root: sudo $0 install"
            exit 1
        fi
        install_services
        ;;
    uninstall)
        if [ "$EUID" -ne 0 ]; then
            log_error "Please run as root: sudo $0 uninstall"
            exit 1
        fi
        uninstall_services
        ;;
    *)
        echo "Usage: sudo $0 {install|uninstall}"
        echo ""
        echo "  install    Install and enable systemd services"
        echo "  uninstall  Disable and remove systemd services"
        exit 1
        ;;
esac
