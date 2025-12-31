import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  
  // 1. root를 frontend 폴더로 명시 (기본값임)
  root: path.resolve(__dirname),

  // 2. 개발 시 기본 경로 설정
  base: '/',

  server: {
    host: '127.0.0.1',
    port: 3000,
    strictPort: true,
    // Django와의 통신을 위해 허용
    origin: 'http://127.0.0.1:3000',
    cors: true,
    hmr: {
      host: '127.0.0.1',
    },
  },

  // 중복되었던 build 블록을 하나로 합쳤습니다.
  build: {
    outDir: path.resolve(__dirname, '../static/dist'),
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      // 멀티 엔트리 설정: 설계(main)와 수집(collector) 진입점을 모두 정의합니다.
      input: {
        main: path.resolve(__dirname, 'src/main.js'),
        collector: path.resolve(__dirname, 'src/collector-main.js'),
      },
    },
  },
  
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
})