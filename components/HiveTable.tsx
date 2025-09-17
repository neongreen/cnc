"use client"

import {
  Table as UiTable,
  TableBody as UiTableBody,
  TableCell as UiTableCell,
  TableHead as UiTableHead,
  TableHeader as UiTableHeader,
  TableRow as UiTableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"
import Link from "next/link"
import { assignColors } from "../lib/colors"
import type { Config, GameStats, Player } from "../lib/hiveData"

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
          href={`https://hivegame.com/@/${
            player.hivegame_nick.replace(
              /^HG#/,
              "",
            )
          }`}
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
        <UiTableHead className="bg-muted text-foreground border border-border p-2 text-center font-semibold dark:bg-muted/40">
          Player
        </UiTableHead>
        <UiTableHead className="bg-muted text-foreground border border-border p-2 text-center font-semibold dark:bg-muted/40">
          Total Games
        </UiTableHead>
        {sortedPlayers.map((player) => (
          <UiTableHead
            key={player.id}
            className="bg-muted text-foreground border border-border p-2 text-center font-semibold min-w-20 dark:bg-muted/40"
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
      {ratedStats && ratedTotal > 0 && (
        <span className="font-semibold">{formatStats(ratedStats)}</span>
      )}
      <br />
      {unratedStats && unratedTotal > 0
        ? (
          <span className="text-xs text-muted-foreground dark:text-muted-foreground/80">
            {formatStats(unratedStats)}
          </span>
        )
        : (
          <span className="text-xs text-muted-foreground dark:text-muted-foreground/80">
            &nbsp;
          </span>
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
    stats: GameStats | undefined,
  ) => string
}) {
  return (
    <UiTableRow key={rowPlayer.id}>
      {/* Player name and groups */}
      <UiTableCell className="bg-muted text-foreground border border-border p-2 text-center font-semibold w-[120px] min-w-[120px] max-w-[120px] dark:bg-muted/40">
        <PlayerInfo player={rowPlayer} groupColorMap={groupColorMap} />
      </UiTableCell>
      {/* Total games */}
      <UiTableCell className="bg-muted text-foreground border border-border p-2 text-center font-semibold w-[80px] min-w-[80px] max-w-[80px] dark:bg-muted/30">
        {rowPlayer.total_games}
      </UiTableCell>
      {/* Game stats (rest of the row) */}
      {sortedPlayers.map((colPlayer) => {
        const stats = getStats(rowPlayer, colPlayer)
        const cellClass = getCellClass(rowPlayer, colPlayer, stats)

        return (
          <UiTableCell
            key={`${rowPlayer.id}-${colPlayer.id}`}
            className={cn(
              "border border-border p-1 text-center min-w-[60px] h-10 align-middle",
              cellClass,
            )}
          >
            <GameStats stats={stats} />
          </UiTableCell>
        )
      })}
    </UiTableRow>
  )
}

// Component for rendering table body
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
    stats: GameStats | undefined,
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
    const aGroupPos = aGroup === "(outsider)" ? groupOrder.length : groupOrder.indexOf(aGroup)
    const bGroupPos = bGroup === "(outsider)" ? groupOrder.length : groupOrder.indexOf(bGroup)

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
    stats: GameStats | undefined,
  ) => {
    if (rowPlayer.id === colPlayer.id)
      return "bg-muted text-muted-foreground dark:bg-muted/40"
    if (!stats)
      return "bg-card text-muted-foreground dark:bg-muted/20"

    const ratedTotal = stats.rated_stats
      ? stats.rated_stats.wins
        + stats.rated_stats.losses
        + stats.rated_stats.draws
      : 0
    const unratedTotal = stats.unrated_stats
      ? stats.unrated_stats.wins
        + stats.unrated_stats.losses
        + stats.unrated_stats.draws
      : 0

    if (ratedTotal > 0 || unratedTotal > 0)
      return "bg-emerald-100 text-emerald-900 dark:bg-emerald-500/20 dark:text-emerald-200"
    return "bg-card text-muted-foreground dark:bg-muted/20"
  }

  const getStats = (player1: Player, player2: Player) => {
    return game_stats.find(
      (stat) => stat.player1 === player1.id && stat.player2 === player2.id,
    )
  }

  return (
    <div className="w-full min-w-[1200px] bg-background text-foreground rounded-lg border border-border shadow-sm dark:bg-slate-950/40 dark:shadow-none">
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
