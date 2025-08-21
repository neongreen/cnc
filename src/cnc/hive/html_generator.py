"""Main HTML generation for hive games"""

from pathlib import Path
import structlog

import flask

from cnc.hive.config import get_config
from cnc.hive.fetch_hive_games import GameCache
from cnc.hive.games_data import create_games_list
from cnc.hive.table_generator import generate_game_counts_table
from cnc.hive.database import HiveDatabase

# Get logger for this module
logger = structlog.get_logger()


def generate_hive_html() -> str:
    """Generate the main hive HTML page"""
    # Get all players
    root = Path(__file__).parent.parent.parent.parent
    config = get_config(root / "data" / "hive.toml")
    known_players = config.players

    # Load cached game data
    cache_file = root / "data" / "hive_games_cache.json"
    all_games_raw = GameCache.model_validate_json(cache_file.read_text()).players

    raw_games = create_games_list(
        [game for player_cache in all_games_raw.values() for game in player_cache.games]
    )

    # Create database instance and load data
    db = HiveDatabase()
    db.load_data(config, raw_games)  # Use raw_games, not merged games

    # Generate game counts table using the database
    game_counts_table = generate_game_counts_table(db, config)

    # Close database connection
    db.close()

    return flask.render_template(
        "hive.html.j2",
        game_counts_table=game_counts_table,
        num_participants=len(known_players),
    )
