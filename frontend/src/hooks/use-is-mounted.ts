import { useRef, useEffect, useCallback } from 'react'

/**
 * Hook to track whether a component is currently mounted.
 * Useful for preventing memory leaks or state updates after unmount.
 */
export function useIsMounted(): () => boolean {
  const isMountedRef = useRef(false)

  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  return useCallback(() => isMountedRef.current, [])
}
