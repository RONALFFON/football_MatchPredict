export interface UserInfo {
  username: string
  email?: string
  user_type: 'free' | 'premium'
  daily_predictions_used: number
  total_predictions: number
  membership_expires?: string | null
}

export interface MatchInput {
  home_team: string
  away_team: string
  league_name?: string
  home_odds?: number | string
  draw_odds?: number | string
  away_odds?: number | string
  odds?: MatchOdds
}

export interface MatchOdds {
  hhad?: { h: number | string; d: number | string; a: number | string }
  home_odds?: number | string
  draw_odds?: number | string
  away_odds?: number | string
  goal_line?: string
}

export interface ClassicPrediction {
  home_team: string
  away_team: string
  probabilities: { home: number; draw: number; away: number }
  odds: { home: number; draw: number; away: number }
  recommendation: string
}

export interface AiPrediction {
  match_id: string
  home_team: string
  away_team: string
  league_name: string
  ai_analysis: string
  odds: { home: number; draw: number; away: number }
}

export interface LotteryMatch extends MatchInput {
  match_id: string
  match_time?: string
  match_date?: string
  match_num?: string
  status?: string
  source?: string
}

export interface PlMatch {
  match_uid: string
  round?: string
  home_team: string
  away_team: string
  utc_date?: string
  status: string
  home_score?: number | null
  away_score?: number | null
}

export interface Standing {
  team_name: string
  position: number
  played: number
  won: number
  drawn: number
  lost: number
  goals_for: number
  goals_against: number
  points: number
}

export interface AgentEvent {
  type: 'tool_call' | 'tool_result' | 'text_delta' | 'done' | 'error'
  tool?: string
  text?: string
  message?: string
  [key: string]: unknown
}
