<template>
  <div class="monitor-screen">
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
    
    <div class="main-content">
      
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
      
      <div class="center-monitor">
        <div v-if="currentDevice" class="monitor-player-box" :class="{ 'offline': currentDevice.status !== 1 }">
          <div class="player-header">
            <div class="header-left">
              <span class="live-badge">LIVE</span>
              <span class="device-title">{{ currentDevice.name }}</span>
              <span class="device-id">ID: {{ currentDevice.id }}</span>
            </div>
            <div class="header-status" :class="currentDevice.status === 1 ? 'online' : 'offline'">
              <span class="status-dot"></span>
              {{ currentDevice.status === 1 ? '信号正常' : '信号丢失' }}
            </div>
          </div>

          <div class="player-content">
            <img 
              :src="getStreamUrl(currentDevice.id)" 
              alt="监控画面" 
              class="main-stream"
              @error="handleVideoError(currentDevice.id)"
              @load="handleVideoLoaded(currentDevice.id)"
            >
            
            <div v-if="currentDevice.status !== 1" class="player-overlay offline">
              <svg viewBox="0 0 24 24" fill="currentColor" width="64" height="64">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8 0-1.85.63-3.55 1.69-4.9L16.9 18.31C15.55 19.37 13.85 20 12 20zm6.31-3.1L7.1 5.69C8.45 4.63 10.15 4 12 4c4.42 0 8 3.58 8 8 0 1.85-.63 3.55-1.69 4.9z"/>
              </svg>
              <div class="overlay-text">设备离线</div>
              <div class="overlay-sub">请检查网络或RTSP配置</div>
            </div>
            
            <div v-else-if="currentDevice.isLoading" class="player-overlay loading">
              <div class="loading-spinner large"></div>
              <div class="overlay-text">正在连接视频流...</div>
            </div>
          </div>

          <div class="player-controls">
            <div class="control-group">
                <div class="control-info">
                    RTSP: {{ currentDevice.rtsp_url }}
                </div>
            </div>
            <div class="control-group right">
              <el-button type="primary" plain size="default" @click="editDevice(currentDevice)">
                <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16" style="margin-right:5px">
                  <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                </svg>
                编辑配置
              </el-button>
              
              <el-button type="danger" plain size="default" @click="deleteDevice(currentDevice.id)">
                <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16" style="margin-right:5px">
                  <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                </svg>
                删除设备
              </el-button>

              <div class="divider"></div>

              <el-button type="primary" circle size="large" @click="viewFullScreen(currentDevice.id)" title="全屏沉浸模式">
                <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                  <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
                </svg>
              </el-button>
            </div>
          </div>
        </div>

        <div v-else class="empty-state">
          <svg viewBox="0 0 24 24" fill="currentColor" width="64" height="64">
            <path d="M21 3H3c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h5v2h8v-2h5c1.1 0 1.99-.9 1.99-2L23 5c0-1.1-.9-2-2-2zm0 14H3V5h18v12z"/>
          </svg>
          <p>暂无选中设备，请从右侧列表选择或添加新设备</p>
          <el-button type="primary" @click="addDevice">立即添加</el-button>
        </div>
      </div>
      
      <div class="side-panel right-panel">
        <div class="panel-section full-height">
          <div class="section-title">
            <span class="title-dot"></span>
            监控列表 ({{ devices.length }})
          </div>
          <div class="device-list-scroll">
            <div 
              v-for="device in devices" 
              :key="device.id" 
              class="device-nav-item"
              :class="{ 
                'active': currentDevice && currentDevice.id === device.id,
                'offline': device.status !== 1 
              }"
              @click="switchDevice(device)"
            >
              <div class="nav-status-indicator"></div>
              <div class="nav-content">
                <div class="nav-name">{{ device.name }}</div>
                <div class="nav-sub">ID: {{ device.id }}</div>
              </div>
              <div class="nav-arrow">
                <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                  <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"/>
                </svg>
              </div>
            </div>
          </div>
        </div>
        
        </div>
    </div>
    
    <div class="bottom-bar">
      <div class="scan-line"></div>
      <span class="copyright">© 2024 智慧校园禁烟监控系统 | 技术支持：智能视觉分析技术</span>
    </div>

    <el-dialog v-model="fullScreenDialogVisible" title="全屏监控" width="90%" height="90%" class="fullscreen-dialog" :close-on-click-modal="false" :close-on-press-escape="true">
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
            <img :src="getStreamUrl(fullScreenDevice.id)" alt="监控画面" class="fullscreen-video-stream" @error="handleVideoError(fullScreenDevice.id)" @load="handleVideoLoaded(fullScreenDevice.id)">
            <div v-if="fullScreenDevice.status !== 1" class="fullscreen-offline-overlay">
              <svg viewBox="0 0 24 24" fill="currentColor" width="64" height="64"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8 0-1.85.63-3.55 1.69-4.9L16.9 18.31C15.55 19.37 13.85 20 12 20zm6.31-3.1L7.1 5.69C8.45 4.63 10.15 4 12 4c4.42 0 8 3.58 8 8 0 1.85-.63 3.55-1.69 4.9z"/></svg>
              <span>信号丢失</span>
            </div>
          </div>
        </div>
      </div>
      <template #footer><span class="dialog-footer"><el-button type="primary" @click="fullScreenDialogVisible = false">关闭</el-button></span></template>
    </el-dialog>

    <el-dialog v-model="addDeviceDialogVisible" title="添加设备" width="500px" class="device-dialog" :close-on-click-modal="false">
      <el-form :model="addDeviceForm" label-width="100px">
        <el-form-item label="设备名称" required><el-input v-model="addDeviceForm.name" placeholder="请输入设备名称" /></el-form-item>
        <el-form-item label="RTSP地址" required>
          <el-input v-model="addDeviceForm.rtsp_url" placeholder="请输入RTSP地址" type="textarea" rows="2" />
          <div class="rtsp-tip">格式示例: rtsp://admin:password@192.168.1.101:554/stream1</div>
        </el-form-item>
      </el-form>
      <template #footer><span class="dialog-footer"><el-button @click="addDeviceDialogVisible = false">取消</el-button><el-button type="primary" @click="submitAddDevice">确定</el-button></span></template>
    </el-dialog>

    <el-dialog v-model="editDeviceDialogVisible" title="编辑设备" width="500px" class="device-dialog" :close-on-click-modal="false">
      <el-form :model="editDeviceForm" label-width="100px">
        <el-form-item label="设备名称" required><el-input v-model="editDeviceForm.name" placeholder="请输入设备名称" /></el-form-item>
        <el-form-item label="RTSP地址" required>
          <el-input v-model="editDeviceForm.rtsp_url" placeholder="请输入RTSP地址" type="textarea" rows="2" />
          <div class="rtsp-tip">格式示例: rtsp://admin:password@192.168.1.101:554/stream1</div>
        </el-form-item>
      </el-form>
      <template #footer><span class="dialog-footer"><el-button @click="editDeviceDialogVisible = false">取消</el-button><el-button type="primary" @click="submitEditDevice">确定</el-button></span></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'
import deviceApi from '../api/device'

const devices = ref<any[]>([]) 
// 新增：当前选中的设备
const currentDevice = ref<any>(null)

// 弹窗状态
const addDeviceDialogVisible = ref(false)
const editDeviceDialogVisible = ref(false)
const fullScreenDialogVisible = ref(false)
const fullScreenDevice = ref<any>(null)
const currentEditingDeviceId = ref<number | null>(null)
const streamVersion = ref(0)

const addDeviceForm = ref({ name: '', rtsp_url: '' })
const editDeviceForm = ref({ name: '', rtsp_url: '' })

const currentTime = ref('')
const currentDate = ref('')
let timeTimer: ReturnType<typeof setInterval> | null = null

const onlineCount = computed(() => devices.value.filter(d => d.status === 1).length)
const offlineCount = computed(() => devices.value.filter(d => d.status !== 1).length)

// 新增：切换设备函数
const switchDevice = (device: any) => {
  currentDevice.value = device
}

// 修改：加载设备列表后自动选中第一个
const loadDevices = async () => {
  try {
    const response = await deviceApi.getDevices()
    if (response.code === 200) {
      devices.value = response.data.map((device: any) => ({
        ...device,
        isLoading: false
      }))
      
      // 逻辑：如果当前没有选中设备，或者选中的设备不在新列表中，默认选中第一个
      if (devices.value.length > 0) {
        if (!currentDevice.value || !devices.value.find(d => d.id === currentDevice.value.id)) {
          // 优先找在线的，没有在线的就找第一个
          const firstOnline = devices.value.find(d => d.status === 1)
          currentDevice.value = firstOnline || devices.value[0]
        } else {
          // 如果当前设备还在列表里，更新它的状态信息
          const updatedCurrent = devices.value.find(d => d.id === currentDevice.value.id)
          if(updatedCurrent) currentDevice.value = updatedCurrent
        }
      } else {
        currentDevice.value = null
      }
      
      console.log('设备列表已更新:', devices.value.length, '个设备')
    }
  } catch (error) {
    console.error(error)
  }
}

// 刷新设备
const refreshDevices = () => {
  loadDevices()
  streamVersion.value++
  ElMessage.success('正在刷新设备列表...')
}

const getStreamUrl = (deviceId: number) => {
  return `${import.meta.env.VITE_API_BASE_URL}/monitor/stream/${deviceId}?v=${streamVersion.value}`
}

const handleVideoError = (deviceId: number) => {
  const device = devices.value.find(d => d.id === deviceId)
  if (device) {
    device.status = 0
    // 如果出错的是当前大屏显示的设备，强制更新视图状态
    if (currentDevice.value && currentDevice.value.id === deviceId) {
        currentDevice.value.status = 0
    }
  }
}

const handleVideoLoaded = (deviceId: number) => {
  const device = devices.value.find(d => d.id === deviceId)
  if (device) {
    device.status = 1
    if (currentDevice.value && currentDevice.value.id === deviceId) {
        currentDevice.value.status = 1
    }
  }
}

// 保持其他逻辑不变...
const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  currentDate.value = now.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
}

onMounted(() => {
  loadDevices()
  updateTime()
  timeTimer = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  if (timeTimer) clearInterval(timeTimer)
})

const viewFullScreen = (deviceId: number) => {
  const device = devices.value.find(d => d.id === deviceId)
  if (device) {
    fullScreenDevice.value = device
    fullScreenDialogVisible.value = true
  }
}

const editDevice = (device: any) => {
  currentEditingDeviceId.value = device.id
  const rtspUrl = device.rtsp_url || device.rtsp || ''
  editDeviceForm.value = {
    name: device.name,
    rtsp_url: rtspUrl
  }
  editDeviceDialogVisible.value = true
}

const submitEditDevice = async () => {
  if (!editDeviceForm.value.name || !editDeviceForm.value.rtsp_url) {
    ElMessage.warning('请填写完整的设备信息')
    return
  }
  try {
    if (!currentEditingDeviceId.value) return
    const response = await deviceApi.updateDevice(currentEditingDeviceId.value, editDeviceForm.value)
    if (response.code === 200) {
      ElMessage.success('设备更新成功')
      editDeviceDialogVisible.value = false
      streamVersion.value++
      loadDevices()
      currentEditingDeviceId.value = null
    }
  } catch (error) {}
}

const deleteDevice = (deviceId: number) => {
  ElMessageBox.confirm('确定要删除该设备吗？', '警告', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
  }).then(async () => {
    try {
      const response = await deviceApi.deleteDevice(deviceId)
      if (response.code === 200) {
        ElMessage.success('设备删除成功')
        // 如果删除的是当前正在看的设备，置空，等待loadDevices重新选择
        if (currentDevice.value && currentDevice.value.id === deviceId) {
            currentDevice.value = null
        }
        loadDevices()
      }
    } catch (error) {}
  }).catch(() => {})
}

const addDevice = () => {
  addDeviceForm.value = { name: '', rtsp_url: '' }
  addDeviceDialogVisible.value = true
}

const submitAddDevice = async () => {
  if (!addDeviceForm.value.name || !addDeviceForm.value.rtsp_url) {
    ElMessage.warning('请填写完整的设备信息')
    return
  }
  try {
    const response = await deviceApi.addDevice(addDeviceForm.value)
    if (response.code === 200) {
      ElMessage.success('设备添加成功')
      addDeviceDialogVisible.value = false
      loadDevices()
      streamVersion.value++
    }
  } catch (error) {}
}
</script>

<style scoped>
/* 保持原有基础样式，新增和修改部分如下 */
.monitor-screen {
  height: 100vh;
  background: linear-gradient(135deg, #0a0e17 0%, #1a1f2e 50%, #0d1119 100%);
  color: #e4e7ed;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 顶部栏保持不变 */
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
  flex-shrink: 0;
}
/* ...logo-section, status-section, time-section 样式保持不变... */
.logo-section { display: flex; align-items: center; gap: 12px; }
.logo-icon { width: 36px; height: 36px; background: linear-gradient(135deg, #409eff 0%, #67c23a 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; box-shadow: 0 0 20px rgba(64, 158, 255, 0.5); }
.system-title { font-size: 20px; font-weight: 600; background: linear-gradient(90deg, #409eff, #67c23a); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; letter-spacing: 2px; }
.status-section { display: flex; gap: 40px; }
.status-item { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.status-label { font-size: 12px; color: #909399; text-transform: uppercase; letter-spacing: 1px; }
.status-value { font-size: 28px; font-weight: 700; font-family: 'Courier New', monospace; }
.status-value.online { color: #67c23a; text-shadow: 0 0 20px rgba(103, 194, 58, 0.5); }
.status-value.offline { color: #f56c6c; text-shadow: 0 0 20px rgba(245, 108, 108, 0.5); }
.time-section { text-align: right; }
.current-time { font-size: 24px; font-weight: 600; font-family: 'Courier New', monospace; color: #409eff; text-shadow: 0 0 15px rgba(64, 158, 255, 0.5); }
.current-date { font-size: 12px; color: #909399; margin-top: 4px; }

/* 主布局修改 */
.main-content {
  display: flex;
  padding: 20px;
  gap: 20px;
  position: relative;
  z-index: 5;
  flex: 1; /* 撑满剩余高度 */
  min-height: 0; /* 🛑 关键：允许容器收缩，防止被内部内容撑大 */
  overflow: hidden; /* 防止内容溢出产生滚动条 */
}

/* 侧边栏样式 */
.side-panel {
  width: 260px; /* 稍微加宽一点 */
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.left-panel { width: 220px; } /* 左侧保持窄一点 */

.panel-section {
  background: rgba(22, 33, 52, 0.8);
  border: 1px solid rgba(64, 158, 255, 0.2);
  border-radius: 8px;
  padding: 15px;
  backdrop-filter: blur(10px);
}

.panel-section.full-height {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 中间大屏样式 (核心修改) */
.center-monitor {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  overflow: hidden;
  position: relative;
  min-height: 0; /* 🛑 关键：防止视频过大撑破布局 */
}

.monitor-player-box {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: rgba(22, 33, 52, 0.9);
  border: 1px solid rgba(64, 158, 255, 0.3);
  border-radius: 12px;
  box-shadow: 0 0 40px rgba(0, 0, 0, 0.5);
  overflow: hidden; /* 🛑 确保子元素不溢出圆角 */
}

.player-header {
  height: 50px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  background: linear-gradient(90deg, rgba(64, 158, 255, 0.15) 0%, transparent 100%);
  border-bottom: 1px solid rgba(64, 158, 255, 0.2);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.live-badge {
  background: #f56c6c;
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
  animation: blink 2s infinite;
}

.device-title {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}

.device-id {
  font-size: 12px;
  color: #909399;
  font-family: monospace;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.header-status.online { color: #67c23a; }
.header-status.online .status-dot { background: #67c23a; box-shadow: 0 0 10px #67c23a; }
.header-status.offline { color: #f56c6c; }
.header-status.offline .status-dot { background: #f56c6c; }

.player-content {
  flex: 1;
  background: #000;
  position: relative;
  overflow: hidden;
  display: flex; /* 确保图片居中 */
  align-items: center;
  justify-content: center;
  min-height: 0; /* 🛑 关键：再次确保图片不撑大容器 */
}

.main-stream {
  width: 100%;
  height: 100%;
  /* ❌ 原来的写法：强制拉伸铺满 (会导致变形) */
  /* object-fit: fill; */ 
  
  /* ✅ 修正写法：保持比例 (可能会有黑边，但画面正常) */
  object-fit: contain; 
  
  /* 可选：如果你想要铺满且不变形 (会裁剪掉一部分画面边缘)，用 cover */
  /* object-fit: cover; *//* 强制铺满 */
}
.fullscreen-video-stream {
  width: 100%;
  height: 100%;
  object-fit: contain; /* 保持全屏时也不变形 */
}

.player-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
  z-index: 10;
}

.player-controls {
  height: 60px;
  background: rgba(10, 14, 23, 0.95);
  border-top: 1px solid rgba(64, 158, 255, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  flex-shrink: 0; /* 🛑 防止控制栏被压缩 */
  position: relative; 
  z-index: 20; /* 🛑 提高层级 */
}

.control-info {
    color: #606266;
    font-size: 12px;
    font-family: monospace;
}

.control-group.right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.divider {
  width: 1px;
  height: 24px;
  background: rgba(255,255,255,0.1);
  margin: 0 5px;
}

/* 右侧导航列表样式 */
.device-list-scroll {
  flex: 1;
  overflow-y: auto;
  padding-right: 5px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 自定义滚动条 */
.device-list-scroll::-webkit-scrollbar { width: 4px; }
.device-list-scroll::-webkit-scrollbar-thumb { background: rgba(64, 158, 255, 0.3); border-radius: 2px; }

.device-nav-item {
  display: flex;
  align-items: center;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  overflow: hidden;
}

.device-nav-item:hover {
  background: rgba(64, 158, 255, 0.1);
}

.device-nav-item.active {
  background: linear-gradient(90deg, rgba(64, 158, 255, 0.2) 0%, transparent 100%);
  border-color: rgba(64, 158, 255, 0.5);
  box-shadow: inset 2px 0 0 #409eff;
}

.nav-status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #67c23a;
  box-shadow: 0 0 8px rgba(103, 194, 58, 0.5);
  margin-right: 12px;
}

.device-nav-item.offline .nav-status-indicator {
  background: #f56c6c;
  box-shadow: none;
}

.nav-content {
  flex: 1;
}

.nav-name {
  font-size: 14px;
  color: #fff;
  font-weight: 500;
  margin-bottom: 2px;
}

.nav-sub {
  font-size: 12px;
  color: #909399;
}

.nav-arrow {
  opacity: 0;
  color: #409eff;
  transform: translateX(-5px);
  transition: all 0.2s;
}

.device-nav-item.active .nav-arrow {
  opacity: 1;
  transform: translateX(0);
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #606266;
  gap: 20px;
}

/* 底部栏 */
.bottom-bar {
  padding: 10px 30px;
  background: #0d1119;
  border-top: 1px solid rgba(64, 158, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
}

/* 左侧栏样式补充 */
.section-title {
  display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; color: #409eff; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(64, 158, 255, 0.2);
}
.title-dot { width: 8px; height: 8px; background: #409eff; border-radius: 50%; box-shadow: 0 0 10px rgba(64, 158, 255, 0.8); }
.status-list { display: flex; flex-direction: column; gap: 10px; }
.status-row { display: flex; align-items: center; gap: 8px; font-size: 13px; padding: 8px; background: rgba(0, 0, 0, 0.3); border-radius: 4px; }
.status-row.active .status-icon { color: #67c23a; }
.status-row .status-icon { color: #909399; }
.status-tag { margin-left: auto; font-size: 11px; padding: 2px 8px; border-radius: 10px; background: rgba(103, 194, 58, 0.2); color: #67c23a; }
.status-tag.warning { background: rgba(230, 162, 60, 0.2); color: #e6a23c; }
.action-buttons { display: flex; flex-direction: column; gap: 10px; }
.action-buttons .el-button {
  display: flex;       /* 确保内容居中 */
  justify-content: center;
  align-items: center;
  gap: 6px;
  border-radius: 6px;
  width: 100%;         /* 强制占满宽度 */
  margin-left: 0 !important; /* 🛑 关键：清除 Element Plus 默认的左边距 */
  margin-right: 0;     /* 保险起见，清除右边距 */
  height: 36px;        /* 建议固定高度，视觉更统一 */
}
@keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
@keyframes spin { to { transform: rotate(360deg); } }
.loading-spinner.large { width: 60px; height: 60px; border-width: 4px; }

/* 响应式 */
@media (max-width: 1200px) {
  .left-panel { display: none; }
}
</style>