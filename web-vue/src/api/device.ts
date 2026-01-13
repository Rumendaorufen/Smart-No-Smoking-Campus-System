import request from '../utils/request'

// ✅ 1. 定义后端统一响应接口
// 这告诉 TS：后端返回的数据里一定有 code, msg, data
export interface ApiResponse<T = any> {
  code: number;
  msg: string;
  data: T;
}

// 设备相关API
const deviceApi = {
  // 获取设备列表
  // request<请求数据类型, 响应数据类型>
  getDevices: () => {
    return request<any, ApiResponse<any[]>>({
      url: '/monitor/devices',
      method: 'get'
    })
  },
  
  // 获取单个设备信息
  getDevice: (deviceId: number) => {
    return request<any, ApiResponse<any>>({
      url: `/monitor/devices/${deviceId}`,
      method: 'get'
    })
  },
  
  // 添加设备
  addDevice: (data: {
    name: string,
    rtsp_url: string,
    area_config?: any
  }) => {
    return request<any, ApiResponse<any>>({
      url: '/monitor/devices',
      method: 'post',
      data
    })
  },
  
  // 更新设备信息
  updateDevice: (deviceId: number, data: {
    name?: string,
    rtsp_url?: string,
    area_config?: any
  }) => {
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
  
  // 获取设备视频流状态
  getStreamStatus: (deviceId: number) => {
    return request<any, ApiResponse<any>>({
      url: `/monitor/stream/status/${deviceId}`,
      method: 'get'
    })
  },
  
  // 获取所有设备视频流状态
  getAllStreamStatus: () => {
    return request<any, ApiResponse<any>>({
      url: '/monitor/stream/status/all',
      method: 'get'
    })
  }
}

export default deviceApi