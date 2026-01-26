#!/usr/bin/env python3
"""
Test script to verify NBA API field mappings against real API responses.

Run with: uv run python scripts/test_nba_api.py
"""

from pprint import pprint

from nba_api.stats.endpoints import (
    BoxScoreTraditionalV3,
    LeagueGameFinder,
    PlayByPlayV3,
)
from nba_api.stats.static import teams as static_teams


def test_static_teams():
    """Test static team data structure."""
    print("\n" + "=" * 60)
    print("STATIC TEAMS")
    print("=" * 60)

    teams = static_teams.get_teams()
    print(f"Total teams: {len(teams)}")
    print("\nFirst team structure:")
    pprint(teams[0])
    print("\nKeys:", list(teams[0].keys()))


def test_schedule():
    """Test LeagueGameFinder response structure."""
    print("\n" + "=" * 60)
    print("SCHEDULE (LeagueGameFinder)")
    print("=" * 60)

    # Get a few games from 2023-24 season
    finder = LeagueGameFinder(
        season_nullable="2023-24",
        season_type_nullable="Regular Season",
        league_id_nullable="00",
    )

    data = finder.get_normalized_dict()
    print("\nTop-level keys:", list(data.keys()))

    games = data.get("LeagueGameFinderResults", [])
    print(f"\nTotal games returned: {len(games)}")

    if games:
        print("\nFirst game structure:")
        pprint(games[0])
        print("\nKeys:", list(games[0].keys()))


def test_boxscore():
    """Test BoxScoreTraditionalV3 response structure."""
    print("\n" + "=" * 60)
    print("BOXSCORE (BoxScoreTraditionalV3)")
    print("=" * 60)

    # Use a known completed game from 2023-24 season
    # Game ID format: 002230XXXX for regular season
    game_id = "0022300001"  # First game of 2023-24 season

    try:
        boxscore = BoxScoreTraditionalV3(game_id=game_id)
        data = boxscore.get_normalized_dict()

        print("\nTop-level keys:", list(data.keys()))

        # Check PlayerStats
        player_stats = data.get("PlayerStats", [])
        print(f"\nPlayerStats count: {len(player_stats)}")
        if player_stats:
            print("\nFirst player stats structure:")
            pprint(player_stats[0])
            print("\nPlayerStats keys:", list(player_stats[0].keys()))

        # Check TeamStats
        team_stats = data.get("TeamStats", [])
        print(f"\nTeamStats count: {len(team_stats)}")
        if team_stats:
            print("\nFirst team stats structure:")
            pprint(team_stats[0])
            print("\nTeamStats keys:", list(team_stats[0].keys()))

    except Exception as e:
        print(f"Error fetching boxscore: {e}")


def test_pbp():
    """Test PlayByPlayV3 response structure."""
    print("\n" + "=" * 60)
    print("PLAY-BY-PLAY (PlayByPlayV3)")
    print("=" * 60)

    game_id = "0022300001"

    try:
        pbp = PlayByPlayV3(game_id=game_id)
        data = pbp.get_normalized_dict()

        print("\nTop-level keys:", list(data.keys()))

        events = data.get("PlayByPlay", [])
        print(f"\nPlayByPlay events count: {len(events)}")

        if events:
            print("\nFirst event structure:")
            pprint(events[0])
            print("\nEvent keys:", list(events[0].keys()))

            # Show a few different event types
            print("\n--- Sample events by type ---")
            seen_types = set()
            for event in events[:50]:
                action_type = event.get("actionType", "unknown")
                if action_type not in seen_types:
                    seen_types.add(action_type)
                    print(f"\n{action_type}:")
                    pprint({k: v for k, v in event.items() if v is not None})

    except Exception as e:
        print(f"Error fetching PBP: {e}")


def main():
    """Run all tests."""
    print("Testing NBA API field structures...")
    print("This will make real API calls - please be patient.\n")

    test_static_teams()
    test_schedule()
    test_boxscore()
    test_pbp()

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
