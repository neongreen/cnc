"use client"

import type { Player } from "../lib/hiveData"
import Link from "next/link"
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

type RecentGame = {
  game_id: string
  white_player: string
  black_player: string
  white_known: boolean
  black_known: boolean
  result: "white" | "black" | "draw"
  rated: boolean
  timestamp?: string
  event: string | null
}

type RecentGamesProps = {
  games: RecentGame[]
  knownPlayers: Player[]
  /** List of player group names that should be highlighted with yellow background */
  highlightGroups: string[]
}

interface PlayerNameProps {
  playerName: string
  isKnown: boolean
  knownPlayers: Player[]
  highlightGroups: string[]
}

function isPlayerHighlighted(
  playerName: string,
  isKnown: boolean,
  knownPlayers: Player[],
  highlightGroups: string[]
): boolean {
  if (!isKnown) return false

  const player = knownPlayers.find((p) =>
    p.hivegame_nicks.some((nick) => nick.replace(/^HG#/, "") === playerName)
  )

  if (!player) return false

  return player.groups.some((group) => highlightGroups.includes(group))
}

function determinePlayerOrder(
  whitePlayer: string,
  blackPlayer: string,
  whiteKnown: boolean,
  blackKnown: boolean,
  knownPlayers: Player[],
  highlightGroups: string[]
) {
  const whiteHighlighted = isPlayerHighlighted(
    whitePlayer,
    whiteKnown,
    knownPlayers,
    highlightGroups
  )
  const blackHighlighted = isPlayerHighlighted(
    blackPlayer,
    blackKnown,
    knownPlayers,
    highlightGroups
  )

  // If neither is highlighted, we shouldn't show this game
  if (!whiteHighlighted && !blackHighlighted) {
    return null
  }

  // Player One should always be highlighted if possible
  if (whiteHighlighted) {
    return {
      playerOne: { name: whitePlayer, known: whiteKnown },
      playerTwo: { name: blackPlayer, known: blackKnown },
      result: "white" as const,
    }
  } else {
    return {
      playerOne: { name: blackPlayer, known: blackKnown },
      playerTwo: { name: whitePlayer, known: whiteKnown },
      result: "black" as const,
    }
  }
}

function getResultClass(result: "white" | "black" | "draw"): string {
  switch (result) {
    case "white":
      return "text-green-600 font-semibold"
    case "black":
      return "text-blue-600 font-semibold"
    case "draw":
      return "text-gray-600 font-semibold"
    default:
      return ""
  }
}

function getResultText(result: "white" | "black" | "draw"): string {
  switch (result) {
    case "white":
      return "1-0"
    case "black":
      return "0-1"
    case "draw":
      return "½-½"
    default:
      return ""
  }
}

function formatRelativeTime(dateString: string): string {
  try {
    const date = new Date(dateString)
    const now = new Date()
    const diffInMs = now.getTime() - date.getTime()
    const diffInMinutes = Math.floor(diffInMs / (1000 * 60))
    const diffInHours = Math.floor(diffInMs / (1000 * 60 * 60))
    const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24))

    if (diffInMinutes < 1) return "just now"
    if (diffInMinutes < 60)
      return `${diffInMinutes} minute${diffInMinutes === 1 ? "" : "s"} ago`
    if (diffInHours < 24)
      return `${diffInHours} hour${diffInHours === 1 ? "" : "s"} ago`
    if (diffInDays < 7)
      return `${diffInDays} day${diffInDays === 1 ? "" : "s"} ago`
    if (diffInDays < 30) {
      const weeks = Math.floor(diffInDays / 7)
      return `${weeks} week${weeks === 1 ? "" : "s"} ago`
    }
    if (diffInDays < 365) {
      const months = Math.floor(diffInDays / 30)
      return `${months} month${months === 1 ? "" : "s"} ago`
    }
    const years = Math.floor(diffInDays / 365)
    return `${years} year${years === 1 ? "" : "s"} ago`
  } catch {
    return dateString
  }
}

function formatDayHeader(dateString: string): string {
  try {
    const date = new Date(dateString)
    // Check if date is valid
    if (isNaN(date.getTime())) {
      return dateString
    }
    return date.toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
    })
  } catch {
    return dateString
  }
}

type ProcessedGame = RecentGame & {
  playerOrder: NonNullable<ReturnType<typeof determinePlayerOrder>>
  adjustedResult: "white" | "black" | "draw"
}

function groupGamesByDay(games: ProcessedGame[]) {
  const groups: Record<string, ProcessedGame[]> = {}

  // Group existing games
  games.forEach((game: ProcessedGame) => {
    if (!game.timestamp) return

    const dateKey = new Date(game.timestamp).toDateString()
    if (!groups[dateKey]) {
      groups[dateKey] = []
    }
    groups[dateKey].push(game)
  })

  // Add empty days for the last 7 days
  const now = new Date()
  for (let i = 0; i < 7; i++) {
    const date = new Date(now)
    date.setDate(now.getDate() - i)
    const dateKey = date.toDateString()

    if (!groups[dateKey]) {
      groups[dateKey] = []
    }
  }

  // Sort groups by date (newest first)
  const sortedGroups = Object.entries(groups).sort(
    ([dateA], [dateB]) => new Date(dateB).getTime() - new Date(dateA).getTime()
  )

  return sortedGroups
}

interface RelativeTimeProps {
  dateString: string
  fallback: string
}

function RelativeTime({ dateString, fallback }: RelativeTimeProps) {
  // If no valid dateString, just show fallback
  if (!dateString) {
    return <span>{fallback}</span>
  }

  const relativeTime = formatRelativeTime(dateString)

  return (
    <time dateTime={dateString} title={dateString}>
      {relativeTime}
    </time>
  )
}

export default function RecentGames({
  games,
  knownPlayers,
  highlightGroups,
}: RecentGamesProps) {
  // First filter and process games
  const processedGames = games
    .map((game: RecentGame) => {
      const playerOrder = determinePlayerOrder(
        game.white_player,
        game.black_player,
        game.white_known,
        game.black_known,
        knownPlayers,
        highlightGroups
      )

      // Skip games where neither player is highlighted
      if (!playerOrder) return null

      // Adjust the result based on player order
      const adjustedResult: "white" | "black" | "draw" =
        game.result === "white" && playerOrder.result === "black"
          ? "black"
          : game.result === "black" && playerOrder.result === "black"
          ? "white"
          : game.result

      return {
        ...game,
        playerOrder,
        adjustedResult,
      } as ProcessedGame
    })
    .filter((game): game is ProcessedGame => game !== null)

  // Helper to render highlighted inline player tag
  function InlinePlayerTag({ name, known }: { name: string; known: boolean }) {
    const player = known
      ? knownPlayers.find((p) =>
          p.hivegame_nicks.some((nick) => nick.replace(/^HG#/, "") === name)
        )
      : undefined
    const shouldHighlight = !!(
      player && player.groups.some((g) => highlightGroups.includes(g))
    )
    const displayName = player ? player.display_name || name : name

    return (
      <Link
        href={`https://hivegame.com/@/${name}`}
        target="_blank"
        rel="noopener noreferrer"
        className={cn(
          "text-gray-700 hover:text-blue-600",
          shouldHighlight ? "" : ""
        )}
        title={displayName}
      >
        <span
          className={cn(
            "px-1.5 py-0.5 rounded",
            shouldHighlight ? "bg-yellow-100" : ""
          )}
        >
          {displayName}
        </span>
      </Link>
    )
  }

  // Group games by day
  const groupedGames = groupGamesByDay(processedGames)

  return (
    <div className="w-full bg-white rounded-lg">
      <div className="space-y-6 max-w-5xl mx-auto pt-10">
        {groupedGames.map(([dateKey, dayGames]) => {
          const dayHeader =
            dayGames.length > 0
              ? formatDayHeader(dayGames[0].timestamp || dateKey)
              : formatDayHeader(dateKey)
          return (
            <div key={dateKey} className="border-gray-200 pb-6">
              <div className="flex items-center gap-3 mb-4">
                <h3 className="text-lg font-semibold text-gray-800">
                  {dayHeader}
                </h3>
                <span className="text-sm text-gray-600 bg-gray-100 px-2 py-1 rounded">
                  {dayGames.length === 0
                    ? "No games"
                    : `${dayGames.length} game${
                        dayGames.length === 1 ? "" : "s"
                      }`}
                </span>
              </div>

              {dayGames.length === 0 ? (
                <div className="text-center py-8 text-gray-500 bg-gray-50 rounded-lg border border-gray-200">
                  <p className="text-sm">No games played on this day</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table className="min-w-[700px] table-fixed">
                    <TableHeader>
                      <TableRow>
                        <TableHead className="bg-[#f8f9fa] border border-[#dee2e6] p-3 text-left font-bold w-1/4">
                          Event
                        </TableHead>
                        <TableHead className="bg-[#f8f9fa] border border-[#dee2e6] p-3 text-left font-bold">
                          Match
                        </TableHead>
                        <TableHead className="bg-[#f8f9fa] border border-[#dee2e6] p-3 text-center font-bold w-24">
                          Rated
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {dayGames.map((game: ProcessedGame) => (
                        <TableRow
                          key={game.game_id}
                          className="hover:bg-gray-50"
                        >
                          <TableCell className="border border-[#dee2e6] p-3">
                            <span
                              className={cn(
                                "text-sm",
                                game.event
                                  ? "text-purple-700 font-medium bg-purple-50 px-2 py-1 rounded"
                                  : "text-gray-400 italic"
                              )}
                            >
                              {game.event || "—"}
                            </span>
                          </TableCell>
                          <TableCell className="border border-[#dee2e6] p-3">
                            <div className="flex flex-col gap-1">
                              <div className="flex items-center gap-1 flex-wrap">
                                <InlinePlayerTag
                                  name={game.playerOrder.playerOne.name}
                                  known={game.playerOrder.playerOne.known}
                                />
                                <span className="text-gray-400">vs</span>
                                <InlinePlayerTag
                                  name={game.playerOrder.playerTwo.name}
                                  known={game.playerOrder.playerTwo.known}
                                />
                              </div>
                              <div
                                className={cn(
                                  "text-sm",
                                  getResultClass(game.adjustedResult)
                                )}
                              >
                                {getResultText(game.adjustedResult)}
                              </div>
                            </div>
                          </TableCell>
                          <TableCell className="border border-[#dee2e6] p-3 text-center">
                            <span
                              className={cn(
                                "px-2 py-1 rounded text-xs font-medium",
                                game.rated
                                  ? "bg-green-100 text-green-800"
                                  : "bg-gray-100 text-gray-800"
                              )}
                            >
                              {game.rated ? "Rated" : "Unrated"}
                            </span>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
