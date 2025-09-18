import Head from "next/head"
import RecentGames from "../../../components/RecentGames"
import { loadRecentHiveData } from "../../../lib/hiveRecent"
import { withBasePath } from "../../../lib/basePath"

export default function RecentPage() {
  const { config, knownPlayers, recentGames } = loadRecentHiveData()

  return (
    <>
      <Head>
        <title>Recent Hive Games</title>
        <meta
          name="description"
          content="Recent Hive games with highlighted players"
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link
          rel="alternate"
          type="application/atom+xml"
          href={withBasePath("/hive/recent/feed.xml")}
          title="Recent Hive Games"
        />
      </Head>
      <main className="bg-background text-foreground">
        <div className="w-[100vw] m-0 bg-background text-foreground rounded-none shadow-none overflow-visible">
          <div className="p-5">
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
