import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

export interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode)
  onError?: (error: Error, errorInfo: ErrorInfo) => void
  onReset?: () => void
  resetKeys?: unknown[]
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: unknown): ErrorBoundaryState {
    const normalizedError = error instanceof Error ? error : new Error(String(error))
    return { hasError: true, error: normalizedError }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.props.onError?.(error, errorInfo)
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps): void {
    if (this.state.hasError && this.props.resetKeys) {
      const prevKeys = prevProps.resetKeys
      const currentKeys = this.props.resetKeys
      const hasChanged =
        !prevKeys ||
        currentKeys.length !== prevKeys.length ||
        currentKeys.some((val, idx) => !Object.is(val, prevKeys[idx]))
      if (hasChanged) {
        this.resetErrorBoundary()
      }
    }
  }

  resetErrorBoundary = (): void => {
    this.props.onReset?.()
    this.setState({ hasError: false, error: null })
  }

  render(): ReactNode {
    if (this.state.hasError && this.state.error) {
      if (typeof this.props.fallback === 'function') {
        return this.props.fallback(this.state.error, this.resetErrorBoundary)
      }
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div
          role="alert"
          data-slot="error-boundary-fallback"
          className="flex min-h-screen items-center justify-center p-4"
        >
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle className="text-destructive">Something went wrong</CardTitle>
              <CardDescription>
                An unexpected error occurred while rendering this view.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-md bg-muted p-3 text-xs font-mono text-muted-foreground break-words overflow-auto max-h-40">
                {this.state.error.message || 'Unknown error'}
              </div>
            </CardContent>
            <CardFooter className="justify-end">
              <Button variant="outline" onClick={this.resetErrorBoundary}>
                Try Again
              </Button>
            </CardFooter>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}
