import fs from "fs"
import Head from "next/head"
import React from "react"
import MaturityGraph from "../../components/MaturityGraph"
import MaturityTable from "../../components/MaturityTable"
import { generateMaturityData } from "../../lib/maturityLogic"

import "./styles.css"
import Image from "next/image"

export default async function Maturity() {
  const maturityCsv = fs.readFileSync("data/maturity.csv", "utf-8")
  const maturityToml = fs.readFileSync("data/maturity-players.toml", "utf-8")
  const data = generateMaturityData(maturityCsv, maturityToml)

  return (
    <>
      <Head>
        <title>Maturity ELO</title>
        <meta
          name="description"
          content="Interactive Maturity ELO table and match history"
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <main>
        <h1>Maturity ELO</h1>
        <p>
          Source on GitHub:
          <a
            href="https://github.com/neongreen/cnc"
            target="_blank"
            rel="noopener noreferrer"
          >
            neongreen/cnc
          </a>
        </p>

        <h2>Matches</h2>
        <p>
          Scores are given for <i>row player – column player</i>.
        </p>
        <p>Total players: {data.numParticipants}</p>
        <p>
          Completion rate: {data.matchesDone} / {data.totalPossiblePairings}{" "}
          <a href="https://en.wikipedia.org/wiki/Pear" className="pear-link">
            pairings
          </a>{" "}
          ({data.completionRate}% done)
        </p>

        <MaturityTable tableContent={data.tableContent} />

        <h2>Match outcomes graph</h2>
        <p>An arrow from A to B means A beat B in a match.</p>
        <p>The graph is sorted in topological order.</p>

        <MaturityGraph
          graphData={data.graphData}
          levelsData={data.levelsData}
          graphHeight={700}
        />

        <h2>Elos</h2>
        <p>
          Last updated: <strong>Jul 5, 2025</strong>.
        </p>
        <Image
          src="/static/elos.png"
          style={{ maxWidth: "100%", height: "auto" }}
          alt="ELO ratings"
        />
      </main>
    </>
  )
}
