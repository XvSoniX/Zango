/**
 * Generic utility and structural types for the application.
 */

export type Nullable<T> = T | null
export type Optional<T> = T | undefined

export type ID = string | number

export interface PaginationParams {
  page?: number
  limit?: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  limit: number
  totalPages: number
}

export type AsyncStatus = 'idle' | 'pending' | 'success' | 'error'

export interface AsyncState<T, E = Error> {
  data: Nullable<T>
  status: AsyncStatus
  error: Nullable<E>
  isLoading: boolean
  isSuccess: boolean
  isError: boolean
}
