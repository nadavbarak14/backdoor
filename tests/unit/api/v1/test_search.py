"""
Unit tests for the search autocomplete API endpoint.

Tests:
    - GET /api/v1/search/autocomplete - Search entities for @-mention autocomplete
"""

from datetime import date

from sqlalchemy.orm import Session

from src.models import League, Player, Season, Team
from src.schemas.enums import Position


class TestAutocomplete:
    """Tests for GET /api/v1/search/autocomplete endpoint."""

    def test_search_returns_empty_for_no_matches(self, client, test_db: Session):
        """Search with no matching entities returns empty results."""
        response = client.get("/api/v1/search/autocomplete?q=xyz")

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []

    def test_search_player_by_first_name(self, client, test_db: Session):
        """Search 'step' returns Stephen Curry."""
        player = Player(
            first_name="Stephen",
            last_name="Curry",
            positions=[Position.POINT_GUARD],
        )
        test_db.add(player)
        test_db.commit()

        response = client.get("/api/v1/search/autocomplete?q=step")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["name"] == "Stephen Curry"
        assert data["results"][0]["type"] == "player"

    def test_search_player_by_last_name(self, client, test_db: Session):
        """Search 'curry' returns Stephen Curry."""
        player = Player(
            first_name="Stephen",
            last_name="Curry",
            positions=[Position.POINT_GUARD],
        )
        test_db.add(player)
        test_db.commit()

        response = client.get("/api/v1/search/autocomplete?q=curry")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["name"] == "Stephen Curry"

    def test_search_player_full_name(self, client, test_db: Session):
        """Search 'stephen curry' returns exact match first."""
        player1 = Player(first_name="Stephen", last_name="Curry")
        player2 = Player(first_name="Stephen", last_name="Adams")
        test_db.add_all([player1, player2])
        test_db.commit()

        response = client.get("/api/v1/search/autocomplete?q=stephen curry")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) >= 1
        # Stephen Curry should be first (better match)
        assert data["results"][0]["name"] == "Stephen Curry"

    def test_search_team_partial(self, client, test_db: Session):
        """Search 'macc' returns Maccabi teams."""
        team = Team(
            name="Maccabi Tel Aviv",
            short_name="MAC",
            city="Tel Aviv",
            country="Israel",
        )
        test_db.add(team)
        test_db.commit()

        response = client.get("/api/v1/search/autocomplete?q=macc")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["name"] == "Maccabi Tel Aviv"
        assert data["results"][0]["type"] == "team"

    def test_search_mixed_results(self, client, test_db: Session):
        """Search 'mac' returns players AND teams."""
        player = Player(first_name="Mac", last_name="McClung")
        team = Team(
            name="Maccabi Tel Aviv",
            short_name="MAC",
            city="Tel Aviv",
            country="Israel",
        )
        test_db.add_all([player, team])
        test_db.commit()

        response = client.get("/api/v1/search/autocomplete?q=mac")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        types = {r["type"] for r in data["results"]}
        assert "player" in types
        assert "team" in types

    def test_search_limit_respected(self, client, test_db: Session):
        """Results limited to requested count."""
        # Create 5 players with similar names
        for i in range(5):
            player = Player(first_name="Test", last_name=f"Player{i}")
            test_db.add(player)
        test_db.commit()

        response = client.get("/api/v1/search/autocomplete?q=test&limit=3")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 3

    def test_search_empty_query_rejected(self, client):
        """Empty query returns 422 validation error."""
        response = client.get("/api/v1/search/autocomplete?q=")

        assert response.status_code == 422

    def test_search_case_insensitive(self, client, test_db: Session):
        """Search is case-insensitive."""
        player = Player(first_name="Stephen", last_name="Curry")
        test_db.add(player)
        test_db.commit()

        # Test lowercase
        response = client.get("/api/v1/search/autocomplete?q=CURRY")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["name"] == "Stephen Curry"

    def test_search_special_characters_safe(self, client, test_db: Session):
        """Handles special characters safely (SQL injection prevention)."""
        # This should not cause SQL error
        response = client.get("/api/v1/search/autocomplete?q='; DROP TABLE players; --")

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []

    def test_search_league(self, client, test_db: Session):
        """Search returns matching leagues."""
        league = League(
            name="Israeli Basketball Premier League",
            code="IBPL",
            country="Israel",
        )
        test_db.add(league)
        test_db.commit()

        response = client.get("/api/v1/search/autocomplete?q=israeli")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["type"] == "league"
        assert data["results"][0]["context"] == "Israel"

    def test_search_season(self, client, test_db: Session):
        """Search returns matching seasons."""
        league = League(name="NBA", code="NBA", country="USA")
        test_db.add(league)
        test_db.flush()

        season = Season(
            league_id=league.id,
            name="2024-25",
            start_date=date(2024, 10, 1),
            end_date=date(2025, 6, 30),
        )
        test_db.add(season)
        test_db.commit()

        response = client.get("/api/v1/search/autocomplete?q=2024")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["type"] == "season"
        assert data["results"][0]["context"] == "NBA"

    def test_search_player_with_team_context(self, client, test_db: Session):
        """Player results include team as context."""
        from src.models import PlayerTeamHistory

        league = League(name="NBA", code="NBA", country="USA")
        test_db.add(league)
        test_db.flush()

        season = Season(
            league_id=league.id,
            name="2024-25",
            start_date=date(2024, 10, 1),
            end_date=date(2025, 6, 30),
        )
        test_db.add(season)
        test_db.flush()

        team = Team(
            name="Golden State Warriors",
            short_name="GSW",
            city="San Francisco",
            country="USA",
        )
        test_db.add(team)
        test_db.flush()

        player = Player(first_name="Stephen", last_name="Curry", positions=[Position.POINT_GUARD])
        test_db.add(player)
        test_db.flush()

        history = PlayerTeamHistory(
            player_id=player.id,
            team_id=team.id,
            season_id=season.id,
            jersey_number=30,
        )
        test_db.add(history)
        test_db.commit()

        response = client.get("/api/v1/search/autocomplete?q=curry")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["context"] == "Golden State Warriors"

    def test_search_max_limit_enforced(self, client, test_db: Session):
        """Limit cannot exceed 20."""
        response = client.get("/api/v1/search/autocomplete?q=test&limit=100")

        assert response.status_code == 422

    def test_search_prefix_match_prioritized(self, client, test_db: Session):
        """Prefix matches appear before contains matches."""
        player1 = Player(first_name="Mac", last_name="McClung")  # Starts with Mac
        player2 = Player(first_name="James", last_name="Macmillan")  # Contains Mac
        test_db.add_all([player1, player2])
        test_db.commit()

        response = client.get("/api/v1/search/autocomplete?q=mac")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        # Mac McClung should be first (starts with "mac")
        assert data["results"][0]["name"] == "Mac McClung"
