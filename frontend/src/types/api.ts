/**
 * Core API types and contracts.
 */

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'OPTIONS' | 'HEAD'

export interface ApiResponse<T = unknown> {
  data: T
  status: number
  message?: string
}

export interface ApiErrorResponse {
  type?: string
  title?: string
  status?: number
  detail?: string
  instance?: string
  message?: string
  code?: string
  errorCode?: string
  isSuccess?: boolean
  details?: unknown
  errors?: unknown
  correlationId?: string
  timestamp?: string
}

export type TokenProvider = () => string | null | Promise<string | null>
