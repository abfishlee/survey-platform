import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

export default defineConfig({
  plugins: [vue()],
  base: '/static/',
  
  // [여기!] 서버 설정 추가
  server: {
    host: '127.0.0.1', // localhost로 명시
    port: 3000,        // 3000번 포트 강제 사용
    strictPort: true,  // 3000번이 이미 사용 중이면 에러 발생 (다른 포트로 넘어가지 않음)
    cors: true,        // Django에서 접근 가능하도록 CORS 허용
    origin: 'http://127.0.0.1:3000', // 에셋 출처 명시
  },

  build: {
    manifest: true,
    outDir: '../static/dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        survey: resolve(__dirname, 'src/survey-main.js'),
        collector: resolve(__dirname, 'src/collector-main.js'),
        analysis: resolve(__dirname, 'src/analysis-main.js'),
        viewer: resolve(__dirname, 'src/viewer-main.js')
      },
      output: {
        entryFileNames: `assets/[name].js`,
        chunkFileNames: `assets/[name].js`,
        assetFileNames: `assets/[name].[ext]`
      }
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
});