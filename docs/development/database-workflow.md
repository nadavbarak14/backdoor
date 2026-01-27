# Database Workflow for Development

This document explains how to manage development databases when working across multiple feature branches.

## Overview

When working on sync features, multiple branches often need access to the same base dataset. To avoid conflicts and ensure reproducibility, we use a **template database** workflow:

1. A shared template database is stored in `data/template.db`
2. Each branch works with its own copy at `basketball.db` (project root)
3. Changes to sync logic can be tested independently
4. The template can be updated when new data is synced

## File Locations

| File | Purpose |
|------|---------|
| `data/template.db` | Shared template database (not in git) |
| `basketball.db` | Working database for current branch (not in git) |
| `data/.gitkeep` | Keeps the data directory in git |

## Environment Configuration

Add to your `.env` file:

```bash
# Working database (default)
DATABASE_URL="sqlite:///./basketball.db"

# Template database location
DB_TEMPLATE_PATH="data/template.db"
```

## Commands

The `scripts/db_manage.py` script provides these commands:

### Check Status

```bash
python scripts/db_manage.py status
```

Shows information about both template and working databases (size, last modified).

### Copy Template to Working Database

```bash
python scripts/db_manage.py copy-template
```

Use this when:
- Starting work on a new feature branch
- Resetting your working database to a clean state
- After pulling changes that require fresh data

This will:
1. Backup your existing working database (if any) to `basketball.db.backup`
2. Copy the template to your working location

### Update Template from Working Database

```bash
python scripts/db_manage.py update-template
```

Use this when:
- You've synced new games/seasons that others should have
- The template is outdated and needs refreshing

This will:
1. Backup the existing template (if any) to `template.db.backup`
2. Copy your working database to the template location

## Typical Workflows

### Starting a New Feature Branch

```bash
# 1. Create your feature branch
git checkout -b feature/my-sync-feature

# 2. Copy the template database
python scripts/db_manage.py copy-template

# 3. Start the servers and work
.venv/bin/python -m uvicorn src.main:app --reload
```

### After Syncing New Data

```bash
# 1. Verify the data looks good in your working database

# 2. Update the template for others to use
python scripts/db_manage.py update-template

# 3. Commit your code changes (database files are gitignored)
git add .
git commit -m "feat: sync new season data"
```

### Switching Between Branches

```bash
# 1. Save your current work if needed
# (your working database is branch-independent)

# 2. Switch branches
git checkout other-branch

# 3. If the other branch needs different data, copy the template
python scripts/db_manage.py copy-template
```

## Best Practices

1. **Don't commit database files** - They're gitignored for a reason
2. **Update the template after major syncs** - Keep it current for the team
3. **Copy template when starting fresh** - Ensures consistent starting point
4. **Backup before destructive operations** - The script does this automatically

## Sharing the Template

Since the template database is not in git, share it via:

1. **Shared drive/cloud storage** - Upload `data/template.db` to a shared location
2. **Direct copy** - Copy between machines manually
3. **Re-sync** - Run the sync to recreate from source APIs

## Troubleshooting

### "Template database not found"

Run the sync to create initial data, then update the template:

```bash
# Run sync via API or CLI
# Then:
python scripts/db_manage.py update-template
```

### "Working database not found"

Copy from template or run migrations:

```bash
python scripts/db_manage.py copy-template
# or
alembic upgrade head
```

### Database schema mismatch

If the template was created with old migrations:

```bash
# Copy template first
python scripts/db_manage.py copy-template

# Run any new migrations
alembic upgrade head
```
