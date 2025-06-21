# How to run: `uv run flask run --debug -h 0.0.0.0 -p 5500`
# How to add dependencies: `uv add <dependency>`

from dataclasses import dataclass
from datetime import date
from babel.dates import format_date
from babel.core import Locale
from flask import Flask, send_from_directory
import os
import shutil


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


def to_match_result(data: dict) -> MatchResult:
    date = data["date"]
    del data["date"]
    p1, p2 = sorted(list(data.keys()))
    return MatchResult(
        date=date, player1=p1, player2=p2, score1=data[p1], score2=data[p2]
    )


MATCH_LOG: list[MatchResult] = [
    to_match_result(x)
    for x in [
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
    result_parts = []
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
                if len(group) == 1:
                    result_parts.append(group[0])
                else:
                    result_parts.append("{" + ", ".join(group) + "}")

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
    del participants  # No longer needed after this point

    graph_height = 800

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
        
        /* Graph styles */
        .graph-container {{ 
            margin: 20px 0; 
            border: 1px solid #ddd; 
            padding: 20px; 
            background-color: #fafafa; 
        }}
        #graph-svg {{
            width: 100%;
            height: {graph_height}px;
            border: 1px solid #ccc;
        }}
        .node {{
            fill: #e3f2fd;
            stroke: #1976d2;
            stroke-width: 2px;
        }}
        .node-text {{
            font-family: sans-serif;
            font-size: 12px;
            font-weight: bold;
            text-anchor: middle;
            dominant-baseline: central;
        }}
        .edge {{
            stroke: #666;
            stroke-width: 2px;
            marker-end: url(#arrowhead);
        }}
        .edge-label {{
            font-family: sans-serif;
            font-size: 10px;
            fill: #333;
            text-anchor: middle;
        }}
    </style>
</head>
<body>
    <table>
        <thead>
            <tr>
                <th></th>
                {"".join(f"<th>{p.name}<br><small>W:{p.wins} L:{p.losses}</small></th>" for p in sorted_participants_stats)}
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

    # Generate D3.js graph data
    import json

    # Create nodes and edges for D3.js
    nodes = [{"id": name, "name": name} for name in participants_list]
    edges = []

    for winner, loser in outcomes:
        edges.append(
            {"source": winner, "target": loser, "label": f"{winner} > {loser}"}
        )

    graph_data = {"nodes": nodes, "edges": edges}

    graph_html = f"""
    <div class="graph-container">
        <h2>Match outcomes graph</h2>
        <p>An arrow from A to B means A beat B in a match.</p>
        <svg id="graph-svg"></svg>
    </div>

    <script type="module">
        import {{ drawGraph }} from './graph.js';
        const graphData = {json.dumps(graph_data)};
        const levelsData = {json.dumps(levels)};
        drawGraph(graphData, {graph_height}, levelsData);
    </script>
    """

    html_content += f"""
        </tbody>
    </table>
    {graph_html}
</body>
</html>
    """
    return html_content


def build():
    """Build the static files for the web app."""
    html_output = generate_match_html(MATCH_LOG)
    output_dir = "build"
    os.makedirs(output_dir, exist_ok=True)
    shutil.copyfile("graph.js", os.path.join(output_dir, "graph.js"))
    output_path = os.path.join(output_dir, "index.html")
    with open(output_path, "w") as f:
        f.write(html_output)
    print(f"Generated {output_path}")


app = Flask(__name__)


@app.route("/")
def serve_html():
    build()
    return send_from_directory("build", "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory("build", filename)


if __name__ == "__main__":
    build()
