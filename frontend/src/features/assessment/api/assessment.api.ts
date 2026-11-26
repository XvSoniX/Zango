import { apiClient } from '@/services/api'
import type {
  AssessmentReport,
  NextQuestionResult,
  SelectionTraceRequest,
  SelectionTraceResponse,
  StartAssessmentRequest,
  StartAssessmentResult,
  SubmitAnswerRequest,
  SubmitAnswerResult,
} from '../types/assessment.types'

const ASSESSMENT_BASE = '/v1/assessments'
const SIMULATION_BASE = '/v1/internal/simulations'

export const assessmentApi = {
  async startAssessment(payload: StartAssessmentRequest): Promise<StartAssessmentResult> {
    const { data } = await apiClient.post<StartAssessmentResult>(`${ASSESSMENT_BASE}/start`, payload)
    return data
  },

  async getNextQuestion(sessionId: string): Promise<NextQuestionResult> {
    const { data } = await apiClient.get<NextQuestionResult>(
      `${ASSESSMENT_BASE}/${encodeURIComponent(sessionId)}/next-question`,
    )
    return data
  },

  async submitAnswer(
    sessionId: string,
    payload: SubmitAnswerRequest,
  ): Promise<SubmitAnswerResult> {
    const { data } = await apiClient.post<SubmitAnswerResult>(
      `${ASSESSMENT_BASE}/${encodeURIComponent(sessionId)}/answers`,
      payload,
    )
    return data
  },

  async getReport(sessionId: string): Promise<AssessmentReport> {
    const { data } = await apiClient.get<AssessmentReport>(
      `${ASSESSMENT_BASE}/${encodeURIComponent(sessionId)}/report`,
    )
    return data
  },

  async runSelectionTrace(payload: SelectionTraceRequest): Promise<SelectionTraceResponse> {
    const { data } = await apiClient.post<SelectionTraceResponse>(
      `${SIMULATION_BASE}/selection-trace`,
      payload,
    )
    return data
  },
}
