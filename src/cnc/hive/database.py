# Copyright (c) 2025 Emily
#
# This work is licensed under the Creative Commons Zero v1.0 Universal License.
#
# To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

"""Hive data processing w/ DuckDB."""

import duckdb
import polars as pl
from pathlib import Path
from typing import List
from cnc.hive.config import Config
from cnc.hive.games_data import RawGameData
from cnc.hive.player_ids import KnownPlayerId


class HiveDatabase:
    """In-memory database for processing Hive game data."""

    def __init__(self):
        """Initialize in-memory DuckDB connection and create schema."""
        self.conn = duckdb.connect(":memory:")
        self.setup_schema()

    def setup_schema(self):
        """Create in-memory tables."""
        schema_sql = (Path(__file__).parent / "schema.sql").read_text()
        self.conn.execute(schema_sql)

    def load_toml_data(self, config: Config):
        """Load hive.toml data into in-memory DuckDB tables."""

        # Convert to new schema format
        players_data = []

        for player_id, player_info in config.players.items():
            players_data.append(
                {
                    "id": player_id.tagged(),
                    "display_name": player_info.display_name,
                    "groups": player_info.groups,
                    "hivegame_nicks": [nick.tagged() for nick in player_info.hivegame],
                    "hivegame_current": (
                        player_info.hivegame_current or player_info.hivegame[0]
                    ).tagged(),
                }
            )

        # Insert into in-memory tables
        if players_data:
            self.conn.execute("DELETE FROM players")

            # Insert players
            for player in players_data:
                self.conn.execute(
                    "INSERT INTO players (id, display_name, groups, hivegame_nicks, hivegame_current) VALUES ($id, $display_name, $groups, $hivegame_nicks, $hivegame_current)",
                    {
                        "id": player["id"],
                        "display_name": player["display_name"],
                        "groups": player["groups"],
                        "hivegame_nicks": player["hivegame_nicks"],
                        "hivegame_current": player["hivegame_current"],
                    },
                )

    def load_games_data(self, games: List[RawGameData]):
        """Load game data into in-memory DuckDB tables."""

        games_data = []
        seen_ids = set()

        for game in games:
            # Skip duplicates
            if game.game_id in seen_ids:
                continue
            seen_ids.add(game.game_id)

            games_data.append(
                {
                    "id": game.game_id,
                    "white_player": game.white_HG.tagged(),
                    "black_player": game.black_HG.tagged(),
                    "result": game.result,
                    "rated": game.rated,
                    "date_played": None,  # RawGameData doesn't have this
                    "time_control": None,  # RawGameData doesn't have this
                }
            )

        # Insert into in-memory table
        if games_data:
            self.conn.execute("DELETE FROM hg_games")
            for game in games_data:
                self.conn.execute(
                    """INSERT OR REPLACE INTO hg_games 
                       (id, hg_white_player, hg_black_player, known_white_player, known_black_player, result, rated, date_played, time_control) 
                       VALUES ($id, $white_player, $black_player, 
                               (SELECT id FROM players WHERE $white_player = ANY(hivegame_nicks)), 
                               (SELECT id FROM players WHERE $black_player = ANY(hivegame_nicks)), 
                               $result, $rated, $date_played, $time_control)""",
                    {
                        "id": game["id"],
                        "white_player": game["white_player"],
                        "black_player": game["black_player"],
                        "result": game["result"],
                        "rated": game["rated"],
                        "date_played": game["date_played"],
                        "time_control": game["time_control"],
                    },
                )

    def load_data(self, config: Config, games: List[RawGameData]):
        """Load all data from files into in-memory database."""
        self.load_toml_data(config)
        self.load_games_data(games)

    def get_game_counts_table(self, order: List[str]) -> pl.DataFrame:
        """Get game counts for table generation with proper column names."""

        # Convert order list to SQL parameters
        placeholders = ",".join(["?" for _ in order])

        query = f"""
        WITH player_games AS (
            SELECT 
                p.id as player_id,
                p.display_name,
                COUNT(*) as total_games,
                SUM(CASE WHEN g.rated THEN 1 ELSE 0 END) as rated_games,
                SUM(CASE WHEN NOT g.rated THEN 1 ELSE 0 END) as unrated_games
            FROM players p
            JOIN hg_games g ON g.white_player = ANY(p.hivegame_nicks) OR g.black_player = ANY(p.hivegame_nicks)
            WHERE p.id IN ({placeholders})
            GROUP BY p.id, p.display_name
        )
        SELECT * FROM player_games ORDER BY total_games DESC
        """

        return self.conn.execute(query, order).pl()

    def get_matchup_table(self) -> pl.DataFrame:
        """Get matchup statistics between players."""
        query = """
        SELECT 
            p1.display_name as player1,
            p2.display_name as player2,
            COUNT(*) as games_played,
            SUM(CASE WHEN g.result = 'white' AND g.white_player = ANY(p1.hivegame_nicks) THEN 1
                      WHEN g.result = 'black' AND g.black_player = ANY(p1.hivegame_nicks) THEN 1
                      ELSE 0 END) as player1_wins
        FROM players p1
        CROSS JOIN players p2
        JOIN hg_games g ON (g.white_player = ANY(p1.hivegame_nicks) AND g.black_player = ANY(p2.hivegame_nicks))
                       OR (g.white_player = ANY(p2.hivegame_nicks) AND g.black_player = ANY(p1.hivegame_nicks))
        WHERE p1.id < p2.id  -- Avoid duplicates
        GROUP BY p1.id, p1.display_name, p2.id, p2.display_name
        """

        return self.conn.execute(query).pl()

    def close(self):
        """Close the database connection."""
        self.conn.close()
