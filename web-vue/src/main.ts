import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import { createPinia } from 'pinia'
import App from './App.vue'
import './style.css'
// ✅ 1. 引入刚才创建的 router
import router from './router'

// 创建应用实例
const app = createApp(App)

// 安装插件
app.use(ElementPlus)
app.use(createPinia())
// ✅ 2. 挂载 router
app.use(router)
// 挂载应用
app.mount('#app')
