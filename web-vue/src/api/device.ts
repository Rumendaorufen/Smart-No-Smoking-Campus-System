import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建axios实例
const apiClient = axios.create({
  // 这里读取 .env 中的 /api/v1
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 响应拦截器
apiClient.interceptors.response.use(
  response => {
    // 这里是为了兼容 Flask 直接返回 json 的情况
    return response.data || response
  },
  error => {
    console.error('API请求错误:', error)
    // 统一处理网络错误提示
    const msg = error.response?.data?.message || '网络连接失败，请检查后端服务是否启动'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

// 设备相关API
const deviceApi = {
  // 获取设备列表 -> /api/v1/monitor/devices
  getDevices: async () => {
    return await apiClient.get('/monitor/devices')
  },
  
  // 获取单个设备信息
  getDevice: async (deviceId: number) => {
    return await apiClient.get(`/monitor/devices/${deviceId}`)
  },
  
  // 添加设备
  addDevice: async (data: {
    name: string,
    rtsp_url: string,
    area_config?: any
  }) => {
    return await apiClient.post('/monitor/devices', data)
  },
  
  // 更新设备信息
  updateDevice: async (deviceId: number, data: {
    name?: string,
    rtsp_url?: string,
    area_config?: any
  }) => {
    return await apiClient.put(`/monitor/devices/${deviceId}`, data)
  },
  
  // 删除设备
  deleteDevice: async (deviceId: number) => {
    return await apiClient.delete(`/monitor/devices/${deviceId}`)
  },
  
  // 获取设备视频流状态
  getStreamStatus: async (deviceId: number) => {
    return await apiClient.get(`/monitor/stream/status/${deviceId}`)
  },
  
  // 获取所有设备视频流状态
  getAllStreamStatus: async () => {
    return await apiClient.get('/monitor/stream/status/all')
  }
}

export default deviceApi
