import request from '../utils/request'

// 设备相关API
const deviceApi = {
  // 获取设备列表
  getDevices: () => {
    return request({
      url: '/monitor/devices',
      method: 'get'
    })
  },
  
  // 获取单个设备信息
  getDevice: (deviceId: number) => {
    return request({
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
    return request({
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
    return request({
      url: `/monitor/devices/${deviceId}`,
      method: 'put',
      data
    })
  },
  
  // 删除设备
  deleteDevice: (deviceId: number) => {
    return request({
      url: `/monitor/devices/${deviceId}`,
      method: 'delete'
    })
  },
  
  // 获取设备视频流状态
  getStreamStatus: (deviceId: number) => {
    return request({
      url: `/monitor/stream/status/${deviceId}`,
      method: 'get'
    })
  },
  
  // 获取所有设备视频流状态
  getAllStreamStatus: () => {
    return request({
      url: '/monitor/stream/status/all',
      method: 'get'
    })
  }
}

export default deviceApi