import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useRecorder } from './useRecorder'
import type { Transcript } from './types'

class FakeSocket {
  static OPEN = 1
  static CLOSING = 2
  static latest: FakeSocket | null = null
  readyState = FakeSocket.OPEN
  binaryType = ''
  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null
  sent: unknown[] = []
  constructor() { FakeSocket.latest = this }
  send(value: unknown) { this.sent.push(value) }
  close() { this.readyState = 3 }
}

function RecorderHarness({ onComplete }: { onComplete: (value: Transcript) => void }) {
  const recorder = useRecorder(() => undefined, onComplete)
  return <button data-state={recorder.state} onClick={() => void recorder.start()}>Start</button>
}

describe('useRecorder app lifecycle', () => {
  afterEach(() => vi.restoreAllMocks())

  it('finalizes once when the app is hidden and does not restart on return', async () => {
    Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
    const stop = vi.fn()
    const disconnect = vi.fn()
    const processor = { connect: vi.fn(), disconnect, onaudioprocess: null }
    const context = {
      sampleRate: 48_000,
      resume: vi.fn().mockResolvedValue(undefined),
      createMediaStreamSource: vi.fn(() => ({ connect: vi.fn(), disconnect })),
      createScriptProcessor: vi.fn(() => processor),
      createGain: vi.fn(() => ({ gain: { value: 1 }, connect: vi.fn(), disconnect })),
      destination: {},
      close: vi.fn().mockResolvedValue(undefined),
    }
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] }) },
    })
    vi.stubGlobal('WebSocket', FakeSocket)
    Object.defineProperty(window, 'AudioContext', {
      configurable: true,
      value: class { constructor() { return context } },
    })
    let visibility: DocumentVisibilityState = 'visible'
    vi.spyOn(document, 'visibilityState', 'get').mockImplementation(() => visibility)

    const container = document.createElement('div')
    const root = createRoot(container)
    const onComplete = vi.fn()
    await act(async () => root.render(<RecorderHarness onComplete={onComplete} />))
    await act(async () => container.querySelector<HTMLButtonElement>('button')?.click())
    const socket = FakeSocket.latest
    if (!socket) throw new Error('Expected the recorder to open a socket.')
    await act(async () => socket.onopen?.())
    expect(container.querySelector('button')?.dataset.state).toBe('recording')

    visibility = 'hidden'
    act(() => document.dispatchEvent(new Event('visibilitychange')))
    act(() => window.dispatchEvent(new Event('pagehide')))
    expect(socket.sent.filter((value) => typeof value === 'string')).toHaveLength(1)
    expect(JSON.parse(String(socket.sent.at(-1)))).toMatchObject({ type: 'finalize' })
    expect(stop).toHaveBeenCalledOnce()
    expect(container.querySelector('button')?.dataset.state).toBe('uploading')

    visibility = 'visible'
    act(() => document.dispatchEvent(new Event('visibilitychange')))
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledOnce()

    const transcript: Transcript = { id: 'synthetic', text: 'Saved text.', created_at: '2026-01-01T00:00:00Z', duration_ms: 1000, engine: 'synthetic', archived: false }
    act(() => socket.onmessage?.({ data: JSON.stringify({ type: 'final', transcript }) }))
    expect(onComplete).toHaveBeenCalledWith(transcript)
    expect(container.querySelector('button')?.dataset.state).toBe('success')
    act(() => root.unmount())
  })
})
