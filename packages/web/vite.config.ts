import react from '@vitejs/plugin-react';
import path from 'node:path';
import { defineConfig } from 'vite';

/** Порт бэкенда для dev-прокси. Переопределяется, если 8000 занят. */
const API_PORT = process.env.API_PORT ?? '8000';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
  server: {
    port: 5173,
    // Проксируем API на бэкенд, чтобы в разработке всё шло с одного origin —
    // ровно как в production, где бэкенд сам раздаёт собранную SPA. Так CORS
    // не нужен нигде, и код запросов одинаков в обоих режимах.
    proxy: {
      '/api': {
        target: `http://localhost:${API_PORT}`,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    // Информация о сборке запекается в бандл на этапе Docker-сборки
    // (см. стейдж web-builder в Dockerfile).
    sourcemap: false,
  },
});
