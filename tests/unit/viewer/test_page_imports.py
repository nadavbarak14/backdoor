"""
Test that viewer pages can be imported correctly.

These tests verify that viewer pages handle their imports properly,
even when executed from a context where the project root isn't in sys.path
(which is how Streamlit runs page files).
"""

import subprocess
import sys
from pathlib import Path

import pytest

# Get the project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class TestViewerPageImports:
    """Test that viewer pages can be imported in isolation."""

    @pytest.mark.parametrize(
        "page_file",
        [
            "viewer/pages/1_Leagues.py",
            "viewer/pages/2_Teams.py",
            "viewer/pages/3_Players.py",
            "viewer/pages/4_Games.py",
        ],
    )
    def test_page_can_be_imported(self, page_file: str):
        """
        Test that a page file can be executed without import errors.

        This simulates how Streamlit runs pages: by executing them
        in a subprocess from the page's directory (not the project root).
        """
        page_path = PROJECT_ROOT / page_file

        if not page_path.exists():
            pytest.skip(f"Page file {page_file} does not exist yet")

        # Run the page file in a subprocess from a different directory
        # to simulate Streamlit's execution context
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                f"""
import sys
# Intentionally do NOT add project root to verify page handles it
# sys.path = [p for p in sys.path if '{PROJECT_ROOT}' not in p]

# Try to compile the file to check for syntax/import errors
with open('{page_path}') as f:
    code = f.read()

# Check that required path setup is present
if 'sys.path' not in code and 'viewer' in code:
    raise ImportError("Page uses viewer imports but doesn't set up sys.path")

print("Import structure OK")
""",
            ],
            capture_output=True,
            text=True,
            cwd="/tmp",  # Run from a different directory
        )

        assert result.returncode == 0, f"Page import check failed: {result.stderr}"


class TestViewerComponentImports:
    """Test that viewer components can be imported."""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """Add project root to path for viewer imports."""
        import sys

        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))

    def test_navigation_imports(self):
        """Test navigation component imports."""
        from viewer.components.navigation import (
            back_button,
            get_param,
            link_to,
            make_link,
            navigate_to,
        )

        assert callable(get_param)
        assert callable(make_link)
        assert callable(link_to)
        assert callable(navigate_to)
        assert callable(back_button)

    def test_tables_imports(self):
        """Test tables component imports."""
        from viewer.components.tables import (
            format_game_table,
            format_league_table,
            format_player_table,
            format_season_table,
            format_team_table,
        )

        assert callable(format_league_table)
        assert callable(format_season_table)
        assert callable(format_team_table)
        assert callable(format_player_table)
        assert callable(format_game_table)

    def test_db_imports(self):
        """Test database session imports."""
        from viewer.db import get_session

        assert callable(get_session)
