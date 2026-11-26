import { useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'

export interface AssessmentOnboardingProps {
  isSubmitting: boolean
  initialToken?: string
  onStart: (params: { age: number; profileCode: string; token?: string }) => void
}

export function AssessmentOnboarding({
  isSubmitting,
  initialToken = '',
  onStart,
}: AssessmentOnboardingProps) {
  const [age, setAge] = useState<string>('14')
  const [profileCode, setProfileCode] = useState<string>('TECHNICAL_TALENT_V1')
  const [parentalConsent, setParentalConsent] = useState<boolean>(false)
  const [token, setToken] = useState<string>(initialToken)
  const [validationError, setValidationError] = useState<string | null>(null)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const parsedAge = Number(age)
    if (!Number.isInteger(parsedAge) || parsedAge < 8 || parsedAge > 18) {
      setValidationError('سن دانش‌آموز باید بین ۸ تا ۱۸ سال باشد.')
      return
    }
    if (!parentalConsent) {
      setValidationError('تأیید رضایت‌نامه آگاهانه والدین یا سرپرست قانونی پیش از شروع الزامی است.')
      return
    }
    setValidationError(null)
    onStart({
      age: parsedAge,
      profileCode: profileCode.trim() || 'TECHNICAL_TALENT_V1',
      token: token.trim() || undefined,
    })
  }

  return (
    <Card className="w-full max-w-[36rem] border-border bg-card text-card-foreground">
      <CardHeader>
        <CardTitle className="text-xl">آزمون انطباقی سنجش مهارت‌های تحلیلی</CardTitle>
        <CardDescription>
          این ارزیابی بر اساس مدل روان‌سنجی IRT/CAT طراحی شده و بدون تایمر استرس‌زا، سؤالات را متناسب
          با سطح پاسخ‌گویی شما انتخاب می‌کند.
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="student-age" className="block text-sm font-medium text-foreground">
              سن آزمودنی (۸ تا ۱۸ سال)
            </label>
            <Input
              id="student-age"
              type="number"
              min={8}
              max={18}
              value={age}
              onChange={(e) => setAge(e.target.value)}
              disabled={isSubmitting}
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="profile-code" className="block text-sm font-medium text-foreground">
              پروفایل ارزیابی
            </label>
            <Input
              id="profile-code"
              type="text"
              value={profileCode}
              onChange={(e) => setProfileCode(e.target.value)}
              disabled={isSubmitting}
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="jwt-token" className="block text-sm font-medium text-foreground">
              توکن احراز هویت (Bearer JWT — در صورت نیاز محیط توسعه)
            </label>
            <Input
              id="jwt-token"
              type="password"
              placeholder="اختیاری در صورت تنظیم خودکار TokenProvider"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              disabled={isSubmitting}
            />
          </div>

          <label className="flex cursor-pointer items-start gap-2.5 rounded-md border border-border bg-muted/40 p-3 text-sm">
            <input
              type="checkbox"
              checked={parentalConsent}
              onChange={(e) => setParentalConsent(e.target.checked)}
              disabled={isSubmitting}
              className="mt-1 h-4 w-4 accent-primary"
            />
            <span className="text-muted-foreground">
              به عنوان والد یا سرپرست قانونی، آگاه هستم که این ابزار یک غربالگری آموزشی است و جایگزین
              تشخیص بالینی روان‌شناس نیست و با ثبت داده‌های ناشناس‌شده آزمون موافقم.
            </span>
          </label>

          {validationError && (
            <p role="alert" className="text-sm text-destructive">
              {validationError}
            </p>
          )}
        </CardContent>
        <CardFooter className="justify-end">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'در حال آماده‌سازی نشست...' : 'شروع آزمون انطباقی'}
          </Button>
        </CardFooter>
      </form>
    </Card>
  )
}
