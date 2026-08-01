import type { ConnectionReport, Health, HistoryPageSize, Settings, Skin, Theme, Transcript } from './types'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options)
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(payload?.detail || `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const api = {
  health: () => request<Health>('/api/health'),
  connection: () => request<ConnectionReport>('/api/connection'),
  history: (archived = false, limit: HistoryPageSize = 25, offset = 0) =>
    request<{ items: Transcript[]; total: number; limit: number; offset: number }>(`/api/history?archived=${archived}&limit=${limit}&offset=${offset}`),
  settings: () => request<Settings>('/api/settings'),
  updateSettings: (patch: { theme?: Theme; skin?: Skin; https_only?: boolean; history_page_size?: HistoryPageSize }) =>
    request<Settings>('/api/settings', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    }),
  transcribe: (blob: Blob, durationMs: number) => {
    const body = new FormData()
    const extension = blob.type.includes('mp4') ? 'm4a' : blob.type.includes('ogg') ? 'ogg' : 'webm'
    body.append('audio', blob, `recording.${extension}`)
    body.append('duration_ms', String(durationMs))
    return request<{ transcript: Transcript }>('/api/transcribe', { method: 'POST', body })
  },
  deleteTranscript: (id: string) => request<{ deleted: boolean }>(`/api/history/${id}`, { method: 'DELETE' }),
  archiveTranscript: (id: string, archived: boolean) =>
    request<{ archived: boolean }>(`/api/history/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ archived }),
    }),
  archiveTranscripts: (ids: string[], archived: boolean) =>
    request<{ updated_ids: string[]; archived: boolean }>('/api/history/bulk', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids, archived }),
    }),
  deleteTranscripts: (ids: string[]) =>
    request<{ deleted_ids: string[] }>('/api/history/bulk', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids }),
    }),
  updateTranscriptText: (id: string, text: string) =>
    request<{ transcript: Transcript }>(`/api/history/${id}/text`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    }),
  clearHistory: () => request<{ deleted: number }>('/api/history', { method: 'DELETE' }),
}
