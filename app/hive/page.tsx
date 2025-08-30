import Head from "next/head"
import HiveTable from "../../components/HiveTable"
import Link from "next/link"

import fs from "fs"
import path from "path"
import { parse as parseToml } from "@ltd/j-toml"
import type { Config, GameStats, Player } from "../../lib/hiveData"

type RawCacheGame = {
  game_id: string
  white_player: { username: string }
  black_player: { username: string }
  game_status:
    | { Finished: { Winner: "White" | "Black" } }
    | { Finished: "Draw" }
  rated: boolean
  created_at: string
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
    const hivegame_current =
      ((meta as any).hivegame_current as string) || hivegame[0]

    const id = tagKnownPlayerId(playerId)
    const hivegame_nicks = hivegame.map((n) => tagHG(n))
    const hivegame_nick = tagHG(hivegame_current)

    for (const nick of hivegame) {
      nickToKnownId.set(nick, id)
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

export default async function Hive() {
  const root = process.cwd()
  const tomlPath = path.join(root, "data", "hive.toml")
  const cachePath = path.join(root, "data", "hive_games_cache.json")

  const tomlText = fs.readFileSync(tomlPath, "utf8")
  const cacheText = fs.readFileSync(cachePath, "utf8")

  const { config, knownPlayers, nickToKnownId } =
    computeConfigAndKnownPlayers(tomlText)
  const games = loadAndDedupGames(cacheText)

  // Identify outsiders (only opponents of selected groups)
  const settingsAny: any = (parseToml(tomlText) as any)?.settings
  const fetchOutsiders: string[] = Array.isArray(settingsAny?.fetch_outsiders)
    ? settingsAny.fetch_outsiders
    : []
  const playerIdToGroups = new Map(
    knownPlayers.map((p) => [p.id, p.groups as string[]])
  )

  const outsiders = new Set<string>()
  for (const g of games) {
    const white = g.white_player.username
    const black = g.black_player.username
    const whiteKnown = nickToKnownId.get(white)
    const blackKnown = nickToKnownId.get(black)

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
        if (s) for (const gid of s) uniq.add(gid)
      }
      p.total_games = uniq.size
    } else {
      const nick = p.hivegame_nick.replace(/^HG#/, "")
      p.total_games = nickToGameIds.get(nick)?.size || 0
    }
  }

  // Precompute canonical game ids (map to known or HG#)
  const canonGames = games
    .map((g) => {
      const whiteNick = g.white_player.username
      const blackNick = g.black_player.username
      const whiteKnown = nickToKnownId.get(whiteNick)
      const blackKnown = nickToKnownId.get(blackNick)
      const whiteId = whiteKnown ?? tagHG(whiteNick)
      const blackId = blackKnown ?? tagHG(blackNick)
      return {
        whiteId,
        blackId,
        rated: g.rated,
        result: resultLabel(g),
      }
    })
    // Only keep games where at least one side is a known player (matches previous logic)
    .filter(
      (cg) =>
        cg.whiteId.startsWith("player#") || cg.blackId.startsWith("player#")
    )

  // Aggregate pairwise stats
  const game_stats: GameStats[] = []
  const playerIds = players.map((p) => p.id)
  for (let i = 0; i < playerIds.length; i++) {
    for (let j = 0; j < playerIds.length; j++) {
      if (i === j) continue
      const rowId = playerIds[i]
      const colId = playerIds[j]

      const rated = { wins: 0, losses: 0, draws: 0 }
      const unrated = { wins: 0, losses: 0, draws: 0 }

      for (const g of canonGames) {
        if (
          (g.whiteId === rowId && g.blackId === colId) ||
          (g.whiteId === colId && g.blackId === rowId)
        ) {
          const bucket = g.rated ? rated : unrated
          if (g.result === "draw") bucket.draws += 1
          else if (
            (g.result === "white" && g.whiteId === rowId) ||
            (g.result === "black" && g.blackId === rowId)
          )
            bucket.wins += 1
          else bucket.losses += 1
        }
      }

      if (
        rated.wins + rated.losses + rated.draws > 0 ||
        unrated.wins + unrated.losses + unrated.draws > 0
      ) {
        game_stats.push({
          player1: rowId,
          player2: colId,
          rated_stats: rated,
          unrated_stats: unrated,
        })
      }
    }
  }

  return (
    <>
      <Head>
        <title>Hive games</title>
        <meta name="description" content="Interactive Hive games table" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <main>
        <div className="w-[100vw] m-0 bg-white rounded-none shadow-none overflow-visible">
          <div className="p-5">
            <div
              id="hive-table-root"
              className="overflow-x-auto border-2 border-[#e9ecef] rounded-lg bg-[#f8f9fa] p-5 max-w-6xl mx-auto"
            >
              <HiveTable
                config={config}
                game_stats={game_stats}
                players={players}
              />
            </div>
          </div>
        </div>
      </main>
    </>
  )
}
