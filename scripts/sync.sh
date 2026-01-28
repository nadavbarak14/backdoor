#!/bin/bash
#
# Data Sync Script
#
# Runs data synchronization for the Basketball Analytics Platform.
# Wrapper around the Python sync script with sensible defaults.
#
# Usage:
#   ./scripts/sync.sh                    # Sync current season (default)
#   ./scripts/sync.sh winner 2025-26     # Sync specific season
#   ./scripts/sync.sh winner 2025-26 --include-pbp
#

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Basketball Analytics - Data Sync ===${NC}"
echo ""

# Default values
SOURCE="${1:-winner}"
SEASON="${2:-2025-26}"
shift 2 2>/dev/null || true

echo -e "Source:  ${YELLOW}$SOURCE${NC}"
echo -e "Season:  ${YELLOW}$SEASON${NC}"
echo ""

# Run the sync script
uv run python scripts/run_sync.py "$SOURCE" "$SEASON" "$@"

echo ""
echo -e "${GREEN}=== Sync Complete ===${NC}"
