// src/stores/device.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import deviceApi from '../api/device'
import { ElMessage } from 'element-plus'

// 定义设备接口
export interface DeviceVO {
  id: number
  name: string
  rtsp_url: string
  status: number // 1:在线, 0:离线
  created_at: string
  isRetrying?: boolean // UI状态：是否正在重连
  failTip?: string     // UI状态：错误提示
  isLoading?: boolean  // UI状态：是否正在加载图片
}

export const useDeviceStore = defineStore('device', () => {
  // --- State ---
  const deviceList = ref<DeviceVO[]>([])
  const streamVersion = ref(0) // 用于强制刷新视频流
  const loading = ref(false)   // 全局加载状态
  let pollTimer: any = null    // 轮询定时器

  // --- Actions ---

  // 1. 获取视频流地址 (计算属性风格的 helper)
  const getStreamUrl = (id: number) => {
    return `${import.meta.env.VITE_API_BASE_URL}/monitor/stream/${id}?v=${streamVersion.value}`
  }

  // 2. 更新单个设备的本地状态 (Helper)
  const updateDeviceState = (id: number, updates: Partial<DeviceVO>) => {
    const target = deviceList.value.find(d => d.id === id)
    if (target) {
      Object.assign(target, updates)
    }
  }

  // 3. 核心：加载设备列表 (带智能合并逻辑)
  const fetchDevices = async (isSilent = false) => {
    if (!isSilent) loading.value = true
    
    try {
      const res = await deviceApi.getDevices()
      if (res.code === 200) {
        const serverList = res.data
        
        // 🔄 智能合并策略 (直接移植之前的逻辑)
        // 这里的 deviceList 是全局的，所以无论哪个页面触发，状态都能保住
        deviceList.value = serverList.map((serverItem: DeviceVO) => {
          const localItem = deviceList.value.find(d => d.id === serverItem.id)
          
          if (!localItem) return { ...serverItem, isLoading: false }

          // 保护重连状态
          if (localItem.isRetrying) {
            return {
              ...serverItem,
              status: localItem.status,
              isRetrying: true,
              failTip: ''
            }
          }
          
          // 保护错误提示
          if (localItem.failTip) {
            return {
              ...serverItem,
              status: 0,
              failTip: localItem.failTip
            }
          }

          // 保护图片加载状态 (防止 Monitor 页面闪烁)
          return {
            ...serverItem,
            isLoading: localItem.isLoading || false
          }
        })
      }
    } catch (e) {
      console.error(e)
    } finally {
      if (!isSilent) loading.value = false
    }
  }

  // 4. 重试连接逻辑
  const retryConnection = async (id: number) => {
    // 立即更新状态
    updateDeviceState(id, { isRetrying: true, failTip: '' })
    
    try {
      // 这里的超时时间要长，因为后端要跑很久
      const res = await deviceApi.getStreamStatus(id)

      if (res.code === 200 && res.data.status === 1) {
        setTimeout(() => {
          updateDeviceState(id, { status: 1, isRetrying: false, failTip: '' })
          streamVersion.value++ // 全局刷新版本号
          fetchDevices(true)    // 同步列表
          ElMessage.success('连接恢复')
        }, 500)
      } else {
        const msg = res.msg || '无法连接设备'
        updateDeviceState(id, { isRetrying: false, failTip: msg, status: 0 })
      }
    } catch (e: any) {
      console.error('Retry error:', e)
      let errorMsg = '网络请求失败'
      if (e.message && (e.message.includes('timeout') || e.code === 'ECONNABORTED')) {
        errorMsg = '请求响应超时'
      }
      updateDeviceState(id, { isRetrying: false, failTip: errorMsg, status: 0 })
    }
  }

  // 5. 处理视频流自然断开
  const handleVideoError = (id: number) => {
    const target = deviceList.value.find(d => d.id === id)
    if (target && target.status === 1) {
      console.log(`视频流断开: ID ${id}`)
      updateDeviceState(id, { status: 0, failTip: '视频流连接中断' })
    }
  }

  // 6. 启动轮询
  const startPolling = () => {
    if (pollTimer) return // 防止重复启动
    fetchDevices(false)   // 首次加载
    pollTimer = setInterval(() => {
      fetchDevices(true)  // 静默轮询
    }, 3000)
  }

  // 7. 停止轮询
  const stopPolling = () => {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  // 8. ⭐ 新增：一键重连所有离线设备
  const reconnectAll = async () => {
    // 1. 筛选出所有离线设备
    const offlineDevices = deviceList.value.filter(d => d.status !== 1)
    
    if (offlineDevices.length === 0) {
      ElMessage.info('所有设备均已在线，无需重连')
      return
    }

    ElMessage.success(`开始尝试重连 ${offlineDevices.length} 台设备...`)
    
    // 2. 并发执行重连
    // 使用 Promise.all 可能导致后端压力过大，稍微限制一下并发比较好
    // 但对于 10-20 台设备，直接并发没问题
    offlineDevices.forEach(device => {
      retryConnection(device.id)
    })
  }

  return {
    deviceList,
    streamVersion,
    loading,
    getStreamUrl,
    fetchDevices,
    retryConnection,
    handleVideoError,
    startPolling,
    stopPolling,
    updateDeviceState ,// 导出这个以便 Monitor 更新 isLoading
    reconnectAll
  }
})