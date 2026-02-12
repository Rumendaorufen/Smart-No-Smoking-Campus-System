import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

// 1. 业务后端 (Java Spring Boot)
const service = axios.create({
  // 对应 .env 中的 VITE_APP_BASE_API = 'http://localhost:8080'
  baseURL: import.meta.env.VITE_APP_BASE_API || 'http://localhost:8080', 
  timeout: 5000
})

// 2. 请求拦截器
service.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      // Spring Security 标准格式
      config.headers['Authorization'] = `Bearer ${token}` 
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 3. 响应拦截器
service.interceptors.response.use(
  (response) => {
    const res = response.data
    // Java 返回 code 200 表示成功
    if (res.code === 200) {
        return res
    } else {
        ElMessage.error(res.msg || '系统错误')
        return Promise.reject(new Error(res.msg || 'Error'))
    }
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      router.push('/login')
    } else {
      ElMessage.error(error.message || '网络异常')
    }
    return Promise.reject(error)
  }
)

export default service