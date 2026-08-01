export type Theme = 'dark' | 'light' | 'system'
export type Skin = 'pickle' | 'graphite' | 'frost'
export interface Settings { theme: Theme; skin: Skin; https_only: boolean; history_page_size: HistoryPageSize }
export type HistoryPageSize = 10 | 25 | 50
export interface ConnectionReport {
  state: 'ready' | 'app-unreachable' | 'tailscale-unavailable' | 'tailscale-disconnected' | 'serve-unavailable' | 'serve-not-configured'
  private_https_url?: string
}
export type RecorderState = 'idle' | 'requesting' | 'recording' | 'paused' | 'uploading' | 'success' | 'error'

export interface Engine {
  id: string
  name: string
  available: boolean
  runnable: boolean
  detail: string
  model?: string
  informational: boolean
}

export interface Health {
  status: string
  ready: boolean
  message: string
  local_only: boolean
  preferred_engine: Engine | null
  engines: Engine[]
}

export interface Transcript {
  id: string
  text: string
  created_at: string
  duration_ms: number
  engine: string
  archived: boolean
}
