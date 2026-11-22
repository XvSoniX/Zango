import { RouterProvider } from 'react-router'
import { createAppRouter, getDefaultRouter } from './routes'

export interface AppRouterProps {
  router?: ReturnType<typeof createAppRouter>
}

export function AppRouter({ router }: AppRouterProps) {
  const activeRouter = router ?? getDefaultRouter()
  return <RouterProvider router={activeRouter} />
}
