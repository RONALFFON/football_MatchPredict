export interface TeamsData {
  leagues: Record<string, string>
  teams: Record<string, string[]>
}

export interface UserInfo {
  username: string
  email?: string
  user_type: 'free' | 'premium'
  daily_predictions_used: number
  total_predictions: number
  membership_expires?: string | null
  membership_status: 'free' | 'active' | 'expired' | 'lifetime' | 'frozen' | 'revoked'
  daily_limit: number | null
  daily_used: number
  remaining: number | null
  quota_resets_at: string
  timezone: string
  role: 'user' | 'system_admin'
  is_admin: boolean
  payment_enabled: boolean
  rules: Record<string, string>
}

export interface MatchInput {
  match_id?: string
  home_team: string
  away_team: string
  league_name?: string
  home_odds?: number | string
  draw_odds?: number | string
  away_odds?: number | string
  odds?: MatchOdds
}

export interface MatchOdds {
  type?: 'had' | 'hhad'
  update_time?: string
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
  save_receipt?: string
  status: 'success' | 'error'
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

export interface SavedPrediction {
  prediction_id: string
  prediction_mode: string
  home_team: string
  away_team: string
  predicted_result: string
  prediction_confidence: number | null
  created_at: string
}
export interface AccountData {
  user: UserInfo
  saved_predictions: SavedPrediction[]
  has_more: boolean
}
export interface MembershipChange {
  action: 'extend' | 'freeze' | 'unfreeze' | 'revoke'
  plan?: 'monthly' | 'annual'
  reason: string
  request_id: string
}
export interface MembershipEvent {
  actor_user_id: number
  action: string
  plan?: string
  reason: string
  before_state: Record<string, unknown>
  after_state: Record<string, unknown>
  created_at: string
}

export interface AdminOverview {
  role: 'system_admin'
  database_configured: boolean
  ai_ready: boolean
  ai_mode: string
  ai_model: string
  business_timezone: string
  payment_enabled: boolean
  capabilities: string[]
}
