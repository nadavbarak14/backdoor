#!/bin/bash
#
# Server Management Script
#
# Manages the Backend (FastAPI) and Frontend (Next.js) servers.
# Automatically uses systemd if services are installed, otherwise falls back to nohup.
#
# Usage:
#   ./scripts/server.sh start|stop|restart|status|logs [backend|frontend]
#
# To install systemd services for persistence after reboot/terminal close:
#   sudo ./scripts/install-services.sh install
#

set -e

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$PROJECT_ROOT/.pids"
LOG_DIR="$PROJECT_ROOT/logs"

# Backend config
BACKEND_PORT=9000
BACKEND_PID_FILE="$PID_DIR/backend.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
BACKEND_SERVICE="basketball-backend"

# Frontend config (agent-chat)
FRONTEND_PORT=3001
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
FRONTEND_LOG="$LOG_DIR/frontend.log"
FRONTEND_SERVICE="basketball-frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Ensure directories exist
mkdir -p "$PID_DIR" "$LOG_DIR"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if systemd service is installed
has_systemd_service() {
    local service=$1
    systemctl list-unit-files "$service.service" 2>/dev/null | grep -q "$service.service"
}

# Check if systemd service is running
is_systemd_running() {
    local service=$1
    systemctl is-active --quiet "$service.service" 2>/dev/null
}

# Check if nohup process is running
is_nohup_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

get_pid() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        cat "$pid_file"
    fi
}

# ============ Backend Functions ============

start_backend() {
    if has_systemd_service "$BACKEND_SERVICE"; then
        if is_systemd_running "$BACKEND_SERVICE"; then
            log_warn "Backend is already running (systemd)"
            return 0
        fi
        log_info "Starting Backend via systemd..."
        sudo systemctl start "$BACKEND_SERVICE"
        sleep 2
        if is_systemd_running "$BACKEND_SERVICE"; then
            log_info "Backend started (systemd, Port: $BACKEND_PORT)"
        else
            log_error "Backend failed to start. Check: sudo journalctl -u $BACKEND_SERVICE"
            return 1
        fi
    else
        # Fallback to nohup
        if is_nohup_running "$BACKEND_PID_FILE"; then
            log_warn "Backend is already running (PID: $(get_pid $BACKEND_PID_FILE))"
            return 0
        fi

        log_info "Starting Backend on port $BACKEND_PORT (nohup)..."
        cd "$PROJECT_ROOT"

        nohup uv run uvicorn src.main:app --host 0.0.0.0 --port $BACKEND_PORT >> "$BACKEND_LOG" 2>&1 &
        local pid=$!
        echo $pid > "$BACKEND_PID_FILE"

        sleep 2
        if is_nohup_running "$BACKEND_PID_FILE"; then
            log_info "Backend started (PID: $pid)"
            log_warn "Note: For persistence after terminal close, run: sudo ./scripts/install-services.sh install"
        else
            log_error "Backend failed to start. Check logs: $BACKEND_LOG"
            rm -f "$BACKEND_PID_FILE"
            return 1
        fi
    fi
}

stop_backend() {
    if has_systemd_service "$BACKEND_SERVICE"; then
        if ! is_systemd_running "$BACKEND_SERVICE"; then
            log_warn "Backend is not running (systemd)"
            return 0
        fi
        log_info "Stopping Backend via systemd..."
        sudo systemctl stop "$BACKEND_SERVICE"
        log_info "Backend stopped"
    else
        if ! is_nohup_running "$BACKEND_PID_FILE"; then
            log_warn "Backend is not running"
            rm -f "$BACKEND_PID_FILE"
            return 0
        fi

        local pid=$(get_pid "$BACKEND_PID_FILE")
        log_info "Stopping Backend (PID: $pid)..."
        kill "$pid" 2>/dev/null || true

        local count=0
        while is_nohup_running "$BACKEND_PID_FILE" && [ $count -lt 10 ]; do
            sleep 1
            count=$((count + 1))
        done

        if is_nohup_running "$BACKEND_PID_FILE"; then
            log_warn "Force killing Backend..."
            kill -9 "$pid" 2>/dev/null || true
        fi

        rm -f "$BACKEND_PID_FILE"
        log_info "Backend stopped"
    fi
}

# ============ Frontend Functions ============

start_frontend() {
    if has_systemd_service "$FRONTEND_SERVICE"; then
        if is_systemd_running "$FRONTEND_SERVICE"; then
            log_warn "Frontend is already running (systemd)"
            return 0
        fi
        log_info "Starting Frontend via systemd..."
        sudo systemctl start "$FRONTEND_SERVICE"
        sleep 3
        if is_systemd_running "$FRONTEND_SERVICE"; then
            log_info "Frontend started (systemd, Port: $FRONTEND_PORT)"
        else
            log_error "Frontend failed to start. Check: sudo journalctl -u $FRONTEND_SERVICE"
            return 1
        fi
    else
        if is_nohup_running "$FRONTEND_PID_FILE"; then
            log_warn "Frontend is already running (PID: $(get_pid $FRONTEND_PID_FILE))"
            return 0
        fi

        log_info "Starting Frontend on port $FRONTEND_PORT (nohup)..."
        cd "$PROJECT_ROOT/agent-chat"

        nohup npm run dev >> "$FRONTEND_LOG" 2>&1 &
        local pid=$!
        echo $pid > "$FRONTEND_PID_FILE"

        sleep 3
        if is_nohup_running "$FRONTEND_PID_FILE"; then
            log_info "Frontend started (PID: $pid)"
            log_warn "Note: For persistence after terminal close, run: sudo ./scripts/install-services.sh install"
        else
            log_error "Frontend failed to start. Check logs: $FRONTEND_LOG"
            rm -f "$FRONTEND_PID_FILE"
            return 1
        fi
    fi
}

stop_frontend() {
    if has_systemd_service "$FRONTEND_SERVICE"; then
        if ! is_systemd_running "$FRONTEND_SERVICE"; then
            log_warn "Frontend is not running (systemd)"
            return 0
        fi
        log_info "Stopping Frontend via systemd..."
        sudo systemctl stop "$FRONTEND_SERVICE"
        log_info "Frontend stopped"
    else
        if ! is_nohup_running "$FRONTEND_PID_FILE"; then
            log_warn "Frontend is not running"
            rm -f "$FRONTEND_PID_FILE"
            return 0
        fi

        local pid=$(get_pid "$FRONTEND_PID_FILE")
        log_info "Stopping Frontend (PID: $pid)..."
        kill -- -"$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true

        local count=0
        while is_nohup_running "$FRONTEND_PID_FILE" && [ $count -lt 10 ]; do
            sleep 1
            count=$((count + 1))
        done

        if is_nohup_running "$FRONTEND_PID_FILE"; then
            log_warn "Force killing Frontend..."
            kill -9 "$pid" 2>/dev/null || true
        fi

        rm -f "$FRONTEND_PID_FILE"
        log_info "Frontend stopped"
    fi
}

# ============ Status Functions ============

show_status() {
    echo ""
    echo "=== Server Status ==="
    echo ""

    # Detect mode
    local mode="nohup"
    if has_systemd_service "$BACKEND_SERVICE"; then
        mode="systemd"
    fi
    echo -e "Mode: ${YELLOW}$mode${NC}"
    echo ""

    # Backend status
    if has_systemd_service "$BACKEND_SERVICE"; then
        if is_systemd_running "$BACKEND_SERVICE"; then
            echo -e "Backend:  ${GREEN}RUNNING${NC} (systemd, Port: $BACKEND_PORT)"
        else
            echo -e "Backend:  ${RED}STOPPED${NC} (systemd)"
        fi
    else
        if is_nohup_running "$BACKEND_PID_FILE"; then
            local pid=$(get_pid "$BACKEND_PID_FILE")
            echo -e "Backend:  ${GREEN}RUNNING${NC} (PID: $pid, Port: $BACKEND_PORT)"
        else
            echo -e "Backend:  ${RED}STOPPED${NC}"
        fi
    fi

    # Frontend status
    if has_systemd_service "$FRONTEND_SERVICE"; then
        if is_systemd_running "$FRONTEND_SERVICE"; then
            echo -e "Frontend: ${GREEN}RUNNING${NC} (systemd, Port: $FRONTEND_PORT)"
        else
            echo -e "Frontend: ${RED}STOPPED${NC} (systemd)"
        fi
    else
        if is_nohup_running "$FRONTEND_PID_FILE"; then
            local pid=$(get_pid "$FRONTEND_PID_FILE")
            echo -e "Frontend: ${GREEN}RUNNING${NC} (PID: $pid, Port: $FRONTEND_PORT)"
        else
            echo -e "Frontend: ${RED}STOPPED${NC}"
        fi
    fi

    echo ""

    if [ "$mode" = "nohup" ]; then
        echo -e "${YELLOW}Tip:${NC} For persistence after terminal close, run:"
        echo "  sudo ./scripts/install-services.sh install"
        echo ""
    fi
}

show_logs() {
    local service=$1
    local lines=${2:-50}

    case "$service" in
        backend)
            if has_systemd_service "$BACKEND_SERVICE"; then
                sudo journalctl -u "$BACKEND_SERVICE" -f -n "$lines"
            elif [ -f "$BACKEND_LOG" ]; then
                tail -n "$lines" -f "$BACKEND_LOG"
            else
                log_error "Backend log not found: $BACKEND_LOG"
            fi
            ;;
        frontend)
            if has_systemd_service "$FRONTEND_SERVICE"; then
                sudo journalctl -u "$FRONTEND_SERVICE" -f -n "$lines"
            elif [ -f "$FRONTEND_LOG" ]; then
                tail -n "$lines" -f "$FRONTEND_LOG"
            else
                log_error "Frontend log not found: $FRONTEND_LOG"
            fi
            ;;
        *)
            echo "Usage: $0 logs [backend|frontend]"
            exit 1
            ;;
    esac
}

# ============ Main Command Handling ============

case "$1" in
    start)
        case "$2" in
            backend)
                start_backend
                ;;
            frontend)
                start_frontend
                ;;
            ""|all)
                start_backend
                start_frontend
                ;;
            *)
                echo "Usage: $0 start [backend|frontend|all]"
                exit 1
                ;;
        esac
        ;;
    stop)
        case "$2" in
            backend)
                stop_backend
                ;;
            frontend)
                stop_frontend
                ;;
            ""|all)
                stop_backend
                stop_frontend
                ;;
            *)
                echo "Usage: $0 stop [backend|frontend|all]"
                exit 1
                ;;
        esac
        ;;
    restart)
        case "$2" in
            backend)
                stop_backend
                start_backend
                ;;
            frontend)
                stop_frontend
                start_frontend
                ;;
            ""|all)
                stop_backend
                stop_frontend
                start_backend
                start_frontend
                ;;
            *)
                echo "Usage: $0 restart [backend|frontend|all]"
                exit 1
                ;;
        esac
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2" "$3"
        ;;
    *)
        echo "Basketball Analytics Platform - Server Management"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs} [backend|frontend]"
        echo ""
        echo "Commands:"
        echo "  start   [service]  Start servers (default: all)"
        echo "  stop    [service]  Stop servers (default: all)"
        echo "  restart [service]  Restart servers (default: all)"
        echo "  status             Show server status"
        echo "  logs    <service>  Tail logs for a service"
        echo ""
        echo "Services:"
        echo "  backend   FastAPI backend (port $BACKEND_PORT)"
        echo "  frontend  Next.js frontend (port $FRONTEND_PORT)"
        echo ""
        echo "For persistence after terminal/tmux close and auto-restart on reboot:"
        echo "  sudo ./scripts/install-services.sh install"
        echo ""
        exit 1
        ;;
esac
