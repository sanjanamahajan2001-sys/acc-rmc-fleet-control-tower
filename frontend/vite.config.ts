import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: process.env.VITE_BASE_URL || '/demo-fleet/',
  plugins: [react()],
  server: {
    port: 8020,
    host: true,
    proxy: {
      '/demo-api/v1': {
        target: 'http://localhost:8020',
        changeOrigin: true,
        ws: true,
        rewrite: (path) => path.replace(/^\/demo-api\/v1/, '/fleet-api/v1'),
      },
      '/demo-fleet/fleet-api': {
        target: process.env.VITE_BACKEND_TARGET || 'http://localhost:8020',
        changeOrigin: true,
        ws: true,
        rewrite: (path) => path.replace(/^\/demo-fleet\/fleet-api/, '/fleet-api'),
      },
      '/fleet-api': {
        target: process.env.VITE_BACKEND_TARGET || 'http://localhost:8020',
        changeOrigin: true,
        ws: true,
      },
      '/api': {
        target: process.env.VITE_BACKEND_TARGET || 'http://localhost:8011',
        changeOrigin: true,
        ws: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/tests/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'src/tests/setup.ts', 'dist/'],
    },
  },
});

