import { useState } from 'react'
import { LoadingSpinner } from '@/components/shared'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ApiError, getAuthTokenProvider, setAuthTokenProvider } from '@/services/api'
import { assessmentApi } from '../api/assessment.api'
import type { AssessmentReport, PublicQuestion } from '../types/assessment.types'
import { AssessmentOnboarding } from './assessment-onboarding'
import { AssessmentReportView } from './assessment-report-view'
import { AssessmentRunner } from './assessment-runner'

type Stage = 'onboarding' | 'running' | 'loading-report' | 'report'

export function AssessmentPage() {
  const [stage, setStage] = useState<Stage>('onboarding')
  const [sessionId, setSessionId] = useState<string>('')
  const [currentQuestion, setCurrentQuestion] = useState<PublicQuestion | null>(null)
  const [answeredCount, setAnsweredCount] = useState<number>(0)
  const [report, setReport] = useState<AssessmentReport | null>(null)
  const [isBusy, setIsBusy] = useState<boolean>(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const formatError = (err: unknown): string => {
    if (err instanceof ApiError) {
      const corr = err.correlationId ? ` (کد پیگیری: ${err.correlationId})` : ''
      return `${err.message}${corr}`
    }
    if (err instanceof Error) return err.message
    return 'خطای غیرمنتظره در ارتباط با سرویس آزمون رخ داد.'
  }

  const loadNextOrFinish = async (activeSessionId: string) => {
    const next = await assessmentApi.getNextQuestion(activeSessionId)
    if (next.should_stop || !next.question) {
      setStage('loading-report')
      const finalReport = await assessmentApi.getReport(activeSessionId)
      setReport(finalReport)
      setStage('report')
      return
    }
    setCurrentQuestion(next.question)
    setStage('running')
  }

  const handleStart = async ({
    age,
    profileCode,
    token,
  }: {
    age: number
    profileCode: string
    token?: string
  }) => {
    setErrorMsg(null)
    setIsBusy(true)
    try {
      if (token) {
        setAuthTokenProvider(() => token)
      } else if (!getAuthTokenProvider()) {
        // Keep existing provider untouched if already configured
      }
      const started = await assessmentApi.startAssessment({
        age,
        profile_code: profileCode,
        language: 'fa',
      })
      setSessionId(started.session_id)
      setAnsweredCount(0)
      await loadNextOrFinish(started.session_id)
    } catch (err) {
      setErrorMsg(formatError(err))
    } finally {
      setIsBusy(false)
    }
  }

  const handleSubmitAnswer = async ({
    questionVersionId,
    selectedOption,
    responseTimeMs,
    idempotencyKey,
  }: {
    questionVersionId: number
    selectedOption: string
    responseTimeMs: number
    idempotencyKey: string
  }) => {
    if (!sessionId) return
    setErrorMsg(null)
    setIsBusy(true)
    try {
      const res = await assessmentApi.submitAnswer(sessionId, {
        question_version_id: questionVersionId,
        answer: { selected_option: selectedOption },
        response_time_ms: responseTimeMs,
        idempotency_key: idempotencyKey,
      })
      setAnsweredCount(res.response_count)
      await loadNextOrFinish(sessionId)
    } catch (err) {
      setErrorMsg(formatError(err))
    } finally {
      setIsBusy(false)
    }
  }

  const handleRestart = () => {
    setStage('onboarding')
    setSessionId('')
    setCurrentQuestion(null)
    setAnsweredCount(0)
    setReport(null)
    setErrorMsg(null)
  }

  return (
    <main
      dir="rtl"
      className="flex min-h-screen flex-col items-center justify-center bg-background p-4 text-foreground"
    >
      {errorMsg && (
        <Card className="mb-4 w-full max-w-[42rem] border-destructive/50 bg-destructive/10">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-destructive">خطا در ارتباط با سامانه</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between gap-3 text-xs">
            <span>{errorMsg}</span>
            <Button type="button" variant="outline" size="sm" onClick={() => setErrorMsg(null)}>
              بستن
            </Button>
          </CardContent>
        </Card>
      )}

      {stage === 'onboarding' && (
        <AssessmentOnboarding isSubmitting={isBusy} onStart={handleStart} />
      )}

      {stage === 'running' && currentQuestion && (
        <AssessmentRunner
          key={currentQuestion.question_version_id}
          question={currentQuestion}
          answeredCount={answeredCount}
          isSubmitting={isBusy}
          onSubmitAnswer={handleSubmitAnswer}
        />
      )}

      {stage === 'loading-report' && (
        <div className="flex flex-col items-center gap-3 py-12">
          <LoadingSpinner />
          <p className="text-sm text-muted-foreground">در حال آماده‌سازی کارنامه استاتیک...</p>
        </div>
      )}

      {stage === 'report' && report && (
        <AssessmentReportView report={report} onRestart={handleRestart} />
      )}
    </main>
  )
}
