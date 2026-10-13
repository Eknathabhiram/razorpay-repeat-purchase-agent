import {defineConfig} from '@playwright/test';

export default defineConfig({
  testDir: './tests/production',
  testMatch: '**/*.spec.ts',
  fullyParallel: true,
  workers: 2,
  timeout: 30000,
  expect: {timeout: 15000},
  use: {baseURL: 'http://127.0.0.1:5174/app/', channel: 'msedge', trace: 'retain-on-failure'},
  reporter: [['list'], ['html', {open:'never'}]],
  webServer: {
    command: 'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5174 --strictPort',
    url: 'http://127.0.0.1:5174/app/',
    reuseExistingServer: !process.env.CI,
  },
});
