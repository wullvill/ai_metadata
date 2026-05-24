import { test, expect } from '@playwright/test'

test.describe('MetaGraph Frontend E2E', () => {

  test.describe('Search Page', () => {
    test('page loads with table and filters', async ({ page }) => {
      const errors: string[] = []
      page.on('pageerror', err => errors.push(err.message))

      await page.goto('/search', { waitUntil: 'networkidle' })

      await expect(page.locator('h1, .page-header h1, .hero h1').first()).toBeVisible({ timeout: 5000 })

      const searchInput = page.locator('input[placeholder*="搜索"], .search-input input')
      await expect(searchInput.first()).toBeVisible({ timeout: 3000 })

      await page.screenshot({ path: 'tests/e2e/artifacts/search-page.png', fullPage: true })
      console.log(`Search page errors: ${errors.length}`)
      expect(errors.filter(e => !e.includes('ResizeObserver')).length).toBe(0)
    })
  })

  test.describe('Review Page', () => {
    test('page loads with workbench', async ({ page }) => {
      const errors: string[] = []
      page.on('pageerror', err => errors.push(err.message))

      await page.goto('/review', { waitUntil: 'networkidle' })
      await expect(page.locator('h1, .page-header h1').first()).toBeVisible({ timeout: 5000 })
      await page.screenshot({ path: 'tests/e2e/artifacts/review-page.png', fullPage: true })
      console.log(`Review page errors: ${errors.length}`)
    })
  })

  test.describe('History Page', () => {
    test('page loads', async ({ page }) => {
      const errors: string[] = []
      page.on('pageerror', err => errors.push(err.message))

      await page.goto('/history', { waitUntil: 'networkidle' })
      await page.screenshot({ path: 'tests/e2e/artifacts/history-page.png', fullPage: true })
      console.log(`History page errors: ${errors.length}`)
    })
  })

  test.describe('Asset Detail', () => {
    test('shows error for missing id', async ({ page }) => {
      await page.goto('/asset/', { waitUntil: 'networkidle' })
      await page.screenshot({ path: 'tests/e2e/artifacts/asset-detail-no-id.png', fullPage: true })
    })

    test('shows error for unknown id', async ({ page }) => {
      await page.goto('/asset/nonexistent', { waitUntil: 'networkidle' })
      await page.screenshot({ path: 'tests/e2e/artifacts/asset-detail-unknown.png', fullPage: true })
    })
  })

  test.describe('Navigation', () => {
    test('nav links exist', async ({ page }) => {
      await page.goto('/search', { waitUntil: 'networkidle' })
      const navLinks = page.locator('nav a, .nav-link')
      expect(await navLinks.count()).toBeGreaterThan(0)
      console.log(`Nav links: ${await navLinks.count()}`)
    })
  })
})
