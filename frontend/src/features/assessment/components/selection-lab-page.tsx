import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ApiError } from '@/services/api'
import { assessmentApi } from '../api/assessment.api'
import type { SelectionTraceResponse } from '../types/assessment.types'

export function SelectionLabPage() {
  const [seed, setSeed] = useState<string>('42')
  const [age, setAge] = useState<string>('12')
  const [maxQuestions, setMaxQuestions] = useState<string>('10')
  const [isRunning, setIsRunning] = useState<boolean>(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [trace, setTrace] = useState<SelectionTraceResponse | null>(null)

  const handleRun = async (e: FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)
    setIsRunning(true)
    try {
      const res = await assessmentApi.runSelectionTrace({
        seed: Number(seed) || 42,
        student_age: Math.max(8, Math.min(18, Number(age) || 12)),
        max_questions: Math.max(1, Math.min(20, Number(maxQuestions) || 10)),
      })
      setTrace(res)
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message)
      } else if (err instanceof Error) {
        setErrorMsg(err.message)
      } else {
        setErrorMsg('خطا در اجرای شبیه‌سازی انتخاب سؤال.')
      }
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <main dir="rtl" className="mx-auto flex min-h-screen w-full max-w-[64rem] flex-col gap-6 bg-background p-6 text-foreground">
      <Card className="border-border bg-card">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="text-xl">آزمایشگاه تست روند منطقی انتخاب سؤال (Seeded Audit Trace)</CardTitle>
            <Button asChild variant="outline" size="sm">
              <Link to="/assessment">بازگشت به آزمون</Link>
            </Button>
          </div>
          <CardDescription>
            این بخش برای بررسی دقیق پس‌زمینه انتخاب گویه‌ها (اطلاع فیشر، پوشش ابعاد، سختی و همگرایی تتا)
            با کاربران شبیه‌سازی‌شده دارای Seed مشخص طراحی شده است. (در فاز بعد، دسترسی این بخش به نقش‌های
            ADMIN و CLINICIAN در پنل مربوطه منتقل خواهد شد.)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleRun} className="grid gap-4 sm:grid-cols-4 sm:items-end">
            <div className="space-y-1.5">
              <label htmlFor="sim-seed" className="block text-xs font-medium">
                Seed تصادفی قطعی
              </label>
              <Input
                id="sim-seed"
                type="number"
                value={seed}
                onChange={(e) => setSeed(e.target.value)}
                disabled={isRunning}
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="sim-age" className="block text-xs font-medium">
                سن آزمودنی مجازی (۸–۱۸)
              </label>
              <Input
                id="sim-age"
                type="number"
                min={8}
                max={18}
                value={age}
                onChange={(e) => setAge(e.target.value)}
                disabled={isRunning}
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="sim-maxq" className="block text-xs font-medium">
                حداکثر گام (۱–۲۰)
              </label>
              <Input
                id="sim-maxq"
                type="number"
                min={1}
                max={20}
                value={maxQuestions}
                onChange={(e) => setMaxQuestions(e.target.value)}
                disabled={isRunning}
              />
            </div>
            <Button type="submit" disabled={isRunning}>
              {isRunning ? 'در حال شبیه‌سازی...' : 'اجرای تست انتخاب سؤال'}
            </Button>
          </form>

          {errorMsg && (
            <p role="alert" className="mt-3 text-xs text-destructive">
              {errorMsg}
            </p>
          )}
        </CardContent>
      </Card>

      {trace && (
        <Card className="border-border bg-card">
          <CardHeader>
            <CardTitle className="text-lg">
              نتیجه شبیه‌سازی (Seed: {trace.seed} | سن: {trace.student_age} | گام‌ها: {trace.steps.length})
            </CardTitle>
            <CardDescription>
              مقایسه بردار توانایی واقعی شبیه‌سازی‌شده با برآورد نهایی موتور
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-border bg-background p-3 text-xs">
                <strong className="mb-1 block">توانایی واقعی (True θ):</strong>
                <pre className="overflow-x-auto text-muted-foreground" dir="ltr">
                  {JSON.stringify(trace.true_ability, null, 2)}
                </pre>
              </div>
              <div className="rounded-lg border border-border bg-background p-3 text-xs">
                <strong className="mb-1 block">برآورد نهایی موتور (Estimated θ):</strong>
                <pre className="overflow-x-auto text-muted-foreground" dir="ltr">
                  {JSON.stringify(trace.final_theta, null, 2)}
                </pre>
              </div>
            </div>

            <div className="space-y-2.5">
              <h3 className="text-sm font-semibold">روند گام‌به‌گام انتخاب گویه‌ها</h3>
              {trace.steps.map((s) => (
                <div key={s.step} className="rounded-lg border border-border bg-background p-3 text-xs">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold">
                      گام {s.step}: سؤال #{s.selected_question_id} (سختی b={s.difficulty})
                    </span>
                    <span className="rounded bg-muted px-2 py-0.5">
                      {s.simulated_correct ? 'پاسخ درست' : 'پاسخ نادرست'}
                      {s.stopping_should_stop ? ` | توقف: ${s.stopping_reason}` : ''}
                    </span>
                  </div>
                  <p className="mt-1.5 text-muted-foreground" dir="ltr">
                    {s.selection_reason}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </main>
  )
}
