import axios from 'axios'
import type {
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from 'axios'
import { env } from '@/config/env'
import type { TokenProvider } from '@/types'
import { ApiError } from './api-error'

export interface CreateApiClientOptions {
  baseURL?: string
  timeout?: number
  headers?: Record<string, string>
  tokenProvider?: TokenProvider
}

let globalTokenProvider: TokenProvider | null = null

/**
 * Configure a global token provider for authorization headers.
 * Keeps auth loosely coupled without hardcoding domain-specific auth logic.
 */
export function setAuthTokenProvider(provider: TokenProvider | null): void {
  globalTokenProvider = provider
}

export function getAuthTokenProvider(): TokenProvider | null {
  return globalTokenProvider
}

/**
 * Factory to create configured Axios client instances.
 */
export function createApiClient(options: CreateApiClientOptions = {}): AxiosInstance {
  const {
    baseURL = env.API_BASE_URL,
    timeout = env.API_TIMEOUT,
    headers = {},
    tokenProvider,
  } = options

  const instance = axios.create({
    baseURL,
    timeout,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...headers,
    },
  })

  // Request Interceptor
  instance.interceptors.request.use(
    async (config: InternalAxiosRequestConfig) => {
      const currentTokenProvider = tokenProvider ?? globalTokenProvider
      if (currentTokenProvider) {
        try {
          const token = await currentTokenProvider()
          if (token && config.headers) {
            config.headers.Authorization = `Bearer ${token}`
          }
        } catch (error) {
          throw ApiError.fromAxiosError(error)
        }
      }
      return config
    },
    (error: unknown) => {
      return Promise.reject(ApiError.fromAxiosError(error))
    },
  )

  // Response Interceptor
  instance.interceptors.response.use(
    (response: AxiosResponse) => {
      return response
    },
    (error: unknown) => {
      return Promise.reject(ApiError.fromAxiosError(error))
    },
  )

  return instance
}

/**
 * Default singleton API client instance.
 */
export const apiClient: AxiosInstance = createApiClient()

/**
 * Generic request helper returning response.data and normalizing errors to ApiError.
 */
export async function apiRequest<T = unknown>(
  client: AxiosInstance,
  config: AxiosRequestConfig,
): Promise<T> {
  try {
    const response = await client.request<T>(config)
    return response.data
  } catch (error) {
    throw ApiError.fromAxiosError(error)
  }
}

/**
 * Centralized HTTP request utility functions.
 */
export const http = {
  request<T = unknown>(config: AxiosRequestConfig): Promise<T> {
    return apiRequest<T>(apiClient, config)
  },
  get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return apiRequest<T>(apiClient, { ...config, method: 'GET', url })
  },
  post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return apiRequest<T>(apiClient, { ...config, method: 'POST', url, data })
  },
  put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return apiRequest<T>(apiClient, { ...config, method: 'PUT', url, data })
  },
  patch<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return apiRequest<T>(apiClient, { ...config, method: 'PATCH', url, data })
  },
  delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return apiRequest<T>(apiClient, { ...config, method: 'DELETE', url })
  },
}
