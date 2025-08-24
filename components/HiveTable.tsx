"use client"

import "./HiveTable.css"
import type { Config, GameStats, Player } from "../lib/hiveData"
import { assignColors } from "../lib/colors"

// Component for rendering player information (name and group)
function PlayerInfo({
  player,
  groupColorMap,
}: {
  player: Player
  groupColorMap: Record<string, string>
}) {
  return (
    <>
      <div className="player-name">{player.display_name}</div>
      <div
        className="player-group"
        style={{
          backgroundColor: groupColorMap[player.groups[0]],
        }}
      >
        {player.groups[0]}
      </div>
    </>
  )
}

// Component for rendering table header
function TableHeader({
  sortedPlayers,
  groupColorMap,
}: {
  sortedPlayers: Player[]
  groupColorMap: Record<string, string>
}) {
  return (
    <thead>
      <tr>
        <th className="header-cell">Player</th>
        <th className="header-cell">Total Games</th>
        {sortedPlayers.map((player) => (
          <th key={player.id} className="header-cell player-header">
            <PlayerInfo player={player} groupColorMap={groupColorMap} />
          </th>
        ))}
      </tr>
    </thead>
  )
}

// Component for rendering game statistics
function GameStats({ stats }: { stats: GameStats | undefined }) {
  const formatStats = (stats: {
    wins: number
    losses: number
    draws: number
  }) => {
    if (!stats || stats.wins + stats.losses + stats.draws === 0) return ""
    return `${stats.wins}W ${stats.losses}L ${stats.draws}D`
  }

  if (!stats) return null

  const ratedStats = stats.rated_stats
  const unratedStats = stats.unrated_stats

  const ratedTotal = ratedStats
    ? ratedStats.wins + ratedStats.losses + ratedStats.draws
    : 0
  const unratedTotal = unratedStats
    ? unratedStats.wins + unratedStats.losses + unratedStats.draws
    : 0

  return (
    <>
      {ratedStats && ratedTotal > 0 && <span>{formatStats(ratedStats)}</span>}
      {unratedStats && unratedTotal > 0 && (
        <>
          <br />
          <span className="unrated-text">{formatStats(unratedStats)}</span>
        </>
      )}
    </>
  )
}

// Component for rendering a single table row
function PlayerRow({
  rowPlayer,
  sortedPlayers,
  groupColorMap,
  getStats,
  getCellClass,
}: {
  rowPlayer: Player
  sortedPlayers: Player[]
  groupColorMap: Record<string, string>
  getStats: (player1: Player, player2: Player) => GameStats | undefined
  getCellClass: (
    rowPlayer: Player,
    colPlayer: Player,
    stats: GameStats | undefined
  ) => string
}) {
  return (
    <tr key={rowPlayer.id} className="player-row">
      <td className="player-cell">
        <PlayerInfo player={rowPlayer} groupColorMap={groupColorMap} />
      </td>
      <td className="total-games">{rowPlayer.total_games}</td>
      {sortedPlayers.map((colPlayer) => {
        const stats = getStats(rowPlayer, colPlayer)
        const cellClass = getCellClass(rowPlayer, colPlayer, stats)

        return (
          <td
            key={`${rowPlayer.id}-${colPlayer.id}`}
            className={`game-cell ${cellClass}`}
          >
            <GameStats stats={stats} />
          </td>
        )
      })}
    </tr>
  )
}

// Component for rendering table body
function TableBody({
  sortedPlayers,
  groupColorMap,
  getStats,
  getCellClass,
}: {
  sortedPlayers: Player[]
  groupColorMap: Record<string, string>
  getStats: (player1: Player, player2: Player) => GameStats | undefined
  getCellClass: (
    rowPlayer: Player,
    colPlayer: Player,
    stats: GameStats | undefined
  ) => string
}) {
  return (
    <tbody>
      {sortedPlayers.map((rowPlayer) => (
        <PlayerRow
          key={rowPlayer.id}
          rowPlayer={rowPlayer}
          sortedPlayers={sortedPlayers}
          groupColorMap={groupColorMap}
          getStats={getStats}
          getCellClass={getCellClass}
        />
      ))}
    </tbody>
  )
}

export default function HiveTable({
  config,
  game_stats,
  players,
}: {
  config: Config
  game_stats: GameStats[]
  players: Player[]
}) {
  const groupColorMap = assignColors(config.group_order)

  // Sort players by group first, then by total games within each group
  const sortedPlayers = [...players].sort((a, b) => {
    // First sort by group position according to config.group_order
    const groupOrder = config.group_order
    const aGroup = a.groups[0] || "(no-group)"
    const bGroup = b.groups[0] || "(no-group)"

    // Get group positions (outsiders go last)
    const aGroupPos =
      aGroup === "(outsider)" ? groupOrder.length : groupOrder.indexOf(aGroup)
    const bGroupPos =
      bGroup === "(outsider)" ? groupOrder.length : groupOrder.indexOf(bGroup)

    // If groups are different, sort by group position
    if (aGroupPos !== bGroupPos) {
      return aGroupPos - bGroupPos
    }

    // If groups are the same, sort by total games (descending - most games first)
    return b.total_games - a.total_games
  })

  const getCellClass = (
    rowPlayer: Player,
    colPlayer: Player,
    stats: GameStats | undefined
  ) => {
    if (rowPlayer.id === colPlayer.id) return "self-match"
    if (!stats) return "no-matches"

    const ratedTotal = stats.rated_stats
      ? stats.rated_stats.wins +
        stats.rated_stats.losses +
        stats.rated_stats.draws
      : 0
    const unratedTotal = stats.unrated_stats
      ? stats.unrated_stats.wins +
        stats.unrated_stats.losses +
        stats.unrated_stats.draws
      : 0

    if (ratedTotal > 0 || unratedTotal > 0) return "has-matches"
    return "no-matches"
  }

  const getStats = (player1: Player, player2: Player) => {
    return game_stats.find(
      (stat) =>
        (stat.player1 === player1.id && stat.player2 === player2.id) ||
        (stat.player1 === player2.id && stat.player2 === player1.id)
    )
  }

  return (
    <div className="hive-table">
      <div className="table-container">
        <table className="game-table">
          <TableHeader
            sortedPlayers={sortedPlayers}
            groupColorMap={groupColorMap}
          />
          <TableBody
            sortedPlayers={sortedPlayers}
            groupColorMap={groupColorMap}
            getStats={getStats}
            getCellClass={getCellClass}
          />
        </table>
      </div>
    </div>
  )
}
