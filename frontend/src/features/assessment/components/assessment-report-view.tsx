import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import type { AssessmentReport } from '../types/assessment.types'

export interface AssessmentReportViewProps {
  report: AssessmentReport
  onRestart: () => void
}

const QUALITY_LABELS: Record<string, { label: string; style: string }> = {
  INTERPRETABLE: {
    label: 'قابل تفسیر و معتبر (داده‌های نشست سالم)',
    style: 'border-primary/40 bg-primary/10 text-foreground',
  },
  CAUTION: {
    label: 'قابل تفسیر با احتیاط (شواهد نیازمند بررسی تکمیلی)',
    style: 'border-border bg-muted text-foreground',
  },
  INSUFFICIENT: {
    label: 'شواهد ناکافی برای استنتاج قطعی',
    style: 'border-destructive/40 bg-destructive/10 text-foreground',
  },
}

export function AssessmentReportView({ report, onRestart }: AssessmentReportViewProps) {
  const qualityMeta = QUALITY_LABELS[report.quality_status] ?? QUALITY_LABELS.INTERPRETABLE

  return (
    <div className="w-full max-w-[56rem] space-y-5">
      <Card className="border-border bg-card text-card-foreground">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
            <span className="rounded-md border border-border bg-muted px-2.5 py-1">
              گزارش تحلیلی رسمی ارزیابی شناختی
            </span>
            <span className="rounded-md border border-border bg-muted px-2.5 py-1">
              وضعیت بازبینی متخصص: {report.clinician_review_status === 'PENDING_REVIEW' ? 'در انتظار تأیید مشاور' : report.clinician_review_status}
            </span>
          </div>
          <CardTitle className="mt-2 text-xl">کارنامه تحلیلی مهارت‌های شناختی و تفکر الگوریتمی</CardTitle>
          <CardDescription>
            تعداد گویه‌های ارزیابی‌شده: {report.total_answered_questions} | مدت زمان نشست:{' '}
            {Math.round(report.total_duration_seconds)} ثانیه | میانگین عدم قطعیت:{' '}
            {report.confidence_audit.average_uncertainty}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* 1. Quality Gate Banner */}
          <section className={`rounded-lg border p-4 text-sm ${qualityMeta.style}`}>
            <div className="font-semibold">وضعیت کفایت و کیفیت نشست: {qualityMeta.label}</div>
            {report.quality_reasons.length > 0 && (
              <ul className="mt-1.5 list-inside list-disc space-y-0.5 text-xs text-muted-foreground">
                {report.quality_reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            )}
          </section>

          {/* 2. Executive Clinical Narrative */}
          <section className="rounded-lg border border-border bg-muted/40 p-4 text-sm leading-relaxed text-foreground">
            <h3 className="mb-1.5 font-semibold">تحلیل جامع عملکرد</h3>
            <p>{report.general_summary}</p>
          </section>

          {/* 3. Observed Highlights */}
          {report.observed_highlights.length > 0 && (
            <section className="space-y-2 rounded-lg border border-border bg-background p-4">
              <h3 className="text-sm font-semibold text-foreground">مشاهدات عینی نشست</h3>
              <ul className="list-inside list-disc space-y-1 text-xs leading-relaxed text-muted-foreground">
                {report.observed_highlights.map((obs, idx) => (
                  <li key={idx}>{obs}</li>
                ))}
              </ul>
            </section>
          )}

          {/* 4. Anomaly Flags */}
          {report.anomaly_flags.length > 0 && (
            <section className="rounded-lg border border-destructive/40 bg-destructive/10 p-3.5 text-sm text-foreground">
              <h3 className="mb-1 font-semibold">هشدارهای کیفیت پاسخ‌دهی</h3>
              <ul className="list-inside list-disc space-y-1 text-xs">
                {report.anomaly_flags.map((flag, idx) => (
                  <li key={idx}>{flag}</li>
                ))}
              </ul>
            </section>
          )}

          {/* 5. Cognitive Dimensions Visual Profile */}
          <section className="space-y-3">
            <h3 className="text-base font-semibold text-foreground">پروفایل تفکیکی ابعاد شناختی</h3>
            <div className="grid gap-3 sm:grid-cols-2">
              {report.ability_overview.map((dim) => (
                <div
                  key={dim.dimension_code}
                  className="space-y-2 rounded-lg border border-border bg-background p-4 text-sm"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-foreground">{dim.dimension_name}</span>
                    <span className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                      {dim.interpretation_level}
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-primary transition-all"
                      style={{ width: `${Math.max(5, Math.min(100, dim.percentile_rank))}%` }}
                    />
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                    <span>تتا (θ): {dim.ability_score}</span>
                    <span>صدک نسبی: {dim.percentile_rank}٪</span>
                    <span>
                      بازه اطمینان ۹۵٪: [{dim.confidence_interval_low} تا {dim.confidence_interval_high}]
                    </span>
                    <span>شواهد: {dim.evidence_count} گویه</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* 6. Strengths & Growth Areas */}
          <section className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2.5 rounded-lg border border-border bg-background p-4">
              <h3 className="text-sm font-semibold text-foreground">نقاط قوت نسبی</h3>
              <ul className="space-y-2 text-xs text-muted-foreground">
                {report.strengths.map((item) => (
                  <li key={item.dimension_code}>
                    <span className="block font-medium text-foreground">{item.title}</span>
                    <span>{item.description}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="space-y-2.5 rounded-lg border border-border bg-background p-4">
              <h3 className="text-sm font-semibold text-foreground">فرصت‌های رشد و تمرین</h3>
              <ul className="space-y-2 text-xs text-muted-foreground">
                {report.growth_areas.map((item) => (
                  <li key={item.dimension_code}>
                    <span className="block font-medium text-foreground">{item.title}</span>
                    <span>{item.description}</span>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          {/* 7. Next Experiments & Practical Recommendations */}
          {(report.next_experiments.length > 0 || report.recommendations.length > 0) && (
            <section className="grid gap-4 sm:grid-cols-2">
              {report.next_experiments.length > 0 && (
                <div className="space-y-2 rounded-lg border border-border bg-background p-4">
                  <h3 className="text-sm font-semibold text-foreground">گام‌ها و تمرین‌های پیشنهادی آتی</h3>
                  <ul className="list-inside list-disc space-y-1.5 text-xs leading-relaxed text-muted-foreground">
                    {report.next_experiments.map((exp, idx) => (
                      <li key={idx}>{exp}</li>
                    ))}
                  </ul>
                </div>
              )}
              {report.recommendations.length > 0 && (
                <div className="space-y-2 rounded-lg border border-border bg-background p-4">
                  <h3 className="text-sm font-semibold text-foreground">توصیه‌های مشاوره‌ای</h3>
                  <ul className="list-inside list-disc space-y-1.5 text-xs leading-relaxed text-muted-foreground">
                    {report.recommendations.map((rec, idx) => (
                      <li key={idx}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}
            </section>
          )}

          {/* 8. Scientific & Ethical Limitations Notice */}
          <section className="rounded-lg border border-border bg-muted/30 p-3.5 text-xs leading-relaxed text-muted-foreground">
            <strong className="block text-foreground">مرزهای استنتاج علمی و سلب مسئولیت:</strong>
            {report.confidence_audit.limitations_notice}
          </section>
        </CardContent>

        <CardFooter className="justify-end">
          <Button type="button" variant="outline" onClick={onRestart}>
            شروع ارزیابی جدید
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}
