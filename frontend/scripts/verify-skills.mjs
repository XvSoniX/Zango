#!/usr/bin/env node

/**
 * verify-skills.mjs
 *
 * Automated verification suite for Task 05: Frontend Development Skills.
 * Validates discovery, manifest integrity, frontmatter schema, file cross-references,
 * category coverage, and constraint compliance.
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const projectRoot = path.resolve(__dirname, '../../')
const agentsDir = path.join(projectRoot, '.agents')
const skillsDir = path.join(agentsDir, 'skills')
const skillsJsonPath = path.join(agentsDir, 'skills.json')
const frontendPackageJson = path.join(projectRoot, 'frontend', 'package.json')

const REQUIRED_CATEGORIES = [
  { id: 'react-best-practices', category: 'React development best practices' },
  { id: 'typescript-best-practices', category: 'TypeScript best practices' },
  { id: 'tailwind-conventions', category: 'Tailwind CSS conventions' },
  { id: 'shadcn-component-development', category: 'Shadcn/ui component development' },
  {
    id: 'frontend-architecture-maintainability',
    category: 'Frontend architecture and maintainability',
  },
  { id: 'accessibility-semantic-html', category: 'Accessibility and semantic HTML' },
  { id: 'frontend-performance-optimization', category: 'Frontend performance optimization' },
]

console.log('=============================================')
console.log('STARTING FRONTEND DEVELOPMENT SKILLS VERIFICATION')
console.log('=============================================')

let failures = 0

function assert(condition, message) {
  if (!condition) {
    console.error(`  FAIL: ${message}`)
    failures++
  } else {
    console.log(`  ✓ ${message}`)
  }
}

// 1. Verify Manifest
console.log('\n1. Verifying .agents/skills.json manifest...')
assert(fs.existsSync(skillsJsonPath), '.agents/skills.json exists')
try {
  const manifest = JSON.parse(fs.readFileSync(skillsJsonPath, 'utf8'))
  assert(Array.isArray(manifest.entries), 'manifest contains entries array')
  const hasSkillsEntry = manifest.entries.some((e) => e.path === '.agents/skills')
  assert(hasSkillsEntry, 'manifest entries points to .agents/skills')
} catch (e) {
  assert(false, `manifest is valid JSON: ${e.message}`)
}

// 2. Discover Skills
console.log('\n2. Discovering installed skills in .agents/skills/...')
assert(fs.existsSync(skillsDir), '.agents/skills directory exists')
const skillFolders = fs
  .readdirSync(skillsDir, { withFileTypes: true })
  .filter((dirent) => dirent.isDirectory())
  .map((dirent) => dirent.name)

console.log(`  Discovered ${skillFolders.length} skill directories:`, skillFolders.join(', '))
assert(
  skillFolders.length === REQUIRED_CATEGORIES.length,
  `Expected exactly ${REQUIRED_CATEGORIES.length} skills, found ${skillFolders.length}`,
)

// 3. Verify Each Skill
console.log('\n3. Validating SKILL.md frontmatter, schema, and cross-references...')
const parsedSkills = new Map()

for (const folder of skillFolders) {
  const folderPath = path.join(skillsDir, folder)
  const skillFile = path.join(folderPath, 'SKILL.md')

  assert(fs.existsSync(skillFile), `${folder}/SKILL.md exists`)
  const content = fs.readFileSync(skillFile, 'utf8')

  // Verify YAML Frontmatter
  const frontmatterMatch = content.match(/^---\r?\n([\s\S]*?)\r?\n---/)
  assert(frontmatterMatch !== null, `${folder} contains valid YAML frontmatter`)

  if (frontmatterMatch) {
    const rawFm = frontmatterMatch[1]
    const nameMatch = rawFm.match(/^name:\s*([a-zA-Z0-9_-]+)/m)
    const descMatch = rawFm.match(/^description:\s*(?:>-\s*)?([\s\S]*?)(?=\n[a-zA-Z0-9_-]+:|$)/m)

    assert(nameMatch !== null, `${folder} frontmatter specifies 'name'`)
    if (nameMatch) {
      assert(
        nameMatch[1] === folder,
        `${folder} frontmatter 'name' (${nameMatch[1]}) matches folder name (${folder})`,
      )
    }

    assert(
      descMatch !== null && descMatch[1].trim().length > 20,
      `${folder} frontmatter specifies detailed 'description'`,
    )
    if (descMatch) {
      const desc = descMatch[1].trim()
      const isThirdPerson =
        /^(Best|Type|Styling|Guidelines|Architectural|Web|Frontend|Use this skill|Manages|Provides)/i.test(
          desc,
        )
      assert(
        isThirdPerson,
        `${folder} description is formatted in third-person: "${desc.slice(0, 50)}..."`,
      )
    }

    parsedSkills.set(folder, { name: nameMatch ? nameMatch[1] : null, content })
  }

  // Enumerate folder contents
  const filesInDir = fs.readdirSync(folderPath, { recursive: true })

  // Verify relative links in SKILL.md and all markdown files in folder
  const allMdFiles = filesInDir.filter((f) => f.endsWith('.md'))
  for (const mdRelFile of allMdFiles) {
    const mdAbsFile = path.join(folderPath, mdRelFile)
    const mdContent = fs.readFileSync(mdAbsFile, 'utf8')
    const linkMatches = [...mdContent.matchAll(/\[([^\]]+)\]\(([^)]+)\)/g)]
    for (const match of linkMatches) {
      const linkTarget = match[2]
      if (
        !linkTarget.startsWith('http://') &&
        !linkTarget.startsWith('https://') &&
        !linkTarget.startsWith('#')
      ) {
        const targetPath = path.resolve(path.dirname(mdAbsFile), linkTarget)
        assert(
          fs.existsSync(targetPath),
          `${folder}/${mdRelFile} link to ${linkTarget} resolves to existing file on disk`,
        )
      }
    }
  }

  // Security check: No unauthorized binary or script files
  const forbiddenExts = ['.exe', '.bat', '.cmd', '.ps1', '.sh', '.vbs', '.py', '.rb']
  const suspiciousFiles = filesInDir.filter((f) => forbiddenExts.some((ext) => f.endsWith(ext)))
  assert(
    suspiciousFiles.length === 0,
    `${folder} contains no executable scripts (${suspiciousFiles.join(', ')})`,
  )
}

// 4. Verify Category Coverage and No Duplication
console.log('\n4. Verifying category coverage without duplicates...')
const coveredCategories = new Set()
for (const req of REQUIRED_CATEGORIES) {
  const isFound = parsedSkills.has(req.id)
  assert(isFound, `Required category '${req.category}' is satisfied by skill '${req.id}'`)
  coveredCategories.add(req.id)
}
assert(
  coveredCategories.size === REQUIRED_CATEGORIES.length,
  'All 7 categories covered uniquely without overlap',
)

// 5. Verify Constraints (No project dependencies introduced)
console.log('\n5. Verifying project dependency constraints...')
const pkg = JSON.parse(fs.readFileSync(frontendPackageJson, 'utf8'))
const dependencies = Object.keys(pkg.dependencies || {})
const devDependencies = Object.keys(pkg.devDependencies || {})
console.log(
  `  Frontend dependencies count: ${dependencies.length}, devDependencies count: ${devDependencies.length}`,
)
assert(
  !dependencies.includes('skills'),
  'Skills did not introduce unnecessary runtime dependencies',
)
assert(!devDependencies.includes('skills'), 'Skills did not introduce unnecessary dev dependencies')

// 6. Verify Documentation
console.log('\n6. Verifying documentation assets...')
assert(fs.existsSync(path.join(agentsDir, 'README.md')), '.agents/README.md documentation exists')
assert(
  fs.existsSync(path.join(projectRoot, 'docs', 'frontend-skills.md')),
  'docs/frontend-skills.md documentation exists',
)

// 7. Verify Technology Stack Alignment
console.log('\n7. Verifying technology stack alignment with frontend configuration...')
const tsconfigPath = path.join(projectRoot, 'frontend', 'tsconfig.app.json')
assert(fs.existsSync(tsconfigPath), 'frontend/tsconfig.app.json exists')
if (fs.existsSync(tsconfigPath)) {
  const tsconfigContent = fs.readFileSync(tsconfigPath, 'utf8')
  assert(
    tsconfigContent.includes('"erasableSyntaxOnly": true'),
    'tsconfig specifies erasableSyntaxOnly: true',
  )
  assert(
    tsconfigContent.includes('"verbatimModuleSyntax": true'),
    'tsconfig specifies verbatimModuleSyntax: true',
  )

  const tsSkill = parsedSkills.get('typescript-best-practices')
  assert(
    tsSkill && tsSkill.content.includes('erasableSyntaxOnly'),
    'typescript-best-practices documents erasableSyntaxOnly',
  )
  assert(
    tsSkill && tsSkill.content.includes('verbatimModuleSyntax'),
    'typescript-best-practices documents verbatimModuleSyntax',
  )
}

const shadcnSkill = parsedSkills.get('shadcn-component-development')
assert(
  shadcnSkill && shadcnSkill.content.includes('data-slot'),
  'shadcn-component-development documents mandatory data-slot attribute',
)

const tailwindSkill = parsedSkills.get('tailwind-conventions')
assert(
  tailwindSkill && tailwindSkill.content.includes('@theme inline'),
  'tailwind-conventions documents @theme inline tokens',
)
assert(
  tailwindSkill && tailwindSkill.content.includes('tw-animate-css'),
  'tailwind-conventions documents tw-animate-css',
)

// 8. Global Security Scan across .agents/
console.log('\n8. Performing global security audit on .agents/ directory...')
const allAgentFiles = fs.readdirSync(agentsDir, { recursive: true })
const agentExecutableFiles = allAgentFiles.filter((f) => {
  const ext = path.extname(f).toLowerCase()
  return ['.exe', '.bat', '.cmd', '.ps1', '.sh', '.vbs', '.py', '.rb', '.bin'].includes(ext)
})
assert(
  agentExecutableFiles.length === 0,
  `No suspicious binary/script files in .agents/ (${agentExecutableFiles.join(', ')})`,
)

console.log('\n=============================================')
if (failures === 0) {
  console.log('ALL FRONTEND SKILLS VERIFICATIONS PASSED SUCCESSFULLY!')
  console.log('=============================================')
  process.exit(0)
} else {
  console.error(`VERIFICATION FAILED WITH ${failures} ERRORS.`)
  console.log('=============================================')
  process.exit(1)
}
