import Head from "next/head"
import HiveTable from "../../components/HiveTable"
import "./styles.css"

import fs from "fs"
import { Config, GameStats, Player } from "../../lib/hiveData"

export default async function Hive() {
  const data = fs.readFileSync("build/data/hive-data.json", "utf8")
  const { config, game_stats, players } = JSON.parse(data) as {
    config: Config
    game_stats: GameStats[]
    players: Player[]
  }

  return (
    <>
      <Head>
        <title>Hive games</title>
        <meta name="description" content="Interactive Hive games table" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <main>
        <div className="container">
          <div className="header">
            <h1>🐝 Hive Games</h1>
            <p>Game statistics and match history</p>
          </div>

          <div className="stats">
            <span>
              Players:{" "}
              <span className="number" id="player-count">
                -
              </span>
            </span>
            <span>
              Total Games:{" "}
              <span className="number" id="total-games">
                -
              </span>
            </span>
            <span>
              Matchups:{" "}
              <span className="number" id="matchup-count">
                -
              </span>
            </span>
          </div>

          <div id="hive-table-root">
            <HiveTable
              config={config}
              game_stats={game_stats}
              players={players}
            />
          </div>
        </div>
      </main>
    </>
  )
}
