import React from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"
import { withBasePath } from "../../../lib/basePath"

(globalThis as any).React = React

vi.mock("../../../lib/hiveRecent", () => ({
  loadRecentHiveData: () => ({
    config: { group_order: [], highlight_games: [] },
    knownPlayers: [],
    players: [],
    recentGames: [],
  }),
}))

vi.mock("../../../components/RecentGames", () => ({
  __esModule: true,
  default: function MockRecentGames() {
    return <div data-testid="recent-games" />
  },
}))

import RecentPage, { metadata } from "./page"

type AlternateLinkDescriptor = { title?: string; url: string | URL }

type AlternateEntry =
  | string
  | URL
  | AlternateLinkDescriptor[]
  | null
  | undefined

function normalizeAlternate(entry: AlternateEntry): { title?: string; url: string }[] {
  if (!entry) return []
  if (Array.isArray(entry)) {
    return entry.map(({ title, url }) => ({
      title,
      url: url instanceof URL ? url.toString() : url,
    }))
  }
  return [
    {
      url: entry instanceof URL ? entry.toString() : entry,
    },
  ]
}

describe("Recent Hive feed discovery", () => {
  it("describes the feed via metadata alternates", () => {
    const types = metadata.alternates?.types ?? {}
    const expectedUrl = withBasePath("/hive/recent/feed.xml")

    const atomEntries = normalizeAlternate(types["application/atom+xml"])
    const rssEntries = normalizeAlternate(types["application/rss+xml"])

    const matcher = expect.arrayContaining([
      expect.objectContaining({
        url: expectedUrl,
        title: expect.stringMatching(/Recent Hive games feed/i),
      }),
    ])

    expect(atomEntries).toEqual(matcher)
    expect(rssEntries).toEqual(matcher)
  })

  it("renders a direct subscription link to the feed", () => {
    const html = renderToStaticMarkup(<RecentPage />)
    const expectedHref = withBasePath("/hive/recent/feed.xml")

    expect(html).toContain(`href="${expectedHref}"`)
    expect(html).toContain("Recent Hive games feed")
  })
})
