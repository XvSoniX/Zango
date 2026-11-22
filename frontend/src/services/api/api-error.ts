import axios, { type AxiosError } from 'axios'
import type { ApiErrorResponse } from '@/types'

export interface ApiErrorParams {
  message: string
  status?: number
  code?: string
  details?: unknown
  correlationId?: string
  instance?: string
  type?: string
  isNetworkError?: boolean
  isTimeout?: boolean
  isCanceled?: boolean
  rawError?: unknown
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details?: unknown
  readonly correlationId?: string
  readonly instance?: string
  readonly type?: string
  readonly isNetworkError: boolean
  readonly isTimeout: boolean
  readonly isCanceled: boolean
  readonly rawError?: unknown

  constructor(params: ApiErrorParams) {
    super(params.message)
    this.name = 'ApiError'
    this.status = params.status ?? 0
    this.code = params.code ?? 'UNKNOWN_ERROR'
    this.details = params.details
    this.correlationId = params.correlationId
    this.instance = params.instance
    this.type = params.type
    this.isNetworkError = params.isNetworkError ?? false
    this.isTimeout = params.isTimeout ?? false
    this.isCanceled = params.isCanceled ?? false
    this.rawError = params.rawError

    // Restore prototype chain
    Object.setPrototypeOf(this, new.target.prototype)
  }

  static fromAxiosError(error: unknown): ApiError {
    if (error instanceof ApiError) {
      return error
    }

    // Check for request cancellation (AbortController, CancelToken, CanceledError)
    const isCanceled =
      axios.isCancel(error) ||
      (error instanceof Error && (error.name === 'CanceledError' || error.name === 'AbortError')) ||
      (typeof error === 'object' &&
        error !== null &&
        'code' in error &&
        (error as { code?: string }).code === 'ERR_CANCELED')

    if (isCanceled) {
      return new ApiError({
        message:
          error instanceof Error && error.message && error.message !== 'canceled'
            ? error.message
            : 'The request was canceled.',
        code: 'REQUEST_CANCELED',
        status: 0,
        isCanceled: true,
        rawError: error,
      })
    }

    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<ApiErrorResponse>

      if (axiosError.code === 'ECONNABORTED' || axiosError.message.includes('timeout')) {
        return new ApiError({
          message: 'The request timed out. Please check your connection and try again.',
          code: 'REQUEST_TIMEOUT',
          status: 408,
          isTimeout: true,
          rawError: error,
        })
      }

      if (!axiosError.response) {
        return new ApiError({
          message: axiosError.message || 'Network error occurred. Unable to reach the server.',
          code: 'NETWORK_ERROR',
          status: 0,
          isNetworkError: true,
          rawError: error,
        })
      }

      const status = axiosError.response.status
      const responseData: unknown = axiosError.response.data
      const responseHeaders = axiosError.response.headers

      let message = axiosError.message || 'An unexpected API error occurred.'
      let code = `HTTP_${status}`
      let details: unknown = undefined
      let correlationId: string | undefined = undefined
      let instance: string | undefined = undefined
      let type: string | undefined = undefined

      // Fallback correlationId from response headers (e.g., Spring Gateway X-Correlation-ID)
      if (responseHeaders) {
        const headerId =
          responseHeaders['x-correlation-id'] ||
          responseHeaders['X-Correlation-ID'] ||
          (typeof responseHeaders.get === 'function'
            ? responseHeaders.get('x-correlation-id')
            : undefined)
        if (typeof headerId === 'string' && headerId.trim()) {
          correlationId = headerId
        }
      }

      if (Array.isArray(responseData)) {
        details = responseData
      } else if (responseData && typeof responseData === 'object') {
        if ('detail' in responseData && typeof responseData.detail === 'string') {
          message = responseData.detail
        } else if ('message' in responseData && typeof responseData.message === 'string') {
          message = responseData.message
        } else if ('title' in responseData && typeof responseData.title === 'string') {
          message = responseData.title
        }

        if ('errorCode' in responseData && typeof responseData.errorCode === 'string') {
          code = responseData.errorCode
        } else if ('code' in responseData && typeof responseData.code === 'string') {
          code = responseData.code
        }

        if ('details' in responseData && responseData.details !== undefined) {
          details = responseData.details
        } else if ('errors' in responseData && responseData.errors !== undefined) {
          details = responseData.errors
        }

        if ('correlationId' in responseData && typeof responseData.correlationId === 'string') {
          correlationId = responseData.correlationId
        }

        if ('instance' in responseData && typeof responseData.instance === 'string') {
          instance = responseData.instance
        }

        if ('type' in responseData && typeof responseData.type === 'string') {
          type = responseData.type
        }
      } else if (typeof responseData === 'string' && responseData.trim()) {
        if (!responseData.includes('<html')) {
          message = responseData
        }
      }

      return new ApiError({
        message,
        status,
        code,
        details,
        correlationId,
        instance,
        type,
        rawError: error,
      })
    }

    if (error instanceof Error) {
      if (error.name === 'TimeoutError' || error.message.toLowerCase().includes('timeout')) {
        return new ApiError({
          message: error.message || 'The request timed out.',
          code: 'REQUEST_TIMEOUT',
          status: 408,
          isTimeout: true,
          rawError: error,
        })
      }

      return new ApiError({
        message: error.message,
        code: 'CLIENT_ERROR',
        rawError: error,
      })
    }

    return new ApiError({
      message: String(error) || 'An unknown error occurred.',
      code: 'UNKNOWN_ERROR',
      rawError: error,
    })
  }

  static isApiError(value: unknown): value is ApiError {
    return value instanceof ApiError
  }

  static isCanceled(value: unknown): boolean {
    return value instanceof ApiError ? value.isCanceled : false
  }

  static isTimeout(value: unknown): boolean {
    return value instanceof ApiError ? value.isTimeout : false
  }

  static isNetworkError(value: unknown): boolean {
    return value instanceof ApiError ? value.isNetworkError : false
  }
}
