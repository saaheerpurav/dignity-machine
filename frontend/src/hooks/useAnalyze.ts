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
      'SSA denied Maria Lopez\'s claim for fibromyalgia-based disability on the grounds that her medical record did not establish the severity of her symptoms or the functional limitations required under 20 CFR § 404.1505. The adjudicator found insufficient objective medical evidence, specifically noting the absence of a treating-provider functional capacity statement and incomplete rheumatology follow-up documentation.',
    policy_citations: [
      {
        title: 'SSA POMS DI 24515.061 — Fibromyalgia',
        url: 'https://secure.ssa.gov/poms.nsf/lnx/0424515061',
        excerpt:
          'Fibromyalgia is a medically determinable impairment when a licensed physician documents widespread pain, at least 11 of 18 tender points, and exclusion of other conditions. A treating-source statement addressing functional limitations is essential to establish severity.',
      },
      {
        title: 'SSA POMS DI 22505.003 — Medical Evidence Standards',
        excerpt:
          'Objective medical evidence from acceptable medical sources must establish the existence of a medically determinable impairment. Treating-source opinions are generally given controlling weight when well-supported and not inconsistent with the record.',
      },
    ],
    medical_evidence: [
      {
        doc_id: 'doc_denial_letter_001',
        index: 'case_documents',
        excerpt:
          'Initial denial dated March 2024: "The medical evidence does not establish that your condition prevents you from performing your past relevant work as a data entry clerk."',
        relevance: 'Core denial reason — establishes basis for appeal',
      },
      {
        doc_id: 'doc_medical_note_lakeview_003',
        index: 'case_documents',
        excerpt:
          'Lakeview Rheumatology visit, Jan 2024: Tender point count 14/18. Patient reports widespread pain, fatigue, and cognitive disruption. No functional capacity assessment completed.',
        relevance: 'Key existing evidence — supports impairment but lacks RFC statement',
      },
      {
        doc_id: 'doc_function_report_002',
        index: 'case_documents',
        excerpt:
          'Maria\'s self-reported function report: Cannot sit or stand for more than 20 minutes without pain. Sleep disrupted nightly. Unable to lift more than 5 lbs consistently.',
        relevance: 'Supports functional limitation claim',
      },
    ],
    missing_evidence: [
      {
        item: 'Treating-physician RFC statement',
        reason: 'SSA requires a formal Residual Functional Capacity form from a treating provider. Without it, functional limitations lack medical source backing.',
      },
      {
        item: 'Complete rheumatology follow-up records (Feb – Apr 2024)',
        reason: 'Three months of follow-up visits at Lakeview Rheumatology are not in the file. These likely document ongoing symptom severity.',
      },
      {
        item: 'Mental health records for cognitive impairment',
        reason: '"Fibro fog" cognitive symptoms were reported but no mental health evaluation is present. A neuropsychological or psychiatric note would strengthen the claim.',
      },
    ],
    records_request_draft:
      `Dear Records Department — Lakeview Rheumatology,

We are writing on behalf of Maria Lopez (DOB: 05/14/1978) in connection with her pending Social Security Disability appeal.

Please provide the following at your earliest convenience:
  1. All clinical notes from February 2024 through April 2024
  2. A completed RFC (Residual Functional Capacity) form addressing Ms. Lopez's ability to sit, stand, walk, lift, and concentrate
  3. Any laboratory or imaging results from this period

These records are needed to support Ms. Lopez's appeal. Please send to:
  Elena Vargas, Disability Advocate
  Community Legal Aid — Disability Unit
  elena.vargas@legalaid.org

Thank you for your prompt attention.`,
    advocate_alert_draft:
      `Hi Elena — new evidence gaps identified for Maria Lopez's fibromyalgia appeal.

Key issues:
• Missing RFC statement from Lakeview Rheumatology
• 3 months of follow-up records not in the file (Feb–Apr 2024)
• No cognitive/mental health evaluation on record

Records request has been drafted. Please review and approve before sending to Lakeview.

— Dignity Machine`,
    packet_summary:
      'Maria Lopez was denied on the basis of insufficient functional limitation evidence. Policy review confirms fibromyalgia is a cognizable impairment under SSA guidelines when properly documented. Three evidence gaps have been identified. A records request has been drafted targeting Lakeview Rheumatology for missing RFC documentation and follow-up notes.',
    next_actions: [
      'Obtain RFC statement from treating rheumatologist at Lakeview',
      'Request Feb–Apr 2024 clinical notes from Lakeview Rheumatology',
      'Schedule neuropsychological evaluation to document cognitive impairment',
      'File appeal within 60-day deadline from denial date',
      'Advocate Elena Vargas to review and approve records request',
    ],
  },
}

export function useAnalyze() {
  const [data, setData] = useState<AnalyzeResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = useCallback(async (mission: string, writeback: boolean) => {
    setLoading(true)
    setError(null)
    setData(null)

    // Simulate minimum agent run time for timeline animation
    const minDelay = new Promise(r => setTimeout(r, 6000))

    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mission, writeback }),
      })
      const text = await res.text()
      let json: AnalyzeResponse
      try {
        json = JSON.parse(text)
      } catch {
        // Backend not running — use mock data for demo
        await minDelay
        setData({ ...MOCK, mission })
        return
      }
      if (!res.ok) throw new Error((json as unknown as { detail: string }).detail || 'Request failed')
      await minDelay
      setData(json)
    } catch {
      // Fall back to mock so the UI is fully visible
      await minDelay
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
