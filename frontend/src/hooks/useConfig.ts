import { useState, useEffect } from 'react'
import type { ConfigResponse } from '@/types/api'

const FALLBACK: ConfigResponse = {
  gcp_project: 'integral-tensor-497618-a8',
  writeback_default: false,
  missions: [
    { id: 'analyze_denial', label: 'Explain the denial', description: 'Explain why this denial happened.' },
    { id: 'find_missing_evidence', label: 'Find missing proof', description: 'Find proof this case still needs.' },
    { id: 'draft_records_request', label: 'Draft doctor records request', description: 'Ask doctors for the missing records.' },
    { id: 'prepare_review_summary', label: 'Create review summary', description: 'Create a summary for a human helper.' },
  ],
}

export function useConfig() {
  const [config, setConfig] = useState<ConfigResponse>(FALLBACK)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/config')
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(setConfig)
      .catch(() => {}) // keep FALLBACK on error
      .finally(() => setLoading(false))
  }, [])

  return { config, loading }
}
