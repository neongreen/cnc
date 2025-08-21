"""HTML table generation for game counts"""

from polars import DataFrame
import structlog

from cnc.hive.database import HiveDatabase
from cnc.hive.config import Config

# Get logger for this module
logger = structlog.get_logger()


def generate_game_counts_table(db: HiveDatabase, config: Config) -> str:
    """Generate a table showing game counts between players

    Args:
        db: HiveDatabase instance containing the data
        config: Configuration from hive.toml

    Returns:
        HTML table string
    """

    logger.info("Generating game counts table")

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

    # Add known players
    for player in known_players.iter_rows(named=True):
        all_players.append(
            {
                "id": player["id"],
                "display_name": player["display_name"],
                "groups": player["groups"],
                "hivegame_nick": player["hivegame_current"],
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

    # Sort players by their group stacks using lexicographic ordering
    # Just like Python's list comparison: ["crc"] < ["crc", "momoh"] < ["crc", "vivid"] < ["emily"]
    def sort_key(player):
        groups = player["groups"]
        # Convert groups to their positions in group_order for comparison
        group_positions = []
        for group in groups:
            if group == "(outsider)":
                group_positions.append(
                    len(config.settings.group_order)
                )  # Outsiders last
            else:
                try:
                    group_positions.append(config.settings.group_order.index(group))
                except ValueError:
                    group_positions.append(
                        len(config.settings.group_order)
                    )  # Unknown groups last

        # Sort lexicographically by group positions (just like Python list comparison)
        return group_positions

    all_players.sort(key=sort_key)

    # Get detailed game statistics between all player pairs
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

    # Determine the maximum number of groups any player has
    max_groups = max(len(player["groups"]) for player in all_players)

    # Generate table HTML
    table_html = '<table class="matchup-table">'

    # Header row 1: Player names
    table_html += '<thead><tr><th><span>rated,</span><span style="font-size: 0.7em; color: gray;">unrated</span></th>'
    for col_player in all_players:
        # Extract the actual hivegame nick without HG# prefix for the URL
        hivegame_nick = col_player["hivegame_nick"]
        if hivegame_nick.startswith("HG#"):
            hivegame_nick = hivegame_nick[3:]  # Remove HG# prefix

        table_html += f'<th><a href="https://hivegame.com/@/{hivegame_nick}" target="_blank" class="player-link">{col_player["display_name"]}</a></th>'
    table_html += "</tr>"

    # Generate stacked group header rows
    for group_level in range(max_groups):
        table_html += "<tr><th></th>"  # Empty corner cell
        for col_player in all_players:
            groups = col_player["groups"]

            if group_level < len(groups):
                # This player has a group at this level
                group = groups[group_level]

                # Define colors for different groups
                group_colors = {
                    "emily": "#e3f2fd",  # Light blue
                    "crc": "#c8e6c9",  # Light green
                    "bot": "#f3e5f5",  # Light purple
                    "(outsider)": "#fff3e0",  # Light orange
                }

                bg_color = group_colors.get(group, "#f5f5f5")

                # Create the group cell with colored background
                table_html += f'<th style="background-color: {bg_color}; font-size: 0.8em; color: #666; padding: 4px;">{group}</th>'
            else:
                # This player doesn't have a group at this level - show empty cell
                table_html += '<th style="background-color: #f5f5f5; font-size: 0.8em; color: #666; padding: 4px;">&nbsp;</th>'

        table_html += "</tr>"

    table_html += "</thead><tbody>"

    # Add rows
    for row_player in all_players:
        # Row header
        display_text = row_player["display_name"]

        # Extract the actual hivegame nick without HG# prefix for the URL
        hivegame_nick = row_player["hivegame_nick"]
        if hivegame_nick.startswith("HG#"):
            hivegame_nick = hivegame_nick[3:]  # Remove HG# prefix

        table_html += f'<tr><th><a href="https://hivegame.com/@/{hivegame_nick}" target="_blank" class="player-link">{display_text}</a></th>'

        # Add game count cells
        for col_player in all_players:
            if row_player["id"] == col_player["id"]:
                # Same player - show self-match styling
                table_html += '<td class="self-match"></td>'
            else:
                # Different players - find game statistics for rated and unrated
                # Look for games between these two players from both perspectives
                games_a_vs_b = game_stats.filter(
                    (game_stats["player1"] == row_player["id"])
                    & (game_stats["player2"] == col_player["id"])
                )
                games_b_vs_a = game_stats.filter(
                    (game_stats["player1"] == col_player["id"])
                    & (game_stats["player2"] == row_player["id"])
                )

                if len(games_a_vs_b) > 0 or len(games_b_vs_a) > 0:
                    # Calculate wins, losses, draws for this player matchup
                    rated_stats = calculate_player_matchup_stats(
                        games_a_vs_b, games_b_vs_a, rated=True
                    )
                    unrated_stats = calculate_player_matchup_stats(
                        games_a_vs_b, games_b_vs_a, rated=False
                    )

                    # Determine cell class based on content and highlighting
                    cell_class = "has-matches"

                    # Check if this should be highlighted (both players have groups in highlight_games)
                    row_highlight_groups = [
                        g
                        for g in row_player["groups"]
                        if g in config.settings.highlight_games
                    ]
                    col_highlight_groups = [
                        g
                        for g in col_player["groups"]
                        if g in config.settings.highlight_games
                    ]

                    if row_highlight_groups and col_highlight_groups:
                        cell_class += " highlighted"

                    if (
                        rated_stats["wins"] == 0
                        and rated_stats["losses"] == 0
                        and rated_stats["draws"] == 0
                        and unrated_stats["wins"] == 0
                        and unrated_stats["losses"] == 0
                        and unrated_stats["draws"] == 0
                    ):
                        cell_class = "no-matches"

                    cell_html = f'<td class="{cell_class}">'

                    # Add rated games (wins-losses-draws)
                    if (
                        rated_stats["wins"] > 0
                        or rated_stats["losses"] > 0
                        or rated_stats["draws"] > 0
                    ):
                        rated_text = f"{rated_stats['wins']}-{rated_stats['losses']}"
                        if rated_stats["draws"] > 0:
                            rated_text += f"-{rated_stats['draws']}"
                        cell_html += f"<span>{rated_text}</span>"
                    else:
                        cell_html += "<span>&nbsp;</span>"

                    # Add unrated games (wins-losses-draws)
                    if (
                        unrated_stats["wins"] > 0
                        or unrated_stats["losses"] > 0
                        or unrated_stats["draws"] > 0
                    ):
                        unrated_text = (
                            f"{unrated_stats['wins']}-{unrated_stats['losses']}"
                        )
                        if unrated_stats["draws"] > 0:
                            unrated_text += f"-{unrated_stats['draws']}"
                        cell_html += f'<br><span style="color: gray; font-size: 0.7em;">{unrated_text}</span>'
                    else:
                        cell_html += '<br><span style="color: gray; font-size: 0.7em;">&nbsp;</span>'

                    cell_html += "</td>"
                    table_html += cell_html
                else:
                    # No games between these players
                    table_html += '<td class="no-matches"></td>'

        table_html += "</tr>"

    table_html += "</tbody></table>"

    logger.info(
        f"Generated table with {len(all_players)} players and {max_groups} group levels"
    )

    return table_html


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
