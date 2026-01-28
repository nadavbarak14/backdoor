#!/bin/bash
#
# Deploy Script
#
# Pulls latest changes from main branch and restarts servers.
#
# Usage:
#   ./scripts/deploy.sh
#

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
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

echo ""
echo -e "${GREEN}=== Basketball Analytics - Deploy ===${NC}"
echo ""

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    log_error "There are uncommitted changes. Please commit or stash them first."
    exit 1
fi

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    log_warn "Currently on branch '$CURRENT_BRANCH', switching to main..."
    git checkout main
fi

# Pull latest changes
log_info "Pulling latest changes from origin/main..."
git pull origin main

# Install any new dependencies
log_info "Installing Python dependencies..."
uv pip install -e ".[dev]"

log_info "Installing frontend dependencies..."
cd "$PROJECT_ROOT/agent-chat"
npm install
cd "$PROJECT_ROOT"

# Run database migrations if any
log_info "Running database migrations..."
uv run alembic upgrade head || log_warn "No migrations to run or alembic not configured"

# Restart servers
log_info "Restarting servers..."
"$PROJECT_ROOT/scripts/server.sh" restart

echo ""
echo -e "${GREEN}=== Deploy Complete ===${NC}"
"$PROJECT_ROOT/scripts/server.sh" status
