from dataclasses import asdict, dataclass
from datetime import date, datetime
import decimal
from pathlib import Path
from typing import Literal

import flask
import tomllib

from cnc.graph import (
    PairingResult,
    d3_graph_data,
    pairing_outcomes,
    topological_sort_participants,
)
from cnc.utils import sort_tuple


@dataclass
class HivePlayerOverallStats:
    name: str
    wins: int
    losses: int
    draws: int


@dataclass
class HiveGameResult:
    date: date | None
    player1: str
    player2: str
    result: Literal["p1", "p2", "draw"]
    link: str


@dataclass
class HivePairingResult(PairingResult):
    """Lifelong stats for a pair of players."""

    player1: str
    player2: str
    score1: decimal.Decimal
    score2: decimal.Decimal


# TODO: show players properly


def load_hive_data(file_path: Path) -> list[HiveGameResult]:
    # Read TOML file and parse matches
    with file_path.open("rb") as f:
        data = tomllib.load(f)
    rows = data.get("games", [])
    return [
        HiveGameResult(
            date=datetime.strptime(row["date"], "%Y-%m-%d").date()
            if row.get("date")
            else None,
            player1=row["players"][0],
            player2=row["players"][1],
            result=row["result"],
            link=row["link"],
        )
        for row in rows
    ]


def calculate_hive_player_total_stats(
    pairing_dict: dict[tuple[str, str], HivePairingResult],
    players: set[str],
) -> list[HivePlayerOverallStats]:
    stats: dict[str, HivePlayerOverallStats] = {
        p: HivePlayerOverallStats(name=p, wins=0, losses=0, draws=0) for p in players
    }

    for key in pairing_dict:
        pairing = pairing_dict[key]
        p1, p2 = pairing.player1, pairing.player2
        match pairing.result:
            case "draw":
                stats[p1].draws += 1
                stats[p2].draws += 1
            case "p1":
                stats[p1].wins += 1
                stats[p2].losses += 1
            case "p2":
                stats[p2].wins += 1
                stats[p1].losses += 1

    # Sort participants: highest wins first, then highest losses last, then by name
    sorted_stats = sorted(stats.values(), key=lambda x: (-x.wins, x.losses, x.name))
    return sorted_stats


def calculate_hive_pairing_stats(
    games: list[HiveGameResult],
) -> dict[tuple[str, str], HivePairingResult]:
    pairing_stats: dict[tuple[str, str], HivePairingResult] = {}

    for game in games:
        key = sort_tuple((game.player1, game.player2))
        if key not in pairing_stats:
            pairing_stats[key] = HivePairingResult(
                player1=game.player1,
                player2=game.player2,
                score1=decimal.Decimal("0"),
                score2=decimal.Decimal("0"),
                result=game.result,
            )
        if game.result == "p1":
            pairing_stats[key].score1 += decimal.Decimal("1")
        elif game.result == "p2":
            pairing_stats[key].score2 += decimal.Decimal("1")
        elif game.result == "draw":
            pairing_stats[key].score1 += decimal.Decimal("0.5")
            pairing_stats[key].score2 += decimal.Decimal("0.5")

    return pairing_stats


def generate_hive_html(games: list[HiveGameResult]) -> str:
    pairing_dict = calculate_hive_pairing_stats(games)

    # We don't have any use for games anymore
    del games

    # Extract unique participants
    participants: set[str] = set()
    for p1, p2 in pairing_dict.keys():
        participants.update([p1, p2])

    sorted_participants_stats = calculate_hive_player_total_stats(
        pairing_dict, participants
    )
    participants_list = [p.name for p in sorted_participants_stats]

    # Generate topological sort string and levels
    outcomes = pairing_outcomes(list(pairing_dict.values()))
    levels = topological_sort_participants(outcomes, participants)
    num_participants = len(participants)
    total_possible_pairings = (
        num_participants * (num_participants - 1) / 2 if num_participants > 1 else 0
    )
    pairings_done = len(pairing_dict)
    completion_rate = (
        (pairings_done / total_possible_pairings) * 100
        if total_possible_pairings > 0
        else 0
    )

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
                <th>{p.name}</th>
            '''
            for p in sorted_participants_stats
        )
    }
            </tr>
        </thead>
        <tbody>
    """

    for row_player_stats in sorted_participants_stats:
        row_player = row_player_stats.name
        table_content += f"""
            <tr>
                <th>
                    <div>{row_player}</div>
                    <div>
                      <small>W {row_player_stats.wins}</small>
                      <small style='margin-left: 0.25rem;'>L {row_player_stats.losses}</small>
                    </div>
                </th>
        """
        for col_player in participants_list:
            key = sort_tuple((row_player, col_player))
            cell_content = ""
            cell_class = ""
            if row_player == col_player:
                cell_class = "self-match-cell"
            elif key in pairing_dict:
                pairing = pairing_dict[key]
                row_player_score = (
                    pairing.score1 if pairing.player1 == row_player else pairing.score2
                )
                col_player_score = (
                    pairing.score2 if pairing.player1 == row_player else pairing.score1
                )
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

    # Create nodes and edges for D3.js
    graph_data = d3_graph_data(
        players=participants_list, results=list(pairing_dict.values())
    )

    return flask.render_template(
        "hive.html.j2",
        table_content=table_content,
        graph_data=json.dumps(asdict(graph_data)),
        levels_data=json.dumps(levels),
        graph_height=graph_height,
        pairings_done=pairings_done,
        total_possible_pairings=int(total_possible_pairings),
        completion_rate=f"{completion_rate:.2f}",
        num_participants=num_participants,
    )
