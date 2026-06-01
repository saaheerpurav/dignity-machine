import { useState, useEffect } from 'react'
import type { ConfigResponse } from '@/types/api'

const FALLBACK: ConfigResponse = {
  case_id: 'case_maria_lopez_fibro_001',
  gcp_project: 'integral-tensor-497618-a8',
  writeback_default: false,
  missions: [
    { id: 'analyze_denial', label: 'Analyze denial', description: 'Extract denial reason and supporting SSA policy.' },
    { id: 'find_missing_evidence', label: 'Find missing evidence', description: 'Compare file against policy requirements.' },
    { id: 'draft_records_request', label: 'Draft records request', description: 'Prepare provider request for missing proof.' },
    { id: 'prepare_packet', label: 'Prepare packet', description: 'Build the full advocate-ready packet draft.' },
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
