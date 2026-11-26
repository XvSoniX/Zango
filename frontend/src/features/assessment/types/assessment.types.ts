export interface StartAssessmentRequest {
  age: number
  profile_code: string
  language?: string
}

export interface StartAssessmentResult {
  session_id: string
  student_id: string
  student_age: number
  profile_id: number
  profile_code: string
  status: string
  started_at: string
  algorithm_version: string
  target_dimensions: string[]
  initial_scores: Record<string, number>
  initial_uncertainty: Record<string, number>
}

export interface PublicQuestionOption {
  key: string
  text: string
}

export interface PublicQuestion {
  question_id: number
  question_version_id: number
  question_type: string
  content: string
  options: PublicQuestionOption[]
  estimated_time: number
  sequence_number: number
}

export interface NextQuestionResult {
  session_id: string
  should_stop: boolean
  stopping_reason?: string | null
  stopping_detail?: string | null
  question?: PublicQuestion | null
  progress: Record<string, unknown>
}

export interface SubmitAnswerRequest {
  question_version_id: number
  answer: { selected_option: string }
  response_time_ms: number
  idempotency_key: string
}

export interface SubmitAnswerResult {
  session_id: string
  response_id: string
  question_id: number
  question_version_id: number
  is_correct: boolean
  score: number
  response_time_ms: number
  idempotency_key: string
  answered_at: string
  response_count: number
  session_status: string
  is_retry: boolean
}

export interface DimensionOverview {
  dimension_code: string
  dimension_name: string
  ability_score: number
  uncertainty: number
  confidence_interval_low: number
  confidence_interval_high: number
  percentile_rank: number
  evidence_count: number
  interpretation_level: string
}

export interface StrengthOrGrowthItem {
  dimension_code: string
  dimension_name: string
  ability_score: number
  uncertainty: number
  title: string
  description: string
  evidence_level: string
}

export interface ConfidenceAudit {
  overall_confidence: string
  average_uncertainty: number
  coverage_summary: string
  limitations_notice: string
}

export interface AssessmentReport {
  report_id: string
  user_id: string
  assessment_session_id: string
  assessment_profile_id: number
  completed_at: string
  total_answered_questions: number
  total_duration_seconds: number
  algorithm_version: string
  report_version: string
  report_mode: string
  clinician_review_status: string
  quality_status: 'INTERPRETABLE' | 'CAUTION' | 'INSUFFICIENT' | string
  quality_reasons: string[]
  ability_overview: DimensionOverview[]
  strengths: StrengthOrGrowthItem[]
  growth_areas: StrengthOrGrowthItem[]
  confidence_audit: ConfidenceAudit
  general_summary: string
  observed_highlights: string[]
  next_experiments: string[]
  recommendations: string[]
  anomaly_flags: string[]
  generated_at: string
}

export interface SelectionTraceRequest {
  seed: number
  student_age: number
  max_questions: number
}

export interface SelectionTraceStep {
  step: number
  selected_question_id: number
  question_version: number
  difficulty: number
  simulated_correct: boolean
  selection_reason: string
  chosen_details: Record<string, unknown>
  theta_after: Record<string, number>
  uncertainty_after: Record<string, number>
  stopping_should_stop: boolean
  stopping_reason?: string | null
}

export interface SelectionTraceResponse {
  seed: number
  student_age: number
  true_ability: Record<string, number>
  steps: SelectionTraceStep[]
  final_theta: Record<string, number>
  final_uncertainty: Record<string, number>
}
