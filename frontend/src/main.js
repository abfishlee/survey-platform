import { createApp } from 'vue'
// import './style.css' // (선택) 기존 기본 스타일이 있다면 유지, 없으면 주석 처리

// [핵심] 설계 화면 컴포넌트
import SurveyWorkbench from './components/SurveyWorkbench.vue'

/* -----------------------------------------------------------
   [수정] 필수 라이브러리 추가
   이게 없어서 설계 팝업의 디자인이 깨지고 모달이 안 떴던 겁니다.
----------------------------------------------------------- */
// 1. Bootstrap CSS & JS (모달, 버튼 스타일 등 필수)
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap/dist/js/bootstrap.bundle.min.js'

// 2. 아이콘 & 애니메이션
import 'bootstrap-icons/font/bootstrap-icons.css'
import 'animate.css'

/* -----------------------------------------------------------
   Ag-Grid 스타일 (설계 화면에서만 사용)!!
----------------------------------------------------------- */
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

// 앱 마운트
createApp(SurveyWorkbench).mount('#app')