// frontend/src/collector-main.js
import { createApp } from 'vue'
import SurveyCollector from './components/SurveyCollector.vue'

/* * [스타일 및 라이브러리 로드]
 * Vue 컴포넌트 내에서 사용하는 스타일을 적용합니다.
 * base.html에서 CDN을 사용 중이라면 중복될 수 있으니 확인 후 주석 처리하세요.
 */
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap-icons/font/bootstrap-icons.css'
import 'animate.css' // 화면 등장 애니메이션용
import 'bootstrap/dist/js/bootstrap.bundle.min.js' // 모달 등 JS 기능용

// 앱 생성 및 마운트
const app = createApp(SurveyCollector)
app.mount('#app-collector')