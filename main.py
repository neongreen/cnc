# How to run: uv run main.py
# How to add dependencies: uv add <dependency>

from dataclasses import dataclass
from datetime import date
from babel.dates import format_date
from babel.core import Locale


@dataclass
class ParticipantStats:
    name: str
    wins: int
    losses: int


MATCH_LOG = [
    {"date": date(2025, 6, 3), "sirius": 11, "chez": 1},
    {"date": date(2025, 6, 3), "baltic": 12, "rick": 0},
    {"date": date(2025, 6, 3), "beniu": 6, "nugget": 7},
    {"date": date(2025, 6, 3), "apollix": 0, "sted": 12},
    {"date": date(2025, 6, 4), "emily": 9, "sirius": 0},
    {"date": date(2025, 6, 4), "kuyi": 11, "vivid": 0},
    {"date": date(2025, 6, 4), "tamp": 3, "baltic": 8},
    {"date": date(2025, 6, 4), "blunderer": 0, "sealand": 10},
    {"date": date(2025, 6, 4), "kan": 0, "nugget": 9},
    {"date": date(2025, 6, 4), "kk": 3, "ral": 5},
    {"date": date(2025, 6, 4), "silvy": 1, "sted": 8},
    {"date": date(2025, 6, 4), "hayden": 8, "erix": 2},
    {"date": date(2025, 6, 5), "emily": 4, "kuyi": 6},
    {"date": date(2025, 6, 5), "baltic": 6, "sealand": 3},
    {"date": date(2025, 6, 5), "nugget": 7, "ral": 3},
    {"date": date(2025, 6, 5), "sted": 8, "hayden": 2},
    {"date": date(2025, 6, 6), "kuyi": 2, "baltic": 11},
    {"date": date(2025, 6, 6), "nugget": 1, "sted": 12},
    {"date": date(2025, 6, 8), "baltic": 8, "sted": 2},
    {"date": date(2025, 6, 9), "kuyi": 9, "nugget": 1},
    {"date": date(2025, 6, 15), "beniu": 11, "apollix": 0},
    {"date": date(2025, 6, 15), "tamp": 14, "silvy": 0},
    {"date": date(2025, 6, 15), "rick": 3, "blunderer": 8},
    {"date": date(2025, 6, 15), "kan": 1, "silvy": 11},
    {"date": date(2025, 6, 16), "garry": 5, "baltic": 6},
    {"date": date(2025, 6, 16), "vivid": 0, "silvy": 13},
    {"date": date(2025, 6, 16), "kk": 2, "rick": 12},
    {"date": date(2025, 6, 16), "kan": 3, "apollix": 11},
    {"date": date(2025, 6, 17), "garry": 7, "sted": 4},
    {"date": date(2025, 6, 17), "vivid": 10, "kan": 3},
    {"date": date(2025, 6, 17), "rick": 10, "chez": 1},
    {"date": date(2025, 6, 17), "kk": 5, "erix": 6},
    {"date": date(2025, 6, 19), "tamp": 9, "emily": 3},
    {"date": date(2025, 6, 19), "sealand": 10, "garry": 2},
    {"date": date(2025, 6, 19), "ral": 3, "beniu": 8},
    {"date": date(2025, 6, 19), "bakel": 8, "no one": 1},
    {"date": date(2025, 6, 19), "kk": 8, "chez": 3},
]


@dataclass
class MatchResult:
    date: date
    player1: str
    player2: str
    score1: int
    score2: int


def sort_tuple(t: tuple[str, str]) -> tuple[str, str]:
    return (t[0], t[1]) if t[0] < t[1] else (t[1], t[0])


def calculate_participant_stats(
    match_dict: dict[tuple[str, str], list[MatchResult]], participants: set[str]
) -> list[ParticipantStats]:
    stats: dict[str, ParticipantStats] = {
        p: ParticipantStats(name=p, wins=0, losses=0) for p in participants
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

    # Sort participants: highest wins first, then highest losses last
    sorted_stats = sorted(stats.values(), key=lambda x: (-x.wins, x.losses))
    return sorted_stats


def generate_match_html(match_log_data: list[dict]) -> str:
    # Create a dictionary to store match data for quick lookup
    match_dict: dict[tuple[str, str], list[MatchResult]] = {}
    for match in match_log_data:
        players: list[str] = [key for key in match.keys() if key != "date"]
        if len(players) == 2:
            p1, p2 = players
            key = sort_tuple((p1, p2))
            if key not in match_dict:
                match_dict[key] = []
            match_dict[key].append(
                MatchResult(
                    date=match["date"],
                    player1=p1,
                    player2=p2,
                    score1=match[p1],
                    score2=match[p2],
                )
            )

    # Extract unique participants
    participants: set[str] = set()
    for p1, p2 in match_dict.keys():
        participants.update([p1, p2])

    sorted_participants_stats = calculate_participant_stats(match_dict, participants)
    participants_list = [p.name for p in sorted_participants_stats]
    del participants

    html_content: str = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Maturity elo</title>
    <style>
        html {{ font-size: 12px; }}
        body {{ font-family: sans-serif; margin: 20px; }}
        table {{ width: auto; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 0.25rem 0.5rem; text-align: center; min-width: 4rem; }}
        th {{ background-color: #f2f2f2; font-weight: bold; font-size: 1rem; }}
        .date-text {{ color: gray; font-size: 0.75rem; }}
        .score-text {{ font-size: 1rem; }}
        td.diagonal {{ background-color: #f9f9f9; }}
        .win-cell {{ background-color: #d4edda; }} /* Light green */
        .loss-cell {{ background-color: #f8d7da; }} /* Light red */
    </style>
</head>
<body>
    <table>
        <thead>
            <tr>
                <th></th>
                {"".join(f"<th>{p}</th>" for p in participants_list)}
            </tr>
        </thead>
        <tbody>
    """

    for row_player in participants_list:
        html_content += f"<tr><th>{row_player}</th>"
        for col_player in participants_list:
            if row_player == col_player:
                html_content += "<td class='diagonal'>-</td>"
            else:
                key = sort_tuple((row_player, col_player))
                cell_content = ""
                cell_class = ""
                if key in match_dict:
                    for match in match_dict[key]:
                        date, p1, p2, score1, score2 = (
                            match.date,
                            match.player1,
                            match.player2,
                            match.score1,
                            match.score2,
                        )
                        if col_player == p1:
                            score_display = f"{score1}-{score2}"
                            if score1 > score2:
                                cell_class = "win-cell"
                            elif score1 < score2:
                                cell_class = "loss-cell"
                        else:  # col_player == p2
                            score_display = f"{score2}-{score1}"
                            if score2 > score1:
                                cell_class = "win-cell"
                            elif score2 < score1:
                                cell_class = "loss-cell"
                        formatted_date = format_date(
                            date, format="MMM d", locale=Locale("en", "US")
                        )
                        cell_content += f"<div class='date-text'>{formatted_date}</div><div class='score-text'>{score_display}</div>"
                else:
                    cell_content = "-"
                html_content += f"<td class='{cell_class}'>{cell_content}</td>"
        html_content += "</tr>"

    html_content += """
        </tbody>
    </table>
</body>
</html>
    """
    return html_content


if __name__ == "__main__":
    import os
    import tempfile

    html_output = generate_match_html(MATCH_LOG)
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, "matches.html")
    with open(output_path, "w") as f:
        f.write(html_output)

    print(f"Generated {output_path}")
    # Open the HTML file in the default browser
    os.system(f"open {output_path}")
