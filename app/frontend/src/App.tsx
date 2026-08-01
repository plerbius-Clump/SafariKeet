import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import { History, Mark, RecorderControl, SecureConnectionNotice, SettingsIcon, SettingsSheet, TranscriptResult, formatDuration } from './components'
import type { ConnectionReport, Health, HistoryPageSize, Skin, Theme, Transcript } from './types'
import { useRecorder } from './useRecorder'

async function copyText(text: string) {
  if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text)
  const field = document.createElement('textarea')
  field.value = text
  field.style.position = 'fixed'
  field.style.opacity = '0'
  document.body.appendChild(field)
  field.select()
  const copied = document.execCommand('copy')
  field.remove()
  if (!copied) throw new Error('Copy failed. Select the transcript and use Copy from Safari.')
}

function applyAppearance(theme: Theme, skin: Skin) {
  const resolved = theme === 'system' ? (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark') : theme
  document.documentElement.dataset.theme = resolved
  document.documentElement.dataset.skin = skin
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', resolved === 'dark' ? '#080a09' : '#e9eeeb')
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [connection, setConnection] = useState<ConnectionReport | null>(null)
  const [history, setHistory] = useState<Transcript[]>([])
  const [archivedHistory, setArchivedHistory] = useState<Transcript[]>([])
  const [historyView, setHistoryView] = useState<'active' | 'archived'>('active')
  const [historyPages, setHistoryPages] = useState({ active: 0, archived: 0 })
  const [historyTotals, setHistoryTotals] = useState({ active: 0, archived: 0 })
  const [historyPageSize, setHistoryPageSize] = useState<HistoryPageSize>(25)
  const [selectionMode, setSelectionMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const visibleHistory = historyView === 'active' ? history : archivedHistory
  const [current, setCurrent] = useState<Transcript | null>(null)
  const [liveText, setLiveText] = useState('')
  const [theme, setTheme] = useState<Theme>('dark')
  const [skin, setSkin] = useState<Skin>('graphite')
  const [httpsOnly, setHttpsOnly] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [editDraft, setEditDraft] = useState('')
  const [alert, setAlert] = useState<string | null>(null)

  const refreshHistory = useCallback(async (pageSize = historyPageSize, requestedPages = historyPages) => {
    const loadView = async (view: 'active' | 'archived') => {
      const archived = view === 'archived'
      let page = requestedPages[view]
      let response = await api.history(archived, pageSize, page * pageSize)
      if (response.total && response.offset >= response.total) {
        page = Math.floor((response.total - 1) / pageSize)
        response = await api.history(archived, pageSize, page * pageSize)
      }
      return { view, page, response }
    }
    const [active, archived] = await Promise.all([loadView('active'), loadView('archived')])
    setHistory(active.response.items)
    setArchivedHistory(archived.response.items)
    setHistoryTotals({ active: active.response.total, archived: archived.response.total })
    setHistoryPages({ active: active.page, archived: archived.page })
  }, [historyPageSize, historyPages])

  useEffect(() => {
    Promise.all([api.health(), api.connection(), api.settings()])
      .then(async ([healthData, connectionData, settings]) => {
        setHealth(healthData)
        setConnection(connectionData)
        setTheme(settings.theme || 'dark')
        setSkin(settings.skin || 'graphite')
        setHttpsOnly(settings.https_only === true)
        const pageSize = settings.history_page_size || 25
        setHistoryPageSize(pageSize)
        await refreshHistory(pageSize, { active: 0, archived: 0 })
      })
      .catch((error) => setAlert(error instanceof Error ? error.message : 'The Mac service is unavailable.'))
  // Initial data is loaded once; subsequent changes use the explicit refresh actions below.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    applyAppearance(theme, skin)
    if (theme !== 'system') return
    const media = matchMedia('(prefers-color-scheme: light)')
    const listener = () => applyAppearance('system', skin)
    media.addEventListener('change', listener)
    return () => media.removeEventListener('change', listener)
  }, [skin, theme])

  const completeRecording = useCallback((transcript: Transcript) => {
    setEditing(false)
    setEditDraft('')
    setCurrent(transcript)
    setHistoryPages((pages) => ({ ...pages, active: 0 }))
    setHistory((items) => [transcript, ...items].slice(0, historyPageSize))
    setHistoryTotals((totals) => ({ ...totals, active: totals.active + 1 }))
  }, [historyPageSize])

  const recorder = useRecorder(setLiveText, completeRecording, httpsOnly)
  const beginBlock = useCallback(() => {
    setEditing(false)
    setEditDraft('')
    setCurrent(null)
    setLiveText('')
    setAlert(null)
    void recorder.start()
  }, [recorder.start])
  const primaryAction = recorder.state === 'recording' ? recorder.pause : beginBlock

  const copy = useCallback(async (item: Transcript | { id: string; text: string }) => {
    try {
      await copyText(item.text)
      setCopiedId(item.id)
      window.setTimeout(() => setCopiedId(null), 1600)
    } catch (error) {
      setAlert(error instanceof Error ? error.message : 'Copy failed.')
    }
  }, [])

  const copyCurrentAndBegin = useCallback(async () => {
    if (!current) return
    try {
      await copyText(current.text)
      setCopiedId(current.id)
      window.setTimeout(() => {
        setCopiedId(null)
        beginBlock()
      }, 450)
    } catch (error) {
      setAlert(error instanceof Error ? error.message : 'Copy failed.')
    }
  }, [beginBlock, current])

  const beginEdit = useCallback(() => {
    if (!current) return
    setEditDraft(current.text)
    setEditing(true)
    setAlert(null)
  }, [current])

  const cancelEdit = useCallback(() => {
    setEditing(false)
    setEditDraft('')
  }, [])

  const saveEdit = useCallback(async () => {
    if (!current || !editDraft.trim()) return
    try {
      const { transcript } = await api.updateTranscriptText(current.id, editDraft)
      setCurrent(transcript)
      setHistory((items) => items.map((item) => item.id === transcript.id ? transcript : item))
      setArchivedHistory((items) => items.map((item) => item.id === transcript.id ? transcript : item))
      setEditing(false)
      setEditDraft('')
    } catch (error) {
      setAlert(error instanceof Error ? error.message : 'The edit could not be saved.')
    }
  }, [current, editDraft])

  const archive = useCallback(async (item: Transcript, archived: boolean) => {
    try {
      await api.archiveTranscript(item.id, archived)
      await refreshHistory()
    } catch (error) {
      setAlert(error instanceof Error ? error.message : 'Could not update this transcript.')
      return
    }
    setCurrent((value) => value?.id === item.id ? null : value)
    if (current?.id === item.id) setLiveText('')
  }, [current?.id, refreshHistory])

  const changeHistoryView = useCallback((view: 'active' | 'archived') => {
    setHistoryView(view)
    setSelectionMode(false)
    setSelectedIds([])
  }, [])

  const changeHistoryPage = useCallback((page: number) => {
    const pages = { ...historyPages, [historyView]: page }
    setHistoryPages(pages)
    setSelectionMode(false)
    setSelectedIds([])
    void refreshHistory(historyPageSize, pages).catch((error) => setAlert(error instanceof Error ? error.message : 'Could not load history.'))
  }, [historyPageSize, historyPages, historyView, refreshHistory])

  const toggleSelectionMode = useCallback(() => {
    setSelectionMode((active) => !active)
    setSelectedIds([])
  }, [])

  const toggleSelection = useCallback((id: string) => {
    setSelectedIds((ids) => ids.includes(id) ? ids.filter((value) => value !== id) : [...ids, id])
  }, [])

  const selectAll = useCallback(() => {
    setSelectedIds(visibleHistory.map((item) => item.id))
  }, [visibleHistory])

  const bulkArchive = useCallback(async (archived: boolean) => {
    if (!selectedIds.length) return
    const action = archived ? 'archive' : 'restore'
    if (!window.confirm(`${action[0].toUpperCase()}${action.slice(1)} ${selectedIds.length} transcript${selectedIds.length === 1 ? '' : 's'}?`)) return
    try {
      const { updated_ids } = await api.archiveTranscripts(selectedIds, archived)
      const updated = new Set(updated_ids)
      await refreshHistory()
      setCurrent((item) => item && updated.has(item.id) ? null : item)
      setSelectedIds([])
      setSelectionMode(false)
    } catch (error) {
      setAlert(error instanceof Error ? error.message : `Could not ${action} the selected transcripts.`)
    }
  }, [refreshHistory, selectedIds])

  const bulkDelete = useCallback(async () => {
    if (!selectedIds.length) return
    if (!window.confirm(`Delete ${selectedIds.length} transcript${selectedIds.length === 1 ? '' : 's'} permanently? This cannot be undone.`)) return
    try {
      const { deleted_ids } = await api.deleteTranscripts(selectedIds)
      const deleted = new Set(deleted_ids)
      await refreshHistory()
      setCurrent((item) => item && deleted.has(item.id) ? null : item)
      setSelectedIds([])
      setSelectionMode(false)
    } catch (error) {
      setAlert(error instanceof Error ? error.message : 'Could not delete the selected transcripts.')
    }
  }, [refreshHistory, selectedIds])

  const deleteItem = useCallback(async (item: Transcript) => {
    if (!window.confirm('Delete this transcript permanently?')) return
    await api.deleteTranscript(item.id)
    await refreshHistory()
    setCurrent((value) => value?.id === item.id ? null : value)
  }, [refreshHistory])

  const changeTheme = useCallback((value: Theme) => {
    setTheme(value)
    api.updateSettings({ theme: value }).catch(() => undefined)
  }, [])

  const changeSkin = useCallback((value: Skin) => {
    setSkin(value)
    api.updateSettings({ skin: value }).catch(() => undefined)
  }, [])

  const changeHttpsOnly = useCallback((value: boolean) => {
    setHttpsOnly(value)
    api.updateSettings({ https_only: value }).catch(() => undefined)
  }, [])

  const changeHistoryPageSize = useCallback((value: HistoryPageSize) => {
    const pages = { active: 0, archived: 0 }
    setHistoryPageSize(value)
    setHistoryPages(pages)
    setSelectionMode(false)
    setSelectedIds([])
    api.updateSettings({ history_page_size: value })
      .then(() => refreshHistory(value, pages))
      .catch((error) => setAlert(error instanceof Error ? error.message : 'Could not save history display settings.'))
  }, [refreshHistory])

  const loopbackHost = window.location.hostname === 'localhost'
  const insecureRemote = !window.isSecureContext && !loopbackHost

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand"><Mark /><span>SafariKeet</span></div>
        <button className="status-button glass-control" onClick={() => setSettingsOpen(true)}>
          <span className={`status-dot ${health?.ready ? 'ready' : ''}`} />
          <span><strong>{health?.ready ? 'Ready' : 'Check engine'}</strong><small>On this Mac</small></span>
        </button>
      </header>

      <main>
        {insecureRemote ? <SecureConnectionNotice connection={connection} /> : null}
        <section className="recording-stage" aria-labelledby="stage-title">
          <h1 id="stage-title" className="sr-only">Record local dictation</h1>
          <RecorderControl state={recorder.state} onPrimary={primaryAction} />
          <p className="stage-caption">
            <span className={recorder.state === 'recording' ? 'live-indicator' : ''} />
            {recorder.state === 'recording' ? `${recorder.liveStatus === 'ready' ? 'Listening' : recorder.liveStatus === 'warming' ? 'Starting local engine' : 'Connecting to local engine'} · ${formatDuration(recorder.elapsedMs)}` : recorder.state === 'uploading' ? 'Finishing this text block…' : recorder.state === 'requesting' ? 'Waiting for microphone permission…' : recorder.state === 'success' ? 'Block ready' : 'Tap to start recording'}
          </p>
        </section>

        {(recorder.error || alert) ? <div className="error-banner" role="alert">{recorder.error || alert}</div> : null}
        <TranscriptResult
          liveText={liveText}
          state={recorder.state}
          transcript={current}
          copied={copiedId === (current?.id || 'live')}
          onCopyPartial={() => void copy({ id: 'live', text: liveText })}
          onPause={recorder.pause}
          onCopy={copyCurrentAndBegin}
          onArchive={() => current && void archive(current, true)}
          editing={editing}
          editDraft={editDraft}
          onBeginEdit={beginEdit}
          onEditDraft={setEditDraft}
          onSaveEdit={() => void saveEdit()}
          onCancelEdit={cancelEdit}
        />
        <History
          items={visibleHistory}
          view={historyView}
          onView={changeHistoryView}
          onCopy={(item) => void copy(item)}
          onArchive={(item) => void archive(item, true)}
          onRestore={(item) => void archive(item, false)}
          onDelete={(item) => void deleteItem(item)}
          selectionMode={selectionMode}
          selectedIds={selectedIds}
          total={historyTotals[historyView]}
          page={historyPages[historyView]}
          pageSize={historyPageSize}
          onSelectionMode={toggleSelectionMode}
          onToggleSelection={toggleSelection}
          onSelectAll={selectAll}
          onBulkArchive={() => void bulkArchive(historyView === 'active')}
          onBulkDelete={() => void bulkDelete()}
          onPage={changeHistoryPage}
          onPageSize={changeHistoryPageSize}
        />
        <button className="settings-row glass-panel" onClick={() => setSettingsOpen(true)}>
          <SettingsIcon /><span>Settings</span><span aria-hidden="true">›</span>
        </button>
      </main>

      <SettingsSheet open={settingsOpen} theme={theme} skin={skin} httpsOnly={httpsOnly} historyPageSize={historyPageSize} health={health} onTheme={changeTheme} onSkin={changeSkin} onHttpsOnly={changeHttpsOnly} onHistoryPageSize={changeHistoryPageSize} onClose={() => setSettingsOpen(false)} />
    </div>
  )
}
