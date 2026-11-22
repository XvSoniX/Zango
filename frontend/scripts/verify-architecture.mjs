import assert from 'node:assert'
import { fileURLToPath } from 'node:url'
import { JSDOM } from 'jsdom'
import { createServer } from 'vite'
import React, { act } from 'react'
import ReactDOMServer from 'react-dom/server'
import ReactDOMClient from 'react-dom/client'
import axios from 'axios'

async function runArchitectureVerification() {
  console.log('\n=============================================')
  console.log('STARTING ARCHITECTURE VERIFICATION SUITE')
  console.log('=============================================\n')

  // Setup DOM environment
  const dom = new JSDOM('<!DOCTYPE html><html><body><div id="root"></div></body></html>', {
    url: 'http://localhost:3000',
    pretendToBeVisual: true,
  })
  global.window = dom.window
  global.document = dom.window.document
  global.HTMLElement = dom.window.HTMLElement
  global.SVGElement = dom.window.SVGElement
  global.Element = dom.window.Element
  global.Node = dom.window.Node
  global.getComputedStyle = dom.window.getComputedStyle.bind(dom.window)
  global.MutationObserver = dom.window.MutationObserver
  global.CustomEvent = dom.window.CustomEvent
  global.IS_REACT_ACT_ENVIRONMENT = true

  const frontendRoot = fileURLToPath(new URL('..', import.meta.url))
  const vite = await createServer({
    root: frontendRoot,
    server: { middlewareMode: true },
    appType: 'custom',
  })

  try {
    // -------------------------------------------------------------
    // 1. ENVIRONMENT & CONFIGURATION VERIFICATION
    // -------------------------------------------------------------
    console.log('1. Verifying Environment & Configuration Strategy...')
    const { parseEnv, env, appConfig, HTTP_STATUS, ROUTE_PATHS, STORAGE_KEYS } =
      await vite.ssrLoadModule('@/config/index')

    assert(env && typeof env === 'object', 'env object is exported')
    assert.strictEqual(typeof env.API_BASE_URL, 'string', 'API_BASE_URL is a string')
    assert.strictEqual(typeof env.API_TIMEOUT, 'number', 'API_TIMEOUT is a number')
    assert(env.API_TIMEOUT > 0, 'API_TIMEOUT is positive')
    assert(typeof env.IS_DEV === 'boolean', 'IS_DEV is a boolean')

    // Test parseEnv fallbacks and edge cases
    const defaultEnv = parseEnv({})
    assert.strictEqual(defaultEnv.API_BASE_URL, '/api', 'Default API_BASE_URL is /api')
    assert.strictEqual(defaultEnv.APP_NAME, 'Zango', 'Default APP_NAME is Zango')
    assert.strictEqual(defaultEnv.APP_ENV, 'development', 'Default APP_ENV is development')
    assert.strictEqual(defaultEnv.API_TIMEOUT, 15000, 'Default API_TIMEOUT is 15000')
    assert.strictEqual(defaultEnv.IS_DEV, true, 'Default IS_DEV is true')
    assert.strictEqual(defaultEnv.IS_PROD, false, 'Default IS_PROD is false')

    // Test parseEnv defensive handling with null and undefined
    const nullEnv = parseEnv(null)
    assert.strictEqual(nullEnv.API_BASE_URL, '/api', 'null rawEnv falls back to /api')
    assert.strictEqual(nullEnv.APP_ENV, 'development', 'null rawEnv falls back to development')

    const undefEnv = parseEnv(undefined)
    assert.strictEqual(undefEnv.API_BASE_URL, '/api', 'undefined rawEnv falls back to /api')

    // Test parseEnv with custom values
    const customEnv = parseEnv({
      VITE_API_BASE_URL: 'https://api.zango.io/v1',
      VITE_APP_NAME: 'Zango Production',
      VITE_APP_ENV: 'production',
      VITE_API_TIMEOUT: '30000',
    })
    assert.strictEqual(customEnv.API_BASE_URL, 'https://api.zango.io/v1')
    assert.strictEqual(customEnv.APP_NAME, 'Zango Production')
    assert.strictEqual(customEnv.APP_ENV, 'production')
    assert.strictEqual(customEnv.API_TIMEOUT, 30000)
    assert.strictEqual(customEnv.IS_PROD, true)
    assert.strictEqual(customEnv.IS_DEV, false)

    // Test parseEnv invalid timeout fallback
    const invalidTimeoutEnv = parseEnv({ VITE_API_TIMEOUT: 'invalid-number' })
    assert.strictEqual(invalidTimeoutEnv.API_TIMEOUT, 15000, 'Invalid timeout falls back to 15000')

    const negativeTimeoutEnv = parseEnv({ VITE_API_TIMEOUT: '-500' })
    assert.strictEqual(
      negativeTimeoutEnv.API_TIMEOUT,
      15000,
      'Negative timeout falls back to 15000',
    )

    // Constants verification
    assert.strictEqual(HTTP_STATUS.OK, 200)
    assert.strictEqual(HTTP_STATUS.CREATED, 201)
    assert.strictEqual(HTTP_STATUS.BAD_REQUEST, 400)
    assert.strictEqual(HTTP_STATUS.UNAUTHORIZED, 401)
    assert.strictEqual(HTTP_STATUS.FORBIDDEN, 403)
    assert.strictEqual(HTTP_STATUS.NOT_FOUND, 404)
    assert.strictEqual(HTTP_STATUS.INTERNAL_SERVER_ERROR, 500)
    assert.strictEqual(ROUTE_PATHS.HOME, '/')
    assert.strictEqual(ROUTE_PATHS.NOT_FOUND, '*')
    assert.strictEqual(STORAGE_KEYS.AUTH_TOKEN, 'zango_access_token')

    console.log('   ✓ Config and Env parsing and fallbacks verified.')

    // -------------------------------------------------------------
    // 2. CENTRALIZED API CLIENT & ERROR HANDLING
    // -------------------------------------------------------------
    console.log('2. Verifying Centralized API Client & Error Handling...')
    const {
      apiClient,
      createApiClient,
      ApiError,
      setAuthTokenProvider,
      getAuthTokenProvider,
      http,
      apiRequest,
    } = await vite.ssrLoadModule('@/services/api/index')

    assert(apiClient, 'apiClient is created')
    assert(typeof createApiClient === 'function', 'createApiClient factory is exported')
    assert(typeof ApiError === 'function', 'ApiError class is exported')

    // Create isolated client instance for testing
    const testClient = createApiClient({
      baseURL: 'https://test-api.zango.internal',
      timeout: 5000,
      headers: { 'X-Custom-Client': 'Architecture-Test' },
    })
    assert.strictEqual(testClient.defaults.baseURL, 'https://test-api.zango.internal')
    assert.strictEqual(testClient.defaults.timeout, 5000)
    assert.strictEqual(testClient.defaults.headers['Content-Type'], 'application/json')
    assert.strictEqual(testClient.defaults.headers['Accept'], 'application/json')
    assert.strictEqual(testClient.defaults.headers['X-Custom-Client'], 'Architecture-Test')

    // Test auth token provider hook
    assert.strictEqual(getAuthTokenProvider(), null, 'Initial token provider is null')
    setAuthTokenProvider(() => 'test-bearer-token-123')
    assert(typeof getAuthTokenProvider() === 'function', 'Token provider successfully set')

    // Simulate request interceptor execution
    const mockRequestConfig = { headers: {} }
    const interceptorHandler = testClient.interceptors.request.handlers[0].fulfilled
    const interceptedConfig = await interceptorHandler(mockRequestConfig)
    assert.strictEqual(
      interceptedConfig.headers.Authorization,
      'Bearer test-bearer-token-123',
      'Authorization header attached by request interceptor',
    )

    // Clear token provider
    setAuthTokenProvider(null)
    const emptyConfig = { headers: {} }
    const interceptedEmpty = await interceptorHandler(emptyConfig)
    assert.strictEqual(
      interceptedEmpty.headers.Authorization,
      undefined,
      'Authorization header omitted when token provider is null',
    )

    // Test TokenProvider rejected promise escalation
    setAuthTokenProvider(async () => {
      throw new Error('Auth token expired or refresh failed')
    })
    let tokenRejectionError = null
    try {
      await interceptorHandler({ headers: {} })
    } catch (err) {
      tokenRejectionError = err
    }
    assert(tokenRejectionError !== null, 'Token provider rejection was caught and escalated')
    assert(ApiError.isApiError(tokenRejectionError), 'Escalated token error is an ApiError')
    assert.strictEqual(
      tokenRejectionError.message,
      'Auth token expired or refresh failed',
      'Original token error message preserved',
    )
    setAuthTokenProvider(null)

    // ApiError class tests
    const manualError = new ApiError({
      message: 'Resource not found',
      status: 404,
      code: 'RESOURCE_NOT_FOUND',
      details: { id: 'item-99' },
    })
    assert(manualError instanceof Error, 'ApiError is an instance of Error')
    assert(ApiError.isApiError(manualError), 'ApiError.isApiError correctly identifies instance')
    assert.strictEqual(manualError.status, 404)
    assert.strictEqual(manualError.code, 'RESOURCE_NOT_FOUND')
    assert.deepStrictEqual(manualError.details, { id: 'item-99' })
    assert.strictEqual(manualError.isNetworkError, false)
    assert.strictEqual(manualError.isTimeout, false)
    assert.strictEqual(manualError.isCanceled, false)

    // Transform Axios 400 response error (RFC 7807 problem+json)
    const mockAxios400 = {
      isAxiosError: true,
      message: 'Request failed with status code 400',
      response: {
        status: 400,
        headers: {
          'x-correlation-id': 'fallback-header-correlation-id',
        },
        data: {
          type: 'http://localhost/problems/bad-request',
          title: 'Invalid request',
          detail: 'The request is not valid.',
          errorCode: 'BAD_REQUEST',
          instance: '/api/v1/auth/register',
          correlationId: '4401740b-20f9-4866-aa25-83f9eae7b9fe',
          errors: [{ field: 'email', message: 'Invalid format' }],
        },
      },
    }
    const converted400 = ApiError.fromAxiosError(mockAxios400)
    assert(ApiError.isApiError(converted400))
    assert.strictEqual(converted400.status, 400)
    assert.strictEqual(converted400.code, 'BAD_REQUEST')
    assert.strictEqual(converted400.message, 'The request is not valid.')
    assert.strictEqual(converted400.correlationId, '4401740b-20f9-4866-aa25-83f9eae7b9fe')
    assert.strictEqual(converted400.instance, '/api/v1/auth/register')
    assert.strictEqual(converted400.type, 'http://localhost/problems/bad-request')
    assert.deepStrictEqual(converted400.details, [{ field: 'email', message: 'Invalid format' }])

    // Transform Axios error with header-based X-Correlation-ID (no body correlationId)
    const mockAxios500 = {
      isAxiosError: true,
      message: 'Request failed with status code 500',
      response: {
        status: 500,
        headers: {
          'x-correlation-id': 'gw-trace-999-header',
        },
        data: {
          detail: 'Internal Server Error',
        },
      },
    }
    const converted500 = ApiError.fromAxiosError(mockAxios500)
    assert.strictEqual(
      converted500.correlationId,
      'gw-trace-999-header',
      'Header-based X-Correlation-ID captured',
    )

    // Transform Axios Network Error
    const mockAxiosNetworkError = {
      isAxiosError: true,
      message: 'Network Error',
      response: undefined,
    }
    const convertedNetwork = ApiError.fromAxiosError(mockAxiosNetworkError)
    assert.strictEqual(convertedNetwork.status, 0)
    assert.strictEqual(convertedNetwork.code, 'NETWORK_ERROR')
    assert.strictEqual(convertedNetwork.isNetworkError, true)
    assert.strictEqual(ApiError.isNetworkError(convertedNetwork), true)
    assert.strictEqual(convertedNetwork.isCanceled, false)

    // Transform Request Cancellation (AbortController / CanceledError)
    const mockAxiosCanceled = {
      isAxiosError: true,
      code: 'ERR_CANCELED',
      name: 'CanceledError',
      message: 'canceled',
      response: undefined,
    }
    const convertedCanceled = ApiError.fromAxiosError(mockAxiosCanceled)
    assert(ApiError.isApiError(convertedCanceled), 'Canceled error is ApiError')
    assert.strictEqual(convertedCanceled.code, 'REQUEST_CANCELED', 'Cancellation code assigned')
    assert.strictEqual(convertedCanceled.isCanceled, true, 'isCanceled flag is true')
    assert.strictEqual(
      convertedCanceled.isNetworkError,
      false,
      'Canceled request is NOT treated as network error',
    )
    assert.strictEqual(
      ApiError.isCanceled(convertedCanceled),
      true,
      'ApiError.isCanceled helper works',
    )

    // Transform Axios Timeout Error
    const mockAxiosTimeout = {
      isAxiosError: true,
      code: 'ECONNABORTED',
      message: 'timeout of 5000ms exceeded',
      response: undefined,
    }
    const convertedTimeout = ApiError.fromAxiosError(mockAxiosTimeout)
    assert.strictEqual(convertedTimeout.status, 408)
    assert.strictEqual(convertedTimeout.code, 'REQUEST_TIMEOUT')
    assert.strictEqual(convertedTimeout.isTimeout, true)
    assert.strictEqual(ApiError.isTimeout(convertedTimeout), true)
    assert.strictEqual(convertedTimeout.isCanceled, false)

    // Non-Axios generic Error
    const genericErr = new Error('Generic JavaScript Error')
    const convertedGeneric = ApiError.fromAxiosError(genericErr)
    assert.strictEqual(convertedGeneric.code, 'CLIENT_ERROR')
    assert.strictEqual(convertedGeneric.message, 'Generic JavaScript Error')

    // String error
    const convertedString = ApiError.fromAxiosError('Unexpected string exception')
    assert.strictEqual(convertedString.code, 'UNKNOWN_ERROR')
    assert.strictEqual(convertedString.message, 'Unexpected string exception')

    // Verify http helper definitions
    assert(typeof http.request === 'function', 'http.request is a function')
    assert(typeof http.get === 'function', 'http.get is a function')
    assert(typeof http.post === 'function', 'http.post is a function')
    assert(typeof http.put === 'function', 'http.put is a function')
    assert(typeof http.patch === 'function', 'http.patch is a function')
    assert(typeof http.delete === 'function', 'http.delete is a function')

    console.log('   ✓ API Client, interceptors, and ApiError transformations verified.')

    // -------------------------------------------------------------
    // 3. REACT ROUTER & NAVIGATION INFRASTRUCTURE
    // -------------------------------------------------------------
    console.log('3. Verifying React Router Infrastructure...')
    const { createAppRouter, appRoutes, getDefaultRouter, resetDefaultRouter } =
      await vite.ssrLoadModule('@/app/routes')
    const { AppRouter } = await vite.ssrLoadModule('@/app/router')

    assert(Array.isArray(appRoutes), 'appRoutes is an array')
    assert(appRoutes.length >= 2, 'appRoutes defines root and not-found routes')
    assert(typeof resetDefaultRouter === 'function', 'resetDefaultRouter is exported')

    // Reset router instance check
    resetDefaultRouter()
    const routerA = getDefaultRouter()
    const routerB = getDefaultRouter()
    assert.strictEqual(routerA, routerB, 'getDefaultRouter returns singleton before reset')
    resetDefaultRouter()
    const routerC = getDefaultRouter()
    assert.notStrictEqual(routerA, routerC, 'resetDefaultRouter clears cached router instance')
    resetDefaultRouter()

    // Root route rendering test
    const homeRouter = createAppRouter(appRoutes, { initialEntries: ['/'] })
    const homeHtml = ReactDOMServer.renderToString(
      React.createElement(AppRouter, { router: homeRouter }),
    )
    assert(homeHtml.includes('data-slot="card"'), 'Root route renders verification card')
    assert(homeHtml.includes('Shadcn/ui Verification'), 'Root route renders card title')

    // 404 Not Found route rendering test
    const notFoundRouter = createAppRouter(appRoutes, { initialEntries: ['/non-existent-page'] })
    const notFoundHtml = ReactDOMServer.renderToString(
      React.createElement(AppRouter, { router: notFoundRouter }),
    )
    assert(notFoundHtml.includes('data-slot="not-found-view"'), '404 route renders not-found-view')
    assert(notFoundHtml.includes('404'), '404 heading rendered')
    assert(notFoundHtml.includes('Back to Home'), 'Back to Home link rendered')

    console.log('   ✓ Router matching, root route, and 404 fallback verified.')

    // -------------------------------------------------------------
    // 4. GLOBAL PROVIDERS & ERROR BOUNDARY
    // -------------------------------------------------------------
    console.log('4. Verifying Global Providers & Error Boundary...')
    const { AppProvider } = await vite.ssrLoadModule('@/app/provider')
    const { ErrorBoundary, LoadingSpinner } = await vite.ssrLoadModule('@/components/shared/index')

    // LoadingSpinner rendering and props
    const spinnerSm = ReactDOMServer.renderToString(
      React.createElement(LoadingSpinner, { size: 'sm', label: 'Fetching data' }),
    )
    assert(spinnerSm.includes('role="status"'), 'Spinner has role=status')
    assert(spinnerSm.includes('aria-label="Fetching data"'), 'Spinner label applied')
    assert(spinnerSm.includes('h-4 w-4'), 'Spinner sm size applied')

    const spinnerLg = ReactDOMServer.renderToString(
      React.createElement(LoadingSpinner, { size: 'lg' }),
    )
    assert(spinnerLg.includes('h-8 w-8'), 'Spinner lg size applied')
    assert(spinnerLg.includes('border-[3px]'), 'Spinner lg uses valid Tailwind border-[3px]')

    // ErrorBoundary normal rendering
    const normalRender = ReactDOMServer.renderToString(
      React.createElement(
        ErrorBoundary,
        null,
        React.createElement('div', { id: 'healthy-child' }, 'Healthy Content'),
      ),
    )
    assert(normalRender.includes('Healthy Content'), 'Normal content rendered when no error')

    // ErrorBoundary error trapping in client DOM
    const testContainer = dom.window.document.createElement('div')
    dom.window.document.body.appendChild(testContainer)
    const testRoot = ReactDOMClient.createRoot(testContainer)

    let caughtError = null
    const ProblematicComponent = () => {
      throw new Error('Simulated runtime render crash!')
    }

    // Suppress console.error during expected error boundary test
    const originalConsoleError = console.error
    console.error = () => {}

    try {
      await act(async () => {
        testRoot.render(
          React.createElement(
            ErrorBoundary,
            {
              onError: (err) => {
                caughtError = err
              },
            },
            React.createElement(ProblematicComponent),
          ),
        )
      })
    } finally {
      console.error = originalConsoleError
    }

    assert(caughtError !== null, 'ErrorBoundary caught simulated render error')
    assert.strictEqual(caughtError.message, 'Simulated runtime render crash!')
    assert(
      testContainer.innerHTML.includes('data-slot="error-boundary-fallback"'),
      'ErrorBoundary fallback card mounted into DOM',
    )
    assert(
      testContainer.innerHTML.includes('Something went wrong'),
      'Error Title rendered in fallback card',
    )
    assert(
      testContainer.innerHTML.includes('Simulated runtime render crash!'),
      'Error message displayed in fallback details',
    )

    // Cleanup test container between test runs
    await act(async () => {
      testRoot.unmount()
    })
    testContainer.innerHTML = ''
    const stringRoot = ReactDOMClient.createRoot(testContainer)

    // Test ErrorBoundary with thrown string (non-Error object)
    let caughtStringError = null
    const StringThrowComponent = () => {
      throw 'Raw string exception from child component!'
    }

    console.error = () => {}
    try {
      await act(async () => {
        stringRoot.render(
          React.createElement(
            ErrorBoundary,
            {
              onError: (err) => {
                caughtStringError = err
              },
            },
            React.createElement(StringThrowComponent),
          ),
        )
      })
    } finally {
      console.error = originalConsoleError
    }

    assert(caughtStringError !== null, 'ErrorBoundary caught thrown string')
    assert(
      testContainer.innerHTML.includes('Raw string exception from child component!'),
      'String error message displayed in fallback details without crashing boundary',
    )

    await act(async () => {
      stringRoot.unmount()
    })
    testContainer.innerHTML = ''
    const resetRoot = ReactDOMClient.createRoot(testContainer)

    // Test ErrorBoundary auto-reset on resetKeys change
    let shouldCrash = false
    const ConditionalCrashComponent = () => {
      if (shouldCrash) {
        throw new Error('Crashing state!')
      }
      return React.createElement('div', { id: 'recovered-view' }, 'Recovered Successfully')
    }

    shouldCrash = true
    console.error = () => {}
    try {
      await act(async () => {
        resetRoot.render(
          React.createElement(
            ErrorBoundary,
            { resetKeys: ['state-1'] },
            React.createElement(ConditionalCrashComponent),
          ),
        )
      })
    } finally {
      console.error = originalConsoleError
    }
    assert(
      testContainer.innerHTML.includes('data-slot="error-boundary-fallback"'),
      'ErrorBoundary in error fallback state',
    )

    // Now update state and change resetKeys to trigger reset
    shouldCrash = false
    await act(async () => {
      resetRoot.render(
        React.createElement(
          ErrorBoundary,
          { resetKeys: ['state-2'] },
          React.createElement(ConditionalCrashComponent),
        ),
      )
    })
    assert(
      testContainer.innerHTML.includes('Recovered Successfully'),
      'ErrorBoundary reset automatically when resetKeys changed',
    )

    // Cleanup test container
    await act(async () => {
      resetRoot.unmount()
    })
    testContainer.remove()

    // AppProvider tree verification
    const providerHtml = ReactDOMServer.renderToString(
      React.createElement(AppProvider, null, React.createElement('div', null, 'Provider Child')),
    )
    assert(providerHtml.includes('Provider Child'), 'AppProvider correctly mounts child hierarchy')

    console.log('   ✓ AppProvider, ErrorBoundary, and LoadingSpinner verified.')

    // -------------------------------------------------------------
    // 5. CUSTOM HOOKS VERIFICATION
    // -------------------------------------------------------------
    console.log('5. Verifying Custom Hooks (useDisclosure, useDebounce, useIsMounted)...')
    const { useDisclosure, useDebounce, useIsMounted } = await vite.ssrLoadModule('@/hooks/index')

    assert(typeof useDisclosure === 'function', 'useDisclosure is exported')
    assert(typeof useDebounce === 'function', 'useDebounce is exported')
    assert(typeof useIsMounted === 'function', 'useIsMounted is exported')

    // Test useDisclosure in client DOM
    let disclosureHandle = null
    const DisclosureTestComponent = () => {
      disclosureHandle = useDisclosure(false)
      return React.createElement('div', null, `isOpen: ${disclosureHandle.isOpen}`)
    }

    const hookContainer = dom.window.document.createElement('div')
    dom.window.document.body.appendChild(hookContainer)
    const hookRoot = ReactDOMClient.createRoot(hookContainer)

    await act(async () => {
      hookRoot.render(React.createElement(DisclosureTestComponent))
    })

    assert.strictEqual(disclosureHandle.isOpen, false, 'useDisclosure initially false')

    await act(async () => {
      disclosureHandle.open()
    })
    assert.strictEqual(disclosureHandle.isOpen, true, 'useDisclosure open() sets true')

    await act(async () => {
      disclosureHandle.close()
    })
    assert.strictEqual(disclosureHandle.isOpen, false, 'useDisclosure close() sets false')

    await act(async () => {
      disclosureHandle.toggle()
    })
    assert.strictEqual(disclosureHandle.isOpen, true, 'useDisclosure toggle() flips state to true')

    await act(async () => {
      disclosureHandle.setOpen(false)
    })
    assert.strictEqual(disclosureHandle.isOpen, false, 'useDisclosure setOpen(false) works')

    // Test useDebounce
    let debouncedVal = null
    const DebounceTestComponent = ({ val }) => {
      debouncedVal = useDebounce(val, 50)
      return React.createElement('div', null, `debounced: ${debouncedVal}`)
    }

    const debounceContainer = dom.window.document.createElement('div')
    dom.window.document.body.appendChild(debounceContainer)
    const debounceRoot = ReactDOMClient.createRoot(debounceContainer)

    await act(async () => {
      debounceRoot.render(React.createElement(DebounceTestComponent, { val: 'initial' }))
    })
    assert.strictEqual(debouncedVal, 'initial', 'useDebounce receives initial value immediately')

    // Change input value
    await act(async () => {
      debounceRoot.render(React.createElement(DebounceTestComponent, { val: 'updated' }))
    })
    // Before delay elapses
    assert.strictEqual(debouncedVal, 'initial', 'useDebounce retains previous value before delay')

    // Wait for timer
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 80))
    })
    assert.strictEqual(debouncedVal, 'updated', 'useDebounce updates after delay')

    await act(async () => {
      debounceRoot.unmount()
    })
    debounceContainer.remove()

    // Test useIsMounted
    let isMountedFn = null
    const MountTestComponent = () => {
      isMountedFn = useIsMounted()
      return React.createElement('div', null, 'Mount Test')
    }

    await act(async () => {
      hookRoot.render(React.createElement(MountTestComponent))
    })
    assert.strictEqual(isMountedFn(), true, 'useIsMounted returns true while mounted')

    await act(async () => {
      hookRoot.unmount()
    })
    assert.strictEqual(isMountedFn(), false, 'useIsMounted returns false after unmount')
    hookContainer.remove()

    console.log('   ✓ Custom hooks disclosure and mount states verified.')

    // -------------------------------------------------------------
    // 6. BARREL EXPORTS & TYPES VERIFICATION
    // -------------------------------------------------------------
    console.log('6. Verifying Barrel Exports & Module Architecture...')
    const typesModule = await vite.ssrLoadModule('@/types/index')
    assert(typesModule, '@/types/index is resolvable')

    const libModule = await vite.ssrLoadModule('@/lib/index')
    assert(typeof libModule.cn === 'function', '@/lib/index exports cn function')

    const servicesModule = await vite.ssrLoadModule('@/services/index')
    assert(servicesModule.apiClient, '@/services/index exports apiClient')
    assert(servicesModule.ApiError, '@/services/index exports ApiError')

    const appModule = await vite.ssrLoadModule('@/app/index')
    assert(typeof appModule.App === 'function', '@/app/index exports App component')
    assert(typeof appModule.AppProvider === 'function', '@/app/index exports AppProvider')
    assert(typeof appModule.AppRouter === 'function', '@/app/index exports AppRouter')

    console.log('   ✓ Barrel exports and module structure fully verified.')

    console.log('\n=============================================')
    console.log('ALL ARCHITECTURE INTEGRATION VERIFICATIONS PASSED!')
    console.log('=============================================\n')
  } finally {
    await vite.close()
  }
}

runArchitectureVerification().catch((err) => {
  console.error('\n❌ ARCHITECTURE VERIFICATION FAILED:', err)
  process.exit(1)
})
