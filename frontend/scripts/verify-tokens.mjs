import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert'
import { fileURLToPath } from 'node:url'
import { JSDOM } from 'jsdom'
import { createServer } from 'vite'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const frontendRoot = path.resolve(__dirname, '..')
const tokensDir = path.join(frontendRoot, 'src', 'styles', 'tokens')
const indexCssPath = path.join(frontendRoot, 'src', 'index.css')

console.log('\n=============================================')
console.log('STARTING DESIGN SYSTEM TOKEN INFRASTRUCTURE VERIFICATION')
console.log('=============================================\n')

// 1. Verify Directory & Modular File Structure
console.log('1. Verifying token module files on disk...')
const REQUIRED_FILES = [
  'colors.css',
  'typography.css',
  'spacing.css',
  'radius.css',
  'shadows.css',
  'breakpoints.css',
  'theme.css',
  'index.css',
  'index.ts',
]

for (const file of REQUIRED_FILES) {
  const filePath = path.join(tokensDir, file)
  assert(fs.existsSync(filePath), `Required token file ${file} exists in src/styles/tokens/`)
  console.log(`  ✓ ${file} verified.`)
}

// 2. Verify Central Import Manifest
console.log('\n2. Verifying central manifest and entry point...')
const indexTokensCss = fs.readFileSync(path.join(tokensDir, 'index.css'), 'utf8')
const expectedImports = [
  'colors.css',
  'typography.css',
  'spacing.css',
  'radius.css',
  'shadows.css',
  'breakpoints.css',
  'theme.css',
]
for (const imp of expectedImports) {
  assert(indexTokensCss.includes(imp), `src/styles/tokens/index.css imports ${imp}`)
}
console.log('  ✓ Token index.css imports all modular stylesheets.')

const rootIndexCss = fs.readFileSync(indexCssPath, 'utf8')
assert(
  rootIndexCss.includes('./styles/tokens/index.css'),
  'src/index.css imports ./styles/tokens/index.css',
)
console.log('  ✓ src/index.css integrates centralized token manifest.')

// 3. Verify CSS Variable Coverage
console.log('\n3. Verifying required token categories in CSS definitions...')
const colorsCss = fs.readFileSync(path.join(tokensDir, 'colors.css'), 'utf8')
const typographyCss = fs.readFileSync(path.join(tokensDir, 'typography.css'), 'utf8')
const spacingCss = fs.readFileSync(path.join(tokensDir, 'spacing.css'), 'utf8')
const radiusCss = fs.readFileSync(path.join(tokensDir, 'radius.css'), 'utf8')
const shadowsCss = fs.readFileSync(path.join(tokensDir, 'shadows.css'), 'utf8')
const breakpointsCss = fs.readFileSync(path.join(tokensDir, 'breakpoints.css'), 'utf8')
const themeCss = fs.readFileSync(path.join(tokensDir, 'theme.css'), 'utf8')

// Brand Colors
const brandVars = [
  '--brand',
  '--brand-foreground',
  '--brand-hover',
  '--brand-active',
  '--brand-subtle',
  '--brand-muted',
  '--brand-emphasis',
  '--brand-50',
  '--brand-500',
  '--brand-950',
]
for (const v of brandVars) {
  assert(colorsCss.includes(v), `colors.css includes brand variable ${v}`)
}
console.log('  ✓ Brand color tokens verified (including numeric scale 50-950).')

// Background & Surface Colors
const bgVars = [
  '--background',
  '--card',
  '--popover',
  '--muted',
  '--surface-canvas',
  '--surface-card',
  '--surface-elevated',
  '--surface-muted',
]
for (const v of bgVars) {
  assert(colorsCss.includes(v), `colors.css includes background/surface variable ${v}`)
}
console.log('  ✓ Background and surface hierarchy tokens verified.')

// Text Colors
const textVars = [
  '--foreground',
  '--muted-foreground',
  '--text-primary',
  '--text-secondary',
  '--text-tertiary',
  '--text-disabled',
  '--text-inverse',
]
for (const v of textVars) {
  assert(colorsCss.includes(v), `colors.css includes text variable ${v}`)
}
console.log('  ✓ Text color hierarchy tokens verified.')

// Border Colors
const borderVars = [
  '--border',
  '--input',
  '--ring',
  '--border-subtle',
  '--border-default',
  '--border-strong',
]
for (const v of borderVars) {
  assert(colorsCss.includes(v), `colors.css includes border variable ${v}`)
}
console.log('  ✓ Border and outline tokens verified.')

// Typography
const typoVars = [
  '--font-family-sans',
  '--font-family-heading',
  '--font-family-mono',
  '--font-size-xs',
  '--font-size-base',
  '--font-size-2xl',
  '--line-height-base',
  '--font-weight-normal',
  '--font-weight-bold',
  '--letter-spacing-normal',
]
for (const v of typoVars) {
  assert(typographyCss.includes(v), `typography.css includes typography variable ${v}`)
}
console.log('  ✓ Typography tokens verified (families, sizes, line heights, weights, tracking).')

// Spacing
const spacingVars = [
  '--spacing-base',
  '--spacing-xs',
  '--spacing-md',
  '--spacing-xl',
  '--spacing-gutter',
  '--spacing-container-padding',
]
for (const v of spacingVars) {
  assert(spacingCss.includes(v), `spacing.css includes spacing variable ${v}`)
}
console.log('  ✓ Spacing scale and layout tokens verified.')

// Border Radius
const radiusVars = [
  '--radius',
  '--radius-none',
  '--radius-sm',
  '--radius-md',
  '--radius-lg',
  '--radius-xl',
  '--radius-full',
]
for (const v of radiusVars) {
  assert(radiusCss.includes(v), `radius.css includes radius variable ${v}`)
}
console.log('  ✓ Border radius tokens verified.')

// Shadows
const shadowVars = ['--shadow-none', '--shadow-xs', '--shadow-sm', '--shadow-md', '--shadow-lg']
for (const v of shadowVars) {
  assert(shadowsCss.includes(v), `shadows.css includes shadow variable ${v}`)
}
console.log('  ✓ Elevation and shadow tokens verified.')

// Breakpoints
const bpVars = [
  '--breakpoint-2xs',
  '--breakpoint-xs',
  '--breakpoint-sm',
  '--breakpoint-md',
  '--breakpoint-lg',
  '--breakpoint-xl',
  '--breakpoint-2xl',
]
for (const v of bpVars) {
  assert(breakpointsCss.includes(v), `breakpoints.css includes breakpoint variable ${v}`)
}
console.log('  ✓ Responsive breakpoint tokens verified.')

// 4. Verify Theme Symmetry (Light & Dark Support)
console.log('\n4. Verifying Light (:root) and Dark (.dark) theme support...')
assert(colorsCss.includes(':root'), 'colors.css includes :root selector')
assert(colorsCss.includes('.dark'), 'colors.css includes .dark selector')
assert(shadowsCss.includes(':root'), 'shadows.css includes :root selector')
assert(shadowsCss.includes('.dark'), 'shadows.css includes .dark selector')

// Verify symmetry for key tokens
const rootMatch = colorsCss.match(/:root\s*\{([\s\S]*?)\}/)
const darkMatch = colorsCss.match(/\.dark\s*\{([\s\S]*?)\}/)
assert(rootMatch && darkMatch, 'Both :root and .dark blocks parsed in colors.css')

const extractVarDeclarations = (css) => {
  const map = new Map()
  for (const match of css.matchAll(/(--[a-zA-Z0-9_-]+)\s*:\s*([^;]+);/g)) {
    map.set(match[1], match[2].trim())
  }
  return map
}

const rootVarMap = extractVarDeclarations(rootMatch[1])
const darkVarMap = extractVarDeclarations(darkMatch[1])

// Every semantic token in :root must have a corresponding dark mode definition
for (const [varName] of rootVarMap) {
  assert(darkVarMap.has(varName), `Dark mode supports symmetrical token: ${varName}`)
}

// Verify that neutral placeholder constraints are honored in .dark
const darkSidebarPrimary = darkVarMap.get('--sidebar-primary')
assert(
  darkSidebarPrimary && !darkSidebarPrimary.includes('264.376'),
  'Dark mode sidebar primary must be a neutral placeholder, not arbitrary saturated blue',
)

// Verify brand numeric scale maintains proper perceptual order (50 is lightest, 950 is darkest)
const parseOklchL = (oklchStr) => {
  const m = oklchStr.match(/oklch\(\s*([\d.]+)/)
  return m ? parseFloat(m[1]) : null
}
const rootBrand50L = parseOklchL(rootVarMap.get('--brand-50'))
const rootBrand950L = parseOklchL(rootVarMap.get('--brand-950'))
const darkBrand50L = parseOklchL(darkVarMap.get('--brand-50'))
const darkBrand950L = parseOklchL(darkVarMap.get('--brand-950'))

assert(rootBrand50L > rootBrand950L, 'Light mode: brand-50 lightness must exceed brand-950')
assert(
  darkBrand50L > darkBrand950L,
  'Dark mode: brand-50 lightness must exceed brand-950 (non-inverted scale)',
)
console.log(
  '  ✓ Theme symmetry and non-inverted brand scale between light and dark modes confirmed.',
)

// 5. Verify Tailwind CSS v4 Theme Bridge & No Breakpoint Duplication
console.log('\n5. Verifying Tailwind CSS v4 theme bridge registration...')
assert(themeCss.includes('@theme inline'), 'theme.css registers @theme inline')
assert(themeCss.includes('--color-brand: var(--brand);'), 'theme.css bridges --color-brand')
assert(
  themeCss.includes('--color-surface-canvas: var(--surface-canvas);'),
  'theme.css bridges surface tokens',
)
assert(
  themeCss.includes('--color-text-primary: var(--text-primary);'),
  'theme.css bridges text tokens',
)
assert(
  themeCss.includes('--color-border-subtle: var(--border-subtle);'),
  'theme.css bridges border tokens',
)
assert(themeCss.includes('--font-sans:'), 'theme.css bridges font-sans')
assert(themeCss.includes('--spacing: var(--spacing-base);'), 'theme.css bridges spacing base')
assert(
  breakpointsCss.includes('@theme'),
  'breakpoints.css is single source of truth registering @theme for breakpoints',
)
assert(!themeCss.includes('--breakpoint-'), 'theme.css does NOT duplicate breakpoint definitions')
assert(
  themeCss.includes('@utility border-subtle'),
  'theme.css defines ergonomic border-subtle utility',
)
assert(
  themeCss.includes('@utility text-tertiary'),
  'theme.css defines ergonomic text-tertiary utility',
)
console.log('  ✓ Tailwind CSS v4 utility mapping and single-source breakpoints verified.')

// 6. Verify TypeScript Contract and Runtime Helpers via Vite SSR module loading
console.log('\n6. Verifying TypeScript token definitions and DOM helpers via Vite...')
const dom = new JSDOM(
  '<!DOCTYPE html><html><head><style>:root { --brand: oklch(0.5 0 0); --primary: oklch(0.2 0 0); }</style></head><body><div id="test-el"></div></body></html>',
  { url: 'http://localhost:3000' },
)
global.window = dom.window
global.document = dom.window.document
global.HTMLElement = dom.window.HTMLElement
global.SVGElement = dom.window.SVGElement
global.Element = dom.window.Element
global.getComputedStyle = dom.window.getComputedStyle.bind(dom.window)

const vite = await createServer({
  root: frontendRoot,
  server: { middlewareMode: true },
  appType: 'custom',
})

try {
  const tokenModule = await vite.ssrLoadModule('@/styles/tokens')

  // Verify exported constants
  assert(tokenModule.COLOR_TOKENS, 'Module exports COLOR_TOKENS')
  assert(tokenModule.COLOR_TOKENS.brand === '--brand', 'COLOR_TOKENS.brand is --brand')
  assert(tokenModule.COLOR_TOKENS.brand50 === '--brand-50', 'COLOR_TOKENS includes brand50')
  assert(tokenModule.COLOR_TOKENS.brand950 === '--brand-950', 'COLOR_TOKENS includes brand950')
  assert(tokenModule.COLOR_TOKENS.chart1 === '--chart-1', 'COLOR_TOKENS includes chart1')
  assert(
    tokenModule.COLOR_TOKENS.sidebarPrimary === '--sidebar-primary',
    'COLOR_TOKENS includes sidebarPrimary',
  )
  assert(tokenModule.BRAND_SCALE_TOKENS, 'Module exports BRAND_SCALE_TOKENS')
  assert(tokenModule.FONT_FAMILIES, 'Module exports FONT_FAMILIES')
  assert(tokenModule.FONT_SIZES, 'Module exports FONT_SIZES')
  assert(tokenModule.FONT_WEIGHTS, 'Module exports FONT_WEIGHTS')
  assert(tokenModule.LINE_HEIGHTS, 'Module exports LINE_HEIGHTS')
  assert(tokenModule.LETTER_SPACING, 'Module exports LETTER_SPACING')
  assert(tokenModule.SPACING_TOKENS, 'Module exports SPACING_TOKENS')
  assert(tokenModule.RADIUS_TOKENS, 'Module exports RADIUS_TOKENS')
  assert(tokenModule.SHADOW_TOKENS, 'Module exports SHADOW_TOKENS')
  assert(tokenModule.BREAKPOINTS, 'Module exports BREAKPOINTS')

  // Verify getCssVar & setCssVar execution
  const { getCssVar, setCssVar, normalizeCssVarName } = tokenModule
  assert.strictEqual(typeof getCssVar, 'function', 'getCssVar is a function')
  assert.strictEqual(typeof setCssVar, 'function', 'setCssVar is a function')
  assert.strictEqual(normalizeCssVarName('brand'), '--brand', 'normalizeCssVarName adds prefix')
  assert.strictEqual(
    normalizeCssVarName('--brand'),
    '--brand',
    'normalizeCssVarName preserves prefix',
  )

  // Test setCssVar & getCssVar with prefix
  setCssVar('--custom-theme-token', 'oklch(0.6 0.1 120)')
  assert.strictEqual(
    getCssVar('--custom-theme-token'),
    'oklch(0.6 0.1 120)',
    'getCssVar reads set property',
  )

  // Test setCssVar & getCssVar without prefix
  setCssVar('unprefixed-token', '1.5rem')
  assert.strictEqual(
    getCssVar('unprefixed-token'),
    '1.5rem',
    'getCssVar/setCssVar handles unprefixed names',
  )

  // Test on specific element
  const testEl = dom.window.document.getElementById('test-el')
  setCssVar('element-token', '2rem', testEl)
  assert.strictEqual(getCssVar('element-token', testEl), '2rem', 'set/get works on element target')

  console.log('  ✓ TypeScript token constants and DOM helper mechanics verified.')
} finally {
  await vite.close()
}

// 7. Verify Shadcn Compatibility
console.log('\n7. Verifying Shadcn/ui token compatibility...')
const allTokenCss = [
  colorsCss,
  typographyCss,
  spacingCss,
  radiusCss,
  shadowsCss,
  breakpointsCss,
].join('\n')
const allRootMatches = [...allTokenCss.matchAll(/:root\s*\{([\s\S]*?)\}/g)]
const allRootVars = new Set()
for (const match of allRootMatches) {
  for (const [v] of extractVarDeclarations(match[1])) {
    allRootVars.add(v)
  }
}

const requiredShadcnVars = [
  '--background',
  '--foreground',
  '--card',
  '--card-foreground',
  '--popover',
  '--popover-foreground',
  '--primary',
  '--primary-foreground',
  '--secondary',
  '--secondary-foreground',
  '--muted',
  '--muted-foreground',
  '--accent',
  '--accent-foreground',
  '--destructive',
  '--border',
  '--input',
  '--ring',
  '--radius',
]

for (const sv of requiredShadcnVars) {
  assert(allRootVars.has(sv), `Shadcn required variable ${sv} is defined in centralized tokens`)
}
console.log('  ✓ All 19 Shadcn/ui foundation variables present and accounted for.')

console.log('\n=============================================')
console.log('ALL DESIGN SYSTEM INFRASTRUCTURE VERIFICATIONS PASSED!')
console.log('=============================================\n')
