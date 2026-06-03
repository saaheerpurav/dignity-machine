import { useState, useCallback } from 'react'
import type { AnalyzeResponse } from '@/types/api'

const MOCK: AnalyzeResponse = {
  answer: '',
  mission_id: 'mock_demo_abc123',
  mission: 'analyze_denial',
  writeback_enabled: false,
  write_counts: {},
  structured: {
    denial_summary:
      "SSA denied Maria Lopez's claim because the file does not yet prove fibromyalgia severity or work-related functional limits.",
    policy_citations: [
      {
        title: 'SSA POMS DI 24515.076 - Evaluation of Fibromyalgia',
        url: 'https://secure.ssa.gov/apps10/poms.nsf/lnx/0424515076',
        excerpt:
          'Fibromyalgia can be a medically determinable impairment when the record contains appropriate longitudinal medical evidence.',
      },
    ],
    medical_evidence: [
      {
        doc_id: 'doc_denial_letter_001',
        index: 'case_documents',
        excerpt:
          'The denial says the current evidence does not establish disabling functional limitations.',
        relevance: 'Core denial reason',
      },
    ],
    missing_evidence: [
      {
        item: 'Treating-source RFC statement',
        reason:
          'The file needs a clinician statement connecting symptoms to sitting, standing, lifting, attendance, and concentration limits.',
      },
    ],
    records_request_draft:
      'Dear Records Department,\n\nPlease provide complete rheumatology notes and any functional capacity documentation for Maria Lopez relevant to her disability appeal.',
    advocate_alert_draft:
      'Hi Elena, Dignity Machine found missing RFC and longitudinal treatment evidence for Maria Lopez. Please review the drafted records request before sending.',
    packet_summary:
      'The appeal packet should focus on missing functional-limit evidence, longitudinal rheumatology records, and SSA fibromyalgia policy.',
    next_actions: [
      'Request RFC statement from treating rheumatologist',
      'Collect missing follow-up records',
      'Have advocate review before sending anything',
    ],
  },
}

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

  const run = useCallback(async (mission: string, writeback: boolean) => {
    setLoading(true)
    setError(null)
    setData(null)

    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mission, writeback }),
      })

      if (!res.ok) {
        const text = await res.text()
        throw new Error(text || 'Request failed')
      }

      if (!res.body) {
        const json: AnalyzeResponse = await res.json()
        setData(json)
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let result: AnalyzeResponse | null = null

      while (true) {
        const { value, done } = await reader.read()
        buffer += decoder.decode(value, { stream: !done })

        const frames = buffer.split('\n\n')
        buffer = frames.pop() ?? ''

        for (const frame of frames) {
          const event = parseSseFrame(frame) as { type?: string; message?: string } | AnalyzeResponse | null
          if (!event) continue
          if ('type' in event && event.type === 'error') throw new Error(event.message || 'Agent failed')
          if ('type' in event && event.type === 'result') result = event as AnalyzeResponse
        }

        if (done) break
      }

      if (buffer.trim()) {
        const event = parseSseFrame(buffer) as { type?: string; message?: string } | AnalyzeResponse | null
        if (event && 'type' in event && event.type === 'error') throw new Error(event.message || 'Agent failed')
        if (event && 'type' in event && event.type === 'result') result = event as AnalyzeResponse
      }

      if (!result) throw new Error('Agent stream ended without a result')
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Agent request failed')
      setData({ ...MOCK, mission })
    } finally {
      setLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setData(null)
    setError(null)
  }, [])

  return { data, loading, error, run, reset }
}
