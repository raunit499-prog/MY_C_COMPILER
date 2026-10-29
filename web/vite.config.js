import { defineConfig } from 'vite';
export default defineConfig({
  server: { host: '0.0.0.0', port: Number(process.env.PORT) || 5173, allowedHosts: true, headers: {'Cross-Origin-Opener-Policy':'same-origin','Cross-Origin-Embedder-Policy':'require-corp'} },
  worker: { format: 'es' },
  build: { target: 'es2022' }
});
