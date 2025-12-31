// frontend/src/main.js
import { createApp } from 'vue'
import App from './App.vue'

// 만약 Pinia를 사용한다면 여기서 등록함
import { createPinia } from 'pinia'

const app = createApp(App)
app.use(createPinia())
app.mount('#app')