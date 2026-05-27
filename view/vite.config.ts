import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    port: 8003,
    proxy: {
      '/control': { target: 'http://localhost:8001', rewrite: (p) => p.replace(/^\/control/, '') },
      '/develop': { target: 'http://localhost:8002', rewrite: (p) => p.replace(/^\/develop/, '') }
    }
  }
});
