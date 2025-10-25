import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { 
    port: 5173,
    host: true
  },
  preview: {
    port: 5173,
    host: true,
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      'lammp.agaii.org',
      '.agaii.org'
    ]
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: false  // Disable terser minification to avoid the dependency issue
  }
})
