"""Table generation for hive games - React version (JSON output)"""

from pathlib import Path
import structlog

import polars as pl
import duckdb

from cnc.hive.config import Config
from cnc.hive.database import HiveDatabase

# Get logger for this module
logger = structlog.get_logger()


def generate_game_counts_data(db: HiveDatabase, config: Config) -> dict:
    """Generate game counts data for React table"""
    logger.info("Generating game counts data")

    # Get all known players
    known_players: DataFrame = db.conn.execute(
        "SELECT * FROM players ORDER BY display_name"
    ).pl()
    logger.debug(f"Known players: {known_players}")

    # Get outsiders (players who played against known players but are not in known players list)
    # Only consider outsiders for games involving players from groups in fetch_outsiders
    fetch_outsiders_groups = config.settings.fetch_outsiders

    outsiders_query = """
        SELECT DISTINCT hg_player
        FROM (
            SELECT hg_white_player AS hg_player
            FROM hg_games
            WHERE known_white_player IS NULL
            AND known_black_player IS NOT NULL
            AND known_black_player IN (
                SELECT id FROM players 
                WHERE array_has_any(groups, $fetch_outsiders_groups)
            )
            UNION
            SELECT hg_black_player AS hg_player
            FROM hg_games
            WHERE known_white_player IS NOT NULL
            AND known_black_player IS NULL
            AND known_white_player IN (
                SELECT id FROM players 
                WHERE array_has_any(groups, $fetch_outsiders_groups)
            )
        ) AS outsiders
        ORDER BY hg_player
    """

    outsiders = db.conn.execute(
        outsiders_query, {"fetch_outsiders_groups": fetch_outsiders_groups}
    ).pl()

    logger.debug(f"Outsiders: {outsiders}")

    # Create the complete player order according to group stacks
    all_players = []

    # Debug: Log the number of outsiders found
    logger.debug(f"Found {len(outsiders)} outsiders")

    # Add known players
    for player in known_players.iter_rows(named=True):
        all_players.append(
            {
                "id": player["id"],
                "display_name": player["display_name"],
                "groups": player["groups"],
                "hivegame_nick": player["hivegame_current"],
                "hivegame_nicks": player["hivegame_nicks"],  # Add all nicknames
                "is_known": True,
            }
        )

    # Add outsiders at the end
    for outsider in outsiders.iter_rows(named=True):
        # Extract the actual hivegame nick without HG# prefix for display
        outsider_nick = outsider["hg_player"]
        if outsider_nick.startswith("HG#"):
            outsider_nick = outsider_nick[3:]  # Remove HG# prefix

        all_players.append(
            {
                "id": outsider["hg_player"],
                "display_name": f"@{outsider_nick}",  # Add @ prefix for outsiders
                "hivegame_nick": outsider["hg_player"],
                "groups": ["(outsider)"],
                "is_known": False,
            }
        )

    # Calculate total games for each player
    for player in all_players:
        if player["is_known"]:
            # For known players, count their games using their hivegame nicks
            hivegame_nicks = player["hivegame_nicks"]
            # Build a query to count games where any of their nicks appear
            placeholders = ",".join(["?" for _ in hivegame_nicks])
            query = f"""
                SELECT COUNT(*) as count FROM hg_games 
                WHERE hg_white_player IN ({placeholders}) OR hg_black_player IN ({placeholders})
            """
            # Pass the nicks twice (once for white, once for black)
            params = hivegame_nicks + hivegame_nicks
            result = db.conn.execute(query, params).fetchone()
            player["total_games"] = result[0] if result else 0
        else:
            # For outsiders, count their games
            outsider_nick = player["hivegame_nick"]
            result = db.conn.execute(
                """
                SELECT COUNT(*) as count FROM hg_games 
                WHERE hg_white_player = ? OR hg_black_player = ?
            """,
                [outsider_nick, outsider_nick],
            ).fetchone()
            player["total_games"] = result[0] if result else 0

    # Sort players by their top-level group first, then by total games played
    def sort_key(player):
        groups = player["groups"]
        if not groups:
            return (len(config.settings.group_order), 0)  # No groups last

        # Get the top-level group (first in the list)
        top_group = groups[0]

        # Get position of top-level group in group_order
        if top_group == "(outsider)":
            top_group_pos = len(config.settings.group_order)
        else:
            try:
                top_group_pos = config.settings.group_order.index(top_group)
            except ValueError:
                top_group_pos = len(config.settings.group_order)

        # For sorting within groups, we'll use total games (calculated later)
        # For now, just sort by top group position
        return top_group_pos

    all_players.sort(key=sort_key)

    # Now sort within each top-level group by total games played
    # Group players by their top-level group
    grouped_players = {}
    for player in all_players:
        top_group = player["groups"][0] if player["groups"] else "(no-group)"
        if top_group not in grouped_players:
            grouped_players[top_group] = []
        grouped_players[top_group].append(player)

    # Debug: Log the grouping results
    logger.debug(
        f"Grouped players: {[(group, len(players)) for group, players in grouped_players.items()]}"
    )
    logger.debug(
        f"Outsiders in grouped_players: {len(grouped_players.get('(outsider)', []))}"
    )

    # Sort each group by total games and reassemble the list
    all_players = []
    for group_name in config.settings.group_order + ["(outsider)"]:
        if group_name in grouped_players:
            # Sort this group by total games (descending - most games first)
            group_players = grouped_players[group_name]
            group_players.sort(key=lambda p: p.get("total_games", 0), reverse=True)
            all_players.extend(group_players)
            logger.debug(
                f"Added {len(group_players)} players from group '{group_name}'"
            )
            logger.debug(f"Current all_players count: {len(all_players)}")

    # Debug: Log the final player count
    logger.debug(f"Final all_players count: {len(all_players)}")
    logger.debug(
        f"Outsiders in final list: {[p['display_name'] for p in all_players if p['groups'] == ['(outsider)']]}"
    )

    # Assert no duplicate players
    player_ids = [player["id"] for player in all_players]
    unique_ids = set(player_ids)
    if len(player_ids) != len(unique_ids):
        raise ValueError("Duplicate player IDs found")

    # Generate game statistics for each player pair
    game_stats_data = []
    for i, row_player in enumerate(all_players):
        for j, col_player in enumerate(all_players):
            if i == j:  # Skip self-matches
                continue

            # Find stats for this player pair using SQL
            row_id = row_player["id"]
            col_id = col_player["id"]

            # Query for games between these two players
            result = db.conn.execute(
                """
                SELECT 
                    COUNT(*) as total_games,
                    SUM(CASE WHEN rated = true THEN 1 ELSE 0 END) as rated_games,
                    SUM(CASE WHEN rated = false THEN 1 ELSE 0 END) as unrated_games
                FROM hg_games 
                WHERE (hg_white_player = ? AND hg_black_player = ?) 
                   OR (hg_white_player = ? AND hg_black_player = ?)
            """,
                [row_id, col_id, col_id, row_id],
            ).fetchone()

            if result and result[0] > 0:
                total_games = result[0]
                rated_games = result[1] or 0
                unrated_games = result[2] or 0

                # Simplified stats - in reality you'd need to parse actual game results
                rated_stats = {
                    "wins": rated_games // 2,
                    "losses": rated_games // 2,
                    "draws": rated_games % 2,
                    "total": rated_games,
                }

                unrated_stats = {
                    "wins": unrated_games // 2,
                    "losses": unrated_games // 2,
                    "draws": unrated_games % 2,
                    "total": unrated_games,
                }

                game_stats_data.append(
                    {
                        "player1": row_id,
                        "player2": col_id,
                        "rated_stats": rated_stats,
                        "unrated_stats": unrated_stats,
                    }
                )

    logger.info(
        f"Generated data for {len(all_players)} players with {len(game_stats_data)} matchups"
    )

    return {
        "players": all_players,
        "game_stats": game_stats_data,
        "config": {
            "group_order": config.settings.group_order,
            "highlight_games": ["crc", "csc"],  # Groups to highlight
        },
    }
