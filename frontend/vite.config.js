import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  // 1. 개발 소스의 기준점 설정
  root: path.resolve(__dirname, 'src'),
  // 2. Django의 static 파일 경로와 일치시킴
  base: '/static/dist/',
  build: {
    // 3. 빌드 결과물이 저장될 위치 (Django의 static 폴더 안쪽)
    outDir: path.resolve(__dirname, '../static/dist'),
    emptyOutDir: true,
    manifest: true, // Django-Vite 연동을 위한 파일 명세서 생성
    rollupOptions: {
      // 4. 앱의 시작점 파일 위치 지정
      input: path.resolve(__dirname, 'src/main.js'),
    },
  },
  server: {
    port: 3000, // 개발 서버 포트를 3000으로 고정
    hot: true,
  }
})