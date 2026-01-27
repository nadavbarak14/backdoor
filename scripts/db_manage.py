#!/usr/bin/env python3
"""
Database Management Script

Manages development database templates for working across multiple branches.
Each branch can work with its own copy of the database while sharing a common template.

Commands:
    copy-template   Copy the template database to the working location
    update-template Update the template from the current working database
    status          Show database file information

Usage:
    python scripts/db_manage.py copy-template
    python scripts/db_manage.py update-template
    python scripts/db_manage.py status

Environment Variables:
    DB_TEMPLATE_PATH - Path to the template database (default: data/template.db)
    DATABASE_URL     - SQLAlchemy URL for working database (default: sqlite:///./basketball.db)
"""

import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()


def get_paths() -> tuple[Path, Path]:
    """Get template and working database paths from environment."""
    template_path = Path(os.getenv("DB_TEMPLATE_PATH", "data/template.db"))

    # Parse DATABASE_URL to get working db path
    db_url = os.getenv("DATABASE_URL", "sqlite:///./basketball.db")
    if db_url.startswith("sqlite:///"):
        working_path = Path(db_url.replace("sqlite:///", "").lstrip("./"))
    else:
        print("Error: This script only works with SQLite databases")
        sys.exit(1)

    return template_path, working_path


def get_file_info(path: Path) -> dict:
    """Get information about a database file."""
    if not path.exists():
        return {"exists": False}

    stat = path.stat()
    return {
        "exists": True,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


def copy_template():
    """Copy template database to working location."""
    template_path, working_path = get_paths()

    if not template_path.exists():
        print(f"Error: Template database not found at {template_path}")
        print("Run 'python scripts/db_manage.py update-template' first to create it.")
        sys.exit(1)

    if working_path.exists():
        backup_path = working_path.with_suffix(".db.backup")
        print(f"Backing up existing database to {backup_path}")
        shutil.copy2(working_path, backup_path)

    print(f"Copying template from {template_path} to {working_path}")
    shutil.copy2(template_path, working_path)

    info = get_file_info(working_path)
    print(f"Done! Working database: {info['size_mb']} MB")


def update_template():
    """Update template from current working database."""
    template_path, working_path = get_paths()

    if not working_path.exists():
        print(f"Error: Working database not found at {working_path}")
        sys.exit(1)

    # Create data directory if it doesn't exist
    template_path.parent.mkdir(parents=True, exist_ok=True)

    if template_path.exists():
        backup_path = template_path.with_suffix(".db.backup")
        print(f"Backing up existing template to {backup_path}")
        shutil.copy2(template_path, backup_path)

    print(f"Updating template from {working_path} to {template_path}")
    shutil.copy2(working_path, template_path)

    info = get_file_info(template_path)
    print(f"Done! Template database: {info['size_mb']} MB")
    print(f"Template location: {template_path.absolute()}")


def status():
    """Show database file information."""
    template_path, working_path = get_paths()

    print("Database Status")
    print("=" * 50)

    print(f"\nTemplate: {template_path}")
    template_info = get_file_info(template_path)
    if template_info["exists"]:
        print(f"  Size: {template_info['size_mb']} MB")
        print(f"  Modified: {template_info['modified']}")
    else:
        print("  (not found)")

    print(f"\nWorking: {working_path}")
    working_info = get_file_info(working_path)
    if working_info["exists"]:
        print(f"  Size: {working_info['size_mb']} MB")
        print(f"  Modified: {working_info['modified']}")
    else:
        print("  (not found)")


def main():
    parser = argparse.ArgumentParser(
        description="Manage development database templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "command",
        choices=["copy-template", "update-template", "status"],
        help="Command to run",
    )

    args = parser.parse_args()

    if args.command == "copy-template":
        copy_template()
    elif args.command == "update-template":
        update_template()
    elif args.command == "status":
        status()


if __name__ == "__main__":
    main()
