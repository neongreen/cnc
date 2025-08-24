import * as Papa from "papaparse"
import { parse } from "@ltd/j-toml"

export type MaturityPlayerStats = {
  name: string
  wins: number
  losses: number
}

export type MaturityMatchResult = {
  date: Date
  player1: string
  player2: string
  result: string
  score1: number
  score2: number
}

// Utility functions
export function sortTuple([a, b]: [string, string]): [string, string] {
  return a < b ? [a, b] : [b, a]
}

export function parseCSV(csvText: string): any[] {
  const result = Papa.parse(csvText.trim(), {
    header: true,
    skipEmptyLines: true,
    transformHeader: (header: string) => header.trim(),
    transform: (value: string) => value?.trim() || "",
  })

  if (result.errors.length > 0) {
    console.warn("CSV parsing errors:", result.errors)
  }

  return result.data
}

export function parseTOML(tomlText: string): any {
  try {
    return parse(tomlText)
  } catch (error) {
    console.warn("TOML parsing error:", error)
    return {}
  }
}

export function loadMaturityData(csvText: string): MaturityMatchResult[] {
  const rows = parseCSV(csvText)
  const results: MaturityMatchResult[] = []

  for (const row of rows) {
    const score1 = parseInt(row.score1)
    const score2 = parseInt(row.score2)

    if (isNaN(score1) || isNaN(score2)) {
      console.warn(`Error processing row: invalid scores`, row)
      continue
    }

    const result = score1 > score2 ? "p1" : score1 < score2 ? "p2" : "draw"

    try {
      const date = new Date(row.date)
      results.push({
        date,
        player1: row.player1,
        player2: row.player2,
        result,
        score1,
        score2,
      })
    } catch (error) {
      console.warn(`Error processing row: invalid date`, row)
      continue
    }
  }

  return results
}

export function getInactivePlayers(tomlText: string): Set<string> {
  const data = parseTOML(tomlText)
  const inactive = new Set<string>()

  for (const [name, meta] of Object.entries(data)) {
    if (
      meta &&
      typeof meta === "object" &&
      "status" in meta &&
      meta.status === "inactive"
    ) {
      inactive.add(name)
    }
  }

  return inactive
}

export function calculateMaturityPlayerStats(
  matchDict: Record<string, MaturityMatchResult[]>,
  players: string[]
): MaturityPlayerStats[] {
  const stats: Record<string, MaturityPlayerStats> = {}
  for (const player of players) {
    stats[player] = { name: player, wins: 0, losses: 0 }
  }

  let totalMatches = 0
  for (const matchList of Object.values(matchDict)) {
    for (const match of matchList) {
      totalMatches++
      const p1 = match.player1
      const p2 = match.player2
      const score1 = match.score1
      const score2 = match.score2

      if (score1 > score2) {
        stats[p1].wins++
        stats[p2].losses++
      } else if (score1 < score2) {
        stats[p1].losses++
        stats[p2].wins++
      }
    }
  }

  // Sort participants: highest wins first, then highest losses last, then by name
  const sortedStats = Object.values(stats).sort((a, b) => {
    if (a.wins !== b.wins) return b.wins - a.wins
    if (a.losses !== b.losses) return a.losses - b.losses
    return a.name.localeCompare(b.name)
  })

  return sortedStats
}

// Graph utilities (ported from graph.py)
export function pairingOutcomes(
  matches: MaturityMatchResult[]
): Record<string, string[][]> {
  const outcomes: Record<string, string[][]> = {}

  for (const match of matches) {
    const key = sortTuple([match.player1, match.player2])
    const keyStr = key.join(" vs ")

    if (!outcomes[keyStr]) {
      outcomes[keyStr] = []
    }

    const outcome =
      match.result === "p1"
        ? [match.player1, match.player2]
        : match.result === "p2"
        ? [match.player2, match.player1]
        : null // draw

    if (outcome) {
      outcomes[keyStr].push(outcome)
    }
  }

  return outcomes
}

export function topologicalSortParticipants(
  outcomes: Record<string, string[][]>,
  participants: string[]
): string[][] {
  // Build graph and in-degree map
  const graph: Record<string, string[]> = {}
  const inDegree: Record<string, number> = {}

  // Initialize all participants
  for (const player of participants) {
    graph[player] = []
    inDegree[player] = 0
  }

  // Build the graph from outcomes
  for (const [_, results] of Object.entries(outcomes)) {
    for (const [winner, loser] of results) {
      // Add edge from winner to loser (winner beats loser)
      if (!graph[winner].includes(loser)) {
        graph[winner].push(loser)
        inDegree[loser]++
      }
    }
  }

  // Kahn's algorithm for topological sort
  const levels: string[][] = []
  const queue: string[] = []

  // Start with players who have no wins against them (in-degree 0)
  for (const player of participants) {
    if (inDegree[player] === 0) {
      queue.push(player)
    }
  }

  // Process levels
  while (queue.length > 0) {
    const levelSize = queue.length
    const level: string[] = []

    for (let i = 0; i < levelSize; i++) {
      const current = queue.shift()!
      level.push(current)

      // Reduce in-degree of all players this player beat
      for (const beaten of graph[current]) {
        inDegree[beaten]--
        if (inDegree[beaten] === 0) {
          queue.push(beaten)
        }
      }
    }

    levels.push(level)
  }

  return levels
}

export function d3GraphData(
  players: string[],
  results: MaturityMatchResult[]
): { nodes: any[]; edges: any[]; ties: any[] } {
  // Create nodes
  const nodes = players.map((player) => ({
    id: player,
    name: player,
  }))

  // Create edges based on match results
  const edges: any[] = []
  const matchDict: Record<string, MaturityMatchResult[]> = {}

  // Group matches by player pairs
  for (const match of results) {
    const key = sortTuple([match.player1, match.player2])
    const keyStr = key.join(" vs ")

    if (!matchDict[keyStr]) {
      matchDict[keyStr] = []
    }
    matchDict[keyStr].push(match)
  }

  // Create edges for wins/losses
  for (const matchList of Object.values(matchDict)) {
    for (const match of matchList) {
      if (match.result === "p1") {
        edges.push({
          source: match.player1,
          target: match.player2,
          index: edges.length,
        })
      } else if (match.result === "p2") {
        edges.push({
          source: match.player2,
          target: match.player1,
          index: edges.length,
        })
      }
    }
  }

  return {
    nodes,
    edges,
    ties: [], // We'll handle ties later if needed
  }
}

// Table generation functions
export function formatDate(date: Date, locale = "en-US"): string {
  return date.toLocaleDateString(locale, { month: "short", day: "numeric" })
}

export function generateMaturityTable(
  matches: MaturityMatchResult[],
  _inactivePlayers: Set<string> | null = null
): string {
  // Create a dictionary to store match data for quick lookup
  const matchDict: Record<string, MaturityMatchResult[]> = {}
  for (const match of matches) {
    const key = sortTuple([match.player1, match.player2]).join(" vs ")
    if (!matchDict[key]) {
      matchDict[key] = []
    }
    matchDict[key].push(match)
  }

  // Extract unique participants
  const participants = new Set<string>()
  for (const [p1, p2] of Object.keys(matchDict).map((k) => k.split(" vs "))) {
    participants.add(p1)
    participants.add(p2)
  }

  const sortedParticipantsStats = calculateMaturityPlayerStats(
    matchDict,
    Array.from(participants)
  )
  const participantsList = sortedParticipantsStats.map((p) => p.name)

  let tableContent = `
    <table>
        <thead>
            <tr>
                <th></th>
    ${sortedParticipantsStats
      .map((p) => `                <th>${p.name}</th>`)
      .join("\n")}
            </tr>
        </thead>
        <tbody>
  `

  for (const rowPlayerStats of sortedParticipantsStats) {
    const rowPlayer = rowPlayerStats.name
    tableContent += `
            <tr>
                <th>
                    <div>${rowPlayer}</div>
                    <div>
                      <small>W ${rowPlayerStats.wins}</small>
                      <small style='margin-left: 0.25rem;'>L ${rowPlayerStats.losses}</small>
                    </div>
                </th>
    `

    for (const colPlayer of participantsList) {
      const key = sortTuple([rowPlayer, colPlayer]).join(" vs ")
      let cellContent = ""
      let cellClass = ""

      if (rowPlayer === colPlayer) {
        cellClass = "self-match-cell"
      } else if (key in matchDict) {
        for (const match of matchDict[key]) {
          let colPlayerScore: number, rowPlayerScore: number
          if (colPlayer === match.player1) {
            colPlayerScore = match.score1
            rowPlayerScore = match.score2
          } else {
            colPlayerScore = match.score2
            rowPlayerScore = match.score1
          }

          cellClass = rowPlayerScore > colPlayerScore ? "win-cell" : "loss-cell"

          const formattedDate = formatDate(match.date)
          cellContent += `
                        <div class='date-text'>${formattedDate}</div>
                        <div class='score-text'>${rowPlayerScore} – ${colPlayerScore}</div>
          `
        }
      }

      tableContent += `<td class='${cellClass}'>${cellContent}</td>`
    }

    tableContent += "</tr>"
  }

  tableContent += `
        </tbody>
    </table>
  `

  return tableContent
}

export function generateMaturityData(csvText: string, tomlText: string): any {
  const matches = loadMaturityData(csvText)
  const inactivePlayers = getInactivePlayers(tomlText)

  // Create a dictionary to store match data for quick lookup
  const matchDict: Record<string, MaturityMatchResult[]> = {}
  for (const match of matches) {
    const key = sortTuple([match.player1, match.player2]).join(" vs ")
    if (!matchDict[key]) {
      matchDict[key] = []
    }
    matchDict[key].push(match)
  }

  // Extract unique participants
  const participants = new Set<string>()
  for (const [p1, p2] of Object.keys(matchDict).map((k) => k.split(" vs "))) {
    participants.add(p1)
    participants.add(p2)
  }

  const sortedParticipantsStats = calculateMaturityPlayerStats(
    matchDict,
    Array.from(participants)
  )
  const participantsList = sortedParticipantsStats.map((p) => p.name)

  // Calculate completion statistics
  const numParticipants = participants.size
  const totalPossiblePairings =
    numParticipants > 1 ? (numParticipants * (numParticipants - 1)) / 2 : 0
  const matchesDone = matches.length
  const completionRate =
    totalPossiblePairings > 0 ? (matchesDone / totalPossiblePairings) * 100 : 0

  // Generate table content
  const tableContent = generateMaturityTable(matches, inactivePlayers)

  // Generate graph data
  const outcomes = pairingOutcomes(matches)
  const levels = topologicalSortParticipants(outcomes, participantsList)
  const graphData = d3GraphData(participantsList, matches)

  // Mark inactive players on nodes
  for (const node of graphData.nodes) {
    if (inactivePlayers.has(node.id)) {
      node.inactive = true
    }
  }

  return {
    numParticipants,
    matchesDone,
    totalPossiblePairings,
    completionRate: completionRate.toFixed(2),
    tableContent,
    graphData,
    levelsData: levels,
  }
}
