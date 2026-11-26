import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import type { PublicQuestion } from '../types/assessment.types'

export interface AssessmentRunnerProps {
  question: PublicQuestion
  answeredCount: number
  isSubmitting: boolean
  onSubmitAnswer: (params: {
    questionVersionId: number
    selectedOption: string
    responseTimeMs: number
    idempotencyKey: string
  }) => void
}

function createIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `idemp-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export function AssessmentRunner({
  question,
  answeredCount,
  isSubmitting,
  onSubmitAnswer,
}: AssessmentRunnerProps) {
  const [selectedOption, setSelectedOption] = useState<string>('')
  const presentedAtRef = useRef<number>(0)
  const idempotencyKeyRef = useRef<string>('')

  useEffect(() => {
    presentedAtRef.current = performance.now()
    idempotencyKeyRef.current = createIdempotencyKey()
  }, [])

  const handleConfirm = () => {
    if (!selectedOption || isSubmitting) return
    const elapsedMs = Math.max(100, Math.round(performance.now() - presentedAtRef.current))
    onSubmitAnswer({
      questionVersionId: question.question_version_id,
      selectedOption,
      responseTimeMs: elapsedMs,
      idempotencyKey: idempotencyKeyRef.current,
    })
  }

  return (
    <Card className="w-full max-w-[42rem] border-border bg-card text-card-foreground">
      <CardHeader>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>سؤال شماره {question.sequence_number}</span>
          <span>پاسخ‌های ثبت‌شده: {answeredCount}</span>
        </div>
        <CardTitle className="mt-2 text-lg leading-relaxed">{question.content}</CardTitle>
        <CardDescription>
          بهترین گزینه را با آرامش و دقت انتخاب کنید؛ هیچ محدودیت زمانی لحظه‌ای برای این سؤال
          وجود ندارد.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-2.5">
        {question.options.map((opt) => {
          const isSelected = selectedOption === opt.key
          return (
            <button
              key={opt.key}
              type="button"
              disabled={isSubmitting}
              onClick={() => setSelectedOption(opt.key)}
              className={`flex w-full items-center gap-3 rounded-lg border p-3.5 text-right text-sm transition-colors ${
                isSelected
                  ? 'border-primary bg-primary/10 text-foreground'
                  : 'border-border bg-background text-foreground hover:bg-muted/60'
              }`}
            >
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold ${
                  isSelected
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-border bg-muted text-muted-foreground'
                }`}
              >
                {opt.key}
              </span>
              <span className="leading-relaxed">{opt.text}</span>
            </button>
          )
        })}
      </CardContent>

      <CardFooter className="justify-between">
        <span className="text-xs text-muted-foreground">
          شناسه نسخه گویه: {question.question_version_id}
        </span>
        <Button type="button" onClick={handleConfirm} disabled={!selectedOption || isSubmitting}>
          {isSubmitting ? 'در حال ثبت و محاسبه انطباقی...' : 'ثبت پاسخ و ادامه'}
        </Button>
      </CardFooter>
    </Card>
  )
}
