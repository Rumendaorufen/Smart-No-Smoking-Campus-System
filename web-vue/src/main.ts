import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import { createPinia } from 'pinia'
import App from './App.vue'
import './style.css'

// 创建应用实例
const app = createApp(App)

// 安装插件
app.use(ElementPlus)
app.use(createPinia())

// 挂载应用
app.mount('#app')
