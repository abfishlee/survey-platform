import { createApp } from 'vue'
import './style.css' // 스타일 파일이 있다면 유지

// [변경 전] import App from './App.vue'
// [변경 후] 새로 만든 SurveyWorkbench 컴포넌트를 불러옵니다.
import SurveyWorkbench from './components/SurveyWorkbench.vue'

// Ag-Grid 스타일 (전역 설정이 편할 경우 여기서 import)
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

// [변경] App 대신 SurveyWorkbench를 마운트합니다.
createApp(SurveyWorkbench).mount('#app')