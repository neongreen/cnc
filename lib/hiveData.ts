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
