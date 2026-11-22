import { env } from './env'
import { HTTP_STATUS, ROUTE_PATHS, STORAGE_KEYS } from './constants'

export const appConfig = Object.freeze({
  env,
  routes: ROUTE_PATHS,
  storage: STORAGE_KEYS,
  httpStatus: HTTP_STATUS,
})

export { env, parseEnv } from './env'
export type { AppEnv } from './env'
export { HTTP_STATUS, ROUTE_PATHS, STORAGE_KEYS } from './constants'
export type { HttpStatus } from './constants'
