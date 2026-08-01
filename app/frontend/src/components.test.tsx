import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { describe, expect, it, vi } from 'vitest'
import { formatDuration, History, SecureConnectionNotice, SettingsSheet, TranscriptResult } from './components'

describe('formatDuration', () => {
  it('formats short and minute-long recordings', () => {
    expect(formatDuration(999)).toBe('0:00')
    expect(formatDuration(61_900)).toBe('1:01')
  })
})

describe('SettingsSheet', () => {
  it('renders HTTPS-only as an opt-in switch', () => {
    const container = document.createElement('div')
    const onHttpsOnly = vi.fn()
    const root = createRoot(container)

    act(() => root.render(
      <SettingsSheet
        open
        theme="dark"
        skin="graphite"
        httpsOnly={false}
        historyPageSize={25}
        health={null}
        onTheme={() => undefined}
        onSkin={() => undefined}
        onHttpsOnly={onHttpsOnly}
        onHistoryPageSize={() => undefined}
        onClose={() => undefined}
      />,
    ))

    const toggle = container.querySelector<HTMLInputElement>('input[type="checkbox"]')
    expect(toggle?.checked).toBe(false)
    act(() => toggle?.click())
    expect(onHttpsOnly).toHaveBeenCalledWith(true)
    act(() => root.unmount())
  })

  it('explains automatic engine selection and lists other runnable engines', () => {
    const container = document.createElement('div')
    const root = createRoot(container)
    const preferred = { id: 'preferred', name: 'Preferred engine', available: true, runnable: true, detail: 'Ready', informational: false }
    const alternative = { id: 'alternative', name: 'Alternative engine', available: true, runnable: true, detail: 'Ready', informational: false }
    const informational = { id: 'informational', name: 'Detected app', available: true, runnable: false, detail: 'Presence only', informational: true }

    act(() => root.render(
      <SettingsSheet
        open
        theme="dark"
        skin="graphite"
        httpsOnly={false}
        historyPageSize={25}
        health={{ status: 'ok', ready: true, message: 'Ready', local_only: true, preferred_engine: preferred, engines: [preferred, alternative, informational] }}
        onTheme={() => undefined}
        onSkin={() => undefined}
        onHttpsOnly={() => undefined}
        onHistoryPageSize={() => undefined}
        onClose={() => undefined}
      />,
    ))

    expect(container.textContent).toContain('Speech engine · Automatic')
    expect(container.textContent).toContain('Preferred engine')
    expect(container.textContent).toContain('Manual model and remote-server selection are not available yet.')
    expect(container.textContent).toContain('Also ready: Alternative engine')
    expect(container.textContent).not.toContain('Detected app')
    act(() => root.unmount())
  })
})

describe('SecureConnectionNotice', () => {
  it('links to a verified private HTTPS route', () => {
    const container = document.createElement('div')
    const root = createRoot(container)
    act(() => root.render(<SecureConnectionNotice connection={{ state: 'ready', private_https_url: 'https://<private-host>:8443/' }} />))

    const link = container.querySelector<HTMLAnchorElement>('a')
    expect(link?.textContent).toBe('Open secure SafaraKeet')
    expect(link?.getAttribute('href')).toBe('https://<private-host>:8443/')
    act(() => root.unmount())
  })
})

describe('TranscriptResult edit mode', () => {
  it('places Edit between copy and archive and renders an editable draft', () => {
    const container = document.createElement('div')
    const root = createRoot(container)
    const transcript = { id: 'synthetic', text: 'Original text.', created_at: '2026-01-01T00:00:00Z', duration_ms: 1000, engine: 'Test engine', archived: false }
    const common = { liveText: '', state: 'success' as const, transcript, copied: false, onCopyPartial: () => undefined, onPause: () => undefined, onCopy: () => undefined, onArchive: () => undefined, onBeginEdit: () => undefined, onEditDraft: () => undefined, onSaveEdit: () => undefined, onCancelEdit: () => undefined }

    act(() => root.render(<TranscriptResult {...common} editing={false} editDraft="" />))
    expect(Array.from(container.querySelectorAll('button')).map((button) => button.textContent)).toEqual(['Copy + new', 'Edit', 'Archive'])

    act(() => root.render(<TranscriptResult {...common} editing editDraft="Edited text." />))
    expect(container.querySelector<HTMLTextAreaElement>('textarea')?.value).toBe('Edited text.')
    expect(Array.from(container.querySelectorAll('button')).map((button) => button.textContent)).toEqual(['Cancel', 'Save & exit'])
    act(() => root.unmount())
  })
})

describe('TranscriptResult completed metadata', () => {
  it('shows only the recording duration, not the speech engine', () => {
    const container = document.createElement('div')
    const root = createRoot(container)
    const transcript = { id: 'synthetic', text: 'Original text.', created_at: '2026-01-01T00:00:00Z', duration_ms: 3_000, engine: 'Test engine', archived: false }
    const common = { liveText: '', state: 'success' as const, transcript, copied: false, onCopyPartial: () => undefined, onPause: () => undefined, onCopy: () => undefined, onArchive: () => undefined, onBeginEdit: () => undefined, onEditDraft: () => undefined, onSaveEdit: () => undefined, onCancelEdit: () => undefined }

    act(() => root.render(<TranscriptResult {...common} editing={false} editDraft="" />))
    expect(container.querySelector('.result-meta')?.textContent).toBe('0:03')
    expect(container.textContent).not.toContain('Test engine')
    act(() => root.unmount())
  })
})

describe('History selection mode', () => {
  it('offers select all and one bulk action bar for the current view', () => {
    const container = document.createElement('div')
    const root = createRoot(container)
    const item = { id: 'synthetic', text: 'Synthetic transcript.', created_at: '2026-01-01T00:00:00Z', duration_ms: 1000, engine: 'Test engine', archived: false }
    const onToggleSelection = vi.fn()
    act(() => root.render(
      <History
        items={[item]}
        view="active"
        onView={() => undefined}
        onCopy={() => undefined}
        onArchive={() => undefined}
        onRestore={() => undefined}
        onDelete={() => undefined}
        selectionMode
        selectedIds={[]}
        total={1}
        page={0}
        pageSize={25}
        onSelectionMode={() => undefined}
        onToggleSelection={onToggleSelection}
        onSelectAll={() => undefined}
        onBulkArchive={() => undefined}
        onBulkDelete={() => undefined}
        onPage={() => undefined}
        onPageSize={() => undefined}
      />,
    ))

    expect(container.textContent).toContain('0 selected')
    expect(container.textContent).toContain('Select all')
    expect(container.textContent).toContain('Archive')
    expect(container.textContent).toContain('Delete')
    const checkbox = container.querySelector<HTMLInputElement>('input[type="checkbox"]')
    act(() => checkbox?.click())
    expect(onToggleSelection).toHaveBeenCalledWith('synthetic')
    act(() => root.unmount())
  })
})

describe('History pagination', () => {
  it('offers a persistent-size control and changes pages without mixing views', () => {
    const container = document.createElement('div')
    const root = createRoot(container)
    const onPage = vi.fn()
    const onPageSize = vi.fn()
    const item = { id: 'synthetic', text: 'Synthetic transcript.', created_at: '2026-01-01T00:00:00Z', duration_ms: 1000, engine: 'Test engine', archived: false }
    act(() => root.render(<History items={[item]} view="archived" onView={() => undefined} onCopy={() => undefined} onArchive={() => undefined} onRestore={() => undefined} onDelete={() => undefined} selectionMode={false} selectedIds={[]} total={26} page={1} pageSize={25} onSelectionMode={() => undefined} onToggleSelection={() => undefined} onSelectAll={() => undefined} onBulkArchive={() => undefined} onBulkDelete={() => undefined} onPage={onPage} onPageSize={onPageSize} />))

    expect(container.textContent).toContain('2 / 2')
    const pageSize = container.querySelector<HTMLSelectElement>('select[aria-label="History page size"]')
    act(() => {
      if (pageSize) {
        pageSize.value = '10'
        pageSize.dispatchEvent(new Event('change', { bubbles: true }))
      }
    })
    expect(onPageSize).toHaveBeenCalledWith(10)
    const previous = Array.from(container.querySelectorAll('button')).find((button) => button.textContent === 'Previous')
    act(() => previous?.click())
    expect(onPage).toHaveBeenCalledWith(0)
    act(() => root.unmount())
  })
})
