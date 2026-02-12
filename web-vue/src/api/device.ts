import request from '../utils/request'
import type { ApiResponse } from './auth' 

export default {
  // 获取设备列表
  getDevices: () => {
    return request<any, ApiResponse<any[]>>({
      url: '/api/monitor/devices', // ✅ 补齐 /api
      method: 'get'
    })
  },
  
  // 添加设备
  addDevice: (data: { name: string, rtspUrl: string }) => { // ✅ 驼峰
    return request<any, ApiResponse<any>>({
      url: '/api/monitor/devices', // ✅ 补齐 /api
      method: 'post',
      data
    })
  },
  
  // 更新设备
  updateDevice: (deviceId: number, data: { name?: string, rtspUrl?: string }) => { // ✅ 驼峰
    return request<any, ApiResponse<any>>({
      url: `/api/monitor/devices/${deviceId}`, // ✅ 补齐 /api
      method: 'put',
      data
    })
  },
  
  // 删除设备
  deleteDevice: (deviceId: number) => {
    return request<any, ApiResponse<any>>({
      url: `/api/monitor/devices/${deviceId}`, // ✅ 补齐 /api
      method: 'delete'
    })
  },

  // 测试流状态
  getStreamStatus: (deviceId: number) => {
    return request<any, ApiResponse<any>>({
      url: `/api/monitor/stream/status/${deviceId}`, // ✅ 补齐 /api
      method: 'get',
      timeout: 30000
    })
  }
}