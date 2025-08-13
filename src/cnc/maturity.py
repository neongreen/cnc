import csv
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from babel import Locale
from babel.dates import format_date

import flask
import tomllib

from cnc.graph import (
    d3_graph_data,
    pairing_outcomes,
    PairingResult,
    topological_sort_participants,
)
from cnc.utils import sort_tuple


@dataclass
class MaturityPlayerStats:
    name: str
    wins: int
    losses: int


@dataclass
class MaturityMatchResult(PairingResult):
    date: date
    score1: int
    score2: int


def load_maturity_data(file_path: Path) -> list[MaturityMatchResult]:
    with file_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    results = []
    for row in rows:
        score1 = int(row["score1"])
        score2 = int(row["score2"])
        results.append(
            MaturityMatchResult(
                date=datetime.strptime(row["date"], "%Y-%m-%d").date(),
                player1=row["player1"],
                player2=row["player2"],
                result="p1" if score1 > score2 else "p2" if score1 < score2 else "draw",
                score1=score1,
                score2=score2,
            )
        )
    return results


def calculate_maturity_player_stats(
    match_dict: dict[tuple[str, str], list[MaturityMatchResult]],
    players: set[str],
) -> list[MaturityPlayerStats]:
    stats: dict[str, MaturityPlayerStats] = {
        p: MaturityPlayerStats(name=p, wins=0, losses=0) for p in players
    }

    for key in match_dict:
        for match in match_dict[key]:
            p1, p2 = match.player1, match.player2
            score1, score2 = match.score1, match.score2

            if score1 > score2:
                stats[p1].wins += 1
                stats[p2].losses += 1
            elif score1 < score2:
                stats[p1].losses += 1
                stats[p2].wins += 1

    # Sort participants: highest wins first, then highest losses last, then by name
    sorted_stats = sorted(stats.values(), key=lambda x: (-x.wins, x.losses, x.name))
    return sorted_stats


def load_maturity_players(file_path: Path) -> set[str]:
    """Load maturity players metadata from TOML and return a set of inactive player names.

    The TOML format is expected to be tables keyed by player id/name, e.g.:

        [amg]
        status = "inactive"

    Any player table with `status = "inactive"` is considered inactive.
    """
    inactive: set[str] = set()
    try:
        with file_path.open("rb") as f:
            data = tomllib.load(f)
        for name, meta in data.items():
            if isinstance(meta, dict) and meta.get("status") == "inactive":
                inactive.add(name)
    except FileNotFoundError:
        # No metadata file; treat everyone as active
        pass
    return inactive


def generate_maturity_html(
    matches: list[MaturityMatchResult],
    inactive_players: set[str] | None = None,
) -> str:
    # Create a dictionary to store match data for quick lookup
    match_dict: dict[tuple[str, str], list[MaturityMatchResult]] = {}
    for match in matches:
        key = sort_tuple((match.player1, match.player2))
        if key not in match_dict:
            match_dict[key] = []
        match_dict[key].append(match)

    # Extract unique participants
    participants: set[str] = set()
    for p1, p2 in match_dict.keys():
        participants.update([p1, p2])

    sorted_participants_stats = calculate_maturity_player_stats(
        match_dict, participants
    )
    participants_list = [p.name for p in sorted_participants_stats]

    # Generate topological sort string and levels
    outcomes = pairing_outcomes(matches)
    levels = topological_sort_participants(outcomes, participants)
    num_participants = len(participants)
    total_possible_pairings = (
        num_participants * (num_participants - 1) / 2 if num_participants > 1 else 0
    )
    matches_done = len(matches)
    completion_rate = (
        (matches_done / total_possible_pairings) * 100
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
            elif key in match_dict:
                for match in match_dict[key]:
                    if col_player == match.player1:
                        col_player_score, row_player_score = (
                            match.score1,
                            match.score2,
                        )
                    else:
                        col_player_score, row_player_score = (
                            match.score2,
                            match.score1,
                        )
                    cell_class = (
                        "win-cell"
                        if row_player_score > col_player_score
                        else "loss-cell"
                    )
                    formatted_date = format_date(
                        match.date, format="MMM d", locale=Locale("en", "US")
                    )
                    cell_content += f"""
                        <div class='date-text'>{formatted_date}</div>
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
        players=participants_list,
        results=matches,
    )

    # Mark inactive players on nodes so the frontend can style them.
    if inactive_players:
        for node in graph_data.nodes:
            node_id = node.get("id")
            if isinstance(node_id, str) and node_id in inactive_players:
                node["inactive"] = True

    return flask.render_template(
        "index.html.j2",
        table_content=table_content,
        graph_data=json.dumps(asdict(graph_data)),
        levels_data=json.dumps(levels),
        graph_height=graph_height,
        matches_done=matches_done,
        total_possible_pairings=int(total_possible_pairings),
        completion_rate=f"{completion_rate:.2f}",
        num_participants=num_participants,
    )
