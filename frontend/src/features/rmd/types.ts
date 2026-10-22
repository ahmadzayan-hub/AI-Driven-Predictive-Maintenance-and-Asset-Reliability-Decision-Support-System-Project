export type EvidenceText = string | { en?: string; ar?: string }
export type EvidenceValue = string | number | boolean | null
export interface ApplicabilityDecision { state: 'unverified' | 'confirmed_current' | 'superseded' | 'not_applicable'; reason?: string; evidence?: string[]; decided_by?: string | null; decided_at?: string }
export type Grain = 'mms_work_order' | 'occ_event' | 'sr_reconciliation' | 'summary' | 'other'
export const grains: Grain[] = ['mms_work_order', 'occ_event', 'sr_reconciliation', 'summary', 'other']

export interface SourceColumn { letter: string; name?: string; label?: string; header?: string; hidden?: boolean; index?: number }
export interface SourceCell { value?: EvidenceValue; raw?: EvidenceValue; raw_value?: EvidenceValue; ref?: string; formula?: string | null; cached?: EvidenceValue; cached_value?: EvidenceValue; has_cached_result?: boolean }
export interface SourceRow { row?: number; source_row?: number; cells?: Record<string, SourceCell> | SourceCell[]; values?: EvidenceValue[]; hidden?: boolean }
export interface SourceSheet {
  name: string; columns?: SourceColumn[]; headers?: SourceColumn[] | string[]; rows?: SourceRow[]
  header_row?: number; proposed_header_row?: number; suggested_header_row?: number
  header_row_proposed?: number; visibility?: string; data_row_count_proposed?: number; source_row_count?: number
  role?: Grain; suggested_role?: Grain; row_count?: number; data_rows?: number
  hidden?: boolean; auto_filter?: string | null; autofilter?: string | null; warnings?: string[]
  auto_filter_ref?: string | null; rows_beyond_filter?: number[]
}
export type ValueState = 'unknown' | 'not_applicable' | 'not_measured' | 'blank' | 'unresolved_placeholder' | 'recorded' | 'measured_zero'
export interface SheetMapping { name: string; role: Grain; header_row: number; columns: Record<string, string>; date_format?: 'ISO' | 'DMY' | 'MDY'; value_states?: Record<string,Record<string,ValueState>> }
export interface SourceMapping { sheets: SheetMapping[] }
export interface SourceDocument {
  code?: string | null; document_code?: string | null; revision?: string | null; language?: string
  applicability?: EvidenceText; digest?: Record<string, unknown>; clauses?: Clause[]
  paragraphs?: unknown[]; tables?: unknown[]; [key: string]: unknown
}
export interface EvidenceSource {
  id: string; name: string; sha256: string; kind: 'procedure' | 'workbook'; created_at?: string
  revision?: number; document_code?: string | null; document_revision?: string | null; applicability?: ApplicabilityDecision
  format?: string; extraction?: Record<string, unknown>; coverage?: Record<string, unknown>
  warnings?: EvidenceText[]; sheets?: SourceSheet[]; document?: SourceDocument; mapping?: SourceMapping | null
  mapping_revision?: number; artifacts?: { name: string; content_type?: string; bytes?: number }[]
  metadata?: { sheets?: SourceSheet[]; document?: SourceDocument; coverage?: Record<string, unknown>; warnings?: EvidenceText[] }
}
export interface AnalysisSummary { id: string; created_at?: string; calculated_at?: string; calculation_version?: string; title?: string }
export interface EvidencePack {
  id: string; title: string; owner?: string; organization_id?: string | null; created_at: string
  sources: EvidenceSource[]; analyses: AnalysisSummary[]; revision?: number
  permissions?: { write?: boolean; review?: boolean }
}
export interface EvidenceRecord {
  id: string; source_id: string; source_sha?: string; sheet: string; source_row: number; grain: Grain
  fields: Record<string, EvidenceValue>; raw_fields?: Record<string, unknown>; [key: string]: unknown
}
export interface EvidenceQuery { record_ids?: string[]; grain?: string; offset?: number; limit?: number }
export interface EvidencePage { records: EvidenceRecord[]; total: number; offset?: number; limit?: number }
export interface Clause {
  id: string; source_id?: string; source_name?: string; document_code?: string; revision?: string | number
  document_revision?: string; source_sha256?: string; section?: string
  locator: string | Record<string, unknown>; text: string; applicability?: ApplicabilityDecision; coverage?: unknown
  heading?: string; language?: string; [key: string]: unknown
}
export interface Kpi {
  id: string; title: EvidenceText; value: number | null; unit: string; grain: string
  formula: string; question: EvidenceText; population: { grain: string; records: number; record_ids?: string[] }
  numerator?: number | null; denominator?: number | null; period?: unknown; coverage?: unknown
  missing_policy?: EvidenceText; exclusions?: unknown; calculation_version: string; source_versions?: unknown
  evidence_record_ids: string[]
}
export interface EvidenceChart {
  id: string; title: EvidenceText; question?: EvidenceText; kind: 'bar' | 'line'; grain: string; unit: string
  table: { label: string; value: number; record_ids: string[]; share?: number | null; cumulative_share?: number | null }[]
  denominator: number; missing_records: number; calculation_id: string
  formula?: string; population?: { grain: string; records: number }; period?: unknown; coverage?: unknown
  missing_policy?: EvidenceText; exclusions?: unknown; source_versions?: unknown; calculation_version?: string
}
export type CalculationDetails = Partial<Pick<Kpi, 'formula' | 'unit' | 'population' | 'numerator' | 'denominator' | 'period' | 'coverage' | 'missing_policy' | 'exclusions' | 'source_versions' | 'calculation_version'>>
export interface Priority {
  id: string; finding: EvidenceText; evidence: { calculation_ids: string[]; record_ids: string[] }
  management_implication: EvidenceText; uncertainty: EvidenceText; proposed_action: EvidenceText
  owner_role: EvidenceText; owner_is_suggested: boolean; due_date: string | null; due_date_basis: EvidenceText; closure_evidence: EvidenceText
}
export interface ReadinessMeasure {
  id: string; label: EvidenceText; available: boolean; state: string
  missing_inputs: EvidenceText[]; reason: EvidenceText; needed_validation: EvidenceText[]
}
export interface EvidenceConflict {
  id: string; kind: string; sr_id?: string; record_ids: string[]
  values: { value: EvidenceValue; record_ids: string[] }[]; status: string; interpretation: EvidenceText
}
export interface ProposedLink {
  id: string; left_record_id: string; right_record_id: string; method: string; relation: string
  state: string; evidence: Record<string, unknown>; reason: EvidenceText; revision?: number
}
export interface Completeness {
  grain: string; field: string; total_records: number; applicable_records: number; recorded: number; missing: number
  unknown: number; not_applicable: number; not_measured: number; unresolved_placeholders: number; record_ids_missing: string[]
}
export interface AnalysisFilters { from?: string; to?: string; location?: string; category?: string; grain?: string }
export interface EvidenceAnalysis extends AnalysisSummary {
  run_id?: string; language?: string; scope?: unknown; period?: unknown; filters?: AnalysisFilters; source_versions?: unknown
  coverage?: unknown; counts_by_grain: Record<string, number>; status_distributions?: unknown
  completeness: Completeness[]; reconciliation?: {
    source_labels: { label: string; count: number; record_ids: string[] }[]
    calculated_outcomes: { code: string; count: number; record_ids: string[] }[]
    comparison_scope?: unknown; records?: unknown[]
  }
  relationships?: unknown; conflicts: EvidenceConflict[]; proposed_links: ProposedLink[]
  recurrence?: { id: string; grain: string; symptom_label: string; location: string; count: number; record_ids: string[]; interpretation: EvidenceText }[]
  age_and_due_date_review?: { as_of: string; records: { record_id: string; age_since_event_days: number | null; overdue: boolean | null; due_date: string | null; outstanding_status: boolean | null; due_date_basis: string | null; reason: string | null }[]; overdue: number; not_overdue: number; unassessable: number; interpretation?: string }
  charts: EvidenceChart[]; readiness: ReadinessMeasure[]; kpis: Kpi[]; priorities: Priority[]; limitations: EvidenceText[]
}
export interface ProposedAction {
  id: string; analysis_id: string; priority_id?: string; title?: EvidenceText; proposed_action?: EvidenceText
  owner_role?: EvidenceText; due_date?: string | null; due_date_basis?: EvidenceText; state?: string
  closure_evidence?: EvidenceText; revision?: number
}
