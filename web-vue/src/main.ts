import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import { createPinia } from 'pinia'
import App from './App.vue'
import './style.css'
// ✅ 1. 引入刚才创建的 router
import router from './router'

// Log collector and X-Trace-Id propagation
import { logCollector } from './utils/logCollector'
import axios from 'axios'

// Global Vue error handler
const app = createApp(App)
app.config.errorHandler = (err, _instance, info) => {
  logCollector.report(
    'ERROR',
    `${err instanceof Error ? err.message : String(err)} | ${info || ''}`,
  )
}

// Axios interceptor: add X-Trace-Id to all outgoing requests
axios.interceptors.request.use((config) => {
  config.headers['X-Trace-Id'] = logCollector.getTraceId()
  return config
})

// Axios response error interceptor
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    const endpoint = error.config?.url || ''
    logCollector.report('ERROR', `HTTP ${error.response?.status || 0}: ${error.message}`, endpoint)
    return Promise.reject(error)
  },
)

// 安装插件
app.use(ElementPlus)
app.use(createPinia())
// ✅ 2. 挂载 router
app.use(router)
// 挂载应用
app.mount('#app')
