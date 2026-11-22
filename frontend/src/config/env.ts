export interface AppEnv {
  readonly API_BASE_URL: string
  readonly APP_NAME: string
  readonly APP_ENV: 'development' | 'production' | 'test'
  readonly API_TIMEOUT: number
  readonly IS_DEV: boolean
  readonly IS_PROD: boolean
  readonly IS_TEST: boolean
}

/**
 * Parses and validates environment variables.
 * Provides fallback defaults when variables are absent or invalid.
 */
export function parseEnv(rawEnv?: Record<string, string | undefined> | null): AppEnv {
  const safeEnv: Record<string, string | undefined> =
    rawEnv ??
    (typeof import.meta !== 'undefined' && import.meta?.env
      ? (import.meta.env as unknown as Record<string, string | undefined>)
      : {})

  const rawEnvType = safeEnv.VITE_APP_ENV || 'development'
  const APP_ENV: 'development' | 'production' | 'test' =
    rawEnvType === 'production' || rawEnvType === 'test' ? rawEnvType : 'development'

  const timeoutRaw = safeEnv.VITE_API_TIMEOUT
  const parsedTimeout = timeoutRaw ? Number.parseInt(timeoutRaw, 10) : 15000
  const API_TIMEOUT = Number.isNaN(parsedTimeout) || parsedTimeout <= 0 ? 15000 : parsedTimeout

  return Object.freeze({
    API_BASE_URL: safeEnv.VITE_API_BASE_URL || '/api',
    APP_NAME: safeEnv.VITE_APP_NAME || 'Zango',
    APP_ENV,
    API_TIMEOUT,
    IS_DEV: APP_ENV === 'development',
    IS_PROD: APP_ENV === 'production',
    IS_TEST: APP_ENV === 'test',
  })
}

export const env: AppEnv = parseEnv()
