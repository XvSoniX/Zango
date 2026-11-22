import { createServer } from 'vite'
import React, { act } from 'react'
import ReactDOMServer from 'react-dom/server'
import ReactDOMClient from 'react-dom/client'
import assert from 'node:assert'
import { fileURLToPath } from 'node:url'
import { JSDOM } from 'jsdom'

async function runVerification() {
  console.log('Initializing DOM environment...')
  const dom = new JSDOM('<!DOCTYPE html><html><body><div id="root"></div></body></html>', {
    url: 'http://localhost:3000',
    pretendToBeVisual: true,
  })

  // Setup browser DOM environment on global before loading modules
  global.window = dom.window
  global.document = dom.window.document
  global.HTMLElement = dom.window.HTMLElement
  global.SVGElement = dom.window.SVGElement
  global.Element = dom.window.Element
  global.Node = dom.window.Node
  global.NodeFilter = dom.window.NodeFilter
  global.getComputedStyle = dom.window.getComputedStyle.bind(dom.window)
  global.MutationObserver = dom.window.MutationObserver
  global.CustomEvent = dom.window.CustomEvent
  global.requestAnimationFrame = dom.window.requestAnimationFrame || ((cb) => setTimeout(cb, 16))
  global.cancelAnimationFrame = dom.window.cancelAnimationFrame || ((id) => clearTimeout(id))
  global.IS_REACT_ACT_ENVIRONMENT = true

  console.log('Initializing Vite dev server for verification...')
  const frontendRoot = fileURLToPath(new URL('..', import.meta.url))
  const vite = await createServer({
    root: frontendRoot,
    server: { middlewareMode: true },
    appType: 'custom',
  })

  try {
    console.log('1. Loading component & utility modules via Vite alias resolution pipeline...')
    const utils = await vite.ssrLoadModule('@/lib/utils')
    const { App } = await vite.ssrLoadModule('./src/App.tsx')
    const { Button, buttonVariants } = await vite.ssrLoadModule('@/components/ui/button')
    const { Input } = await vite.ssrLoadModule('@/components/ui/input')
    const { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter, CardAction } =
      await vite.ssrLoadModule('@/components/ui/card')
    const {
      Dialog,
      DialogTrigger,
      DialogContent,
      DialogHeader,
      DialogFooter,
      DialogTitle,
      DialogDescription,
      DialogClose,
    } = await vite.ssrLoadModule('@/components/ui/dialog')

    // Verify module exports
    assert(typeof utils.cn === 'function', '@/lib/utils exports cn function')
    assert(typeof Button === 'function', 'Button is a function/component')
    assert(typeof buttonVariants === 'function', 'buttonVariants helper is exported')
    assert(typeof Input === 'function', 'Input is a function/component')
    assert(typeof Card === 'function', 'Card is a function/component')
    assert(typeof Dialog === 'function', 'Dialog is a function/component')

    console.log('2. Verifying cn() utility behavior and edge cases...')
    assert.strictEqual(utils.cn('px-2 py-1', 'px-4'), 'py-1 px-4', 'Conflicting padding merged')
    assert.strictEqual(
      utils.cn('text-sm', false && 'text-lg', null, undefined, {
        'font-bold': true,
        italic: false,
      }),
      'text-sm font-bold',
      'Falsy and object conditions handled',
    )
    assert.strictEqual(
      utils.cn(['bg-red-500', ['text-white', false && 'hidden']]),
      'bg-red-500 text-white',
      'Nested arrays handled correctly',
    )

    console.log('3. SSR Verification: Rendering App component tree...')
    const appHtml = ReactDOMServer.renderToString(React.createElement(App))
    console.log('App SSR render succeeded, output size:', appHtml.length)

    assert(appHtml.includes('data-slot="card"'), 'App includes card')
    assert(appHtml.includes('data-slot="input"'), 'App includes input')
    assert(appHtml.includes('data-slot="button"'), 'App includes button')
    assert(appHtml.includes('data-slot="dialog-trigger"'), 'App includes dialog trigger')

    console.log('4. SSR Verification: Variant matrices, boundaries, and compound components...')

    // Edge case 1: Button all variants, sizes, and states
    const variants = ['default', 'outline', 'secondary', 'ghost', 'destructive', 'link']
    const sizes = ['xs', 'sm', 'default', 'lg', 'icon', 'icon-xs', 'icon-sm', 'icon-lg']
    for (const variant of variants) {
      for (const size of sizes) {
        const btnHtml = ReactDOMServer.renderToString(
          React.createElement(Button, { variant, size }, `${variant}-${size}`),
        )
        assert(btnHtml.includes(`data-variant="${variant}"`), `Button variant ${variant} rendered`)
        assert(btnHtml.includes(`data-size="${size}"`), `Button size ${size} rendered`)
      }
    }

    // Button disabled and aria-invalid
    const disabledBtn = ReactDOMServer.renderToString(
      React.createElement(Button, { disabled: true, 'aria-invalid': true }, 'Disabled'),
    )
    assert(disabledBtn.includes('disabled=""'), 'Disabled button has disabled attribute')
    assert(disabledBtn.includes('aria-invalid="true"'), 'Aria invalid preserved')

    // Button asChild
    const asChildBtn = ReactDOMServer.renderToString(
      React.createElement(
        Button,
        { asChild: true },
        React.createElement('a', { href: '/test' }, 'Link Button'),
      ),
    )
    assert(asChildBtn.includes('<a href="/test"'), 'asChild renders link tag')
    assert(asChildBtn.includes('data-slot="button"'), 'asChild retains data-slot="button"')

    // Edge case 2: Input with empty vs populated value, and invalid/disabled states
    const inputEmpty = ReactDOMServer.renderToString(React.createElement(Input))
    assert(inputEmpty.includes('data-slot="input"'), 'Empty input renders')

    const inputInvalid = ReactDOMServer.renderToString(
      React.createElement(Input, { 'aria-invalid': true, defaultValue: 'bad value' }),
    )
    assert(inputInvalid.includes('aria-invalid="true"'), 'Input aria-invalid applied')
    assert(inputInvalid.includes('value="bad value"'), 'Input default value applied')

    // Edge case 3: Card sizes and full subcomponents
    const cardDefault = ReactDOMServer.renderToString(
      React.createElement(
        Card,
        null,
        React.createElement(
          CardHeader,
          null,
          React.createElement(CardTitle, null, 'Default Card'),
          React.createElement(CardAction, null, 'Action'),
        ),
        React.createElement(CardDescription, null, 'Description text'),
        React.createElement(CardContent, null, 'Content'),
        React.createElement(CardFooter, null, 'Footer'),
      ),
    )
    assert(cardDefault.includes('data-size="default"'), 'Default card size')
    assert(cardDefault.includes('data-slot="card-action"'), 'CardAction rendered')
    assert(cardDefault.includes('data-slot="card-description"'), 'CardDescription rendered')

    const cardSm = ReactDOMServer.renderToString(
      React.createElement(
        Card,
        { size: 'sm' },
        React.createElement(CardContent, null, 'Small Card'),
      ),
    )
    assert(cardSm.includes('data-size="sm"'), 'Card size="sm" applied')

    // Edge case 4: Dialog compound components
    const dialogHeaderHtml = ReactDOMServer.renderToString(
      React.createElement(
        Dialog,
        null,
        React.createElement(
          DialogHeader,
          null,
          React.createElement(DialogTitle, null, 'Dialog Title Text'),
          React.createElement(DialogDescription, null, 'Dialog Description Text'),
        ),
      ),
    )
    assert(dialogHeaderHtml.includes('data-slot="dialog-header"'), 'DialogHeader rendered')
    assert(dialogHeaderHtml.includes('data-slot="dialog-title"'), 'DialogTitle rendered')
    assert(
      dialogHeaderHtml.includes('data-slot="dialog-description"'),
      'DialogDescription rendered',
    )

    const dialogFooterHtml = ReactDOMServer.renderToString(
      React.createElement(
        Dialog,
        null,
        React.createElement(DialogFooter, { showCloseButton: true }),
      ),
    )
    assert(dialogFooterHtml.includes('data-slot="dialog-footer"'), 'DialogFooter rendered')
    assert(dialogFooterHtml.includes('Close'), 'DialogFooter showCloseButton rendered')

    console.log(
      '5. Client DOM & Interactive Verification: Mounting App and testing user interactions...',
    )
    const container = dom.window.document.getElementById('root')
    const root = ReactDOMClient.createRoot(container)

    await act(async () => {
      root.render(React.createElement(App))
    })

    // Verify App mounted into DOM
    const cardEl = container.querySelector('[data-slot="card"]')
    assert(cardEl, 'Card mounted in DOM')
    const inputEl = container.querySelector('[data-slot="input"]')
    assert(inputEl, 'Input mounted in DOM')
    const dialogTrigger = container.querySelector('[data-slot="dialog-trigger"]')
    assert(dialogTrigger, 'DialogTrigger mounted in DOM')

    // Test Input user typing interaction
    inputEl.value = 'User Typed Text'
    inputEl.dispatchEvent(new dom.window.Event('input', { bubbles: true }))
    assert.strictEqual(inputEl.value, 'User Typed Text', 'Input reflection verified')

    // Verify Dialog is NOT mounted before trigger click
    let modalEl = dom.window.document.querySelector('[data-slot="dialog-content"]')
    assert(!modalEl, 'Dialog content is not mounted before trigger click')

    // Click DialogTrigger to open Dialog
    console.log('Simulating trigger click to open Dialog modal portal...')
    await act(async () => {
      dialogTrigger.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true }))
    })

    modalEl = dom.window.document.querySelector('[data-slot="dialog-content"]')
    assert(modalEl, 'DialogContent portal mounted into document.body after click')
    assert(
      dom.window.document.body.textContent.includes('Dialog Verification'),
      'Dialog Title rendered in active portal',
    )
    assert(
      dom.window.document.body.textContent.includes(
        'Dialog component rendered and mounted successfully.',
      ),
      'Dialog Description rendered in active portal',
    )

    // Test dismiss button inside DialogFooter
    console.log('Simulating Dismiss button click to close Dialog...')
    const dismissBtn = Array.from(modalEl.querySelectorAll('button')).find((b) =>
      b.textContent.includes('Dismiss'),
    )
    assert(dismissBtn, 'Dismiss button found in Dialog')

    await act(async () => {
      dismissBtn.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true }))
    })

    modalEl = dom.window.document.querySelector('[data-slot="dialog-content"]')
    assert(!modalEl, 'DialogContent portal unmounted after Dismiss click')

    // Test re-opening and closing via Keyboard Escape key
    console.log('Simulating re-open and closing via Keyboard Escape key...')
    await act(async () => {
      dialogTrigger.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true }))
    })
    modalEl = dom.window.document.querySelector('[data-slot="dialog-content"]')
    assert(modalEl, 'Dialog opened again')

    await act(async () => {
      dom.window.document.dispatchEvent(
        new dom.window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }),
      )
    })
    modalEl = dom.window.document.querySelector('[data-slot="dialog-content"]')
    assert(!modalEl, 'Dialog unmounted after Escape key')

    // Cleanup root
    await act(async () => {
      root.unmount()
    })

    console.log('\n=============================================')
    console.log('ALL SHADCN/UI INTEGRATION VERIFICATIONS PASSED!')
    console.log('- Alias Resolution: PASSED')
    console.log('- Utility Merging: PASSED')
    console.log('- SSR Tree Rendering: PASSED')
    console.log('- Variant/Size Matrices: PASSED')
    console.log('- Client DOM Mounting: PASSED')
    console.log('- Portal Mount / Unmount: PASSED')
    console.log('- Keyboard Escape Handling: PASSED')
    console.log('=============================================\n')
  } finally {
    await vite.close()
  }
}

runVerification().catch((err) => {
  console.error('VERIFICATION FAILED:', err)
  process.exit(1)
})
