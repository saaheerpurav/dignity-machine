import { useState, useCallback } from 'react'
import type { AgentEvent, AnalyzeResponse } from '@/types/api'

function parseSseFrame(frame: string): unknown | null {
  const dataLines = frame
    .split('\n')
    .filter(line => line.startsWith('data:'))
    .map(line => line.slice(5).trim())

  if (dataLines.length === 0) return null

  const payload = dataLines.join('\n')
  if (!payload || payload === '[DONE]') return null

  return JSON.parse(payload)
}

export function useAnalyze() {
  const [data, setData] = useState<AnalyzeResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [statusMessages, setStatusMessages] = useState<string[]>([])

  const run = useCallback(async (caseId: string, mission: string, writeback: boolean) => {
    setLoading(true)
    setError(null)
    setData(null)
    setEvents([])
    setStatusMessages([])

    const collectedEvents: AgentEvent[] = []

    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case_id: caseId, mission, writeback }),
      })

      if (!res.ok) {
        const text = await res.text()
        throw new Error(text || 'Request failed')
      }

      if (!res.body) {
        const json: AnalyzeResponse = await res.json()
        setData({ ...json, events: collectedEvents })
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let result: AnalyzeResponse | null = null

      const handleEvent = (event: { type?: string; message?: string; event?: AgentEvent } | AnalyzeResponse | null) => {
        if (!event) return
        if ('type' in event && event.type === 'error') throw new Error(event.message || 'Agent failed')
        if ('type' in event && event.type === 'status' && event.message) {
          setStatusMessages(prev => [...prev, event.message as string])
          return
        }
        if ('type' in event && event.type === 'agent_event' && event.event) {
          collectedEvents.push(event.event)
          setEvents([...collectedEvents])
          return
        }
        if ('type' in event && event.type === 'result') {
          result = { ...(event as AnalyzeResponse), events: [...collectedEvents] }
        }
      }

      while (true) {
        const { value, done } = await reader.read()
        buffer += decoder.decode(value, { stream: !done })

        const frames = buffer.split('\n\n')
        buffer = frames.pop() ?? ''

        for (const frame of frames) {
          handleEvent(parseSseFrame(frame) as { type?: string; message?: string; event?: AgentEvent } | AnalyzeResponse | null)
        }

        if (done) break
      }

      if (buffer.trim()) {
        handleEvent(parseSseFrame(buffer) as { type?: string; message?: string; event?: AgentEvent } | AnalyzeResponse | null)
      }

      if (!result) throw new Error('Agent stream ended without a result')
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Agent request failed')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setData(null)
    setError(null)
    setEvents([])
    setStatusMessages([])
  }, [])

  return { data, loading, error, events, statusMessages, run, reset }
}
