from dataclasses import dataclass
from graphlib import TopologicalSorter
from typing import Literal, Sequence
import structlog

from cnc.utils import sort_tuple

# Get logger for this module
logger = structlog.get_logger()


def topological_sort_participants[T](
    outcomes: Sequence[tuple[T, T]],
    participants: set[T],
) -> list[list[T]]:
    """
    Perform a topological sort of participants based on match outcomes.

    If A beats B, then B depends on A (A comes before B in ranking).

    Args:
        outcomes: List of tuples where each tuple contains (winner, loser).
        participants: Set of all participants.

    Returns:
        A list of lists, where each inner list contains participants that are at the same "level" in the ranking.
        The first list contains the top-ranked participants (unbeaten), etc.
    """
    logger.debug(
        f"Starting topological sort for {len(participants)} participants with {len(outcomes)} outcomes"
    )

    graph = {}

    # Initialize all participants with no dependencies
    for p in participants:
        graph[p] = set()

    # Add dependencies based on outcomes
    for winner, loser in outcomes:
        graph[loser].add(winner)

    logger.debug(f"Built dependency graph with {len(graph)} nodes")

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

    logger.debug("Starting topological sort processing")

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

    return levels


@dataclass
class D3GraphEdge[IdT]:
    source: IdT
    target: IdT


@dataclass
class D3GraphData[IdT]:
    nodes: list[dict]
    edges: list[D3GraphEdge[IdT]]
    ties: list[D3GraphEdge[IdT]]


@dataclass
class PairingResult[IdT]:
    player1: IdT
    player2: IdT
    result: Literal["p1", "p2", "draw"]


def pairing_outcomes[IdT](
    matches: Sequence[PairingResult[IdT]],
) -> list[tuple[IdT, IdT]]:
    """Extract match outcomes as tuples of (winner, loser). If a match is a draw, it is ignored."""
    outcomes = []
    for match in matches:
        if match.result == "p1":
            outcomes.append((match.player1, match.player2))
        elif match.result == "p2":
            outcomes.append((match.player2, match.player1))
    return outcomes


def d3_graph_data[IdT](
    players: Sequence[IdT],
    results: Sequence[PairingResult[IdT]],
) -> D3GraphData[IdT]:
    """Generate D3.js graph data"""

    # Create nodes and edges for D3.js
    nodes = [{"id": name, "name": name} for name in players]
    edges = []

    ties: set[tuple[IdT, IdT]] = set()

    for pairing in results:
        if pairing.result == "draw":
            key = sort_tuple((pairing.player1, pairing.player2))
            ties.add(key)
        elif pairing.result == "p1":
            winner, loser = pairing.player1, pairing.player2
            edges.append({"source": winner, "target": loser})
        elif pairing.result == "p2":
            winner, loser = pairing.player2, pairing.player1
            edges.append({"source": winner, "target": loser})

    ties_edges: list[D3GraphEdge] = []
    for p1, p2 in ties:
        ties_edges.append(D3GraphEdge(source=p1, target=p2))

    return D3GraphData(nodes=nodes, edges=edges, ties=ties_edges)
