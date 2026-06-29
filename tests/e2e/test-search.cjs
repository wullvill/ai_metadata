const { chromium } = require('playwright')

const BASE = 'http://localhost:5173'
const ARTIFACTS = 'tests/e2e/artifacts'
const results = []

async function test(name, fn) {
  const browser = await chromium.launch()
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } })
  const page = await ctx.newPage()
  const pageErrors = []
  page.on('pageerror', err => {
    if (!err.message.includes('ResizeObserver')) pageErrors.push(err.message)
  })
  try {
    await fn(page)
    await page.screenshot({ path: `${ARTIFACTS}/${name}.png`, fullPage: true })
    results.push({ name, status: 'pass', errors: pageErrors })
    console.log(`  ✓ ${name}`)
  } catch (e) {
    await page.screenshot({ path: `${ARTIFACTS}/${name}-fail.png`, fullPage: true })
    results.push({ name, status: 'fail', error: e.message, errors: pageErrors })
    console.log(`  ✗ ${name}: ${e.message}`)
  } finally {
    await browser.close()
  }
}

;(async () => {
console.log('=== MetaGraph Search E2E ===\n')

await test('page-loads', async (page) => {
  await page.goto(`${BASE}/search`, { waitUntil: 'networkidle', timeout: 15000 })
  const title = await page.title()
  const rows = await page.locator('table tbody tr').count()
  const inputs = await page.locator('input').count()
  console.log(`    title="${title}", rows=${rows}, inputs=${inputs}`)
  if (!title) throw new Error('No page title')
})

await test('search-input', async (page) => {
  await page.goto(`${BASE}/search`, { waitUntil: 'networkidle', timeout: 15000 })
  const input = page.locator('input').first()
  await input.waitFor({ state: 'visible', timeout: 5000 })
  await input.fill('交易')
  await page.waitForTimeout(500)
  const val = await input.inputValue()
  if (val !== '交易') throw new Error(`Input: ${val}`)
})

await test('table-columns', async (page) => {
  await page.goto(`${BASE}/search`, { waitUntil: 'networkidle', timeout: 15000 })
  const headers = await page.locator('th').allTextContents()
  console.log(`    headers: ${headers.filter(h => h.trim()).join(' | ')}`)
})

await test('no-console-errors', async (page) => {
  const errors = []
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()) })
  await page.goto(`${BASE}/search`, { waitUntil: 'networkidle', timeout: 15000 })
  await page.waitForTimeout(2000)
  const real = errors.filter(e => !e.includes('ResizeObserver'))
  if (real.length) throw new Error(`${real.length} console errors: ${real.join('; ')}`)
  console.log('    clean')
})

await test('empty-search-state', async (page) => {
  await page.goto(`${BASE}/search`, { waitUntil: 'networkidle', timeout: 15000 })
  const input = page.locator('input').first()
  await input.fill('xyznonexistent999')
  await page.waitForTimeout(800)
  const t = await page.textContent('body')
  console.log(`    empty: ${t.includes('没有') || t.includes('无结果') || t.includes('匹配')}`)
})

await test('nav-to-review', async (page) => {
  await page.goto(`${BASE}/search`, { waitUntil: 'networkidle', timeout: 15000 })
  await page.locator('a[href*="review"]').first().click()
  await page.waitForTimeout(1000)
  console.log(`    to: ${page.url()}`)
})

await test('responsive-mobile', async (page) => {
  await page.setViewportSize({ width: 375, height: 667 })
  await page.goto(`${BASE}/search`, { waitUntil: 'networkidle', timeout: 15000 })
  console.log('    mobile loaded')
})

console.log(`\nPassed: ${results.filter(r => r.status === 'pass').length} / ${results.length}`)
results.filter(r => r.status === 'fail').forEach(r => {
  console.log(`  FAIL ${r.name}: ${r.error}`)
})
})()
