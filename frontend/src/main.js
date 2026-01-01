import { createApp } from 'vue'
import './style.css' 

// 새로 만든 SurveyWorkbench 컴포넌트
import SurveyWorkbench from './components/SurveyWorkbench.vue'

/* ----------------------------------------------------
   [수정] 누락된 스타일 및 라이브러리 추가
   이 부분이 없어서 아이콘 404 에러 및 레이아웃 깨짐 발생
---------------------------------------------------- */
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap-icons/font/bootstrap-icons.css'
import 'animate.css'
import 'bootstrap/dist/js/bootstrap.bundle.min.js' // 모달, 툴팁 등 동작 필수

// Ag-Grid 스타일
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

// 앱 마운트
createApp(SurveyWorkbench).mount('#app')