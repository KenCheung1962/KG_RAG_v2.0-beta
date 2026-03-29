import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  // Base URL for production (change if deploying to subdirectory)
  base: './',
  
  // Development server config
  server: {
    port: 8081,
    host: true,
    proxy: {
      // Proxy API requests to LightRAG backend
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        headers: {
          'X-API-Key': 'static-internal-key'
        },
        // Handle proxy errors gracefully
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('Proxy error:', err.message);
          });
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log('Proxy request:', req.method, req.url);
          });
        }
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        headers: {
          'X-API-Key': 'static-internal-key'
        }
      },
      // Proxy for pgvector API (port 8002 - native)
      '/pgvector-api': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/pgvector-api/, '')
      },
      // Proxy for pgvector proxy (port 8012 - docker)
      '/pgvector-proxy': {
        target: 'http://localhost:8012',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/pgvector-proxy/, '')
      }
    }
  },
  
  // Build output
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          // Separate vendor chunk if we add dependencies later
          vendor: []
        }
      }
    }
  },
  
  // Path aliases
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@api': resolve(__dirname, 'src/api'),
      '@components': resolve(__dirname, 'src/components'),
      '@stores': resolve(__dirname, 'src/stores'),
      '@utils': resolve(__dirname, 'src/utils')
    }
  },
  
  // CSS config
  css: {
    devSourcemap: true
  }
});
