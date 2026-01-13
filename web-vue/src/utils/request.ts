import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router' // 引入路由以便跳转登录

// 创建 axios 实例
const service = axios.create({
  // 这里的 base URL 取决于你的 vite.config.ts 代理配置或后端地址
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1', 
  timeout: 5000 // 请求超时时间
})

// 🚀 请求拦截器：每次请求自动带上 Token
service.interceptors.request.use(
  (config) => {
    // 从 localStorage 获取 Token
    const token = localStorage.getItem('token')
    if (token) {
      // 按照 JWT 标准，Header 格式通常是: Authorization: Bearer <token>
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 🚀 响应拦截器：统一处理 401 过期
service.interceptors.response.use(
  (response) => {
    const res = response.data
    // 假设后端 200 表示业务成功，其他都是业务错误
    // 注意：有些后端在 401 时会直接返回 HTTP 状态码 401，那样会进下面的 error 分支
    return res
  },
  (error) => {
    // 处理 HTTP 状态码错误
    if (error.response && error.response.status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      // 清除本地缓存
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      // 强制跳转登录页
      router.push('/login')
    } else {
      ElMessage.error(error.message || '网络异常')
    }
    return Promise.reject(error)
  }
)

export default service