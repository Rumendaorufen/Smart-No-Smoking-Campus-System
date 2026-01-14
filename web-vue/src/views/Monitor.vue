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
      
      <div class="right-controls">
        <div class="time-section">
          <div class="current-time">{{ currentTime }}</div>
          <div class="current-date">{{ currentDate }}</div>
        </div>

        <div class="user-actions">
          <el-button 
            v-if="isAdmin" 
            type="warning" 
            size="small" 
            class="action-btn"
            @click="$router.push('/users')"
          >
            <el-icon><Setting /></el-icon>
            用户管理
          </el-button>

          <el-button 
            type="info" 
            size="small" 
            class="action-btn" 
            @click="handleLogout"
          >
            <el-icon><SwitchButton /></el-icon>
            退出
          </el-button>
        </div>
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
          </div>
        </div>
        
        <div class="panel-section">
          <div class="section-title">
            <span class="title-dot"></span>
            快捷操作
          </div>
          <div class="action-buttons">
            <el-button type="primary" size="small" @click="refreshDevices">
              <el-icon><Refresh /></el-icon>
              刷新设备
            </el-button>
            
            <el-button 
              v-if="isAdmin" 
              type="success" 
              size="small" 
              @click="addDevice"
            >
              <el-icon><Plus /></el-icon>
              添加设备
            </el-button>
          </div>
        </div>

        <div class="panel-section user-info-card">
          <div class="user-avatar">{{ username.charAt(0).toUpperCase() }}</div>
          <div class="user-details">
            <div class="user-name">{{ username }}</div>
            <div class="user-role">{{ isAdmin ? '系统管理员' : '监控操作员' }}</div>
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
              <el-icon :size="64"><VideoCameraFilled /></el-icon>
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
              <template v-if="isAdmin">
                <el-button type="primary" plain size="default" @click="editDevice(currentDevice)">
                  <el-icon><Edit /></el-icon> 编辑
                </el-button>
                
                <el-button type="danger" plain size="default" @click="deleteDevice(currentDevice.id)">
                  <el-icon><Delete /></el-icon> 删除
                </el-button>
                <div class="divider"></div>
              </template>

              <el-button type="primary" circle size="large" @click="viewFullScreen(currentDevice.id)" title="全屏沉浸模式">
                <el-icon><FullScreen /></el-icon>
              </el-button>
            </div>
          </div>
        </div>

        <div v-else class="empty-state">
          <el-icon :size="80" color="#606266"><Monitor /></el-icon>
          <p>暂无选中设备，请从右侧列表选择</p>
          <el-button v-if="isAdmin" type="primary" @click="addDevice">立即添加</el-button>
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
                <el-icon><ArrowRight /></el-icon>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="bottom-bar">
      <div class="scan-line"></div>
      <span class="copyright">© 2026 智慧校园禁烟监控系统 | 技术支持：智能视觉分析技术</span>
    </div>

    <el-dialog v-model="fullScreenDialogVisible" title="全屏监控" width="95%" top="2vh" class="fullscreen-dialog" :close-on-click-modal="false">
      <div class="fullscreen-video-container">
        <div v-if="fullScreenDevice" style="width:100%; height:100%">
          <img :src="getStreamUrl(fullScreenDevice.id)" class="fullscreen-video-stream">
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="addDeviceDialogVisible" title="添加设备" width="500px" :close-on-click-modal="false">
      <el-form :model="addDeviceForm" label-width="100px">
        <el-form-item label="设备名称" required><el-input v-model="addDeviceForm.name" /></el-form-item>
        <el-form-item label="RTSP地址" required>
          <el-input v-model="addDeviceForm.rtsp_url" type="textarea" rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDeviceDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAddDevice">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editDeviceDialogVisible" title="编辑设备" width="500px" :close-on-click-modal="false">
      <el-form :model="editDeviceForm" label-width="100px">
        <el-form-item label="设备名称" required><el-input v-model="editDeviceForm.name" /></el-form-item>
        <el-form-item label="RTSP地址" required>
          <el-input v-model="editDeviceForm.rtsp_url" type="textarea" rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDeviceDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitEditDevice">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Setting, SwitchButton, Refresh, Plus, Edit, Delete, 
  FullScreen, VideoCameraFilled, Monitor, ArrowRight 
} from '@element-plus/icons-vue'
import deviceApi from '../api/device'
import authApi from '../api/auth'

const router = useRouter()
const devices = ref<any[]>([]) 
const currentDevice = ref<any>(null)

// 状态管理
const addDeviceDialogVisible = ref(false)
const editDeviceDialogVisible = ref(false)
const fullScreenDialogVisible = ref(false)
const fullScreenDevice = ref<any>(null)
const currentEditingDeviceId = ref<number | null>(null)
const streamVersion = ref(0)
const currentTime = ref('')
const currentDate = ref('')

const addDeviceForm = ref({ name: '', rtsp_url: '' })
const editDeviceForm = ref({ name: '', rtsp_url: '' })

let timeTimer: any = null

// ✅ 权限逻辑核心
const userInfoStr = localStorage.getItem('userInfo')
const currentUser = userInfoStr ? JSON.parse(userInfoStr) : { role: 'user', username: 'Guest' }

const isAdmin = computed(() => currentUser.role === 'admin')
const username = computed(() => currentUser.username || 'User')

const onlineCount = computed(() => devices.value.filter(d => d.status === 1).length)
const offlineCount = computed(() => devices.value.filter(d => d.status !== 1).length)

// 退出登录
const handleLogout = async () => {
  ElMessageBox.confirm('确定要退出系统吗?', '提示', {
    type: 'info'
  }).then(async () => {
    // 调用后端接口(可选)
    try { await authApi.logout() } catch(e) {}
    // 清除本地缓存
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
    ElMessage.success('已退出登录')
    router.push('/login')
  }).catch(() => {})
}

// 切换设备
const switchDevice = (device: any) => {
  currentDevice.value = device
}

// 加载设备列表
const loadDevices = async () => {
  try {
    const response = await deviceApi.getDevices()
    if (response.code === 200) {
      devices.value = response.data.map((device: any) => ({
        ...device,
        isLoading: false
      }))
      
      // 自动选中逻辑
      if (devices.value.length > 0) {
        if (!currentDevice.value || !devices.value.find(d => d.id === currentDevice.value.id)) {
          const firstOnline = devices.value.find(d => d.status === 1)
          currentDevice.value = firstOnline || devices.value[0]
        } else {
          // 更新当前设备状态
          const updatedCurrent = devices.value.find(d => d.id === currentDevice.value.id)
          if(updatedCurrent) currentDevice.value = updatedCurrent
        }
      } else {
        currentDevice.value = null
      }
    }
  } catch (error) {
    console.error(error)
  }
}

// 刷新设备
const refreshDevices = () => {
  loadDevices()
  streamVersion.value++
  ElMessage.success('列表已刷新')
}

// 获取视频流地址 (Flask后端)
const getStreamUrl = (deviceId: number) => {
  // 注意：这里需要 VITE_API_BASE_URL 指向后端根地址(例如 http://localhost:5000)
  // 如果你的 VITE_API_BASE_URL 带了 /api/v1，这里可能需要调整字符串替换
  // 假设 .env 中 VITE_API_BASE_URL = http://localhost:5000/api/v1
  return `${import.meta.env.VITE_API_BASE_URL}/monitor/stream/${deviceId}?v=${streamVersion.value}`
}

// 视频流状态处理
const handleVideoError = (deviceId: number) => {
  const device = devices.value.find(d => d.id === deviceId)
  if (device) {
    device.status = 0
    if (currentDevice.value && currentDevice.value.id === deviceId) currentDevice.value.status = 0
  }
}

const handleVideoLoaded = (deviceId: number) => {
  const device = devices.value.find(d => d.id === deviceId)
  if (device) {
    device.status = 1
    if (currentDevice.value && currentDevice.value.id === deviceId) currentDevice.value.status = 1
  }
}

// 时间更新
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

// 功能操作
const viewFullScreen = (deviceId: number) => {
  const device = devices.value.find(d => d.id === deviceId)
  if (device) {
    fullScreenDevice.value = device
    fullScreenDialogVisible.value = true
  }
}

const editDevice = (device: any) => {
  currentEditingDeviceId.value = device.id
  editDeviceForm.value = { name: device.name, rtsp_url: device.rtsp_url }
  editDeviceDialogVisible.value = true
}

const submitEditDevice = async () => {
  if (!editDeviceForm.value.name || !editDeviceForm.value.rtsp_url) return ElMessage.warning('请填写完整')
  try {
    if (!currentEditingDeviceId.value) return
    const res = await deviceApi.updateDevice(currentEditingDeviceId.value, editDeviceForm.value)
    if (res.code === 200) {
      ElMessage.success('更新成功')
      editDeviceDialogVisible.value = false
      streamVersion.value++
      loadDevices()
    }
  } catch (error) {}
}

const deleteDevice = (deviceId: number) => {
  ElMessageBox.confirm('确定要删除该设备吗？', '警告', {
    type: 'warning'
  }).then(async () => {
    const res = await deviceApi.deleteDevice(deviceId)
    if (res.code === 200) {
      ElMessage.success('删除成功')
      if (currentDevice.value && currentDevice.value.id === deviceId) currentDevice.value = null
      loadDevices()
    }
  }).catch(() => {})
}

const addDevice = () => {
  addDeviceForm.value = { name: '', rtsp_url: '' }
  addDeviceDialogVisible.value = true
}

const submitAddDevice = async () => {
  if (!addDeviceForm.value.name || !addDeviceForm.value.rtsp_url) return ElMessage.warning('请填写完整')
  try {
    const res = await deviceApi.addDevice(addDeviceForm.value)
    if (res.code === 200) {
      ElMessage.success('添加成功')
      addDeviceDialogVisible.value = false
      loadDevices()
    }
  } catch (error) {}
}
</script>

<style scoped>
/* 保持原有深色科技风样式 */
.monitor-screen {
  height: 100vh;
  background: linear-gradient(135deg, #0a0e17 0%, #1a1f2e 50%, #0d1119 100%);
  color: #e4e7ed;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 顶部栏 */
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 30px;
  height: 70px;
  background: rgba(22, 33, 52, 0.95);
  border-bottom: 1px solid rgba(64, 158, 255, 0.2);
  flex-shrink: 0;
}

.logo-section { display: flex; align-items: center; gap: 12px; }
.logo-icon { width: 36px; height: 36px; background: linear-gradient(135deg, #409eff 0%, #67c23a 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; box-shadow: 0 0 15px rgba(64, 158, 255, 0.4); }
.system-title { font-size: 20px; font-weight: 600; background: linear-gradient(90deg, #409eff, #67c23a); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 1px; }

.status-section { display: flex; gap: 40px; }
.status-item { display: flex; flex-direction: column; align-items: center; }
.status-label { font-size: 12px; color: #909399; }
.status-value { font-size: 24px; font-weight: 700; font-family: 'Courier New', monospace; }
.status-value.online { color: #67c23a; }
.status-value.offline { color: #f56c6c; }

.right-controls { display: flex; align-items: center; gap: 20px; }
.time-section { text-align: right; }
.current-time { font-size: 20px; font-weight: 600; color: #409eff; }
.current-date { font-size: 12px; color: #909399; }
.user-actions { display: flex; gap: 10px; }
.action-btn { display: flex; align-items: center; gap: 5px; }

/* 主内容区 */
.main-content { display: flex; padding: 20px; gap: 20px; flex: 1; min-height: 0; }
.side-panel { width: 260px; display: flex; flex-direction: column; gap: 15px; flex-shrink: 0; }
.left-panel { width: 240px; }

.panel-section { background: rgba(22, 33, 52, 0.6); border: 1px solid rgba(64, 158, 255, 0.1); border-radius: 8px; padding: 15px; backdrop-filter: blur(10px); }
.panel-section.full-height { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

.section-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; color: #409eff; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(64, 158, 255, 0.1); }
.title-dot { width: 6px; height: 6px; background: #409eff; border-radius: 50%; }

.status-list { display: flex; flex-direction: column; gap: 10px; }
.status-row { display: flex; align-items: center; gap: 8px; font-size: 13px; padding: 8px; background: rgba(0,0,0,0.2); border-radius: 4px; }
.status-row .status-icon { color: #67c23a; }
.status-tag { margin-left: auto; font-size: 11px; padding: 2px 8px; border-radius: 10px; background: rgba(103, 194, 58, 0.2); color: #67c23a; }

.action-buttons { display: flex; flex-direction: column; gap: 10px; }
.action-buttons .el-button { width: 100%; margin: 0; justify-content: center; }

/* 用户信息卡片 */
.user-info-card { display: flex; align-items: center; gap: 15px; margin-top: auto; }
.user-avatar { width: 40px; height: 40px; background: #409eff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px; }
.user-details { display: flex; flex-direction: column; }
.user-name { font-weight: bold; }
.user-role { font-size: 12px; color: #909399; }

/* 中间大屏 */
.center-monitor { flex: 1; background: rgba(0,0,0,0.2); border-radius: 12px; overflow: hidden; position: relative; display: flex; flex-direction: column; }
.monitor-player-box { width: 100%; height: 100%; display: flex; flex-direction: column; background: rgba(22, 33, 52, 0.8); border: 1px solid rgba(64, 158, 255, 0.3); border-radius: 12px; overflow: hidden; }

.player-header { height: 50px; display: flex; justify-content: space-between; align-items: center; padding: 0 20px; background: linear-gradient(90deg, rgba(64,158,255,0.1) 0%, transparent 100%); }
.header-left { display: flex; align-items: center; gap: 12px; }
.live-badge { background: #f56c6c; padding: 2px 6px; border-radius: 4px; font-size: 12px; font-weight: bold; animation: blink 2s infinite; }
.device-title { font-size: 18px; font-weight: 600; }
.device-id { color: #909399; font-family: monospace; }
.header-status { display: flex; align-items: center; gap: 6px; font-size: 14px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #67c23a; box-shadow: 0 0 8px #67c23a; }
.header-status.offline { color: #f56c6c; }
.header-status.offline .status-dot { background: #f56c6c; box-shadow: none; }

.player-content { flex: 1; background: #000; position: relative; overflow: hidden; display: flex; align-items: center; justify-content: center; }
.main-stream { width: 100%; height: 100%; object-fit: contain; }
.player-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.8); display: flex; flex-direction: column; align-items: center; justify-content: center; color: #909399; z-index: 10; }

.player-controls { height: 60px; background: rgba(10, 14, 23, 0.9); border-top: 1px solid rgba(64,158,255,0.2); display: flex; justify-content: space-between; align-items: center; padding: 0 20px; z-index: 20; }
.control-info { color: #606266; font-size: 12px; font-family: monospace; }
.control-group.right { display: flex; gap: 15px; align-items: center; }
.divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

/* 右侧列表 */
.device-list-scroll { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; padding-right: 5px; }
.device-list-scroll::-webkit-scrollbar { width: 4px; }
.device-list-scroll::-webkit-scrollbar-thumb { background: rgba(64,158,255,0.3); border-radius: 2px; }

.device-nav-item { display: flex; align-items: center; padding: 12px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; cursor: pointer; transition: all 0.2s; }
.device-nav-item:hover { background: rgba(64,158,255,0.1); }
.device-nav-item.active { background: linear-gradient(90deg, rgba(64,158,255,0.2) 0%, transparent 100%); border-color: rgba(64,158,255,0.5); box-shadow: inset 2px 0 0 #409eff; }
.nav-status-indicator { width: 8px; height: 8px; border-radius: 50%; background: #67c23a; margin-right: 12px; }
.device-nav-item.offline .nav-status-indicator { background: #f56c6c; }
.nav-content { flex: 1; }
.nav-name { font-size: 14px; font-weight: 500; }
.nav-sub { font-size: 12px; color: #909399; }
.nav-arrow { opacity: 0; transform: translateX(-5px); transition: all 0.2s; }
.device-nav-item.active .nav-arrow { opacity: 1; transform: translateX(0); }

.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #606266; gap: 20px; }
.bottom-bar { padding: 10px; background: #0d1119; border-top: 1px solid rgba(64,158,255,0.1); text-align: center; font-size: 12px; color: #606266; flex-shrink: 0; }

@keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
.loading-spinner.large { width: 50px; height: 50px; border: 4px solid #409eff; border-top-color: transparent; border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 10px; }
@keyframes spin { to { transform: rotate(360deg); } }

/* 响应式 */
@media (max-width: 1200px) { .left-panel { display: none; } }
.fullscreen-video-stream { width: 100%; height: 100%; object-fit: contain; }
</style>