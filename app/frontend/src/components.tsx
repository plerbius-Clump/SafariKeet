import type { ConnectionReport, Health, HistoryPageSize, RecorderState, Skin, Theme, Transcript } from './types'

export function Mark() {
  return (
    <svg className="mark" viewBox="0 0 64 64" aria-hidden="true">
      <path d="M8 14c12 1 18 8 20 19 5-7 12-10 24-8-4 15-14 24-29 25-5 5-11 8-17 8 5-5 8-9 8-14C5 37 2 25 8 14Z" fill="currentColor" />
      <path d="M39 36v10m7-14v18m7-13v8" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
    </svg>
  )
}

function MicIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="9" y="3" width="6" height="12" rx="3" fill="currentColor" />
      <path d="M6 11a6 6 0 0 0 12 0M12 17v4M9 21h6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

function PauseIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="4" width="4.5" height="16" rx="2" fill="currentColor" /><rect x="13.5" y="4" width="4.5" height="16" rx="2" fill="currentColor" /></svg>
}

function CopyIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="11" height="11" rx="2.5" fill="none" stroke="currentColor" strokeWidth="1.8" /><path d="M16 8V6.5A2.5 2.5 0 0 0 13.5 4h-7A2.5 2.5 0 0 0 4 6.5v7A2.5 2.5 0 0 0 6.5 16H8" fill="none" stroke="currentColor" strokeWidth="1.8" /></svg>
}

function ArchiveIcon({ restore = false }: { restore?: boolean }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 8.5h14v10A1.5 1.5 0 0 1 17.5 20h-11A1.5 1.5 0 0 1 5 18.5v-10ZM4 4h16v4.5H4V4Z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      {restore ? <path d="m9 14 3-3 3 3M12 11v5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /> : <path d="M9 12h6" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />}
    </svg>
  )
}

function TrashIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4.5 7h15M9 7V4.5h6V7m3 0-.8 12H6.8L6 7m4 4v5m4-5v5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>
}

function EditIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 16.5-1 3.5 3.5-1L18 8.5 15.5 6 5 16.5ZM14 7.5l2.5 2.5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
}

export function SettingsIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Zm7.4 3.5 1.5-1.2-1.8-3.1-1.9.7a7.8 7.8 0 0 0-1.7-1L15.2 5h-3.6l-.4 2.2a7.8 7.8 0 0 0-1.8 1L7.5 7.5l-1.8 3.1L7.3 12a7.7 7.7 0 0 0 0 2l-1.6 1.3 1.8 3.1 2-.7c.5.4 1.1.7 1.7 1l.4 2.2h3.6l.4-2.2c.6-.2 1.2-.6 1.7-1l1.9.7 1.8-3.1-1.6-1.3a7.7 7.7 0 0 0 0-2Z" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
}

export function SecureConnectionNotice({ connection }: { connection: ConnectionReport | null }) {
  const url = connection?.state === 'ready' ? connection.private_https_url : undefined
  return (
    <aside className="secure-connection glass-panel" aria-label="Secure microphone connection">
      <div><strong>Microphone needs private HTTPS</strong><p>This HTTP page can show status, but browsers block its microphone.</p></div>
      {url ? <a className="action-button primary" href={url}>Open secure SafaraKeet</a> : <p className="connection-setup">On the Mac, run <code>./scripts/share.sh start</code>, then refresh.</p>}
    </aside>
  )
}

const stateLabel: Record<RecorderState, string> = {
  idle: 'Record',
  requesting: 'Allow mic',
  recording: 'Pause',
  paused: 'Paused',
  uploading: 'Finishing',
  success: 'New block',
  error: 'Try again',
}

export function RecorderControl({ state, onPrimary }: { state: RecorderState; onPrimary: () => void }) {
  const busy = state === 'requesting' || state === 'uploading'
  return (
    <div className="recorder-controls">
      <button className={`record-button state-${state}`} onClick={onPrimary} disabled={busy} aria-label={stateLabel[state]}>
        <span className="record-icon">{state === 'recording' ? <PauseIcon /> : <MicIcon />}</span>
        <span>{stateLabel[state]}</span>
      </button>
    </div>
  )
}

interface TranscriptResultProps {
  liveText: string
  state: RecorderState
  transcript: Transcript | null
  copied: boolean
  onCopyPartial: () => void
  onPause: () => void
  onCopy: () => void
  onArchive: () => void
  editing: boolean
  editDraft: string
  onBeginEdit: () => void
  onEditDraft: (value: string) => void
  onSaveEdit: () => void
  onCancelEdit: () => void
}

export function TranscriptResult({ liveText, state, transcript, copied, onCopyPartial, onPause, onCopy, onArchive, editing, editDraft, onBeginEdit, onEditDraft, onSaveEdit, onCancelEdit }: TranscriptResultProps) {
  const text = transcript?.text || liveText
  const pending = !transcript
  const finalizing = state === 'uploading'
  return (
    <section className={`result glass-panel ${pending ? 'is-live' : 'is-final'}`} aria-live="polite">
      {editing ? <textarea className="result-editor" value={editDraft} onChange={(event) => onEditDraft(event.target.value)} autoFocus aria-label="Edit transcript" /> : <p className={text ? '' : 'result-placeholder'}>{text || 'Your English transcript will appear here while you speak.'}</p>}
      <footer>
        <span className="result-meta">
          {editing ? 'Edit locally · select any text to copy' : pending ? (finalizing ? 'Finishing on this Mac…' : liveText ? 'Live · English' : 'Private · local') : formatDuration(transcript.duration_ms)}
        </span>
        <div className={`result-actions ${transcript && !editing ? 'final-actions' : ''}`}>
          {editing ? (
            <>
              <button className="action-button secondary" onClick={onCancelEdit}>Cancel</button>
              <button className="action-button primary" onClick={onSaveEdit} disabled={!editDraft.trim()}>Save &amp; exit</button>
            </>
          ) : pending ? (
            <>
              <button className="action-button secondary" onClick={onCopyPartial} disabled={!liveText || finalizing}><CopyIcon />{copied ? 'Copied' : 'Copy partial'}</button>
              <button className="action-button primary" onClick={onPause} disabled={!liveText || state !== 'recording'}><PauseIcon />Pause & save</button>
            </>
          ) : (
            <>
              <button className="action-button primary" onClick={onCopy}><CopyIcon />{copied ? 'Copied' : 'Copy + new'}</button>
              <button className="action-button secondary" onClick={onBeginEdit}><EditIcon />Edit</button>
              <button className="action-button secondary" onClick={onArchive}><ArchiveIcon />Archive</button>
            </>
          )}
        </div>
      </footer>
    </section>
  )
}

interface HistoryProps {
  items: Transcript[]
  view: 'active' | 'archived'
  onView: (view: 'active' | 'archived') => void
  onCopy: (item: Transcript) => void
  onArchive: (item: Transcript) => void
  onRestore: (item: Transcript) => void
  onDelete: (item: Transcript) => void
  selectionMode: boolean
  selectedIds: string[]
  total: number
  page: number
  pageSize: HistoryPageSize
  onSelectionMode: () => void
  onToggleSelection: (id: string) => void
  onSelectAll: () => void
  onBulkArchive: () => void
  onBulkDelete: () => void
  onPage: (page: number) => void
  onPageSize: (pageSize: HistoryPageSize) => void
}

export function History({ items, view, onView, onCopy, onArchive, onRestore, onDelete, selectionMode, selectedIds, total, page, pageSize, onSelectionMode, onToggleSelection, onSelectAll, onBulkArchive, onBulkDelete, onPage, onPageSize }: HistoryProps) {
  const selectedCount = selectedIds.length
  const pageCount = Math.max(1, Math.ceil(total / pageSize))
  return (
    <section className="history" aria-labelledby="history-title">
      <div className="section-heading"><h2 id="history-title">History</h2><button className="history-select-button" onClick={onSelectionMode}>{selectionMode ? 'Cancel' : 'Select'}</button></div>
      <div className="history-tabs glass-control" role="tablist" aria-label="Transcript history">
        <button role="tab" aria-selected={view === 'active'} className={view === 'active' ? 'selected' : ''} onClick={() => onView('active')}>Active</button>
        <button role="tab" aria-selected={view === 'archived'} className={view === 'archived' ? 'selected' : ''} onClick={() => onView('archived')}>Archived</button>
      </div>
      <div className="history-pagination" aria-label="History pagination">
        <label>Show <select value={pageSize} onChange={(event) => onPageSize(Number(event.target.value) as HistoryPageSize)} aria-label="History page size"><option value="10">10</option><option value="25">25</option><option value="50">50</option></select> per page</label>
        {total > pageSize ? <div className="page-controls"><button onClick={() => onPage(page - 1)} disabled={page === 0}>Previous</button><span>{page + 1} / {pageCount}</span><button onClick={() => onPage(page + 1)} disabled={page + 1 >= pageCount}>Next</button></div> : null}
      </div>
      {selectionMode ? <div className="bulk-toolbar glass-panel" aria-label="Bulk transcript actions"><span>{selectedCount} selected</span><button onClick={onSelectAll} disabled={!items.length || selectedCount === items.length}>Select all</button><button onClick={onBulkArchive} disabled={!selectedCount}>{view === 'archived' ? 'Restore' : 'Archive'}</button><button className="danger" onClick={onBulkDelete} disabled={!selectedCount}>Delete</button></div> : null}
      {items.length ? (
        <div className="history-list">
          {items.map((item) => (
            <HistoryRow
              key={item.id}
              item={item}
              archived={view === 'archived'}
              onCopy={() => onCopy(item)}
              onArchive={() => onArchive(item)}
              onRestore={() => onRestore(item)}
              onDelete={() => onDelete(item)}
              selecting={selectionMode}
              selected={selectedIds.includes(item.id)}
              onToggleSelection={() => onToggleSelection(item.id)}
            />
          ))}
        </div>
      ) : <p className="history-empty glass-panel">{view === 'active' ? 'Saved dictation blocks will appear here.' : 'Archived blocks stay recoverable here.'}</p>}
    </section>
  )
}

function HistoryRow({ item, archived, onCopy, onArchive, onRestore, onDelete, selecting, selected, onToggleSelection }: { item: Transcript; archived: boolean; onCopy: () => void; onArchive: () => void; onRestore: () => void; onDelete: () => void; selecting: boolean; selected: boolean; onToggleSelection: () => void }) {
  return (
    <article className={`history-row glass-panel ${selecting ? 'is-selecting' : ''} ${selected ? 'is-selected' : ''}`}>
      {selecting ? <label className="history-checkbox"><input type="checkbox" checked={selected} onChange={onToggleSelection} aria-label={`Select transcript: ${item.text}`} /><i aria-hidden="true" /></label> : null}
      <div className="history-copy"><p>{item.text}</p><span>{formatDuration(item.duration_ms)} · {formatDate(item.created_at)}</span></div>
      {!selecting ? <div className="history-actions">
        <button onClick={onCopy}><CopyIcon /><span>Copy</span></button>
        <button onClick={archived ? onRestore : onArchive}><ArchiveIcon restore={archived} /><span>{archived ? 'Restore' : 'Archive'}</span></button>
        <button className="danger" onClick={onDelete}><TrashIcon /><span>Delete</span></button>
      </div> : null}
    </article>
  )
}

interface SettingsSheetProps {
  open: boolean
  theme: Theme
  skin: Skin
  httpsOnly: boolean
  historyPageSize: HistoryPageSize
  health: Health | null
  onTheme: (theme: Theme) => void
  onSkin: (skin: Skin) => void
  onHttpsOnly: (value: boolean) => void
  onHistoryPageSize: (value: HistoryPageSize) => void
  onClose: () => void
}

export function SettingsSheet({ open, theme, skin, httpsOnly, historyPageSize, health, onTheme, onSkin, onHttpsOnly, onHistoryPageSize, onClose }: SettingsSheetProps) {
  if (!open) return null
  const selectedEngine = health?.preferred_engine
  const alternativeEngines = health?.engines.filter((engine) => engine.runnable && !engine.informational && engine.id !== selectedEngine?.id) || []
  return (
    <div className="sheet-layer" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="settings-sheet glass-panel" role="dialog" aria-modal="true" aria-labelledby="settings-title">
        <header><div><h2 id="settings-title">Settings</h2><p>Appearance and local engine status.</p></div><button className="close-button glass-control" onClick={onClose} aria-label="Close settings">×</button></header>
        <div className="setting-block"><h3>Theme</h3><div className="option-control glass-control">{(['dark', 'light', 'system'] as Theme[]).map((value) => <button key={value} className={theme === value ? 'selected' : ''} onClick={() => onTheme(value)}>{capitalize(value)}</button>)}</div></div>
        <div className="setting-block"><h3>Skin</h3><div className="option-control skin-control glass-control">{(['pickle', 'graphite', 'frost'] as Skin[]).map((value) => <button key={value} className={skin === value ? 'selected' : ''} onClick={() => onSkin(value)}><i className={`skin-swatch skin-${value}`} />{capitalize(value)}</button>)}</div></div>
        <div className="setting-block"><h3>Connection</h3><label className="toggle-row"><span><strong>Require HTTPS</strong><small>Opt in to blocking recording on HTTP connections.</small></span><input type="checkbox" checked={httpsOnly} onChange={(event) => onHttpsOnly(event.target.checked)} /><i aria-hidden="true" /></label><p className="connection-note">{!window.isSecureContext ? 'This page is using HTTP. SafaraKeet allows it, but common browsers block microphone access on remote HTTP addresses.' : 'For fewer microphone prompts, keep using this exact address and set Microphone to Allow in the browser’s website settings.'}</p></div>
        <div className="setting-block"><h3>History</h3><label className="history-setting">Blocks per page <select value={historyPageSize} onChange={(event) => onHistoryPageSize(Number(event.target.value) as HistoryPageSize)} aria-label="Blocks per history page"><option value="10">10</option><option value="25">25</option><option value="50">50</option></select></label></div>
        <div className="setting-block"><h3>Speech engine · Automatic</h3><div className="engine-card"><span className={`status-dot ${health?.ready ? 'ready' : ''}`} /><div><strong>{selectedEngine?.name || 'No engine ready'}</strong><p>{selectedEngine ? 'Selected automatically as the preferred runnable engine. Manual model and remote-server selection are not available yet.' : health?.message || 'Checking this Mac…'}</p>{alternativeEngines.length ? <p>Also ready: {alternativeEngines.map((engine) => engine.name).join(', ')}</p> : health ? <p>No other runnable engines detected.</p> : null}</div></div></div>
        <div className="privacy-note"><strong>On this Mac</strong><p>Audio streams to this Mac through your private connection. The Mac transcribes it locally and discards it. Saved text remains in local SQLite history until deleted.</p></div>
      </section>
    </div>
  )
}

export function formatDuration(ms: number) {
  const total = Math.floor(ms / 1000)
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

function formatDate(value: string) {
  const date = new Date(value)
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(date)
}

function capitalize(value: string) {
  return value[0].toUpperCase() + value.slice(1)
}
