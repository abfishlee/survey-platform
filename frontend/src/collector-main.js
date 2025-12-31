// frontend/src/collector-main.js
import { createApp } from 'vue'
import SurveyCollector from './SurveyCollector.vue' // 이전에 만든 Vue 파일

// Django 템플릿의 #app-collector 요소에 마운트
const app = createApp(SurveyCollector)
app.mount('#app-collector')