import request from '../utils/request'
import type { ApiResponse } from './auth' // 假设你在某个地方定义了 ApiResponse

export default {
  // 获取设备列表
  getDevices: () => {
    return request<any, ApiResponse<any[]>>({
      url: '/monitor/devices',
      method: 'get'
    })
  },
  
  // 添加设备
  addDevice: (data: { name: string, rtsp_url: string }) => {
    return request<any, ApiResponse<any>>({
      url: '/monitor/devices',
      method: 'post',
      data
    })
  },
  
  // 更新设备
  updateDevice: (deviceId: number, data: { name?: string, rtsp_url?: string }) => {
    return request<any, ApiResponse<any>>({
      url: `/monitor/devices/${deviceId}`,
      method: 'put',
      data
    })
  },
  
  // 删除设备
  deleteDevice: (deviceId: number) => {
    return request<any, ApiResponse<any>>({
      url: `/monitor/devices/${deviceId}`,
      method: 'delete'
    })
  },

  // 测试流状态
  getStreamStatus: (deviceId: number) => {
    return request<any, ApiResponse<any>>({
      url: `/monitor/stream/status/${deviceId}`,
      method: 'get'
    })
  }
}