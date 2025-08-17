from decimal import Decimal
from pathlib import Path
from typing import Literal

import flask
from pydantic import BaseModel

from cnc.graph import (
    PairingResult,
    d3_graph_data,
    pairing_outcomes,
    topological_sort_participants,
)
from cnc.utils import get_logger, pprint_dict, Pair
from cnc.hivegame import (
    HG_GameResponse,
    HG_GameStatusFinished,
    HivePlayerInfo,
    HivePlayerId,
    get_all_players,
)
from cnc.fetch_hive_games import GameCache

# Get logger for this module
logger = get_logger("hive")


class HiveGameResult(BaseModel):
    player1: HivePlayerId
    player2: HivePlayerId
    result: Literal["p1", "p2", "draw"]
    rated: bool


class HivePlayerOverallStats(BaseModel):
    id: HivePlayerId
    wins: int
    losses: int
    draws: int
    total_games: int


class PlayerGameCounts(BaseModel):
    """Game counts for a player with rated/unrated breakdown"""

    rated_games: int
    unrated_games: int

    def __str__(self) -> str:
        return f"{self.rated_games} (+{self.unrated_games})"


class Games:
    def __init__(
        self,
        raw_games: list[HG_GameResponse],
        all_players: dict[HivePlayerId, HivePlayerInfo],
    ):
        self.raw_games = raw_games
        # map of (p_white, p_black) -> list of games
        self.games_dict: dict[Pair[HivePlayerId], list[HiveGameResult]] = {}
        self.games_list: list[HiveGameResult] = []

        for game in raw_games:
            p_white_hivegame = game.white_player.username
            p_black_hivegame = game.black_player.username
            p_white = next(
                (
                    id
                    for id, info in all_players.items()
                    if p_white_hivegame in info.hivegame
                ),
            )
            if not p_white:
                logger.error(f"Could not find player for @{p_white_hivegame}")
                continue
            p_black = next(
                (
                    id
                    for id, info in all_players.items()
                    if p_black_hivegame in info.hivegame
                ),
            )
            if not p_black:
                logger.error(f"Could not find player for @{p_black_hivegame}")
                continue

            if not isinstance(game.game_status.root, HG_GameStatusFinished):
                logger.error(f"Unknown game status: {game.game_status.root}")
                continue

            converted_game = HiveGameResult(
                player1=p_white,
                player2=p_black,
                result="draw"
                if game.game_status.root.Finished == "Draw"
                else "p1"
                if game.game_status.root.Finished.Winner == "White"
                else "p2",
                rated=game.rated,
            )

            self.games_list.append(converted_game)
            if Pair(p_white, p_black) not in self.games_dict:
                self.games_dict[Pair(p_white, p_black)] = []
            self.games_dict[Pair(p_white, p_black)].append(converted_game)

    def get_games(self, p1: HivePlayerId, p2: HivePlayerId) -> list[HiveGameResult]:
        return self.games_dict.get(Pair(p1, p2), [])


def calculate_game_counts_table(
    games: Games,
    all_players: dict[HivePlayerId, HivePlayerInfo],
) -> tuple[str, dict[HivePlayerId, PlayerGameCounts]]:
    """Generate a table showing game counts between players, sorted by total games

    Returns:
        Tuple of (HTML table, dict of player ID to PlayerGameCounts)
    """
    logger.info("Generating game counts table")
    logger.debug(
        f"Processing {len(games.games_dict)} game pairings for {len(all_players)} players"
    )

    # Calculate total games per player
    player_counts: dict[HivePlayerId, PlayerGameCounts] = {}

    for player_id in all_players:
        player_counts[player_id] = PlayerGameCounts(rated_games=0, unrated_games=0)

    # Count games for each player
    total_games = 0
    for game in games.games_list:
        total_games += 1
        if game.rated:
            player_counts[game.player1].rated_games += 1
            player_counts[game.player2].rated_games += 1
        else:
            player_counts[game.player1].unrated_games += 1
            player_counts[game.player2].unrated_games += 1

    logger.debug(f"Processed {total_games} total games")

    # Sort players by total games (descending)
    sorted_players = sorted(
        player_counts.items(),
        key=lambda x: x[1].rated_games + x[1].unrated_games,
        reverse=True,
    )

    logger.info(f"Generated game counts table with {len(sorted_players)} players")

    # Generate table HTML
    table_html = """
    <table class="matchup-table">
        <thead>
            <tr>
                <th>Player</th>
    """

    # Add column headers
    for player_id, _ in sorted_players:
        player_data = all_players[player_id]
        display_name = player_data.display_name
        hivegame = player_data.current_nick
        table_html += f'<th><a href="https://hivegame.com/@/{hivegame}" target="_blank" class="player-link">{display_name}</a></th>'

    table_html += "</tr></thead><tbody>"

    # Add rows
    for row_player_id, row_counts in sorted_players:
        row_player_data = all_players[row_player_id]
        row_display_name = row_player_data.display_name
        row_hivegame = row_player_data.current_nick

        table_html += f'<tr><th><a href="https://hivegame.com/@/{row_hivegame}" target="_blank" class="player-link">{row_display_name}</a></th>'

        for col_player_id, _ in sorted_players:
            if row_player_id == col_player_id:
                table_html += '<td class="self-match">-</td>'
            else:
                games_list = games.get_games(row_player_id, col_player_id)
                if games_list:
                    rated_count = sum(1 for g in games_list if g.rated)
                    unrated_count = sum(1 for g in games_list if not g.rated)
                    total_count = len(games_list)

                    if total_count == 0:
                        table_html += '<td class="no-matches">0</td>'
                    else:
                        unrated_str = (
                            f" (+{unrated_count})" if unrated_count > 0 else ""
                        )
                        table_html += (
                            f'<td class="has-matches">{rated_count}{unrated_str}</td>'
                        )
                else:
                    table_html += '<td class="no-matches">0</td>'

        table_html += "</tr>"

    table_html += "</tbody></table>"

    return table_html, player_counts


def calculate_rated_lifetime_scores(
    games: Games,
) -> dict[Pair[HivePlayerId], dict[HivePlayerId, Decimal]]:
    """Calculate lifetime scores for rated games only"""
    stats: dict[Pair[HivePlayerId], dict[HivePlayerId, Decimal]] = {}
    for game in games.games_list:
        pair = Pair(game.player1, game.player2)
        if pair not in stats:
            stats[pair] = {game.player1: Decimal("0"), game.player2: Decimal("0")}
        if not game.rated:
            continue

        match game.result:
            case "p1":
                stats[pair][game.player1] += Decimal("1")
            case "p2":
                stats[pair][game.player2] += Decimal("1")
            case "draw":
                stats[pair][game.player1] += Decimal("0.5")
                stats[pair][game.player2] += Decimal("0.5")

    return stats


def calculate_hive_player_total_stats(
    games: Games,
) -> list[HivePlayerOverallStats]:
    stats: dict[HivePlayerId, HivePlayerOverallStats] = {}

    for game in games.games_list:
        if game.player1 not in stats:
            stats[game.player1] = HivePlayerOverallStats(
                id=game.player1, wins=0, losses=0, draws=0, total_games=0
            )
        if game.player2 not in stats:
            stats[game.player2] = HivePlayerOverallStats(
                id=game.player2, wins=0, losses=0, draws=0, total_games=0
            )

        stats[game.player1].total_games += 1
        stats[game.player2].total_games += 1

        match game.result:
            case "p1":
                stats[game.player1].wins += 1
                stats[game.player2].losses += 1
            case "p2":
                stats[game.player2].wins += 1
                stats[game.player1].losses += 1
            case "draw":
                stats[game.player1].draws += 1
                stats[game.player2].draws += 1

    return sorted(stats.values(), key=lambda x: (-x.wins, x.losses, x.id))


def generate_hive_html() -> str:
    # Get all players
    root = Path(__file__).parent.parent.parent
    all_players = get_all_players(root / "data" / "hive.toml")

    # Load cached game data
    cache_file = root / "data" / "hive_games_cache.json"
    all_games_raw = GameCache.model_validate_json(cache_file.read_text()).pairings

    games = Games(
        [
            game
            for pairing_cache in all_games_raw.values()
            for game in pairing_cache.games
        ],
        all_players,
    )

    # Generate game counts table
    game_counts_table, _ = calculate_game_counts_table(games, all_players)

    # Calculate rated lifetime scores
    lifetime_scores = calculate_rated_lifetime_scores(games)
    logger.debug(f"Lifetime scores: {pprint_dict(lifetime_scores)}")

    # Extract unique participants from games
    participants: set[HivePlayerId] = set()
    for pair in lifetime_scores.keys():
        participants.update([pair.a, pair.b])

    sorted_participants_list = [p.id for p in calculate_hive_player_total_stats(games)]

    # Generate topological sort string and levels
    outcomes = pairing_outcomes(
        [
            PairingResult(
                player1=pair.a,
                player2=pair.b,
                result="p1"
                if scores[pair.a] > scores[pair.b]
                else "p2"
                if scores[pair.b] > scores[pair.a]
                else "draw",
            )
            for pair, scores in lifetime_scores.items()
        ]
    )
    logger.debug(f"Outcomes: {outcomes}")
    logger.debug(f"Participants: {participants}")
    levels = topological_sort_participants(outcomes, participants)

    del participants  # No longer needed after this point

    graph_height = 700

    table_content: str = f"""
    <table>
        <thead>
            <tr>
                <th></th>
    {
        "".join(
            f'''
                <th>{all_players[p].display_name}</th>
            '''
            for p in sorted_participants_list
        )
    }
            </tr>
        </thead>
        <tbody>
    """

    for row_player in sorted_participants_list:
        table_content += f"""
            <tr>
                <th>
                    <div>{all_players[row_player].display_name}</div>
                </th>
        """
        for col_player in sorted_participants_list:
            cell_content = ""
            cell_class = ""
            if row_player == col_player:
                cell_class = "self-match-cell"
            elif Pair(row_player, col_player) in lifetime_scores:
                scores = lifetime_scores[Pair(row_player, col_player)]
                row_player_score = scores[row_player]
                col_player_score = scores[col_player]
                cell_class = (
                    "win-cell"
                    if row_player_score > col_player_score
                    else "loss-cell"
                    if row_player_score < col_player_score
                    else "draw-cell"
                )
                cell_content += f"""
                        <div class='score-text'>{row_player_score} – {col_player_score}</div>
                    """
            table_content += f"<td class='{cell_class}'>{cell_content}</td>"
        table_content += "</tr>"

    table_content += """
        </tbody>
    </table>
    """

    # Generate D3.js graph data
    import json
    from dataclasses import asdict

    # Create nodes and edges for D3.js
    graph_data = d3_graph_data(
        players=sorted_participants_list,
        results=[
            PairingResult(
                player1=pair.a,
                player2=pair.b,
                result="p1"
                if scores[pair.a] > scores[pair.b]
                else "p2"
                if scores[pair.b] > scores[pair.a]
                else "draw",
            )
            for pair, scores in lifetime_scores.items()
        ],
    )

    return flask.render_template(
        "hive.html.j2",
        table_content=table_content,
        game_counts_table=game_counts_table,
        graph_data=json.dumps(asdict(graph_data)),
        levels_data=json.dumps(levels),
        graph_height=graph_height,
        num_participants=len(sorted_participants_list),
    )
