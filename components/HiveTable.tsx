"use client"

import type { Config, GameStats, Player } from "../lib/hiveData"
import { assignColors } from "../lib/colors"
import Link from "next/link"
import {
  Table as UiTable,
  TableHeader as UiTableHeader,
  TableBody as UiTableBody,
  TableRow as UiTableRow,
  TableHead as UiTableHead,
  TableCell as UiTableCell,
} from "@/components/ui/table"

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
      <div className="font-bold mb-1 flex justify-center items-center">
        <Link
          href={`https://hivegame.com/@/${player.hivegame_nick.replace(
            /^HG#/,
            ""
          )}`}
        >
          <span className="flex items-center gap-2">
            <span
              className="inline-block rounded-full bg-gray-300 dark:bg-gray-600 w-2 h-2"
              aria-hidden="true"
            />
            <span className="cursor-pointer transition-colors hover:text-blue-700 focus-visible:text-blue-700 outline-none">
              {player.display_name}
            </span>
          </span>
        </Link>
      </div>
      <div
        className="w-full text-[10px] text-white text-center"
        style={{ backgroundColor: groupColorMap[player.groups[0]] }}
      >
        {player.groups[0]}
      </div>
    </>
  )
}

// Component for rendering table header (uses shadcn Table primitives)
function HiveHeader({
  sortedPlayers,
  groupColorMap,
}: {
  sortedPlayers: Player[]
  groupColorMap: Record<string, string>
}) {
  return (
    <UiTableHeader>
      <UiTableRow>
        <UiTableHead className="bg-[#f8f9fa] border border-[#dee2e6] p-2 text-center font-bold">
          Player
        </UiTableHead>
        <UiTableHead className="bg-[#f8f9fa] border border-[#dee2e6] p-2 text-center font-bold">
          Total Games
        </UiTableHead>
        {sortedPlayers.map((player) => (
          <UiTableHead
            key={player.id}
            className="bg-[#f8f9fa] border border-[#dee2e6] p-2 text-center font-bold min-w-20"
          >
            <PlayerInfo player={player} groupColorMap={groupColorMap} />
          </UiTableHead>
        ))}
      </UiTableRow>
    </UiTableHeader>
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
    if (stats.draws === 0) return `${stats.wins}-${stats.losses}`
    return `${stats.wins}-${stats.losses}-${stats.draws}`
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
      <br />
      {unratedStats && unratedTotal > 0 ? (
        <span className="unrated-text">{formatStats(unratedStats)}</span>
      ) : (
        <span className="unrated-text">&nbsp;</span>
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
    <UiTableRow key={rowPlayer.id}>
      {/* Player name and groups */}
      <UiTableCell className="bg-[#f8f9fa] border border-[#dee2e6] p-2 text-center font-bold w-[120px] min-w-[120px] max-w-[120px]">
        <PlayerInfo player={rowPlayer} groupColorMap={groupColorMap} />
      </UiTableCell>
      {/* Total games */}
      <UiTableCell className="bg-[#e9ecef] border border-[#dee2e6] p-2 text-center font-bold w-[80px] min-w-[80px] max-w-[80px]">
        {rowPlayer.total_games}
      </UiTableCell>
      {/* Game stats (rest of the row) */}
      {sortedPlayers.map((colPlayer) => {
        const stats = getStats(rowPlayer, colPlayer)
        const cellClass = getCellClass(rowPlayer, colPlayer, stats)

        return (
          <UiTableCell
            key={`${rowPlayer.id}-${colPlayer.id}`}
            className={`border border-[#dee2e6] p-1 text-center min-w-[60px] h-10 align-middle ${cellClass}`}
          >
            <GameStats stats={stats} />
          </UiTableCell>
        )
      })}
    </UiTableRow>
  )
}

// Component for rendering table body (uses shadcn Table primitives)
function HiveBody({
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
    <UiTableBody>
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
    </UiTableBody>
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
    if (rowPlayer.id === colPlayer.id) return "bg-[#e9ecef] text-[#6c757d]"
    if (!stats) return "bg-[#f8f9fa] text-[#6c757d]"

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

    if (ratedTotal > 0 || unratedTotal > 0) return "bg-[#e8f5e8]"
    return "bg-[#f8f9fa] text-[#6c757d]"
  }

  const getStats = (player1: Player, player2: Player) => {
    return game_stats.find(
      (stat) => stat.player1 === player1.id && stat.player2 === player2.id
    )
  }

  return (
    <div className="w-full min-w-[1200px] bg-white rounded-lg shadow">
      <div className="min-w-[800px]">
        <UiTable className="w-max text-[12px] border-collapse">
          <HiveHeader
            sortedPlayers={sortedPlayers}
            groupColorMap={groupColorMap}
          />
          <HiveBody
            sortedPlayers={sortedPlayers}
            groupColorMap={groupColorMap}
            getStats={getStats}
            getCellClass={getCellClass}
          />
        </UiTable>
      </div>
    </div>
  )
}
