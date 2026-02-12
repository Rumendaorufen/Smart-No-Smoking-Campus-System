import { defineStore } from 'pinia'
import { ref } from 'vue'
import deviceApi from '../api/device' // 🚀 确保此文件已定义 getStatusOnly 方法
import { ElMessage } from 'element-plus'

// 定义设备接口
export interface DeviceVO {
  id: number
  name: string
  rtspUrl: string 
  status: number    // 1:在线, 0:离线
  enabled: boolean  // 🚀 核心：启停状态
  created_at: string
  isRetrying?: boolean // UI状态：是否正在重连
  failTip?: string     // UI状态：错误提示
  isVideoError?: boolean // UI状态：视频加载错误
}

export const useDeviceStore = defineStore('device', () => {
  // --- State ---
  const deviceList = ref<DeviceVO[]>([])
  const streamVersion = ref(0) // 用于强制刷新视频流
  const loading = ref(false)   // 全局加载状态
  let pollTimer: any = null    // 轮询定时器

  // --- Actions ---

  // 1. 获取视频流地址 (Helper)
  const getStreamUrl = (id: number) => {
    // 自动读取环境变量中的 AI 地址
    const aiBase = import.meta.env.VITE_APP_AI_API || 'http://localhost:5000'
    return `${aiBase}/api/v1/monitor/stream/${id}?v=${streamVersion.value}`
  }

  // 2. 更新单个设备的本地状态 (Helper)
  const updateDeviceState = (id: number, updates: Partial<DeviceVO>) => {
    const target = deviceList.value.find(d => d.id === id)
    if (target) {
      Object.assign(target, updates)
    }
  }

  // 3. 全量同步：用于页面初始化（获取 RTSP URL 等全量数据）
  const fetchDevices = async (isSilent = false) => {
    if (!isSilent) loading.value = true
    try {
      const res = await deviceApi.getDevices()
      if (res.code === 200) {
        // 智能合并：保留本地的重连状态，不被服务器覆盖
        const serverList = res.data
        deviceList.value = serverList.map((serverItem: any) => {
          const localItem = deviceList.value.find(d => d.id === serverItem.id)
          return {
            ...serverItem,
            rtspUrl: serverItem.rtspUrl || serverItem.rtsp_url, // 字段兼容
            // 保护本地 UI 状态
            isRetrying: localItem?.isRetrying || false,
            isVideoError: localItem?.isVideoError || false
          }
        })
      }
    } catch (e) {
      console.error('Fetch devices error:', e)
    } finally {
      if (!isSilent) loading.value = false
    }
  }

  // 4. 🚀 极简状态轮询：解决 500 错误和卡死问题
  // 必须确保 deviceApi.getStatusOnly() 已经定义
  const pollStatusOnly = async () => {
    if (document.hidden) return // 标签页隐藏时不请求

    try {
      // 🚀 使用封装好的 api 避免 Token 缺失导致的 500
      // 如果没有封装，请确保 axios 请求带上 Header
      const res = await deviceApi.getStatusOnly() 
      
      if (res && res.code === 200) {
        const remoteStatuses = res.data
        deviceList.value.forEach(localDev => {
          const remote = remoteStatuses.find((s: any) => s.id === localDev.id)
          if (remote) {
            // 只有非正在重连状态下，才更新在线状态
            if (!localDev.isRetrying) {
              localDev.status = remote.status
            }
            localDev.enabled = remote.enabled // 同步启停开关
          }
        })
      }
    } catch (e) {
      console.error('Status polling error:', e)
    }
  }

  // 5. 重试连接逻辑
 // src/stores/device.ts

const retryConnection = async (id: number) => {
  updateDeviceState(id, { isRetrying: true, isVideoError: false });
  try {
    const res = await deviceApi.getStreamStatus(id);
    if (res.code === 200) {
      // 🚀 核心：成功后立即修改版本号，带上随机数彻底杀死缓存
      streamVersion.value = Date.now(); 
      updateDeviceState(id, { status: 1, isRetrying: false });
      console.log("✅ 前端状态已更新，准备重载图像");
    }
  } catch (e) {
    updateDeviceState(id, { isRetrying: false });
  }
}

  // 6. 启动轮询
  const startPolling = () => {
    if (pollTimer) return 
    // 首次全量同步
    fetchDevices(false)
    // 开启 5 秒一次的状态同步
    pollTimer = setInterval(pollStatusOnly, 5000)
  }

  // 7. 停止轮询
  const stopPolling = () => {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  // 8. 一键重连
  const reconnectAll = async () => {
    const offlineOnes = deviceList.value.filter(d => d.enabled && d.status === 0)
    if (offlineOnes.length === 0) return ElMessage.info('没有需要重连的设备')
    
    ElMessage.success(`正在重连 ${offlineOnes.length} 台设备...`)
    offlineOnes.forEach(d => retryConnection(d.id))
  }

  return {
    deviceList,
    streamVersion,
    loading,
    getStreamUrl,
    fetchDevices,
    retryConnection,
    startPolling,
    stopPolling,
    updateDeviceState,
    reconnectAll,
    pollStatusOnly
  }
})