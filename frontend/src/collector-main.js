import { createApp } from 'vue'
import SurveyCollector from './components/SurveyCollector.vue'

/* -----------------------------------------------------------
   [필수] 스타일 및 라이브러리 로드
   이게 없으면 모달이 깨지거나(CSS), 열리지 않습니다(JS).
----------------------------------------------------------- */
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap-icons/font/bootstrap-icons.css'
import 'animate.css'

// Bootstrap JS 로드 (팝업 기능을 위해 필수)
import * as bootstrap from 'bootstrap'

// [중요] HTML 인라인 스크립트(onclick)에서 bootstrap을 쓸 수 있도록 전역에 할당
window.bootstrap = bootstrap;

/* -----------------------------------------------------------
   [필수] Vue 앱 마운트
   data_entry_list.html의 <div id="app-collector"> 와 일치해야 함
----------------------------------------------------------- */
createApp(SurveyCollector).mount('#app-collector')