import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        ws: true,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('[Vite Proxy] 代理错误:', err)
          })
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log('[Vite Proxy] 发送请求:', req.method, req.url)
          })
          proxy.on('proxyRes', (proxyRes, req, _res) => {
            console.log('[Vite Proxy] 收到响应:', proxyRes.statusCode, req.url)
          })
        }
      }
    }
  }
})