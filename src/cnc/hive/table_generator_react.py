"""Table generation for hive games - React version (JSON output)"""

from pathlib import Path
import structlog

import polars as pl
from polars import DataFrame
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

        # Get detailed game statistics between all player pairs (same as old version)
    game_stats_query = """
        SELECT 
            CASE 
                WHEN known_white_player IS NOT NULL THEN known_white_player
                ELSE hg_white_player
            END AS player1,
            CASE 
                WHEN known_black_player IS NOT NULL THEN known_black_player
                ELSE hg_black_player
            END AS player2,
            rated,
            result,
            COUNT(*) as total_games
        FROM hg_games
        WHERE (known_white_player IS NOT NULL OR known_black_player IS NOT NULL)
        GROUP BY player1, player2, rated, result
    """

    game_stats: DataFrame = db.conn.execute(game_stats_query).pl()
    logger.debug(f"Game stats: {game_stats}")

    # Generate game statistics for each player pair
    game_stats_data = []
    for i, row_player in enumerate(all_players):
        for j, col_player in enumerate(all_players):
            if i == j:  # Skip self-matches
                continue

            # Find stats for this player pair from the game_stats DataFrame
            row_id = row_player["id"]
            col_id = col_player["id"]

            # Look for games between these two players from both perspectives
            games_a_vs_b = game_stats.filter(
                (game_stats["player1"] == row_id) & (game_stats["player2"] == col_id)
            )
            games_b_vs_a = game_stats.filter(
                (game_stats["player1"] == col_id) & (game_stats["player2"] == row_id)
            )

            if len(games_a_vs_b) > 0 or len(games_b_vs_a) > 0:
                # Calculate wins, losses, draws for this player matchup
                rated_stats = calculate_player_matchup_stats(
                    games_a_vs_b, games_b_vs_a, rated=True
                )
                unrated_stats = calculate_player_matchup_stats(
                    games_a_vs_b, games_b_vs_a, rated=False
                )

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


def calculate_player_matchup_stats(
    games_a_vs_b: DataFrame, games_b_vs_a: DataFrame, rated: bool
) -> dict:
    """Calculate wins, losses, and draws for a player in a specific matchup.

    Args:
        games_a_vs_b: Games where player_id was player1 (white)
        games_b_vs_a: Games where player_id was player2 (black)
        rated: Whether to look at rated (True) or unrated (False) games

    Returns:
        Dictionary with 'wins', 'losses', 'draws' counts
    """
    # Filter games by rated status
    rated_games_a_vs_b = games_a_vs_b.filter(games_a_vs_b["rated"] == rated)
    rated_games_b_vs_a = games_b_vs_a.filter(games_b_vs_a["rated"] == rated)

    wins = 0
    losses = 0
    draws = 0

    # When player_id was player1 (white), result 'white' means they won
    for game in rated_games_a_vs_b.iter_rows(named=True):
        if game["result"] == "white":
            wins += game["total_games"]  # Player won
        elif game["result"] == "black":
            losses += game["total_games"]  # Player lost
        elif game["result"] == "draw":
            draws += game["total_games"]  # Player drew

    # When player_id was player2 (black), result 'black' means they won
    for game in rated_games_b_vs_a.iter_rows(named=True):
        if game["result"] == "black":
            wins += game["total_games"]  # Player won
        elif game["result"] == "white":
            losses += game["total_games"]  # Player lost
        elif game["result"] == "draw":
            draws += game["total_games"]  # Player drew

    return {"wins": wins, "losses": losses, "draws": draws}


def save_game_counts_json(db: HiveDatabase, config: Config, output_path: Path) -> None:
    """Save game counts data as JSON file"""
    data = generate_game_counts_data(db, config)

    import json

    # Ensure the output directory exists before writing the file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.touch(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Saved game counts JSON to {output_path}")
