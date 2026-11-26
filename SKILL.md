---
name: nextminds-architecture-and-phase1-guide
description: Complete architectural, domain, security, API, psychometric, frontend, and Phase 1 execution blueprint for the NextMinds (formerly Zango) microservices platform. Any AI coding agent working on any service or frontend slice MUST read this skill before making changes.
---

<div dir="rtl">

# راهنمای جامع معماری و اجرای فاز اول پروژه NextMinds (`SKILL.md`)

**مخزن اصلی:** `https://github.com/XvSoniX/next-minds`  
**توضیح برای ایجنت‌های هوشمند:** اگر به تازگی این مخزن را باز کرده‌اید و قرار است روی یکی از بخش‌های بک‌اند، موتور آزمون، فرانت‌اند یا زیرساخت کار کنید، این سند **نقشه قطعی و مرجع واحد حقیقت (Single Source of Truth)** برای جلوگیری از دوباره‌کاری، تخریب قراردادهای بین‌سرویسی یا کدنویسی خارج از اسکوپ فاز اول است.

---

## ۱. قوانین خط قرمز (Non-Negotiable Rules)

هر ایجنتی که در این مخزن کد می‌نویسد باید بدون استثنا این ۷ قانون را رعایت کند:

1. **ممنوعیت تغییر هسته `auth-service`:** سرویس `auth-service` تکمیل‌شده است و مرجع واحد احراز هویت، هش رمز عبور (Argon2id)، مدیریت نقش‌های پایه و صدور توکن **RS256 JWT** با `private.pem` است. هیچ سرویس دیگری حق ساخت جدول رمز عبور، لاگین یا صدور توکن ندارد.
2. **هویت یکپارچه در کل میکروسرویس‌ها:** تمام سرویس‌ها (`user-service`, `admin-service`, `consulting-service`, `assessment-service`) کاربر را از طریق `sub` (UUID کاربر در `auth-service`) می‌شناسند و اعتبار توکن را با **`public.pem`** + تطابق `JWT_ISSUER` و `JWT_AUDIENCE` تأیید می‌کنند. **هرگز جدول یوزر با رمز عبور جداگانه در سرویس‌های دیگر نسازید و بین دیتابیس سرویس‌ها Foreign Key نگذارید.**
3. **اسکوپ فاز اول بدون LLM و چت‌بات:** به دلیل محدودیت منابع سرور فعلی، **هیچ اتصالی به OpenAI / LLM API، Vector DB یا چت‌بات در فاز اول پیاده‌سازی نمی‌شود.** خروجی کارنامه آزمون در فاز اول قطعی و مبتنی بر قواعد (`RULE_BASED_ANALYTICAL`) است.
4. **ممنوعیت متن‌های تستی و ادعاهای تشخیصی در کارنامه:** در متن‌های نمایشی کارنامه هرگز عباراتی مثل «بدون هوش مصنوعی / ماک / تستی» ننویسید؛ همچنین هرگز برچسب تشخیص بیماری، اختلال (مثل ADHD) یا نمره IQ صادر نکنید.
5. **حفاظت از حریم خصوصی کودکان (۸ تا ۱۸ سال) و امنیت کلید سؤالات:** در داده‌های ارسالی به موتور آزمون و گزارش‌گیری از `pseudonym_id` استفاده شود؛ فیلد `correct_answer` و پارامترهای روان‌سنجی ($a, b, c$) هرگز در پاسخ‌های عمومی دانش‌آموز/والد افشا نشوند.
6. **تضمین سازگاری قرارداد خطا و همبستگی:** تمام سرویس‌های بک‌اند باید خطاها را با فرمت **RFC 7807 / RFC 9457 (`application/problem+json`)** و فیلدهای `isSuccess`, `errorCode`, `correlationId`, `errors` برگردانند و هدر `X-Correlation-ID` را عبور دهند.
7. **فاز‌بندی دقیق موتور آزمون:** موتور ریاضی 3PL IRT + Fisher Information + MFI در `assessment-service` کامل است و نباید به مدل هیوریستیک قبلی برگردانده شود.

---

## ۲. نقشه کامل معماری و وضعیت واقعی سرویس‌ها

```text
[Browser / React 19 + Vite 8 (:3000)]
               │
               ▼ (/api/*)
[gateway-service :8080] ──(Eureka Discovery :8761)──┐
   │  Validates RS256 JWT (public.pem)              │
   │  Enforces CORS, X-Correlation-ID, RateLimit    │
   ├──► /api/v1/auth/**        ──► [auth-service :8081]       ──► (auth-db)         [DONE ✅]
   ├──► /api/v1/users/**       ──► [user-service :8082]       ──► (user-db)         [EMPTY SKELETON → آرش]
   ├──► /api/v1/admin/**       ──► [admin-service :8083]      ──► (admin-db)        [LOCAL ON MAHDI'S PC → مهدی]
   ├──► /api/v1/consulting/**  ──► [consulting-service :8084] ──► (consulting-db)   [EMPTY SKELETON → آرش]
   └──► /api/v1/assessments/** ──► [assessment-service :8000] ──► (assessment-db)   [ENGINE READY → وهاب]
```

*(تذکر فنی: در زمان استقرار، پورت‌های داخلی سرویس‌ها در `docker-compose.yml` نباید تداخل داشته باشند؛ مثلاً `user-service` روی `8082`، `admin-service` روی `8083` و `consulting-service` روی `8084` تنظیم شوند تا با هم تداخل نکنند.)*

| ماژول | استک فنی | وضعیت کنونی | مالک |
| :--- | :--- | :--- | :--- |
| **`auth-service`** | Java 24, Spring Boot 4.1.0, PostgreSQL 16, Liquibase | تکمیل‌شده (مرجع معماری) | تغییر نکند |
| **`discovery-service`** | Java 24, Spring Cloud Netflix Eureka (`8761`) | پیاده‌سازی‌شده (پایه) | مهدی (ثبت سرویس‌ها) |
| **`gateway-service`** | Java 24, Spring Cloud Gateway WebFlux (`8080`) | دارای باگ i18n/Jackson3 و نبود Routeهای جدید | **آرش (`ARASH-01`)** |
| **`user-service`** | Java 24, Spring Boot 4.1.0, Liquibase | اسکلت خالی در مخزن | **آرش (`ARASH-02`)** |
| **`admin-service`** | Java 24, Spring Boot 4.1.0 | تکمیل‌شده روی سیستم لوکال مهدی (هنوز پوش نشده) | **مهدی (`MAHDI-01`)** |
| **`consulting-service`** | Java 24, Spring Boot 4.1.0, Liquibase | اسکلت خالی با `.permitAll()` | **آرش (`ARASH-03`)** |
| **`assessment-service`** | Python 3.12+, FastAPI, SQLAlchemy Async, Alembic (`8000`) | موتور 3PL IRT/MFI + ۱۸۴ سؤال (سنین ۸–۱۸) + کارنامه تحلیلی + `selection-trace` آماده | **وهاب (`VAHAB-01..04`)** |
| **`frontend`** | React 19, Vite 8, TS 6, Tailwind v4, Shadcn/Radix (`3000`) | شالوده فنی + `/assessment` و `/assessment/selection-lab` آماده؛ رنگ‌بندی پایه سیاه‌وسفید و نیازمند بازطراحی بصری + اسلایس‌های `auth`, `profile`, `admin`, `clinician` | **آیدا (`AIDA-01..06`)** |

---

## ۳. قراردادهای حیاتی برای جلوگیری از خرابی یکپارچه‌سازی

### ۳.۱. قرارداد خطا و سازگاری Spring Boot 4.1.0 (بسیار مهم برای بک‌اند)
- پروژه والد از **Java 24** و **Spring Boot 4.1.0** استفاده می‌کند که مبتنی بر **Jackson 3** (`tools.jackson.databind.json.JsonMapper`) است، نه Jackson 2 (`com.fasterxml.jackson.databind.ObjectMapper`). در `GatewayErrorWriter` و سرویس‌های جدید حتماً از استاندارد Boot 4 مشابه `AuthSecurityErrorHandler` استفاده کنید.
- در `gateway-service` نام فایل‌های `i18n` به صورت مفرد (`message.properties`, `message_en.properties`, `message_fa.properties`) است ولی در YAML اشتباهاً `i18n/messages` تنظیم شده که باید اصلاح شود.
- فرمت خطای تمام سرویس‌ها (`application/problem+json`) باید شامل فیلدهای زیر باشد تا `ApiError` در فرانت‌اند آن را پارس کند:
  ```json
  {
    "type": "https://api.nextminds.ir/problems/...",
    "title": "...",
    "status": 400,
    "detail": "...",
    "instance": "/api/v1/...",
    "isSuccess": false,
    "errorCode": "BAD_REQUEST",
    "correlationId": "uuid",
    "errors": { "field": "message" }
  }
  ```

### ۳.۲. نکات و تله‌های فنی فرانت‌اند (`frontend/` — بسیار مهم برای آیدا)
1. **معماری Vertical Slice (`verify-architecture.mjs`):**
   - هر اسلایس جدید باید در `src/features/<slice-name>/` ایجاد شود و **تنها نقطه ورود عمومی آن `src/features/<slice-name>/index.ts`** باشد. ایمپورت مستقیم به داخل فایل‌های درونی یک اسلایس از بیرون ممنوع است.
   - کامپوننت‌ها هرگز نباید `axios` خام را صدا بزنند؛ فقط از `apiClient` در `@/services/api` استفاده کنید.
2. **تله بحرانی Tailwind CSS v4 در این مخزن:**
   - فایل `src/styles/tokens/theme.css` در `@theme inline` متغیرهای `--spacing-xl: 2rem` (`32px`)، `--spacing-2xl: 2.5rem` و ... را تعریف کرده است. در Tailwind v4 این نام‌گذاری باعث می‌شود کلاس‌هایی مثل `max-w-xl` به جای `36rem` مقدار **`2rem` (`32px`)** بگیرند و کادر صفحه له شود!
   - **راه‌حل اجباری:** برای عرض کانتینرها و کارت‌ها از مقادیر صریح مثل `max-w-[36rem]`، `max-w-[42rem]`، `max-w-[56rem]` یا `max-w-full` استفاده کنید.
3. **حفظ اسکریپت‌های تست پایه (`verify-components.mjs` و `verify-tokens.mjs`):**
   - `verify-tokens.mjs` تقارن کامل کلیدهای `:root` و `.dark` و حضور ۱۹ متغیر پایه Shadcn را چک می‌کند. هنگام زیباسازی پالت رنگ در `colors.css`، نام متغیرها را حذف نکنید و تقارن `:root` و `.dark` را حفظ کنید.
   - در `RootView` (`/`) وجود `Card`, `Input`, `Button`, `Dialog` توسط `verify-components.mjs` تست می‌شود؛ بنابراین هنگام ساخت `AppShell` یا صفحه اصلی، تست‌های `npm --prefix frontend run test` (به‌جز `verify-skills.mjs` اگر `.agents` نباشد) باید سبز بمانند.
4. **حذف فیلد موقت توکن از `/assessment`:**
   - در `AssessmentOnboarding` فعلی یک فیلد موقت برای پیست کردن JWT جهت تست ایزوله وجود دارد. به محض پیاده‌سازی `features/auth` و تنظیم سراسری `setAuthTokenProvider`، این فیلد باید **به‌طور کامل حذف شود**.

### ۳.۳. مشخصات دقیق میکروسرویس مشاوران و میزکار تخصصی (`consulting-service`)
- **نقش‌های سازمانی (`organization_members`):** `CLINIC_ADMIN`, `CLINICIAN`, `PSYCHOMETRICIAN`, `ANALYST`, `SCHOOL_COUNSELOR` (علاوه بر نقش‌های `PARENT` و `STUDENT`).
- **دعوت‌نامه یک‌بارمصرف (`member_invites`):** ذخیره فقط `SHA-256` هش توکن با انقضای ۳۰ روزه و مصرف اتمیک.
- **کنترل هم‌زمانی در داوری سؤالات (`item_reviews`):** کلید یکتای `(reviewer_user_id, kind, target_id, target_version)`؛ ذخیره خودکار `DRAFT` و ثبت نهایی `SUBMITTED` همراه با عدد `revision` (در صورت تعارض هم‌زمان **`409 Conflict`** برگردد) و ثبت تاریخچه تغییرناپذیر در `item_review_history`.
- **منطق صف‌های داوری:** اولویت‌بندی دقیق `CRITICAL` (کلید غلط/مبهم یا حذف) ← `DISAGREEMENT` (اختلاف نظر داوران) ← `REVIEWED` / `UNREVIEWED`؛ محاسبه نسبت توافق توصیفی (CVI) با حذف موارد «خارج از تخصص» از مخرج.
- **فرم پیش از آزمون خانواده (`family_contexts`):** پرسش‌های `P01–P10` به صورت `snapshot` تغییرناپذیر متصل به نشست بدون نام کودک/مدرسه/تشخیص؛ **سابقه کلاس اجباری (مثل Scratch) هرگز به امتیاز یا استعداد تبدیل نشود.**
- **کنترل کیفیت روز آزمون (`session_quality_records`):** خوداظهاری کوتاه کودک + رویدادهای عینی ناظر و خروجی سه‌گانه `INTERPRETABLE` | `CAUTION` | `INSUFFICIENT`.
- **قفل انتشار کارنامه (HITL Gate):** والد (`PARENT`) تا زمانی که وضعیت گزارش به `SIGNED_BY_CLINICIAN` نرسیده باشد یا رضایت‌نامه فعال نباشد، اجازه مشاهده کارنامه را ندارد (`403`/`409`).

### ۳.۴. مشخصات موتور آزمون و بانک سؤالات (`assessment-service`)
- **بازه سنی:** **۸ تا ۱۸ سال** در ۳ باند سنی: A (۸–۱۱)، B (۱۱–۱۴)، C (۱۴–۱۸).
- **بانک سؤالات:** ۱۸۴ گویه کپسوله‌شده در `data/sample_questions.json` با وزن‌های ۵ بعدی (`logical_reasoning`, `algorithmic_thinking`, `problem_solving`, `spatial_reasoning`, `computational_thinking`) و پارامترهای 3PL ($a, b, c=0.25$).
- **الگوریتم:** 3PL IRT + Fisher Information Posterior SE + Maximum Fisher Information (MFI) + تشخیص پاسخ شتاب‌زده (`< 1500ms`) + `Idempotency-Key` اجباری در ثبت پاسخ.
- **آزمایشگاه تست انتخاب سؤال:** `POST /api/v1/internal/simulations/selection-trace` و مسیر فرانت `/assessment/selection-lab` در فاز اول باز هستند و در فاز بعد به نقش‌های `ADMIN` و `CLINICIAN` محدود می‌شوند.

---

## ۴. ترتیب اجرای موازی و وابستگی‌های تیمی

1. **شروع فوری و هم‌زمان (بدون انتظار):**
   - **مهدی (`MAHDI-01`, `MAHDI-02`):** تست و پوش `admin-service` + یکسان‌سازی کلیدهای RSA و `.env`.
   - **آرش (`ARASH-02`):** تکمیل `user-service`.
   - **آیدا (`AIDA-01`, `AIDA-02`):** زیباسازی بیس فرانت‌اند (پالت رنگ، فونت فارسی، RTL، `AppShell`) + شروع `features/auth` بر اساس قرارداد `docs/auth-api.md`.
2. **موج دوم (پس از `MAHDI-01` و `MAHDI-02`):**
   - **آرش (`ARASH-01`, `ARASH-03`):** رفع باگ‌های Gateway و Routeها + پیاده‌سازی کامل `consulting-service`.
   - **وهاب (`VAHAB-02`, `VAHAB-04`):** سینک `public.pem` و ثبت Eureka + غنی‌سازی سؤالات و افزودن `diagram` به خروجی.
3. **موج سوم (تکمیل یکپارچگی):**
   - **آیدا (`AIDA-03`, `AIDA-04B`, `AIDA-05`, `AIDA-06`):** اتصال `profile`، حذف توکن دستی از آزمون + زیباسازی فضای آزمون، پنل `admin` و میزکار `clinician`.
   - **مهدی (`MAHDI-03`, `MAHDI-04`, `MAHDI-05`):** تکمیل `docker-compose.yml`، تست ترافیک Eureka/Gateway و راه‌اندازی CI/SSL.

---

## ۵. چک‌لیست تأیید پیش از تحویل هر تسک

هر ایجنت موظف است پیش از پایان کار خود دستورات زیر را روی بخش مربوطه اجرا و سبز بودن آن‌ها را تأیید کند:
- **سرویس‌های جاوا:** `./mvnw -pl <service-name> -am test`
- **سرویس آزمون پایتون:** `pytest tests -q`
- **فرانت‌اند:** `npm --prefix frontend run lint` و `npm --prefix frontend run build` و اجرای `scripts/verify-components.mjs`, `scripts/verify-architecture.mjs`, `scripts/verify-tokens.mjs`
- **زیرساخت:** `docker compose config`

</div>
