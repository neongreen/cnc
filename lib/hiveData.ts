export type Player = {
  id: string
  display_name: string
  groups: string[]
  hivegame_nick: string
  hivegame_nicks: string[]
  is_known: boolean
  total_games: number
}

export type GameStats = {
  player1: string
  player2: string
  rated_stats: {
    wins: number
    losses: number
    draws: number
  }
  unrated_stats: {
    wins: number
    losses: number
    draws: number
  }
}

export type Config = {
  group_order: string[]
  highlight_games: string[]
}

/**
 * Extracts game ID from a Hive game URL in the format https://hivegame.com/game/{id}
 *
 * @param url - The Hive game URL (e.g., "https://hivegame.com/game/ABC123")
 * @returns The game ID or null if not found or invalid
 *
 * @example
 * ```typescript
 * extractGameIdFromUrl("https://hivegame.com/game/Ldb_urJrLZ1-") // "Ldb_urJrLZ1-"
 * extractGameIdFromUrl("https://example.com/game/whatever") // null
 * extractGameIdFromUrl("https://hivegame.com/_MDDf492DNYt") // null
 * ```
 */
export function extractGameIdFromUrl(url: string): string | null {
  if (!url || typeof url !== "string") {
    return null
  }

  try {
    const parsed = new URL(url)
    if (parsed.hostname !== "hivegame.com") return null
    const segments = parsed.pathname.split("/").filter(Boolean)
    if (segments.length !== 2) return null
    if (segments[0] !== "game") return null
    return segments[1] || null
  } catch {
    return null
  }
}

// In-source tests (Vitest). See: https://vitest.dev/guide/in-source.html
if (import.meta.vitest) {
  const { it, expect, describe } = import.meta.vitest

  describe("extractGameIdFromUrl", () => {
    it("matches JSDoc examples", () => {
      expect(
        extractGameIdFromUrl("https://hivegame.com/game/Ldb_urJrLZ1-")
      ).toBe("Ldb_urJrLZ1-")
      expect(
        extractGameIdFromUrl("https://example.com/game/whatever")
      ).toBeNull()
      expect(
        extractGameIdFromUrl("https://hivegame.com/_MDDf492DNYt")
      ).toBeNull()
    })

    it("handles valid and invalid formats", () => {
      expect(
        extractGameIdFromUrl("https://hivegame.com/game/6T9zVqpzgdiH")
      ).toBe("6T9zVqpzgdiH")
      expect(extractGameIdFromUrl("https://hivegame.com/ABC123")).toBeNull()
      expect(extractGameIdFromUrl("https://hivegame.com/game/")).toBeNull()
      expect(extractGameIdFromUrl("https://hivegame.com/game/simple")).toBe(
        "simple"
      )
      expect(extractGameIdFromUrl("")).toBeNull()
      expect(extractGameIdFromUrl("not-a-url")).toBeNull()
    })
  })
}
