"""
Capture real API responses as test fixtures.

This script fetches real data from each source's API and saves
the responses as JSON fixtures for integration testing.

Usage:
    uv run python scripts/capture_fixtures.py [source]

    # Capture all sources
    uv run python scripts/capture_fixtures.py

    # Capture specific source
    uv run python scripts/capture_fixtures.py winner
    uv run python scripts/capture_fixtures.py euroleague
    uv run python scripts/capture_fixtures.py nba
    uv run python scripts/capture_fixtures.py ibasketball
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


def save_fixture(source: str, name: str, data: dict | list) -> None:
    """Save data as a JSON fixture file."""
    path = FIXTURES_DIR / source / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Saved: {path}")


def capture_winner() -> None:
    """Capture Winner API responses."""
    print("\n=== Capturing Winner fixtures ===")
    import httpx

    # Schedule - all games
    print("Fetching schedule...")
    resp = httpx.get(
        "https://basket.co.il/pbp/json/games_all.json",
        timeout=30.0
    )
    resp.raise_for_status()
    schedule_data = resp.json()

    # Structure is: [{"games": [...], ...}, ...] - list of competitions
    # Extract games from first competition with games
    all_games = []
    if isinstance(schedule_data, list):
        for comp in schedule_data:
            if isinstance(comp, dict) and "games" in comp:
                all_games.extend(comp["games"])

    # Save first 5 games as sample
    save_fixture("winner", "schedule", all_games[:5])

    # Find a completed game (has scores)
    completed_games = [g for g in all_games if g.get("score_team1") and g.get("score_team2")]
    if completed_games:
        game = completed_games[0]
        game_id = game.get("ExternalID") or game.get("id")

        if game_id:
            # Boxscore
            print(f"Fetching boxscore for game {game_id}...")
            try:
                box_resp = httpx.get(
                    f"https://stats.segevstats.com/realtimestat_heb/get_team_score.php?game_id={game_id}",
                    timeout=30.0
                )
                box_resp.raise_for_status()
                save_fixture("winner", "boxscore", box_resp.json())
            except Exception as e:
                print(f"  Warning: Could not fetch boxscore: {e}")

            # PBP
            print(f"Fetching PBP for game {game_id}...")
            try:
                pbp_resp = httpx.get(
                    f"https://stats.segevstats.com/realtimestat_heb/get_team_action.php?game_id={game_id}",
                    timeout=30.0
                )
                pbp_resp.raise_for_status()
                pbp_data = pbp_resp.json()
                # Save first 50 events
                if isinstance(pbp_data, list):
                    save_fixture("winner", "pbp", pbp_data[:50])
                else:
                    save_fixture("winner", "pbp", pbp_data)
            except Exception as e:
                print(f"  Warning: Could not fetch PBP: {e}")
    else:
        print("  No completed games found")

    print("Winner fixtures captured!")


def capture_euroleague() -> None:
    """Capture Euroleague API responses."""
    print("\n=== Capturing Euroleague fixtures ===")
    import xml.etree.ElementTree as ET
    import httpx
    from euroleague_api.boxscore_data import BoxScoreData
    from euroleague_api.play_by_play_data import PlayByPlay

    season = 2024
    competition = "E"

    # Schedule - use direct API (returns XML)
    print("Fetching schedule...")
    played_games = []
    try:
        resp = httpx.get(
            f"https://api-live.euroleague.net/v1/schedules?seasonCode={competition}{season}",
            timeout=30.0
        )
        resp.raise_for_status()

        # Parse XML
        root = ET.fromstring(resp.text)
        games = []
        for item in root.findall("item"):
            game = {}
            for child in item:
                game[child.tag] = child.text
            games.append(game)

        # Save first 10 games
        save_fixture("euroleague", "schedule", games[:10])
        played_games = [g for g in games if g.get("played") == "true"]

    except Exception as e:
        print(f"  Warning: Could not fetch schedule: {e}")
        import traceback
        traceback.print_exc()

    # Find a played game for boxscore/PBP
    if played_games:
        game = played_games[0]
        # gamecode format is like "E2024_1" - extract the number
        gamecode_str = game.get("gamecode", "")
        try:
            game_code = int(gamecode_str.split("_")[-1]) if "_" in gamecode_str else int(game.get("game", 0))
        except ValueError:
            game_code = 1

        if game_code:
            # Boxscore using euroleague_api
            print(f"Fetching boxscore for game {game_code}...")
            try:
                boxscore = BoxScoreData(competition)
                box_df = boxscore.get_player_boxscore_stats_data(
                    season, game_code
                )
                if box_df is not None and not box_df.empty:
                    save_fixture("euroleague", "boxscore", box_df.to_dict(orient="records"))
            except Exception as e:
                print(f"  Warning: Could not fetch boxscore: {e}")

            # PBP using euroleague_api
            print(f"Fetching PBP for game {game_code}...")
            try:
                pbp = PlayByPlay(competition)
                pbp_df = pbp.get_game_play_by_play_data(season, game_code)
                if pbp_df is not None and not pbp_df.empty:
                    # Save first 50 events
                    save_fixture("euroleague", "pbp", pbp_df.head(50).to_dict(orient="records"))
            except Exception as e:
                print(f"  Warning: Could not fetch PBP: {e}")

    print("Euroleague fixtures captured!")


def capture_nba() -> None:
    """Capture NBA API responses."""
    print("\n=== Capturing NBA fixtures ===")
    import time
    from nba_api.stats.endpoints import LeagueGameFinder
    from nba_api.stats.endpoints import BoxScoreTraditionalV3
    from nba_api.stats.endpoints import PlayByPlayV3

    season = "2024-25"

    # Schedule - get recent games
    print("Fetching schedule...")
    time.sleep(1)  # Rate limit
    finder = LeagueGameFinder(
        season_nullable=season,
        league_id_nullable="00",
        season_type_nullable="Regular Season"
    )
    games_df = finder.get_data_frames()[0]

    if games_df is not None and not games_df.empty:
        # Save first 20 rows (10 games, 2 rows per game)
        save_fixture("nba", "schedule", games_df.head(20).to_dict(orient="records"))

        # Get a completed game
        game_ids = games_df["GAME_ID"].unique()
        if len(game_ids) > 0:
            game_id = game_ids[0]

            # Boxscore V3
            print(f"Fetching boxscore for game {game_id}...")
            time.sleep(3)  # Rate limit - NBA is strict
            try:
                boxscore = BoxScoreTraditionalV3(game_id=game_id)
                box_data = boxscore.get_dict()
                save_fixture("nba", "boxscore", box_data)
            except Exception as e:
                print(f"  Warning: Could not fetch boxscore: {e}")

            # PBP V3
            print(f"Fetching PBP for game {game_id}...")
            time.sleep(3)  # Rate limit
            try:
                pbp = PlayByPlayV3(game_id=game_id)
                pbp_data = pbp.get_dict()
                # Just save the game.actions part, limited to 100 events
                game = pbp_data.get("game", {})
                actions = game.get("actions", [])[:100]
                save_fixture("nba", "pbp", {"game": {"actions": actions}})
            except Exception as e:
                print(f"  Warning: Could not fetch PBP: {e}")

    print("NBA fixtures captured!")


def capture_ibasketball() -> None:
    """Capture iBasketball API responses."""
    print("\n=== Capturing iBasketball fixtures ===")
    import httpx

    base_url = "https://ibasketball.co.il/wp-json/sportspress/v2"
    league_id = 119474  # Liga Leumit

    # Events (games) - get future games for schedule
    print("Fetching schedule (future games)...")
    try:
        resp = httpx.get(
            f"{base_url}/events",
            params={"leagues": league_id, "per_page": 10},
            timeout=30.0
        )
        resp.raise_for_status()
        events = resp.json()
        save_fixture("ibasketball", "schedule", events[:5])
    except Exception as e:
        print(f"  Warning: Could not fetch schedule: {e}")

    # Get completed events (status=publish means results available)
    print("Fetching completed games...")
    try:
        resp = httpx.get(
            f"{base_url}/events",
            params={"leagues": league_id, "per_page": 20, "status": "publish"},
            timeout=30.0
        )
        resp.raise_for_status()
        completed = resp.json()

        # Find one with actual results
        for event in completed:
            if event.get("main_results"):
                event_id = event["id"]
                print(f"Fetching boxscore for event {event_id}...")
                try:
                    box_resp = httpx.get(
                        f"{base_url}/events/{event_id}",
                        timeout=30.0
                    )
                    box_resp.raise_for_status()
                    save_fixture("ibasketball", "boxscore", box_resp.json())
                    break
                except Exception as e:
                    print(f"  Warning: Could not fetch boxscore: {e}")
        else:
            print("  No completed games with results found")
    except Exception as e:
        print(f"  Warning: Could not fetch completed games: {e}")

    # Note: iBasketball PBP requires HTML scraping, skip for now
    print("  Note: PBP requires HTML scraping, skipping")

    print("iBasketball fixtures captured!")


def main() -> None:
    """Main entry point."""
    sources = sys.argv[1:] if len(sys.argv) > 1 else ["winner", "euroleague", "nba", "ibasketball"]

    print(f"Capturing fixtures for: {', '.join(sources)}")
    print(f"Output directory: {FIXTURES_DIR}")

    for source in sources:
        try:
            if source == "winner":
                capture_winner()
            elif source == "euroleague":
                capture_euroleague()
            elif source == "nba":
                capture_nba()
            elif source == "ibasketball":
                capture_ibasketball()
            else:
                print(f"Unknown source: {source}")
        except Exception as e:
            print(f"Error capturing {source}: {e}")
            import traceback
            traceback.print_exc()

    print("\nDone!")


if __name__ == "__main__":
    main()
