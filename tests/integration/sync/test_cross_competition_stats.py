"""
Cross-Competition Stats Tests

Verifies that teams like Maccabi Tel Aviv can have separate stats
in Winner League and Euroleague while remaining deduplicated.
"""

from datetime import date

from sqlalchemy import func, select

from src.models.league import League, Season
from src.models.player import Player
from src.models.stats import PlayerSeasonStats
from src.models.team import Team
from src.sync.deduplication import TeamMatcher
from src.sync.types import RawTeam


def test_maccabi_separate_stats_per_competition(test_db):
    """
    Maccabi Tel Aviv has ONE team record but separate stats per competition.

    Scottie Wilbekin plays in both Winner League and Euroleague with
    different stats in each.
    """
    # Setup leagues and seasons
    winner = League(name="Winner League", code="WINNER", country="Israel")
    euroleague = League(name="Euroleague", code="EUROLEAGUE", country="Europe")
    test_db.add_all([winner, euroleague])
    test_db.commit()

    winner_season = Season(
        league_id=winner.id,
        name="2023-24",
        start_date=date(2023, 10, 1),
        end_date=date(2024, 6, 30),
        is_current=True,
    )
    euroleague_season = Season(
        league_id=euroleague.id,
        name="2023-24",
        start_date=date(2023, 10, 1),
        end_date=date(2024, 5, 30),
        is_current=True,
    )
    test_db.add_all([winner_season, euroleague_season])
    test_db.commit()

    # Create Maccabi (deduplicated)
    matcher = TeamMatcher(test_db)
    maccabi, _ = matcher.find_or_create_team_season(
        source="winner",
        external_id="w-maccabi-ta",
        team_data=RawTeam(
            external_id="w-maccabi-ta",
            name="Maccabi Tel Aviv",
            short_name="MTA",
        ),
        season_id=winner_season.id,
    )
    matcher.find_or_create_team_season(
        source="euroleague",
        external_id="EL-MTA",
        team_data=RawTeam(
            external_id="EL-MTA",
            name="Maccabi Tel Aviv",
            short_name="MTA",
        ),
        season_id=euroleague_season.id,
    )

    # Create Wilbekin (deduplicated)
    wilbekin = Player(
        first_name="Scottie",
        last_name="Wilbekin",
        birth_date=date(1993, 7, 19),
        external_ids={"winner": "w-wilbekin", "euroleague": "EL-PWB"},
    )
    test_db.add(wilbekin)
    test_db.commit()

    # Winner League stats: 15 PPG
    winner_stats = PlayerSeasonStats(
        player_id=wilbekin.id,
        team_id=maccabi.id,
        season_id=winner_season.id,
        games_played=34,
        total_points=510,
        avg_points=15.0,
    )

    # Euroleague stats: 14 PPG (tougher competition)
    euroleague_stats = PlayerSeasonStats(
        player_id=wilbekin.id,
        team_id=maccabi.id,
        season_id=euroleague_season.id,
        games_played=30,
        total_points=420,
        avg_points=14.0,
    )
    test_db.add_all([winner_stats, euroleague_stats])
    test_db.commit()

    # Verify: ONE player, ONE team, TWO stat records
    assert test_db.scalar(select(func.count()).select_from(Player)) == 1
    assert test_db.scalar(select(func.count()).select_from(Team)) == 1

    stats = test_db.scalars(
        select(PlayerSeasonStats).where(PlayerSeasonStats.player_id == wilbekin.id)
    ).all()
    assert len(stats) == 2

    # Stats differ by competition
    by_season = {s.season_id: s for s in stats}
    assert by_season[winner_season.id].avg_points == 15.0
    assert by_season[euroleague_season.id].avg_points == 14.0


def test_query_stats_by_league(test_db):
    """Stats can be queried by league/competition."""
    # Setup
    winner = League(name="Winner League", code="WINNER", country="Israel")
    euroleague = League(name="Euroleague", code="EUROLEAGUE", country="Europe")
    test_db.add_all([winner, euroleague])
    test_db.commit()

    winner_season = Season(
        league_id=winner.id,
        name="2023-24",
        start_date=date(2023, 10, 1),
        end_date=date(2024, 6, 30),
        is_current=True,
    )
    euroleague_season = Season(
        league_id=euroleague.id,
        name="2023-24",
        start_date=date(2023, 10, 1),
        end_date=date(2024, 5, 30),
        is_current=True,
    )
    test_db.add_all([winner_season, euroleague_season])
    test_db.commit()

    matcher = TeamMatcher(test_db)
    maccabi, _ = matcher.find_or_create_team_season(
        source="winner",
        external_id="w-mta",
        team_data=RawTeam(
            external_id="w-mta", name="Maccabi Tel Aviv", short_name="MTA"
        ),
        season_id=winner_season.id,
    )
    matcher.find_or_create_team_season(
        source="euroleague",
        external_id="EL-MTA",
        team_data=RawTeam(
            external_id="EL-MTA", name="Maccabi Tel Aviv", short_name="MTA"
        ),
        season_id=euroleague_season.id,
    )

    wilbekin = Player(
        first_name="Scottie",
        last_name="Wilbekin",
        birth_date=date(1993, 7, 19),
        external_ids={},
    )
    test_db.add(wilbekin)
    test_db.commit()

    test_db.add_all(
        [
            PlayerSeasonStats(
                player_id=wilbekin.id,
                team_id=maccabi.id,
                season_id=winner_season.id,
                games_played=34,
                total_points=510,
                avg_points=15.0,
            ),
            PlayerSeasonStats(
                player_id=wilbekin.id,
                team_id=maccabi.id,
                season_id=euroleague_season.id,
                games_played=30,
                total_points=420,
                avg_points=14.0,
            ),
        ]
    )
    test_db.commit()

    # Query by Winner League
    winner_stats = test_db.scalars(
        select(PlayerSeasonStats).join(Season).where(Season.league_id == winner.id)
    ).all()
    assert len(winner_stats) == 1
    assert winner_stats[0].avg_points == 15.0

    # Query by Euroleague
    el_stats = test_db.scalars(
        select(PlayerSeasonStats).join(Season).where(Season.league_id == euroleague.id)
    ).all()
    assert len(el_stats) == 1
    assert el_stats[0].avg_points == 14.0
