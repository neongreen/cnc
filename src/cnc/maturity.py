import csv
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from babel import Locale
from babel.dates import format_date

import flask

from cnc.graph import (
    d3_graph_data,
    pairing_outcomes,
    PairingResult,
    topological_sort_participants,
)
from cnc.utils import sort_tuple
from cnc.maturity_ratings import clamp, expected_score


@dataclass
class MaturityPlayerStats:
    name: str
    wins: int
    losses: int
    elo: float = 1500       # Default ELO rating for new players
    k_factor: float = 40  # K-factor for rating updates. Clamped between 40 and 18.
    total_matches: int = 0


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

def update_elo(
    p1: MaturityPlayerStats, p2: MaturityPlayerStats,
    score1: int, score2: int
) -> tuple[MaturityPlayerStats, MaturityPlayerStats]:
    """Update ELO ratings for two players based on their scores."""
    # Calculate actual and expected scores
    expected1 = expected_score(p1.elo, p2.elo)
    expected2 = expected_score(p2.elo, p1.elo)
    score_rate_1 = score1 / (score1 + score2) # Convert to score%
    score_rate_2 = score2 / (score1 + score2)

    # Update ratings
    p1.elo += p1.k_factor * (score_rate_1 - expected1)
    p2.elo += p2.k_factor * (score_rate_2 - expected2)

    # Update total matches and K-factors
    p1.k_factor = clamp(250 / pow(p1.total_matches + 96, 0.4), 18, 40)
    p2.k_factor = clamp(250 / pow(p2.total_matches + 96, 0.4), 18, 40)
    p1.total_matches += 1
    p2.total_matches += 1

    return (p1, p2)


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

            p1_stats = stats[p1]
            p2_stats = stats[p2]
            updated_p1, updated_p2 = update_elo(p1_stats, p2_stats, score1, score2)
            stats[p1] = updated_p1
            stats[p2] = updated_p2

            if score1 > score2:
                stats[p1].wins += 1
                stats[p2].losses += 1
            elif score1 < score2:
                stats[p1].losses += 1
                stats[p2].wins += 1

    # Sort participants: highest wins first, then highest losses last, then by name
    sorted_stats = sorted(stats.values(), key=lambda x: (-x.wins, x.losses, x.name))
    return sorted_stats


def generate_maturity_html(matches: list[MaturityMatchResult]) -> str:
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

    sorted_participants_stats = sorted(
        sorted_participants_stats, key=lambda x: (-x.elo, -x.wins, x.losses, x.name)
    )
    # for stats in sorted_participants_stats:
    #    stats.elo = round(stats.elo, 2)
    #    print(f"{stats.name:10}: {stats.elo:6} ELO, {stats.wins:2}W-{stats.losses:2}L, {stats.total_matches:2} matches")

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

# root = Path(__file__).parent.parent.parent
# maturity = load_maturity_data(root / "data" / "maturity.csv")
# generate_maturity_html(maturity)