import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  projects: [{ name: 'chrome', use: { browserName: 'chromium' } }],
  use: {
    baseURL: 'http://localhost:5173',
    actionTimeout: 10000,
    screenshot: 'on',
  },
})
