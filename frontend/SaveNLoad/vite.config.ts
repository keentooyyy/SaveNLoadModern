import { fileURLToPath, URL } from 'node:url'
import path from 'node:path'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import vueDevTools from 'vite-plugin-vue-devtools'

const rootDir = fileURLToPath(new URL('.', import.meta.url))

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  base: mode === 'development' ? '/' : '/static/vite/',
  plugins: [
    vue(),
    vueJsx(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@/': `${fileURLToPath(new URL('./src', import.meta.url))}/`
    },
  },
  build: {
    manifest: true,
    outDir: path.resolve(rootDir, '../../SaveNLoad/static/vite'),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        login: path.resolve(rootDir, 'src/utils/loginIsland.ts'),
        settings: path.resolve(rootDir, 'src/utils/settingsIsland.ts'),
        dashboard: path.resolve(rootDir, 'src/utils/dashboardIsland.ts'),
        gameDetail: path.resolve(rootDir, 'src/utils/gameDetailIsland.ts'),
        register: path.resolve(rootDir, 'src/utils/registerIsland.ts'),
        forgotPassword: path.resolve(rootDir, 'src/utils/forgotPasswordIsland.ts'),
        verifyOtp: path.resolve(rootDir, 'src/utils/verifyOtpIsland.ts'),
        resetPassword: path.resolve(rootDir, 'src/utils/resetPasswordIsland.ts'),
        workerRequired: path.resolve(rootDir, 'src/utils/workerRequiredIsland.ts')
      }
    }
  }
}))
