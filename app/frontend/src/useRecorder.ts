import { useCallback, useEffect, useRef, useState } from 'react'
import type { RecorderState, Transcript } from './types'

const TARGET_SAMPLE_RATE = 16_000
const SEND_CHUNK_SAMPLES = TARGET_SAMPLE_RATE

type LiveStatus = 'connecting' | 'warming' | 'ready'

interface LiveMessage {
  type: 'status' | 'partial' | 'final' | 'error'
  status?: LiveStatus
  text?: string
  transcript?: Transcript
  message?: string
}

function mediaError(error: unknown): string {
  if (!(error instanceof DOMException)) return 'The microphone could not be started.'
  if (error.name === 'NotAllowedError') return 'Microphone access is off. Allow it in this browser’s site settings, then try again.'
  if (error.name === 'NotFoundError') return 'No microphone is available to this browser.'
  if (error.name === 'NotReadableError') return 'The microphone is busy in another app. Close it there, then try again.'
  if (error.name === 'SecurityError') return 'The browser blocked microphone access because this page is not a secure context.'
  return `Microphone error: ${error.message || error.name}`
}

function downsample(input: Float32Array<ArrayBufferLike>, sourceRate: number): Float32Array<ArrayBuffer> {
  if (sourceRate === TARGET_SAMPLE_RATE) return new Float32Array(input)
  const ratio = sourceRate / TARGET_SAMPLE_RATE
  const output = new Float32Array(Math.floor(input.length / ratio))
  for (let index = 0; index < output.length; index += 1) {
    const start = Math.floor(index * ratio)
    const end = Math.max(start + 1, Math.floor((index + 1) * ratio))
    let total = 0
    for (let sourceIndex = start; sourceIndex < end && sourceIndex < input.length; sourceIndex += 1) {
      total += input[sourceIndex]
    }
    output[index] = total / (end - start)
  }
  return output
}

function appendSamples(
  current: Float32Array<ArrayBufferLike>,
  next: Float32Array<ArrayBufferLike>,
): Float32Array<ArrayBuffer> {
  const combined = new Float32Array(current.length + next.length)
  combined.set(current)
  combined.set(next, current.length)
  return combined
}

export function useRecorder(
  onPartial: (text: string) => void,
  onComplete: (transcript: Transcript) => void,
  httpsOnly = false,
) {
  const [state, setState] = useState<RecorderState>('idle')
  const [elapsedMs, setElapsedMs] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [liveStatus, setLiveStatus] = useState<LiveStatus>('connecting')
  const socketRef = useRef<WebSocket | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const contextRef = useRef<AudioContext | null>(null)
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const muteRef = useRef<GainNode | null>(null)
  const pendingRef = useRef(new Float32Array())
  const startedAtRef = useRef(0)
  const sessionActiveRef = useRef(false)
  const completedRef = useRef(false)

  const releaseCapture = useCallback(() => {
    if (processorRef.current) processorRef.current.onaudioprocess = null
    processorRef.current?.disconnect()
    sourceRef.current?.disconnect()
    muteRef.current?.disconnect()
    void contextRef.current?.close()
    streamRef.current?.getTracks().forEach((track) => track.stop())
    processorRef.current = null
    sourceRef.current = null
    muteRef.current = null
    contextRef.current = null
    streamRef.current = null
  }, [])

  const release = useCallback(() => {
    releaseCapture()
    const socket = socketRef.current
    socketRef.current = null
    if (socket && socket.readyState < WebSocket.CLOSING) socket.close()
    sessionActiveRef.current = false
    pendingRef.current = new Float32Array()
  }, [releaseCapture])

  useEffect(() => release, [release])

  useEffect(() => {
    if (state !== 'recording') return
    const update = () => setElapsedMs(performance.now() - startedAtRef.current)
    update()
    const timer = window.setInterval(update, 100)
    return () => window.clearInterval(timer)
  }, [state])

  const flush = useCallback((force = false) => {
    const socket = socketRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN) return
    while (pendingRef.current.length >= SEND_CHUNK_SAMPLES) {
      socket.send(pendingRef.current.slice(0, SEND_CHUNK_SAMPLES).buffer)
      pendingRef.current = pendingRef.current.slice(SEND_CHUNK_SAMPLES)
    }
    if (force && pendingRef.current.length) {
      socket.send(pendingRef.current.buffer)
      pendingRef.current = new Float32Array()
    }
  }, [])

  const start = useCallback(async () => {
    release()
    setError(null)
    setElapsedMs(0)
    setLiveStatus('connecting')
    onPartial('')
    if (httpsOnly && window.location.protocol !== 'https:') {
      setState('error')
      setError('HTTPS-only recording is enabled in Settings.')
      return
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setState('error')
      setError('This browser does not expose microphone access to a remote HTTP address. Use HTTPS, or open the app on this Mac through localhost. This browser security rule cannot be overridden by SafaraKeet.')
      return
    }
    const AudioContextClass = window.AudioContext || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!AudioContextClass) {
      setState('error')
      setError('This browser does not support live microphone audio.')
      return
    }

    setState('requesting')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      })
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const socket = new WebSocket(`${protocol}//${window.location.host}/api/live`)
      socket.binaryType = 'arraybuffer'
      socketRef.current = socket
      streamRef.current = stream
      sessionActiveRef.current = true
      completedRef.current = false

      socket.onopen = async () => {
        if (socketRef.current !== socket) {
          socket.close()
          return
        }
        try {
          const context = new AudioContextClass()
          await context.resume()
          const source = context.createMediaStreamSource(stream)
          const processor = context.createScriptProcessor(4096, 1, 1)
          const mute = context.createGain()
          mute.gain.value = 0
          processor.onaudioprocess = (event) => {
            const samples = downsample(event.inputBuffer.getChannelData(0), context.sampleRate)
            pendingRef.current = appendSamples(pendingRef.current, samples)
            flush()
          }
          source.connect(processor)
          processor.connect(mute)
          mute.connect(context.destination)
          contextRef.current = context
          sourceRef.current = source
          processorRef.current = processor
          muteRef.current = mute
          startedAtRef.current = performance.now()
          setState('recording')
        } catch (caught) {
          release()
          setState('error')
          setError(mediaError(caught))
        }
      }

      socket.onmessage = (event) => {
        if (socketRef.current !== socket) return
        const message = JSON.parse(String(event.data)) as LiveMessage
        if (message.type === 'status' && message.status) setLiveStatus(message.status)
        if (message.type === 'partial') onPartial(message.text || '')
        if (message.type === 'error') {
          release()
          setState('error')
          setError(message.message || 'Live transcription failed.')
        }
        if (message.type === 'final' && message.transcript) {
          completedRef.current = true
          onPartial(message.transcript.text)
          onComplete(message.transcript)
          release()
          setState('success')
        }
      }

      socket.onerror = () => {
        if (socketRef.current !== socket) return
        if (!completedRef.current) setError('The live connection to this Mac was interrupted.')
      }
      socket.onclose = () => {
        if (socketRef.current !== socket) return
        if (sessionActiveRef.current && !completedRef.current) {
          release()
          setState('error')
          setError((current) => current || 'The live connection closed before this block was saved.')
        }
      }
    } catch (caught) {
      release()
      setState('error')
      setError(mediaError(caught))
    }
  }, [flush, httpsOnly, onComplete, onPartial, release])

  const pause = useCallback(() => {
    const socket = socketRef.current
    if (!sessionActiveRef.current || !socket || socket.readyState !== WebSocket.OPEN) return
    const duration = Math.max(0, Math.round(performance.now() - startedAtRef.current))
    setElapsedMs(duration)
    flush(true)
    releaseCapture()
    setState('uploading')
    socket.send(JSON.stringify({ type: 'finalize', duration_ms: duration }))
  }, [flush, releaseCapture])

  const reset = useCallback(() => {
    release()
    setState('idle')
    setError(null)
    setElapsedMs(0)
    setLiveStatus('connecting')
    onPartial('')
  }, [onPartial, release])

  return { state, elapsedMs, error, liveStatus, start, pause, reset }
}
