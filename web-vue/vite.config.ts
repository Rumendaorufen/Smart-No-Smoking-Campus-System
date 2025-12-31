import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    host: '0.0.0.0', // 允许局域网访问
    port: 5173,
    proxy: {
      // 核心配置：将 /api 开头的请求代理到后端 5000 端口
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        // 如果后端路由本身就包含 /api，则不需要 rewrite
        // rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
