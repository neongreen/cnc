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

    # Get known players (will be shown first) - exclude bots
    known_players: DataFrame = db.conn.execute(
        "SELECT * FROM players WHERE bot = false ORDER BY display_name"
    ).pl()
    logger.debug(f"Known players: {known_players}")

    # Get outsiders (players who played against known players but are not in known players list)
    # Exclude bots from consideration
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
                "display_name": outsider_nick,  # Use hivegame nick without HG# as display name
                "hivegame_nick": outsider["hg_player"],
                "is_known": False,
            }
        )

    # Get game counts between all player pairs
    # Exclude games involving bots
    game_counts_query = """
        WITH player_pairs AS (
            SELECT 
                CASE 
                    WHEN known_white_player IS NOT NULL THEN known_white_player
                    ELSE hg_white_player
                END AS player1,
                CASE 
                    WHEN known_black_player IS NOT NULL THEN known_black_player
                    ELSE hg_black_player
                END AS player2,
                COUNT(*) as games_played
            FROM hg_games
            WHERE (known_white_player IS NOT NULL OR known_black_player IS NOT NULL)
            AND (known_white_player IS NULL OR known_white_player NOT IN (SELECT id FROM players WHERE bot = true))
            AND (known_black_player IS NULL OR known_black_player NOT IN (SELECT id FROM players WHERE bot = true))
            GROUP BY player1, player2
            
            UNION ALL
            
            SELECT 
                CASE 
                    WHEN known_black_player IS NOT NULL THEN known_black_player
                    ELSE hg_black_player
                END AS player1,
                CASE 
                    WHEN known_white_player IS NOT NULL THEN known_white_player
                    ELSE hg_white_player
                END AS player2,
                COUNT(*) as games_played
            FROM hg_games
            WHERE (known_white_player IS NOT NULL OR known_black_player IS NOT NULL)
            AND (known_white_player IS NULL OR known_white_player NOT IN (SELECT id FROM players WHERE bot = true))
            AND (known_black_player IS NULL OR known_black_player NOT IN (SELECT id FROM players WHERE bot = true))
            GROUP BY player1, player2
        )
        SELECT 
            player1,
            player2,
            SUM(games_played) as total_games
        FROM player_pairs
        WHERE player1 != player2
        GROUP BY player1, player2
    """

    game_counts: DataFrame = db.conn.execute(game_counts_query).pl()
    logger.debug(f"Game counts: {game_counts}")

    # Generate table HTML
    table_html = """
    <table class="matchup-table">
        <thead>
            <tr>
                <th></th>
    """

    # Add column headers
    for player in all_players:
        display_text = player["display_name"]
        if player["is_known"]:
            # For known players, show display name
            link_text = display_text
        else:
            # For outsiders, show display name (which is already cleaned of HG#)
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
            # For outsiders, show display name (which is already cleaned of HG#)
            link_text = display_text

        # Extract the actual hivegame nick without HG# prefix for the URL
        hivegame_nick = row_player["hivegame_nick"]
        if hivegame_nick.startswith("HG#"):
            hivegame_nick = hivegame_nick[3:]  # Remove HG# prefix

        table_html += f'<tr><th><a href="https://hivegame.com/@/{hivegame_nick}" target="_blank" class="player-link">{link_text}</a></th>'

        # Add game count cells
        for col_player in all_players:
            if row_player["id"] == col_player["id"]:
                # Same player - show dash
                table_html += '<td class="self">-</td>'
            else:
                # Different players - find game count
                # Look for games between these two players
                games = game_counts.filter(
                    (
                        (game_counts["player1"] == row_player["id"])
                        & (game_counts["player2"] == col_player["id"])
                    )
                    | (
                        (game_counts["player1"] == col_player["id"])
                        & (game_counts["player2"] == row_player["id"])
                    )
                )

                if len(games) > 0:
                    # Get the first row and extract the total_games value
                    game_row = games.row(0)
                    game_count = game_row[2]  # total_games is the third column
                    table_html += f"<td>{game_count}</td>"
                else:
                    table_html += "<td></td>"

        table_html += "</tr>"

    table_html += "</tbody></table>"

    logger.info(f"Generated table with {len(all_players)} players")

    return table_html
