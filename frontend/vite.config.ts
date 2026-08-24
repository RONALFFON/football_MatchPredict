import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 唯一允许的业务环境变量：后端 API 地址（开发时走 vite proxy）
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
