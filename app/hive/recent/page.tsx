import type { Metadata } from "next"
import RecentGames from "../../../components/RecentGames"
import { withBasePath } from "../../../lib/basePath"
import { loadRecentHiveData } from "../../../lib/hiveRecent"

const RECENT_HIVE_FEED_PATH = "/hive/recent/feed.xml"
const RECENT_HIVE_PAGE_PATH = "/hive/recent/"
const RECENT_HIVE_FEED_LABEL = "Recent Hive games feed"

const recentHiveFeedUrl = withBasePath(RECENT_HIVE_FEED_PATH)
const recentHivePageUrl = withBasePath(RECENT_HIVE_PAGE_PATH)

export const metadata: Metadata = {
  title: "Recent Hive Games",
  description: "Recent Hive games with highlighted players",
  alternates: {
    canonical: recentHivePageUrl,
    types: {
      "application/atom+xml": [
        { title: RECENT_HIVE_FEED_LABEL, url: recentHiveFeedUrl },
      ],
      "application/rss+xml": [
        { title: RECENT_HIVE_FEED_LABEL, url: recentHiveFeedUrl },
      ],
    },
  },
}

export default function RecentPage() {
  const { config, knownPlayers, recentGames } = loadRecentHiveData()

  return (
    <>
      <main className="bg-background text-foreground">
        <div className="w-[100vw] m-0 bg-background text-foreground rounded-none shadow-none overflow-visible">
          <div className="p-5 space-y-4">
            <p className="text-sm text-muted-foreground">
              Subscribe to the{" "}
              <a className="underline" href={recentHiveFeedUrl} rel="alternate">
                {RECENT_HIVE_FEED_LABEL}
              </a>
              .
            </p>
            <RecentGames
              games={recentGames}
              knownPlayers={knownPlayers}
              highlightGroups={config.highlight_games}
            />
          </div>
        </div>
      </main>
    </>
  )
}
