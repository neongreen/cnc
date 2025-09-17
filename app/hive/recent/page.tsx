import { parse as parseToml } from "@ltd/j-toml"
import fs from "fs"
import Head from "next/head"
import Link from "next/link"
import path from "path"
import RecentGames from "../../../components/RecentGames"
import type { Config, GameStats, Player } from "../../../lib/hiveData"
import { extractGameIdFromUrl } from "../../../lib/hiveData"

type RawCacheGame = {
  game_id: string
  white_player: { username: string }
  black_player: { username: string }
  game_status:
    | { Finished: { Winner: "White" | "Black" } }
    | { Finished: "Draw" }
  rated: boolean
  created_at: string
  last_interaction?: string
}

type CacheFile = {
  players: Record<string, { last_fetch: string; games: RawCacheGame[] }>
}

function tagKnownPlayerId(id: string): string {
  return `player#${id}`
}

function tagHG(nick: string): string {
  return `HG#${nick.replace(/^HG#/, "")}`
}

function computeConfigAndKnownPlayers(tomlText: string): {
  config: Config
  knownPlayers: Array<{
    id: string
    display_name: string
    groups: string[]
    hivegame_nicks: string[]
    hivegame_nick: string
  }>
  nickToKnownId: Map<string, string>
} {
  const data: any = parseToml(tomlText)

  const settings = data.settings || {}
  const config: Config = {
    group_order: Array.isArray(settings.group_order)
      ? settings.group_order
      : [],
    highlight_games: Array.isArray(settings.highlight_games)
      ? settings.highlight_games
      : [],
  }

  const playersObj: Record<string, any> = data.players || {}
  const knownPlayers: Array<{
    id: string
    display_name: string
    groups: string[]
    hivegame_nicks: string[]
    hivegame_nick: string
  }> = []
  const nickToKnownId = new Map<string, string>()

  for (const [playerId, meta] of Object.entries(playersObj)) {
    const display_name = (meta as any).display_name as string
    const groups = ((meta as any).groups as string[]) || []
    const hivegame = ((meta as any).hivegame as string[]) || []
    const hivegame_current = ((meta as any).hivegame_current as string) || hivegame[0]

    const id = tagKnownPlayerId(playerId)
    const hivegame_nicks = hivegame.map((n) => tagHG(n))
    const hivegame_nick = tagHG(hivegame_current)

    for (const nick of hivegame) {
      nickToKnownId.set(nick.toLowerCase(), id)
    }

    knownPlayers.push({
      id,
      display_name,
      groups,
      hivegame_nicks,
      hivegame_nick,
    })
  }

  return { config, knownPlayers, nickToKnownId }
}

function loadAndDedupGames(cacheText: string): RawCacheGame[] {
  const parsed = JSON.parse(cacheText) as CacheFile
  const allGames: RawCacheGame[] = []
  for (const player of Object.values(parsed.players || {})) {
    if (!player || !Array.isArray(player.games)) continue
    allGames.push(...player.games)
  }

  const byId = new Map<string, RawCacheGame>()
  for (const g of allGames) {
    if (!byId.has(g.game_id)) byId.set(g.game_id, g)
  }
  return Array.from(byId.values())
}

function resultLabel(game: RawCacheGame): "white" | "black" | "draw" {
  const gs: any = game.game_status
  if (typeof gs?.Finished === "string" && gs.Finished === "Draw") return "draw"
  const winner = (gs?.Finished?.Winner as string) || ""
  return winner === "White" ? "white" : "black"
}

export default async function RecentPage() {
  const root = process.cwd()
  const tomlPath = path.join(root, "data", "hive.toml")
  const cachePath = path.join(root, "data", "hive_games_cache.json")

  const tomlText = fs.readFileSync(tomlPath, "utf8")
  const cacheText = fs.readFileSync(cachePath, "utf8")

  const { config, knownPlayers, nickToKnownId } = computeConfigAndKnownPlayers(tomlText)
  const games = loadAndDedupGames(cacheText)

  // Parse game metadata from TOML
  const parsedToml = parseToml(tomlText) as any
  const gameMetadata: Array<{ url: string; event: string }> = parsedToml.games || []

  // Create a map from game ID to event (only /game/{id} urls)
  const gameIdToEvent = new Map<string, string>()
  for (const m of gameMetadata) {
    const id = extractGameIdFromUrl(m.url)
    if (id && m.event) gameIdToEvent.set(id, m.event)
  }

  // Identify outsiders (only opponents of selected groups)
  const settingsAny: any = (parseToml(tomlText) as any)?.settings
  const fetchOutsiders: string[] = Array.isArray(settingsAny?.fetch_outsiders)
    ? settingsAny.fetch_outsiders
    : []
  const playerIdToGroups = new Map(
    knownPlayers.map((p) => [p.id, p.groups as string[]]),
  )

  const outsiders = new Set<string>()
  for (const g of games) {
    const white = g.white_player.username
    const black = g.black_player.username
    const whiteKnown = nickToKnownId.get(white.toLowerCase())
    const blackKnown = nickToKnownId.get(black.toLowerCase())

    if (whiteKnown && !blackKnown) {
      const topGroup = (playerIdToGroups.get(whiteKnown) || [])[0]
      if (fetchOutsiders.includes(topGroup)) outsiders.add(black)
    } else if (!whiteKnown && blackKnown) {
      const topGroup = (playerIdToGroups.get(blackKnown) || [])[0]
      if (fetchOutsiders.includes(topGroup)) outsiders.add(white)
    }
  }

  // Build players list
  const players: Player[] = []
  for (const kp of knownPlayers) {
    players.push({
      id: kp.id,
      display_name: kp.display_name,
      groups: kp.groups,
      hivegame_nick: kp.hivegame_nick,
      hivegame_nicks: kp.hivegame_nicks,
      is_known: true,
      total_games: 0, // fill next
    })
  }
  for (const nick of outsiders) {
    players.push({
      id: tagHG(nick),
      display_name: `@${nick.replace(/^HG#/, "")}`,
      groups: ["(outsider)"],
      hivegame_nick: tagHG(nick),
      hivegame_nicks: [tagHG(nick)],
      is_known: false,
      total_games: 0, // fill next
    })
  }

  // Build nick -> game_ids set for counting unique games
  const nickToGameIds = new Map<string, Set<string>>()
  for (const g of games) {
    const wid = g.white_player.username
    const bid = g.black_player.username
    if (!nickToGameIds.has(wid)) nickToGameIds.set(wid, new Set())
    if (!nickToGameIds.has(bid)) nickToGameIds.set(bid, new Set())
    nickToGameIds.get(wid)!.add(g.game_id)
    nickToGameIds.get(bid)!.add(g.game_id)
  }

  // Fill total_games
  for (const p of players) {
    if (p.is_known) {
      const uniq = new Set<string>()
      for (const tagged of p.hivegame_nicks) {
        const nick = tagged.replace(/^HG#/, "")
        const s = nickToGameIds.get(nick)
        if (s) { for (const gid of s) uniq.add(gid) }
      }
      p.total_games = uniq.size
    } else {
      const nick = p.hivegame_nick.replace(/^HG#/, "")
      p.total_games = nickToGameIds.get(nick)?.size || 0
    }
  }

  // Prepare recent games data
  const recentGames = games
    .map((g) => {
      const whiteNick = g.white_player.username
      const blackNick = g.black_player.username
      const whiteKnownId = nickToKnownId.get(whiteNick.toLowerCase())
      const blackKnownId = nickToKnownId.get(blackNick.toLowerCase())

      // Check if players belong to highlighted groups
      const whiteHighlighted = whiteKnownId
        ? (playerIdToGroups.get(whiteKnownId) || []).some((group) => config.highlight_games.includes(group))
        : false
      const blackHighlighted = blackKnownId
        ? (playerIdToGroups.get(blackKnownId) || []).some((group) => config.highlight_games.includes(group))
        : false

      // Only include games where at least one player is in a highlighted group
      if (!whiteHighlighted && !blackHighlighted) return null

      return {
        game_id: g.game_id,
        white_player: whiteNick,
        black_player: blackNick,
        white_known: whiteKnownId !== undefined,
        black_known: blackKnownId !== undefined,
        result: resultLabel(g),
        rated: g.rated,
        timestamp: g.last_interaction || g.created_at,
        event: gameIdToEvent.get(g.game_id) || null,
      }
    })
    .filter((g): g is NonNullable<typeof g> => g !== null)
    .sort((a, b) => {
      // Sort by timestamp (newest first)
      return Date.parse(b.timestamp) - Date.parse(a.timestamp)
    })

  return (
    <>
      <Head>
        <title>Recent Hive Games</title>
        <meta
          name="description"
          content="Recent Hive games with highlighted players"
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <main className="bg-background text-foreground">
        <div className="w-[100vw] m-0 bg-background text-foreground rounded-none shadow-none overflow-visible">
          <div className="p-5">
            <RecentGames
              games={recentGames}
              knownPlayers={players.filter((p) => p.is_known)}
              highlightGroups={config.highlight_games}
            />
          </div>
        </div>
      </main>
    </>
  )
}
