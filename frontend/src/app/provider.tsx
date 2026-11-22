import { Suspense, type ReactNode } from 'react'
import { ErrorBoundary } from '@/components/shared/error-boundary'
import { LoadingSpinner } from '@/components/shared/loading-spinner'

export interface AppProviderProps {
  children: ReactNode
}

export function AppProvider({ children }: AppProviderProps) {
  return (
    <ErrorBoundary>
      <Suspense
        fallback={
          <div role="status" className="flex min-h-screen items-center justify-center p-4">
            <LoadingSpinner size="lg" label="Loading application..." />
          </div>
        }
      >
        {children}
      </Suspense>
    </ErrorBoundary>
  )
}
