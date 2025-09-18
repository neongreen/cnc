import { parse as parseToml } from "@ltd/j-toml"
import fs from "fs"
import path from "path"
import type { Config, Player } from "./hiveData"
import { extractGameIdFromUrl } from "./hiveData"

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

type KnownPlayerMeta = {
  id: string
  display_name: string
  groups: string[]
  hivegame_nicks: string[]
  hivegame_nick: string
}

export type RecentHiveGame = {
  game_id: string
  white_player: string
  black_player: string
  white_known: boolean
  black_known: boolean
  result: "white" | "black" | "draw"
  rated: boolean
  timestamp: string
  event: string | null
}

export type HiveRecentData = {
  config: Config
  players: Player[]
  knownPlayers: Player[]
  recentGames: RecentHiveGame[]
}

function tagKnownPlayerId(id: string): string {
  return `player#${id}`
}

function tagHG(nick: string): string {
  return `HG#${nick.replace(/^HG#/, "")}`
}

function computeConfigAndKnownPlayers(tomlText: string): {
  config: Config
  knownPlayers: KnownPlayerMeta[]
  nickToKnownId: Map<string, string>
} {
  const data: any = parseToml(tomlText)

  const settings = data.settings || {}
  const config: Config = {
    group_order: Array.isArray(settings.group_order) ? settings.group_order : [],
    highlight_games: Array.isArray(settings.highlight_games)
      ? settings.highlight_games
      : [],
  }

  const playersObj: Record<string, any> = data.players || {}
  const knownPlayers: KnownPlayerMeta[] = []
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

function buildPlayerList(
  knownMeta: KnownPlayerMeta[],
  outsiders: Set<string>,
): Player[] {
  const players: Player[] = []
  for (const kp of knownMeta) {
    players.push({
      id: kp.id,
      display_name: kp.display_name,
      groups: kp.groups,
      hivegame_nick: kp.hivegame_nick,
      hivegame_nicks: kp.hivegame_nicks,
      is_known: true,
      total_games: 0,
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
      total_games: 0,
    })
  }
  return players
}

function countGamesForPlayers(players: Player[], games: RawCacheGame[]) {
  const nickToGameIds = new Map<string, Set<string>>()
  for (const g of games) {
    const wid = g.white_player.username
    const bid = g.black_player.username
    if (!nickToGameIds.has(wid)) nickToGameIds.set(wid, new Set())
    if (!nickToGameIds.has(bid)) nickToGameIds.set(bid, new Set())
    nickToGameIds.get(wid)!.add(g.game_id)
    nickToGameIds.get(bid)!.add(g.game_id)
  }

  for (const p of players) {
    if (p.is_known) {
      const uniq = new Set<string>()
      for (const tagged of p.hivegame_nicks) {
        const nick = tagged.replace(/^HG#/, "")
        const s = nickToGameIds.get(nick)
        if (s) {
          for (const gid of s) uniq.add(gid)
        }
      }
      p.total_games = uniq.size
    } else {
      const nick = p.hivegame_nick.replace(/^HG#/, "")
      p.total_games = nickToGameIds.get(nick)?.size || 0
    }
  }
}

function sortByTimestampDesc(a: RecentHiveGame, b: RecentHiveGame): number {
  const parse = (value?: string) => {
    if (!value) return 0
    const t = Date.parse(value)
    return Number.isNaN(t) ? 0 : t
  }
  return parse(b.timestamp) - parse(a.timestamp)
}

export function loadRecentHiveData(): HiveRecentData {
  const root = process.cwd()
  const tomlPath = path.join(root, "data", "hive.toml")
  const cachePath = path.join(root, "data", "hive_games_cache.json")

  const tomlText = fs.readFileSync(tomlPath, "utf8")
  const cacheText = fs.readFileSync(cachePath, "utf8")

  const { config, knownPlayers: knownMeta, nickToKnownId } =
    computeConfigAndKnownPlayers(tomlText)
  const games = loadAndDedupGames(cacheText)

  const parsedToml = parseToml(tomlText) as any
  const gameMetadata: Array<{ url: string; event: string }> = parsedToml.games || []

  const gameIdToEvent = new Map<string, string>()
  for (const m of gameMetadata) {
    const id = extractGameIdFromUrl(m.url)
    if (id && m.event) gameIdToEvent.set(id, m.event)
  }

  const settingsAny: any = parsedToml?.settings
  const fetchOutsiders: string[] = Array.isArray(settingsAny?.fetch_outsiders)
    ? settingsAny.fetch_outsiders
    : []
  const playerIdToGroups = new Map(
    knownMeta.map((p) => [p.id, p.groups as string[]]),
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

  const players = buildPlayerList(knownMeta, outsiders)
  countGamesForPlayers(players, games)

  const knownPlayers = players.filter((p) => p.is_known)

  const recentGames = games
    .map((g) => {
      const whiteNick = g.white_player.username
      const blackNick = g.black_player.username
      const whiteKnownId = nickToKnownId.get(whiteNick.toLowerCase())
      const blackKnownId = nickToKnownId.get(blackNick.toLowerCase())

      const whiteHighlighted = whiteKnownId
        ? (playerIdToGroups.get(whiteKnownId) || []).some((group) =>
            config.highlight_games.includes(group),
          )
        : false
      const blackHighlighted = blackKnownId
        ? (playerIdToGroups.get(blackKnownId) || []).some((group) =>
            config.highlight_games.includes(group),
          )
        : false

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
    .filter((g): g is RecentHiveGame => g !== null)
    .sort(sortByTimestampDesc)

  return {
    config,
    players,
    knownPlayers,
    recentGames,
  }
}
