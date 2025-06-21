# How to run: see mise.toml
# How to add dependencies: `uv add <dependency>`

from dataclasses import dataclass
from datetime import date, datetime
from babel.dates import format_date
from babel.core import Locale
from flask import Flask, render_template, send_from_directory
import os
import shutil
import csv


@dataclass
class ParticipantStats:
    name: str
    wins: int
    losses: int


@dataclass
class MatchResult:
    date: date
    player1: str
    player2: str
    score1: int
    score2: int


def load_match_data(file_path: str) -> list[MatchResult]:
    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return [
        MatchResult(
            date=datetime.strptime(row["date"], "%Y-%m-%d").date(),
            player1=row["player1"],
            player2=row["player2"],
            score1=int(row["score1"]),
            score2=int(row["score2"]),
        )
        for row in rows
    ]


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

    # Sort participants: highest wins first, then highest losses last, then by name
    sorted_stats = sorted(stats.values(), key=lambda x: (-x.wins, x.losses, x.name))
    return sorted_stats


def get_match_outcomes(matches: list[MatchResult]) -> list[tuple[str, str]]:
    """Extract match outcomes as tuples of (winner, loser). If a match is a draw, it is ignored."""
    outcomes = []
    for match in matches:
        if match.score1 > match.score2:
            outcomes.append((match.player1, match.player2))
        elif match.score1 < match.score2:
            outcomes.append((match.player2, match.player1))
    return outcomes


def topological_sort_participants(
    outcomes: list[tuple[str, str]], participants: set[str]
) -> list[list[str]]:
    from graphlib import TopologicalSorter

    # Build the graph for TopologicalSorter
    # TopologicalSorter expects dependencies, so we need to reverse the relationship
    # If A beats B, then B depends on A (A comes before B in ranking)
    graph = {}

    # Initialize all participants with no dependencies
    for p in participants:
        graph[p] = set()

    # Add dependencies based on outcomes
    for winner, loser in outcomes:
        graph[loser].add(winner)

    # Build a reachability graph to check if there's any path between nodes
    def has_path(start, end, graph):
        """Check if there's a path from start to end in the dependency graph"""
        if start == end:
            return True
        visited = set()
        stack = [start]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            if current == end:
                return True

            # Add all nodes that depend on current (reverse direction)
            for node in sorted(graph.keys()):  # Sort keys for deterministic iteration
                if current in graph[node]:
                    stack.append(node)

            # Add all nodes that current depends on
            for dep in sorted(
                list(graph.get(current, []))
            ):  # Sort dependencies for deterministic iteration
                stack.append(dep)

        return False

    # Use TopologicalSorter with batch processing, but group only truly equivalent nodes
    ts = TopologicalSorter(graph)
    levels = []  # Store the levels for graph visualization
    ts.prepare()

    while ts.is_active():
        # Get nodes that are ready to be processed (no remaining dependencies)
        ready_nodes = sorted(list(ts.get_ready()))  # Sort ready nodes alphabetically
        if ready_nodes:
            # Group nodes that have no path between them
            groups = []
            remaining = list(ready_nodes)

            while remaining:
                current_group = [remaining.pop(0)]
                i = 0
                while i < len(remaining):
                    node = remaining[i]
                    # Check if this node has a path to/from any node in current group
                    has_connection = False
                    for group_node in current_group:
                        if has_path(node, group_node, graph) or has_path(
                            group_node, node, graph
                        ):
                            has_connection = True
                            break

                    if not has_connection:
                        current_group.append(remaining.pop(i))
                    else:
                        i += 1

                groups.append(
                    sorted(current_group)
                )  # Ensure group is sorted alphabetically

            # Add groups to result and levels
            level_groups = []
            # Sort groups by their first element (player name) for consistent ordering
            for group in sorted(groups, key=lambda x: x[0]):
                level_groups.extend(group)

            levels.append(level_groups)

            # Mark these nodes as done
            ts.done(*ready_nodes)
        else:
            # If no nodes are ready but the sorter is still active, we have a cycle
            break

    print("Topologically sorted:", " ".join([f"{{{', '.join(x)}}}" for x in levels]))
    return levels


def generate_match_html(matches: list[MatchResult]) -> str:
    # Create a dictionary to store match data for quick lookup
    match_dict: dict[tuple[str, str], list[MatchResult]] = {}
    for match in matches:
        key = sort_tuple((match.player1, match.player2))
        if key not in match_dict:
            match_dict[key] = []
        match_dict[key].append(match)

    # Extract unique participants
    participants: set[str] = set()
    for p1, p2 in match_dict.keys():
        participants.update([p1, p2])

    sorted_participants_stats = calculate_participant_stats(match_dict, participants)
    print(
        "Players:",
        ", ".join(
            [f"{p.name} W:{p.wins} L:{p.losses}" for p in sorted_participants_stats]
        ),
    )
    participants_list = [p.name for p in sorted_participants_stats]

    # Generate topological sort string and levels
    outcomes = get_match_outcomes(matches)
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

    graph_height = 800

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
    nodes = [{"id": name, "name": name} for name in participants_list]
    edges = []

    for winner, loser in outcomes:
        edges.append({"source": winner, "target": loser})

    graph_data = {"nodes": nodes, "edges": edges}

    return render_template(
        "index.html.j2",
        table_content=table_content,
        graph_data=json.dumps(graph_data),
        levels_data=json.dumps(levels),
        graph_height=graph_height,
        matches_done=matches_done,
        total_possible_pairings=int(total_possible_pairings),
        completion_rate=f"{completion_rate:.2f}",
        num_participants=num_participants,
    )


def build():
    """Build the static files for the web app."""
    matches = load_match_data(os.path.join(os.path.dirname(__file__), "match_data.csv"))
    html_output = generate_match_html(matches)
    output_dir = "build"
    os.makedirs(output_dir, exist_ok=True)
    shutil.copyfile("graph.js", os.path.join(output_dir, "graph.js"))
    output_path = os.path.join(output_dir, "index.html")
    with open(output_path, "w") as f:
        f.write(html_output)
    print(f"Generated {output_path}")


app = Flask(__name__)
with app.app_context():
    build()


@app.route("/")
def serve_html():
    return send_from_directory("build", "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory("build", filename)
