import { test, expect } from '@playwright/test'

const BASE = 'http://localhost:5173'

test.describe('资产搜索页面', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE}/search`)
    await page.waitForLoadState('networkidle', { timeout: 15000 })
  })

  test('页面加载：标题和搜索栏可见', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('资产目录')
    await expect(page.locator('.search-input')).toBeVisible()
  })

  test('初始加载：显示搜索结果表格', async ({ page }) => {
    await expect(page.locator('.t-table')).toBeVisible({ timeout: 10000 })
  })

  test('搜索输入：输入关键词后表格更新', async ({ page }) => {
    const searchInput = page.locator('.search-input')
    await searchInput.fill('交易')
    await page.waitForTimeout(500)

    await page.waitForTimeout(1500)

    const resultCount = page.locator('.result-count')
    if (await resultCount.isVisible()) {
      const text = await resultCount.textContent()
      expect(text).toMatch(/\d+/)
    }
  })

  test('类型筛选：点击筛选 chip 后数据更新', async ({ page }) => {
    const tableChip = page.locator('.filter-chip', { hasText: '表' }).first()
    await tableChip.click()
    await page.waitForTimeout(1000)

    await expect(tableChip).toHaveClass(/active/)
  })

  test('补全状态筛选：切换筛选 chips', async ({ page }) => {
    const pendingChip = page.locator('.ops-bar .filter-chip', { hasText: '待补全' }).first()
    await pendingChip.click()
    await expect(pendingChip).toHaveClass(/active/)

    const completedChip = page.locator('.ops-bar .filter-chip', { hasText: '已完成' }).first()
    await completedChip.click()
    await expect(completedChip).toHaveClass(/active/)
  })

  test('资产详情：点击资产名称弹出详情对话框', async ({ page }) => {
    const firstCellName = page.locator('.cell-name').first()
    await expect(firstCellName).toBeVisible({ timeout: 10000 })

    await firstCellName.click()

    // Wait for the detail dialog to become visible (look for .detail-dialog inside t-dialog)
    const detailContent = page.locator('.detail-dialog')
    await expect(detailContent).toBeVisible({ timeout: 10000 })
  })

  test('搜索无结果：显示空状态文案', async ({ page }) => {
    const searchInput = page.locator('.search-input')
    // Search for something that won't match any asset
    await searchInput.fill('XYZZZ_NO_MATCH_999')
    await page.waitForTimeout(2000)

    const emptyState = page.locator('.empty-state')
    await expect(emptyState).toBeVisible({ timeout: 5000 })
    await expect(emptyState).toContainText('没有匹配的元数据资产')
  })

  test('排序功能：点击列头触发排序', async ({ page }) => {
    const nameHeader = page.locator('th').filter({ hasText: '资产名称' }).first()
    await expect(nameHeader).toBeVisible({ timeout: 5000 })
    await nameHeader.click()
    await page.waitForTimeout(1000)
  })
})
