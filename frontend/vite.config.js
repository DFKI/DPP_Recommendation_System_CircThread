import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    server: {
        host: '0.0.0.0',
        port: 5173,
        proxy: {
            '/api/resolver': {
                target: 'http://localhost:8001',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api\/resolver/, ''),
            },
            '/api/recommendation': {
                target: 'http://localhost:8002',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api\/recommendation/, ''),
            },
            '/api/registry': {
                target: 'http://localhost:8003',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api\/registry/, ''),
            },
            '/api/products': {
                target: 'http://localhost:8010',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api\/products/, '/products'),
            },
        },
    },
})
