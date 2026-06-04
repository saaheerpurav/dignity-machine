export interface Mission {
  id: string
  label: string
  description: string
}

export interface ConfigResponse {
  case_id: string
  missions: Mission[]
  writeback_default: boolean
  gcp_project: string
}

export interface PolicyCitation {
  doc_id?: string
  chunk_id?: string | null
  title: string
  url?: string
  excerpt?: string
  why_it_matters?: string
}

export interface MedicalEvidence {
  doc_id: string
  index?: string
  title?: string
  excerpt?: string
  finding?: string
  relevance?: string
}

export interface MissingEvidenceItem {
  item?: string
  reason?: string
  gap_type?: string
  description?: string
  why_it_matters?: string
  supporting_policy_ids?: string[]
  supporting_case_doc_ids?: string[]
  confidence?: number
}

export interface StructuredResult {
  denial_summary?: string
  policy_citations?: PolicyCitation[]
  medical_evidence?: MedicalEvidence[]
  missing_evidence?: MissingEvidenceItem[]
  records_request_draft?: string
  advocate_alert_draft?: string
  packet_summary?: string
  next_actions?: string[]
  case_id?: string
  mode?: string
}

export interface AnalyzeResponse {
  answer: string
  structured: StructuredResult
  mission_id: string
  mission?: string
  writeback_enabled: boolean
  write_counts: Record<string, number>
}
