"""HTML table generation for game counts"""

from polars import DataFrame
import structlog

from cnc.hive.database import HiveDatabase

# Get logger for this module
logger = structlog.get_logger()


def generate_game_counts_table(db: HiveDatabase) -> str:
    """Generate a table showing game counts between players

    Args:
        db: HiveDatabase instance containing the data

    Returns:
        HTML table string
    """

    logger.info("Generating game counts table")

    # Get all known players (including bots) - will be shown first
    known_players: DataFrame = db.conn.execute(
        "SELECT * FROM players ORDER BY display_name"
    ).pl()
    logger.debug(f"Known players: {known_players}")

    # Get outsiders (players who played against known players but are not in known players list)
    # Exclude bots from consideration when calculating outsiders
    outsiders = db.conn.execute("""
        SELECT DISTINCT hg_player
        FROM (
            SELECT hg_white_player AS hg_player
            FROM hg_games
            WHERE known_white_player IS NULL
            AND known_black_player IS NOT NULL
            AND known_black_player NOT IN (SELECT id FROM players WHERE bot = true)
            UNION
            SELECT hg_black_player AS hg_player
            FROM hg_games
            WHERE known_white_player IS NOT NULL
            AND known_black_player IS NULL
            AND known_white_player NOT IN (SELECT id FROM players WHERE bot = true)
        ) AS outsiders
        ORDER BY hg_player
    """).pl()

    logger.debug(f"Outsiders: {outsiders}")

    # Create the complete player order: known players first, then outsiders
    all_players = []

    # Add known players
    for player in known_players.iter_rows(named=True):
        all_players.append(
            {
                "id": player["id"],
                "display_name": player["display_name"],
                "hivegame_nick": player["hivegame_current"],
                "is_known": True,
                "is_bot": player["bot"],
            }
        )

    # Add outsiders
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
                "is_known": False,
                "is_bot": False,
            }
        )

    # Get detailed game statistics between all player pairs, separated by rated status
    # Include games involving bots
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

    # Calculate total games per player for sorting
    player_total_games = {}
    for player in all_players:
        player_id = player["id"]
        total = 0

        # Count games where this player appears
        player_games = game_stats.filter(
            (game_stats["player1"] == player_id) | (game_stats["player2"] == player_id)
        )

        if len(player_games) > 0:
            total = player_games["total_games"].sum()

        player_total_games[player_id] = total

    # Sort players: known players first (by game count), then bots (by game count), then outsiders (by game count)
    def sort_key(player):
        player_id = player["id"]
        total_games = player_total_games.get(player_id, 0)

        if player["is_known"]:
            if player["is_bot"]:
                return (1, -total_games)  # Bots second, sorted by game count desc
            else:
                return (
                    0,
                    -total_games,
                )  # Known non-bots first, sorted by game count desc
        else:
            return (2, -total_games)  # Outsiders third, sorted by game count desc

    all_players.sort(key=sort_key)

    # Generate table HTML
    table_html = """
    <table class="matchup-table">
        <thead>
            <tr>
                <th>
                    <span style="">rated,</span>
                    <span style="font-size: 0.7em; color: gray;">unrated</span>
                </th>
    """

    # Add column headers
    for player in all_players:
        display_text = player["display_name"]
        if player["is_known"]:
            # For known players, show display name
            link_text = display_text
        else:
            # For outsiders, show display name (which already has @ prefix)
            link_text = display_text

        # Extract the actual hivegame nick without HG# prefix for the URL
        hivegame_nick = player["hivegame_nick"]
        if hivegame_nick.startswith("HG#"):
            hivegame_nick = hivegame_nick[3:]  # Remove HG# prefix

        table_html += f'<th><a href="https://hivegame.com/@/{hivegame_nick}" target="_blank" class="player-link">{link_text}</a></th>'

    table_html += "</tr></thead><tbody>"

    # Add rows
    for row_player in all_players:
        # Row header
        display_text = row_player["display_name"]
        if row_player["is_known"]:
            # For known players, show display name
            link_text = display_text
        else:
            # For outsiders, show display name (which already has @ prefix)
            link_text = display_text

        # Extract the actual hivegame nick without HG# prefix for the URL
        hivegame_nick = row_player["hivegame_nick"]
        if hivegame_nick.startswith("HG#"):
            hivegame_nick = hivegame_nick[3:]  # Remove HG# prefix

        table_html += f'<tr><th><a href="https://hivegame.com/@/{hivegame_nick}" target="_blank" class="player-link">{link_text}</a></th>'

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
                        row_player["id"], games_a_vs_b, games_b_vs_a, rated=True
                    )
                    unrated_stats = calculate_player_matchup_stats(
                        row_player["id"], games_a_vs_b, games_b_vs_a, rated=False
                    )

                    # Determine cell class based on content
                    cell_class = "has-matches"
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

    logger.info(f"Generated table with {len(all_players)} players")

    return table_html


def calculate_player_matchup_stats(
    player_id: str, games_a_vs_b: DataFrame, games_b_vs_a: DataFrame, rated: bool
) -> dict:
    """Calculate wins, losses, and draws for a player in a specific matchup.

    Args:
        player_id: The ID of the player we're calculating stats for
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
