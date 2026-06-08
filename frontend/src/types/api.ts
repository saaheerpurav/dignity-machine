export interface Mission {
  id: string
  label: string
  description: string
}

export interface ConfigResponse {
  missions: Mission[]
  writeback_default: boolean
  gcp_project: string
}

export interface CaseSummary {
  case_id: string
  title: string
  source_name: string
  extracted_text_preview: string
  document_count: number
  pdf_url?: string | null
  document_classification?: {
    type: 'valid_denial' | 'possible_denial' | 'irrelevant'
    confidence: number
    matched_signals: string[]
    missing_signals: string[]
    message: string
  }
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

export interface AppealDeadline {
  notice_date?: string | null
  assumed_receipt_date?: string | null
  appeal_deadline?: string | null
  confidence: number
  source: string
  human_review_required: boolean
}

export type CaseTaskType =
  | 'missing_proof'
  | 'missing_notice_date'
  | 'missing_denial_reason'
  | 'missing_condition'
  | 'missing_appeal_stage'
  | 'missing_provider'
  | 'records_request_review'
  | 'review_summary_review'

export type CaseTaskStatus =
  | 'suggested'
  | 'needs_info'
  | 'draft_created'
  | 'ready_for_review'

export interface CaseTask {
  task_id: string
  task_type: CaseTaskType
  title: string
  description: string
  reason: string
  status: CaseTaskStatus
  source: 'denial_letter' | 'ssa_policy' | 'agent_inference'
}

export interface StructuredResult {
  mission?: string
  denial_summary?: string
  denial_reason?: string
  ssa_explanation?: string
  evidence_mentioned?: string[]
  case_context?: string
  policy_citations?: PolicyCitation[]
  medical_evidence?: MedicalEvidence[]
  missing_evidence?: MissingEvidenceItem[]
  deadline?: AppealDeadline
  case_tasks?: CaseTask[]
  request_context?: string
  records_needed?: string[]
  placeholder_fields?: string[]
  records_request_draft?: string
  advocate_alert_draft?: string
  packet_summary?: string
  review_summary?: string
  human_review_note?: string
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
  events?: AgentEvent[]
}

export interface AgentEvent {
  event_id?: string
  case_id?: string
  mission_id?: string
  event_type?: string
  tool_name?: string
  index_name?: string
  input?: unknown
  output?: unknown
  created_at?: string
}
