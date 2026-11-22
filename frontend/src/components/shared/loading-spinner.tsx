import React from 'react'
import { cn } from '@/lib/utils'

export interface LoadingSpinnerProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: 'sm' | 'default' | 'lg'
  label?: string
}

const sizeClasses = {
  sm: 'h-4 w-4 border-2',
  default: 'h-6 w-6 border-2',
  lg: 'h-8 w-8 border-[3px]',
}

export function LoadingSpinner({
  size = 'default',
  label = 'Loading...',
  className,
  ...props
}: LoadingSpinnerProps) {
  return (
    <div
      role="status"
      aria-label={label}
      data-slot="loading-spinner"
      className={cn('inline-flex items-center justify-center', className)}
      {...props}
    >
      <span
        className={cn(
          'animate-spin rounded-full border-solid border-current border-t-transparent text-primary',
          sizeClasses[size],
        )}
      />
      <span className="sr-only">{label}</span>
    </div>
  )
}
