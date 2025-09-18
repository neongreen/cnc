import { Feed } from "feed"
import { loadRecentHiveData } from "../../../../lib/hiveRecent"
import { withBasePath } from "../../../../lib/basePath"

export const dynamic = "force-static"
export const runtime = "nodejs"

const FEED_ID = "tag:cnc,2024-01-01:recent-hive-games"
const FEED_TITLE = "Recent Hive Games"
const FEED_DESCRIPTION = "Highlighted recent Hive games involving CNC players"
const MAX_ENTRIES = 50

type GameResult = "white" | "black" | "draw"

function resultScore(result: GameResult): string {
  switch (result) {
    case "white":
      return "1-0"
    case "black":
      return "0-1"
    case "draw":
    default:
      return "½-½"
  }
}

function resultSummary(result: GameResult, white: string, black: string): string {
  switch (result) {
    case "white":
      return `${white} defeats ${black}`
    case "black":
      return `${black} defeats ${white}`
    default:
      return `${white} draws ${black}`
  }
}

function parseTimestamp(timestamp?: string): Date {
  if (!timestamp) return new Date()
  const parsed = Date.parse(timestamp)
  if (Number.isNaN(parsed)) return new Date()
  return new Date(parsed)
}

function getSiteOrigin(): string | undefined {
  const envOrigin = process.env.NEXT_PUBLIC_SITE_URL || process.env.SITE_URL
  if (envOrigin) {
    return envOrigin.replace(/\/$/, "")
  }
  return undefined
}

export function GET(): Response {
  const { recentGames } = loadRecentHiveData()
  const siteOrigin = getSiteOrigin()
  const feedPath = withBasePath("/hive/recent/feed.xml")
  const pagePath = withBasePath("/hive/recent/")

  const updatedDate = recentGames.length > 0
    ? parseTimestamp(recentGames[0].timestamp)
    : new Date()

  const feedUrl = siteOrigin ? `${siteOrigin}${feedPath}` : feedPath
  const pageUrl = siteOrigin ? `${siteOrigin}${pagePath}` : pagePath

  const feed = new Feed({
    id: FEED_ID,
    title: FEED_TITLE,
    description: FEED_DESCRIPTION,
    updated: updatedDate,
    link: pageUrl,
    feedLinks: { atom: feedUrl },
    author: { name: FEED_TITLE },
    copyright: FEED_TITLE,
  })

  recentGames.slice(0, MAX_ENTRIES).forEach((game) => {
    const gameUrl = `https://hivegame.com/game/${game.game_id}`
    const publishedDate = parseTimestamp(game.timestamp)
    const entryYear = publishedDate.getUTCFullYear()
    const entryId = `tag:hivegame.com,${entryYear}:${game.game_id}`
    const score = resultScore(game.result)

    const summaryText = `${resultSummary(
      game.result,
      game.white_player,
      game.black_player,
    )} (${score}). ${game.rated ? "Rated" : "Unrated"}${
      game.event ? ` — Event: ${game.event}` : ""
    }.`

    feed.addItem({
      id: entryId,
      title: `${game.white_player} vs ${game.black_player} (${score})`,
      link: gameUrl,
      date: publishedDate,
      description: summaryText,
      content: summaryText,
      author: [
        { name: game.white_player },
        { name: game.black_player },
      ],
    })
  })

  const atomFeed = feed.atom1()

  return new Response(atomFeed, {
    headers: {
      "Content-Type": "application/atom+xml; charset=utf-8",
      "Cache-Control": "public, max-age=300",
    },
  })
}
