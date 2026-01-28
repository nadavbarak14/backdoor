# Server Deployment Setup

**Ticket ID:** SERVER-001
**Status:** Implemented
**Priority:** High
**Created:** 2026-01-28

## Overview

Set up persistent server infrastructure for the Basketball Analytics Platform with manual control for sync operations and deployments.

## Requirements

### 1. Persistent Server Process
- Backend (FastAPI) and Frontend (Next.js) should run continuously
- Auto-restart on crash
- Survive terminal disconnection and system reboots
- Log output to files for debugging

### 2. Manual Operations
The following operations should be easy to execute manually:

#### Sync Script
```bash
# Run the data sync script
./scripts/sync.sh
```

#### Deploy (Checkout & Restart)
```bash
# Pull latest main and restart servers
./scripts/deploy.sh
```

### 3. Server Management Commands
```bash
# Start servers
./scripts/server.sh start

# Stop servers
./scripts/server.sh stop

# Restart servers
./scripts/server.sh restart

# Check status
./scripts/server.sh status

# View logs
./scripts/server.sh logs [backend|frontend]
```

## Technical Approach

### Option A: systemd Services (Recommended for Linux)
- Create systemd service files for backend and frontend
- Use `systemctl` for management
- Automatic restart on failure
- Proper logging via journald

### Option B: PM2 Process Manager
- Single tool for both Python and Node.js
- Built-in log management
- Easy deployment with `pm2 deploy`

### Option C: Supervisor
- Python-based process manager
- Simple configuration
- Good for development servers

## Implementation Plan

### Phase 1: Server Scripts
1. Create `scripts/server.sh` - Main server management script
2. Create `scripts/sync.sh` - Data sync wrapper
3. Create `scripts/deploy.sh` - Git pull and restart

### Phase 2: Process Management
1. Choose process manager (systemd/PM2/supervisor)
2. Create configuration files
3. Set up auto-restart policies
4. Configure log rotation

### Phase 3: Documentation
1. Update README with server commands
2. Document deployment workflow
3. Add troubleshooting guide

## Configuration

### Backend (FastAPI)
- **Port:** 9000
- **Host:** 0.0.0.0
- **Workers:** 1 (development)
- **Command:** `uv run uvicorn src.main:app --host 0.0.0.0 --port 9000`

### Frontend (Next.js)
- **Port:** 3001
- **Host:** 0.0.0.0
- **Command:** `npm run dev -- --port 3001`

## File Structure
```
scripts/
├── server.sh      # Main server management
├── sync.sh        # Data sync script
├── deploy.sh      # Git pull and restart
└── config/
    ├── backend.service    # systemd service (if using)
    └── frontend.service   # systemd service (if using)
```

## Acceptance Criteria

- [ ] Servers persist after terminal disconnect
- [ ] Servers auto-restart on crash
- [ ] Can manually trigger sync with single command
- [ ] Can deploy (pull + restart) with single command
- [ ] Can view server status and logs easily
- [ ] Documentation updated

## Notes

- For development/staging environment
- Production would need additional considerations (nginx, SSL, etc.)
- Current ports: Backend 9000, Frontend 3001
