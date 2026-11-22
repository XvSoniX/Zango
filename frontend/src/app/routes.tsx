import { createBrowserRouter, createMemoryRouter, type RouteObject } from 'react-router'
import { RootView } from './root-view'
import { NotFoundView } from './not-found-view'

export const appRoutes: RouteObject[] = [
  {
    path: '/',
    element: <RootView />,
  },
  {
    path: '*',
    element: <NotFoundView />,
  },
]

export interface CreateRouterOptions {
  initialEntries?: string[]
}

/**
 * Creates a React Router instance.
 * Automatically selects MemoryRouter in non-browser/SSR environments or when initialEntries are specified,
 * and BrowserRouter in the client.
 */
export function createAppRouter(routes: RouteObject[] = appRoutes, options?: CreateRouterOptions) {
  if (typeof window === 'undefined' || options?.initialEntries) {
    return createMemoryRouter(routes, {
      initialEntries: options?.initialEntries ?? ['/'],
    })
  }
  return createBrowserRouter(routes)
}

let defaultRouterInstance: ReturnType<typeof createAppRouter> | null = null

export function getDefaultRouter() {
  if (!defaultRouterInstance) {
    defaultRouterInstance = createAppRouter()
  }
  return defaultRouterInstance
}

export function resetDefaultRouter(): void {
  defaultRouterInstance = null
}
