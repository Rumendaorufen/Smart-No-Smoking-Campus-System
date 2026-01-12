<!-- 实时监控大屏页面 -->
<template>
  <div class="monitor-screen">
    <!-- 顶部状态栏 -->
    <div class="top-bar">
      <div class="logo-section">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
          </svg>
        </div>
        <span class="system-title">智慧校园禁烟监控系统</span>
      </div>
      
      <div class="status-section">
        <div class="status-item">
          <span class="status-label">在线设备</span>
          <span class="status-value online">{{ onlineCount }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">离线设备</span>
          <span class="status-value offline">{{ offlineCount }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">监控区域</span>
          <span class="status-value">{{ devices.length }}</span>
        </div>
      </div>
      
      <div class="time-section">
        <div class="current-time">{{ currentTime }}</div>
        <div class="current-date">{{ currentDate }}</div>
      </div>
    </div>
    
    <!-- 主监控区域 -->
    <div class="main-content">
      <!-- 左侧信息面板 -->
      <div class="side-panel left-panel">
        <div class="panel-section">
          <div class="section-title">
            <span class="title-dot"></span>
            系统状态
          </div>
          <div class="status-list">
            <div class="status-row active">
              <span class="status-icon">●</span>
              <span>视频流服务</span>
              <span class="status-tag">运行中</span>
            </div>
            <div class="status-row active">
              <span class="status-icon">●</span>
              <span>数据采集</span>
              <span class="status-tag">运行中</span>
            </div>
            <div class="status-row active">
              <span class="status-icon">●</span>
              <span>智能分析</span>
              <span class="status-tag">运行中</span>
            </div>
            <div class="status-row">
              <span class="status-icon">●</span>
              <span>告警通知</span>
              <span class="status-tag warning">待激活</span>
            </div>
          </div>
        </div>
        
        <div class="panel-section">
          <div class="section-title">
            <span class="title-dot"></span>
            快捷操作
          </div>
          <div class="action-buttons">
            <el-button type="primary" size="small" @click="refreshDevices">
              <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
              </svg>
              刷新设备
            </el-button>
            <el-button type="success" size="small" @click="addDevice">
              <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
              </svg>
              添加设备
            </el-button>
          </div>
        </div>
      </div>
      
      <!-- 视频监控网格 -->
      <div class="video-grid">
        <div 
          v-for="device in devices" 
          :key="device.id" 
          class="video-card"
          :class="{ 'offline': device.status !== 1 }"
        >
          <div class="card-header">
            <div class="device-name">
              <span class="name-icon">
                <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                  <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/>
                </svg>
              </span>
              {{ device.name }}
            </div>
            <div class="device-status" :class="device.status === 1 ? 'online' : 'offline'">
              <span class="status-dot"></span>
              {{ device.status === 1 ? '在线' : '离线' }}
            </div>
          </div>
          
          <div class="video-container">
            <img 
              :src="getStreamUrl(device.id)" 
              alt="监控画面" 
              class="video-stream"
              @error="handleVideoError(device.id)"
              @load="handleVideoLoaded(device.id)"
            >
            <div v-if="device.status !== 1" class="offline-overlay">
              <svg viewBox="0 0 24 24" fill="currentColor" width="48" height="48">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8 0-1.85.63-3.55 1.69-4.9L16.9 18.31C15.55 19.37 13.85 20 12 20zm6.31-3.1L7.1 5.69C8.45 4.63 10.15 4 12 4c4.42 0 8 3.58 8 8 0 1.85-.63 3.55-1.69 4.9z"/>
              </svg>
              <span>信号丢失</span>
            </div>
            <div v-else-if="device.isLoading" class="loading-overlay">
              <div class="loading-spinner"></div>
              <span>加载中...</span>
            </div>
          </div>
          
          <div class="card-footer">
            <div class="device-info">
              <span class="info-label">设备ID:</span>
              <span class="info-value">{{ device.id }}</span>
            </div>
            <div class="device-actions">
              <el-button size="small" circle @click="viewFullScreen(device.id)" title="全屏">
                <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                  <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
                </svg>
              </el-button>
              <el-button size="small" circle type="warning" @click="editDevice(device)" title="编辑">
                <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                  <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                </svg>
              </el-button>
              <el-button size="small" circle type="danger" @click="deleteDevice(device.id)" title="删除">
                <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                  <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                </svg>
              </el-button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 右侧信息面板 -->
      <div class="side-panel right-panel">
        <div class="panel-section">
          <div class="section-title">
            <span class="title-dot"></span>
            设备列表
          </div>
          <div class="device-list-mini">
            <div 
              v-for="device in devices" 
              :key="device.id" 
              class="device-item"
              :class="{ 'online': device.status === 1, 'offline': device.status !== 1 }"
            >
              <span class="item-status"></span>
              <span class="item-name">{{ device.name }}</span>
            </div>
          </div>
        </div>
        
        <div class="panel-section">
          <div class="section-title">
            <span class="title-dot"></span>
            帮助信息
          </div>
          <div class="help-text">
            <p>• 点击全屏按钮可放大查看单个监控画面</p>
            <p>• 设备离线时请检查网络连接</p>
            <p>• 如需添加新设备，请点击添加设备按钮</p>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 底部信息栏 -->
    <div class="bottom-bar">
      <div class="scan-line"></div>
      <span class="copyright">© 2024 智慧校园禁烟监控系统 | 技术支持：智能视觉分析技术</span>
    </div>
    
    <!-- 全屏视频弹窗 -->
    <el-dialog 
      v-model="fullScreenDialogVisible" 
      title="全屏监控" 
      width="90%"
      height="90%"
      class="fullscreen-dialog"
      :close-on-click-modal="false"
      :close-on-press-escape="true"
    >
      <div class="fullscreen-video-container">
        <div v-if="fullScreenDevice">
          <div class="fullscreen-device-info">
            <h3>{{ fullScreenDevice.name }}</h3>
            <div class="fullscreen-device-status" :class="fullScreenDevice.status === 1 ? 'online' : 'offline'">
              <span class="status-dot"></span>
              {{ fullScreenDevice.status === 1 ? '在线' : '离线' }}
            </div>
          </div>
          <div class="fullscreen-video-wrapper">
            <img 
              :src="getStreamUrl(fullScreenDevice.id)" 
              alt="监控画面" 
              class="fullscreen-video-stream"
              @error="handleVideoError(fullScreenDevice.id)"
              @load="handleVideoLoaded(fullScreenDevice.id)"
            >
            <div v-if="fullScreenDevice.status !== 1" class="fullscreen-offline-overlay">
              <svg viewBox="0 0 24 24" fill="currentColor" width="64" height="64">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8 0-1.85.63-3.55 1.69-4.9L16.9 18.31C15.55 19.37 13.85 20 12 20zm6.31-3.1L7.1 5.69C8.45 4.63 10.15 4 12 4c4.42 0 8 3.58 8 8 0 1.85-.63 3.55-1.69 4.9z"/>
              </svg>
              <span>信号丢失</span>
            </div>
            <div v-else-if="fullScreenDevice.isLoading" class="fullscreen-loading-overlay">
              <div class="loading-spinner"></div>
              <span>加载中...</span>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button type="primary" @click="fullScreenDialogVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 添加设备弹窗 -->
    <el-dialog 
      v-model="addDeviceDialogVisible" 
      title="添加设备" 
      width="500px"
      class="device-dialog"
      :close-on-click-modal="false"
    >
      <el-form :model="addDeviceForm" label-width="100px">
        <el-form-item label="设备名称" required>
          <el-input v-model="addDeviceForm.name" placeholder="请输入设备名称" />
        </el-form-item>
        <el-form-item label="RTSP地址" required>
          <el-input v-model="addDeviceForm.rtsp_url" placeholder="请输入RTSP地址" type="textarea" rows="2" />
          <div class="rtsp-tip">
            格式示例: rtsp://admin:password@192.168.1.101:554/stream1
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="addDeviceDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitAddDevice">确定</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 编辑设备弹窗 -->
    <el-dialog 
      v-model="editDeviceDialogVisible" 
      title="编辑设备" 
      width="500px"
      class="device-dialog"
      :close-on-click-modal="false"
    >
      <el-form :model="editDeviceForm" label-width="100px">
        <el-form-item label="设备名称" required>
          <el-input v-model="editDeviceForm.name" placeholder="请输入设备名称" />
        </el-form-item>
        <el-form-item label="RTSP地址" required>
          <el-input v-model="editDeviceForm.rtsp_url" placeholder="请输入RTSP地址" type="textarea" rows="2" />
          <div class="rtsp-tip">
            格式示例: rtsp://admin:password@192.168.1.101:554/stream1
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDeviceDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitEditDevice">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'
import deviceApi from '../api/device'

const devices = ref<any[]>([]) 
const addDeviceDialogVisible = ref(false)
const editDeviceDialogVisible = ref(false)
const fullScreenDialogVisible = ref(false)
const fullScreenDevice = ref<any>(null)
const currentEditingDeviceId = ref<number | null>(null)
const streamVersion = ref(0) // 用于强制刷新视频流
const addDeviceForm = ref({
  name: '',
  rtsp_url: ''
})
const editDeviceForm = ref({
  name: '',
  rtsp_url: ''
})

const currentTime = ref('')
const currentDate = ref('')
let timeTimer: ReturnType<typeof setInterval> | null = null

const onlineCount = computed(() => devices.value.filter(d => d.status === 1).length)
const offlineCount = computed(() => devices.value.filter(d => d.status !== 1).length)

const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit',
    hour12: false 
  })
  currentDate.value = now.toLocaleDateString('zh-CN', { 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric', 
    weekday: 'long' 
  })
}

onMounted(() => {
  loadDevices()
  updateTime()
  timeTimer = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  if (timeTimer) clearInterval(timeTimer)
})

// 加载设备列表
const loadDevices = async () => {
  try {
    const response = await deviceApi.getDevices()
    if (response.code === 200) {
      // 初始化设备状态，确保每次加载都是全新数据
      devices.value = response.data.map((device: any) => ({
        ...device,
        isLoading: false
      }))
      console.log('设备列表已更新:', devices.value.length, '个设备')
    }
  } catch (error) {
    // 错误由拦截器处理，这里不需要额外处理
  }
}

// 刷新设备
const refreshDevices = () => {
  loadDevices()
  // 刷新视频流版本，强制浏览器重新请求
  streamVersion.value++
  ElMessage.success('正在刷新设备列表...')
}

// 获取视频流URL
const getStreamUrl = (deviceId: number) => {
  // 使用代理路径访问视频流，添加版本号参数防止浏览器缓存
  const url = `${import.meta.env.VITE_API_BASE_URL}/monitor/stream/${deviceId}?v=${streamVersion.value}`
  console.log(`获取视频流URL: ${url}`)
  return url
}

// 处理视频加载错误
const handleVideoError = (deviceId: number) => {
  const device = devices.value.find(d => d.id === deviceId)
  if (device) {
    device.status = 0
    console.error(`设备 ${deviceId} 视频加载失败`)
    ElNotification.error({
      title: '视频加载失败',
      message: `设备 ${device.name} 视频流加载失败，请检查设备连接`,
      duration: 5000
    })
  }
}

// 处理视频加载成功
const handleVideoLoaded = (deviceId: number) => {
  const device = devices.value.find(d => d.id === deviceId)
  if (device) {
    device.status = 1
    console.log(`设备 ${deviceId} 视频加载成功`)
  }
}

// 全屏查看
const viewFullScreen = (deviceId: number) => {
  const device = devices.value.find(d => d.id === deviceId)
  if (device) {
    fullScreenDevice.value = device
    fullScreenDialogVisible.value = true
  }
}

// 编辑设备
const editDevice = (device: any) => {
  currentEditingDeviceId.value = device.id
  // 兼容后端返回的 'rtsp' 或 'rtsp_url' 字段名
  const rtspUrl = device.rtsp_url || device.rtsp || ''
  editDeviceForm.value = {
    name: device.name,
    rtsp_url: rtspUrl
  }
  editDeviceDialogVisible.value = true
}

// 提交编辑设备
const submitEditDevice = async () => {
  // 表单验证
  if (!editDeviceForm.value.name || !editDeviceForm.value.rtsp_url) {
    ElMessage.warning('请填写完整的设备信息')
    return
  }
  
  try {
    if (!currentEditingDeviceId.value) {
      ElMessage.error('设备ID获取失败')
      return
    }
    
    const response = await deviceApi.updateDevice(currentEditingDeviceId.value, editDeviceForm.value)
    if (response.code === 200) {
      ElMessage.success('设备更新成功')
      editDeviceDialogVisible.value = false
      streamVersion.value++ // 先刷新视频流版本
      loadDevices() // 再重新加载设备列表
      currentEditingDeviceId.value = null
    }
  } catch (error) {
    // 错误由拦截器处理，这里不需要额外处理
  }
}

// 删除设备
const deleteDevice = (deviceId: number) => {
  ElMessageBox.confirm('确定要删除该设备吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      const response = await deviceApi.deleteDevice(deviceId)
      if (response.code === 200) {
        ElMessage.success('设备删除成功')
        loadDevices() // 重新加载设备列表
        // 如果当前全屏的是被删除的设备，关闭全屏
        if (fullScreenDevice.value?.id === deviceId) {
          fullScreenDialogVisible.value = false
          fullScreenDevice.value = null
        }
      }
    } catch (error) {
      // 错误由拦截器处理，这里不需要额外处理
    }
  }).catch(() => {
    // 取消删除
  })
}

// 打开添加设备弹窗
const addDevice = () => {
  addDeviceForm.value = {
    name: '',
    rtsp_url: ''
  }
  addDeviceDialogVisible.value = true
}

// 提交添加设备
const submitAddDevice = async () => {
  // 表单验证
  if (!addDeviceForm.value.name || !addDeviceForm.value.rtsp_url) {
    ElMessage.warning('请填写完整的设备信息')
    return
  }
  
  try {
    const response = await deviceApi.addDevice(addDeviceForm.value)
    if (response.code === 200) {
      ElMessage.success('设备添加成功')
      addDeviceDialogVisible.value = false
      loadDevices() // 重新加载设备列表
      streamVersion.value++ // 刷新视频流
    }
  } catch (error) {
    // 错误由拦截器处理，这里不需要额外处理
  }
}
</script>

<style scoped>
.monitor-screen {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0e17 0%, #1a1f2e 50%, #0d1119 100%);
  color: #e4e7ed;
  position: relative;
  overflow: hidden;
}

.monitor-screen::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    radial-gradient(ellipse at 20% 20%, rgba(64, 158, 255, 0.05) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 80%, rgba(64, 158, 255, 0.05) 0%, transparent 50%);
  pointer-events: none;
  z-index: 0;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 30px;
  background: linear-gradient(180deg, rgba(22, 33, 52, 0.95) 0%, rgba(22, 33, 52, 0.8) 100%);
  border-bottom: 1px solid rgba(64, 158, 255, 0.3);
  position: relative;
  z-index: 10;
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.5);
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 0 20px rgba(64, 158, 255, 0.5);
}

.system-title {
  font-size: 20px;
  font-weight: 600;
  background: linear-gradient(90deg, #409eff, #67c23a);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 2px;
}

.status-section {
  display: flex;
  gap: 40px;
}

.status-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.status-label {
  font-size: 12px;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.status-value {
  font-size: 28px;
  font-weight: 700;
  font-family: 'Courier New', monospace;
}

.status-value.online {
  color: #67c23a;
  text-shadow: 0 0 20px rgba(103, 194, 58, 0.5);
}

.status-value.offline {
  color: #f56c6c;
  text-shadow: 0 0 20px rgba(245, 108, 108, 0.5);
}

.time-section {
  text-align: right;
}

.current-time {
  font-size: 24px;
  font-weight: 600;
  font-family: 'Courier New', monospace;
  color: #409eff;
  text-shadow: 0 0 15px rgba(64, 158, 255, 0.5);
}

.current-date {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.main-content {
  display: flex;
  padding: 20px;
  gap: 20px;
  position: relative;
  z-index: 5;
  min-height: calc(100vh - 140px);
}

.side-panel {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.panel-section {
  background: rgba(22, 33, 52, 0.8);
  border: 1px solid rgba(64, 158, 255, 0.2);
  border-radius: 8px;
  padding: 15px;
  backdrop-filter: blur(10px);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #409eff;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(64, 158, 255, 0.2);
}

.title-dot {
  width: 8px;
  height: 8px;
  background: #409eff;
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(64, 158, 255, 0.8);
}

.status-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  padding: 8px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
}

.status-row.active .status-icon {
  color: #67c23a;
}

.status-row .status-icon {
  color: #909399;
}

.status-tag {
  margin-left: auto;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(103, 194, 58, 0.2);
  color: #67c23a;
}

.status-tag.warning {
  background: rgba(230, 162, 60, 0.2);
  color: #e6a23c;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.action-buttons .el-button {
  justify-content: center;
  gap: 6px;
  border-radius: 6px;
}

.device-list-mini {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 200px;
  overflow-y: auto;
}

.device-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  font-size: 12px;
}

.device-item .item-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.device-item.online .item-status {
  background: #67c23a;
  box-shadow: 0 0 8px rgba(103, 194, 58, 0.8);
}

.device-item.offline .item-status {
  background: #f56c6c;
  box-shadow: 0 0 8px rgba(245, 108, 108, 0.8);
}

.help-text {
  font-size: 12px;
  color: #909399;
}

.help-text p {
  margin: 6px 0;
  padding-left: 12px;
  position: relative;
}

.help-text p::before {
  content: '›';
  position: absolute;
  left: 0;
  color: #409eff;
}

.video-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
  align-content: start;
}

.video-card {
  background: rgba(22, 33, 52, 0.9);
  border: 1px solid rgba(64, 158, 255, 0.3);
  border-radius: 10px;
  overflow: hidden;
  transition: all 0.3s ease;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.video-card:hover {
  border-color: rgba(64, 158, 255, 0.6);
  box-shadow: 0 0 30px rgba(64, 158, 255, 0.2);
  transform: translateY(-2px);
}

.video-card.offline {
  border-color: rgba(245, 108, 108, 0.3);
}

.video-card.offline:hover {
  border-color: rgba(245, 108, 108, 0.6);
  box-shadow: 0 0 30px rgba(245, 108, 108, 0.2);
}

.video-card .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  background: linear-gradient(90deg, rgba(64, 158, 255, 0.1) 0%, transparent 100%);
  border-bottom: 1px solid rgba(64, 158, 255, 0.2);
}

.device-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
}

.name-icon {
  color: #409eff;
}

.device-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.device-status .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.device-status.online .status-dot {
  background: #67c23a;
  box-shadow: 0 0 10px rgba(103, 194, 58, 0.8);
  animation: pulse-green 2s infinite;
}

.device-status.online {
  color: #67c23a;
}

.device-status.offline .status-dot {
  background: #f56c6c;
  box-shadow: 0 0 10px rgba(245, 108, 108, 0.8);
}

.device-status.offline {
  color: #f56c6c;
}

@keyframes pulse-green {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.video-container {
  position: relative;
  width: 100%;
  height: 200px;
  background: #000;
  overflow: hidden;
}

.video-stream {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.offline-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #909399;
}

.offline-overlay svg {
  opacity: 0.5;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #409eff;
  font-size: 13px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(64, 158, 255, 0.2);
  border-top-color: #409eff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.video-card .card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: rgba(0, 0, 0, 0.3);
}

.device-info {
  display: flex;
  gap: 8px;
  font-size: 12px;
}

.info-label {
  color: #909399;
}

.info-value {
  color: #e4e7ed;
  font-family: 'Courier New', monospace;
}

.device-actions {
  display: flex;
  gap: 6px;
}

.device-actions .el-button {
  padding: 6px;
  min-height: 28px;
  min-width: 28px;
}

.bottom-bar {
  padding: 12px 30px;
  background: linear-gradient(180deg, rgba(22, 33, 52, 0.8) 0%, rgba(22, 33, 52, 0.6) 100%);
  border-top: 1px solid rgba(64, 158, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.scan-line {
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, transparent, #409eff, transparent);
  animation: scan 3s linear infinite;
}

@keyframes scan {
  0% { left: -100%; }
  100% { left: 100%; }
}

.copyright {
  font-size: 12px;
  color: #606266;
  letter-spacing: 1px;
}

:deep(.el-dialog) {
  background: #1a1f2e;
  border: 1px solid rgba(64, 158, 255, 0.3);
  border-radius: 10px;
}

:deep(.el-dialog__header) {
  border-bottom: 1px solid rgba(64, 158, 255, 0.2);
  padding-bottom: 15px;
}

:deep(.el-dialog__title) {
  color: #e4e7ed;
}

:deep(.el-form-item__label) {
  color: #e4e7ed;
}

:deep(.el-input__wrapper),
:deep(.el-textarea__inner) {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(64, 158, 255, 0.2);
  box-shadow: none;
  color: #e4e7ed;
}

:deep(.el-input__inner),
:deep(.el-textarea__inner) {
  color: #e4e7ed;
}

:deep(.el-input__inner::placeholder),
:deep(.el-textarea__inner::placeholder) {
  color: #606266;
}

.rtsp-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

@media (max-width: 1200px) {
  .side-panel {
    display: none;
  }
}

@media (max-width: 768px) {
  .top-bar {
    flex-direction: column;
    gap: 15px;
    padding: 15px;
  }
  
  .status-section {
    gap: 20px;
  }
  
  .video-grid {
    grid-template-columns: 1fr;
  }
}

/* 全屏视频弹窗样式 */
.fullscreen-dialog {
  display: flex;
  align-items: center;
  justify-content: center;
}

:deep(.fullscreen-dialog .el-dialog__body) {
  padding: 0;
  height: calc(100% - 100px);
  overflow: hidden;
}

.fullscreen-video-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #000;
}

.fullscreen-device-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: rgba(22, 33, 52, 0.95);
  border-bottom: 1px solid rgba(64, 158, 255, 0.3);
}

.fullscreen-device-info h3 {
  margin: 0;
  font-size: 20px;
  color: #e4e7ed;
  font-weight: 600;
}

.fullscreen-device-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
}

.fullscreen-device-status.online {
  color: #67c23a;
}

.fullscreen-device-status.offline {
  color: #f56c6c;
}

.fullscreen-video-wrapper {
  flex: 1;
  position: relative;
  width: 100%;
  height: calc(100% - 60px);
  overflow: hidden;
}

.fullscreen-video-stream {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.fullscreen-offline-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 15px;
  color: #909399;
  font-size: 18px;
}

.fullscreen-offline-overlay svg {
  opacity: 0.7;
}

.fullscreen-loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 15px;
  color: #409eff;
  font-size: 18px;
}

:deep(.fullscreen-dialog) {
  background: #1a1f2e;
  border: 1px solid rgba(64, 158, 255, 0.3);
  border-radius: 10px;
}

:deep(.fullscreen-dialog .el-dialog__header) {
  border-bottom: 1px solid rgba(64, 158, 255, 0.2);
  padding-bottom: 15px;
}

:deep(.fullscreen-dialog .el-dialog__title) {
  color: #e4e7ed;
  font-size: 18px;
  font-weight: 600;
}

:deep(.fullscreen-dialog .el-dialog__footer) {
  border-top: 1px solid rgba(64, 158, 255, 0.2);
  padding-top: 15px;
}
</style>
