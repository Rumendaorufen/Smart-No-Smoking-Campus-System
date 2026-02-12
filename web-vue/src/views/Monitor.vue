<template>
  <div class="monitor-screen">
    <div class="top-bar">
      <div class="logo-section">
        <div class="logo-icon">
          <el-icon :size="20"><Platform /></el-icon>
        </div>
        <span class="system-title">智慧校园禁烟监控系统</span>
      </div>
      
      <div class="status-section">
        <div class="status-item">
          <span class="status-label">在线</span>
          <span class="status-value online">{{ onlineCount }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">离线</span>
          <span class="status-value offline">{{ offlineCount }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">总数</span>
          <span class="status-value">{{ deviceList.length }}</span>
        </div>
      </div>
      
      <div class="right-controls">
        <div class="time-section">
          <div class="current-time">{{ currentTime }}</div>
          <div class="current-date">{{ currentDate }}</div>
        </div>

        <div class="user-actions">
          <el-button type="danger" size="small" class="action-btn" @click="$router.push('/audit')">
            <el-icon><Bell /></el-icon> 报警仲裁
          </el-button>
          
          <el-button type="primary" size="small" class="action-btn" @click="$router.push('/archive')">
            <el-icon><Files /></el-icon> 历史档案
          </el-button>
          
          <template v-if="isAdmin">
            <el-button type="success" size="small" class="action-btn" @click="$router.push('/system')">
              <el-icon><Odometer /></el-icon> 系统控制
            </el-button>
            <el-button type="warning" size="small" class="action-btn" @click="$router.push('/devices')">
              <el-icon><VideoCameraFilled /></el-icon> 设备管理
            </el-button>
          </template>

          <el-button type="info" size="small" class="action-btn" @click="handleLogout" circle>
            <el-icon><SwitchButton /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
    
    <div class="main-content">
      <aside class="side-panel left-panel">
        <div class="panel-section">
          <div class="section-title"><span class="title-dot"></span> 运行状态</div>
          <div class="status-list">
            <div class="status-row">
              <span class="status-icon" :style="{ color: systemStatus.totalStreams > 0 ? '#67c23a' : '#909399' }">●</span>
              <span>视频流服务</span>
              <span class="status-tag" :class="systemStatus.totalStreams > 0 ? 'online' : 'offline'">
                {{ systemStatus.totalStreams > 0 ? '推流中' : '空闲' }}
              </span>
            </div>
            <div class="status-row">
              <span class="status-icon" :style="{ color: systemStatus.globalAi ? '#67c23a' : '#f56c6c' }">●</span>
              <span>AI 检测引擎</span>
              <span class="status-tag" :class="systemStatus.globalAi ? 'online' : 'offline'">
                {{ systemStatus.globalAi ? '运行中' : '已暂停' }}
              </span>
            </div>
            <div class="status-row">
              <span class="status-icon" :style="{ color: isSocketConnected ? '#67c23a' : '#f56c6c' }">●</span>
              <span>WebSocket</span>
              <span class="status-tag" :class="isSocketConnected ? 'online' : 'offline'">
                {{ isSocketConnected ? '已连接' : '断开' }}
              </span>
            </div>
          </div>
        </div>
        
        <div class="panel-section">
          <div class="section-title"><span class="title-dot"></span> 快速管理</div>
          <div class="action-buttons">
            <el-button type="primary" class="manage-btn" @click="refreshDevices">
              <el-icon><Refresh /></el-icon> 刷新设备列表
            </el-button>
            <el-button type="warning" class="manage-btn" @click="handleReconnectAll" :loading="isGlobalRetrying">
              <el-icon><Connection /></el-icon> 重连离线设备
            </el-button>
          </div>
        </div>

        <div class="panel-section user-info-card">
          <div class="user-avatar">{{ username.charAt(0) }}</div>
          <div class="user-details">
            <div class="user-name">{{ username }}</div>
            <div class="user-role">{{ isAdmin ? '系统管理员' : '监控操作员' }}</div>
          </div>
        </div>
      </aside>
      
      <section class="center-monitor">
        <div v-if="currentDevice" class="monitor-player-box" 
             :class="{ 'offline': currentDevice.isVideoError, 'is-alarm': alarmState[currentDevice.id] }">
          
          <div class="player-header">
            <div class="header-left">
              <span v-if="!currentDevice.isVideoError" class="live-badge">LIVE</span>
              <span v-else class="offline-badge">OFFLINE</span>
              <span class="device-title">{{ currentDevice.name }}</span>
              <span class="device-id">#{{ currentDevice.id }}</span>
            </div>
            <div class="header-status" :class="!currentDevice.isVideoError ? 'online' : 'offline'">
              <span class="status-dot"></span>
              {{ !currentDevice.isVideoError ? '信号正常' : '信号丢失' }}
            </div>
          </div>

          <div class="player-content">
            <img 
              :src="getStreamUrl(currentDevice.id)" 
              class="main-stream" 
              v-show="!currentDevice.isVideoError"
              @error="handleVideoError(currentDevice.id)" 
              @load="handleVideoLoaded(currentDevice.id)"
            >
            
            <div v-if="currentDevice.isVideoError" class="player-overlay">
              <el-icon :size="64" :class="{ 'spin-icon': currentDevice.isRetrying, 'error-icon': !currentDevice.isRetrying }">
                <component :is="currentDevice.isRetrying ? Loading : CircleCloseFilled" />
              </el-icon>
              <div style="margin-top:20px" :class="{ 'error-text': !currentDevice.isRetrying }">
                {{ currentDevice.isRetrying ? '正在重连 AI 引擎...' : '监控信号中断 (Python 404)' }}
              </div>
              <el-button v-if="!currentDevice.isRetrying" type="primary" size="small" style="margin-top:15px" @click="retryConnection">重试连接</el-button>
            </div>
            
            <div v-if="alarmState[currentDevice.id]" class="alarm-overlay">
              <el-icon class="nav-alarm-icon"><Warning /></el-icon>
              <span>警告：检测到违规吸烟行为！</span>
            </div>
          </div>

          <div class="player-controls">
            <div class="control-info">URL: {{ currentDevice.rtspUrl }}</div>
            <div class="control-group right">
              <el-button type="primary" :icon="FullScreen" @click="viewFullScreen(currentDevice.id)" circle plain></el-button>
            </div>
          </div>
        </div>

        <div v-else class="empty-state">
          <el-icon :size="80"><Monitor /></el-icon>
          <p>请选择监控区域</p>
        </div>
      </section>
      
      <aside class="side-panel right-panel">
        <div class="panel-section full-height">
          <div class="section-title"><span class="title-dot"></span> 监控矩阵 ({{ deviceList.length }})</div>
          <div class="device-list-scroll">
            <div v-for="device in deviceList" 
                 :key="device.id" 
                 class="device-nav-item" 
                 :class="{ 
                    'active': currentDevice?.id === device.id, 
                    'offline': device.status !== 1,
                    'is-alarm': alarmState[device.id]
                 }" 
                 @click="switchDevice(device)">
              <div class="nav-status-indicator"></div>
              <div class="nav-content">
                <div class="nav-name">{{ device.name }}</div>
                <div class="nav-sub">ID: {{ device.id }}</div>
              </div>
              <el-icon v-if="alarmState[device.id]" class="blink-icon" color="#f56c6c"><Warning /></el-icon>
              <div class="nav-arrow"><el-icon><ArrowRight /></el-icon></div>
            </div>
          </div>
        </div>
      </aside>
    </div>
    
    <div class="bottom-bar">
      <span>© 2026 智慧校园禁烟监控系统 · 实时视觉 AI 检测已开启</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useDeviceStore } from '../stores/device'
import { storeToRefs } from 'pinia'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { 
  Setting, SwitchButton, Refresh, Connection, Bell, Files, Platform,
  FullScreen, VideoCameraFilled, Monitor, Loading, Warning, CircleCloseFilled, Odometer, ArrowRight
} from '@element-plus/icons-vue'
import axios from 'axios'
import SockJS from 'sockjs-client'
import Stomp from 'stompjs'

const JAVA_BASE = import.meta.env.VITE_APP_BASE_API || 'http://localhost:8080'
const AI_API = import.meta.env.VITE_APP_AI_API || 'http://localhost:5000'

const systemStatus = reactive({ totalStreams: 0, globalAi: false })
const isSocketConnected = ref(false)
const alarmState = ref<Record<number, boolean>>({}) 

let stompClient: any = null
let socket: any = null

const initWebSocket = () => {
  socket = new SockJS(`${JAVA_BASE}/ws`)
  stompClient = Stomp.over(socket)
  stompClient.debug = null 
  stompClient.connect({}, () => {
    isSocketConnected.value = true
    stompClient.subscribe('/topic/alarm', (res: any) => {
      handleIncomingAlarm(JSON.parse(res.body))
    })
  }, () => {
    isSocketConnected.value = false
    setTimeout(initWebSocket, 5000)
  })
}

const handleIncomingAlarm = (alarm: any) => {
  const devId = alarm.cameraId
  alarmState.value[devId] = true
   ElNotification({ title: '发现吸烟违规', message: `${alarm.deviceName} 区域告警`, type: 'error', position: 'bottom-right' })
  setTimeout(() => { alarmState.value[devId] = false }, 8000)
}

const fetchSystemStatus = async () => {
  try {
    const res = await axios.get(`${JAVA_BASE}/api/system/status`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    if (res.data.code === 200) {
      systemStatus.totalStreams = res.data.data.business?.devices?.filter((d:any) => d.status === 1).length || 0
      systemStatus.globalAi = res.data.data.business?.globalAi || false
    }
  } catch (e) {}
}

const deviceStore = useDeviceStore()
const { deviceList } = storeToRefs(deviceStore)
const currentDevice = ref<any>(null)
const currentTime = ref(''), currentDate = ref('')
const router = useRouter()

const getStreamUrl = (id: number) => `${AI_API}/api/v1/monitor/stream/${id}?t=${deviceStore.streamVersion}`

const currentUser = JSON.parse(localStorage.getItem('userInfo') || '{}')
const isAdmin = computed(() => currentUser.role === 'admin')
const username = computed(() => currentUser.username || 'Admin')
const onlineCount = computed(() => deviceList.value.filter(d => d.status === 1).length)
const offlineCount = computed(() => deviceList.value.filter(d => d.status !== 1).length)
const isGlobalRetrying = computed(() => deviceList.value.some(d => d.isRetrying))

const switchDevice = (device: any) => {
  // 🚀 切换时重置该设备的错误状态，防止白屏
  deviceStore.updateDeviceState(device.id, { isVideoError: false, isLoading: true })
  currentDevice.value = device
}

const handleLogout = () => {
  ElMessageBox.confirm('确定退出系统监控？', '退出确认').then(() => {
    localStorage.clear(); router.push('/login')
  })
}

const retryConnection = () => {
  if(currentDevice.value) {
    deviceStore.updateDeviceState(currentDevice.value.id, { isVideoError: false })
    deviceStore.retryConnection(currentDevice.value.id)
  }
}
const refreshDevices = () => deviceStore.fetchDevices(false)
const handleReconnectAll = () => deviceStore.reconnectAll()

// 🚀 视频加载失败处理器
const handleVideoError = (id: number) => {
    deviceStore.updateDeviceState(id, { 
        isVideoError: true,   // 触发遮罩
        isLoading: false 
    })
}

// 🚀 视频加载成功处理器
const handleVideoLoaded = (id: number) => {
    deviceStore.updateDeviceState(id, { 
        isVideoError: false, 
        isLoading: false 
    })
}

watch(deviceList, (newList) => {
  if (!currentDevice.value && newList.length > 0) {
    currentDevice.value = newList[0]
  } else if (currentDevice.value) {
    const found = newList.find(d => d.id === currentDevice.value.id)
    if (found) currentDevice.value = found
  }
}, { deep: true })

onMounted(() => {
  const updateTime = () => {
    const now = new Date()
    currentTime.value = now.toLocaleTimeString('zh-CN', { hour12: false })
    currentDate.value = now.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
  }
  updateTime(); setInterval(updateTime, 1000)
  deviceStore.startPolling()
  initWebSocket()
  fetchSystemStatus(); setInterval(fetchSystemStatus, 10000)
})

onUnmounted(() => {
  deviceStore.stopPolling()
  if (stompClient) stompClient.disconnect(() => {})
})

const viewFullScreen = (id: number) => {
  ElMessage.info("正在进入全屏模式...")
  // 全屏逻辑可根据需要补充
}
</script>

<style scoped>

/* 原有样式保持不变 */

.monitor-screen { height: 100vh; background: linear-gradient(135deg, #0a0e17 0%, #1a1f2e 50%, #0d1119 100%); color: #e4e7ed; display: flex; flex-direction: column; overflow: hidden; }



/* 顶部栏 */

.top-bar { display: flex; justify-content: space-between; align-items: center; padding: 0 30px; height: 70px; background: rgba(22, 33, 52, 0.95); border-bottom: 1px solid rgba(64, 158, 255, 0.2); flex-shrink: 0; }

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



/* 动画和错误样式 */

.spin-icon { animation: spin 1s linear infinite; color: #409eff; }

.error-icon { color: #f56c6c; animation: shake 0.4s ease-in-out; }

.error-text { color: #f56c6c !important; font-weight: bold; }

@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

@keyframes shake { 0%, 100% { transform: translateX(0); } 25% { transform: translateX(-5px); } 75% { transform: translateX(5px); } }



.section-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; color: #409eff; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(64, 158, 255, 0.1); }

.title-dot { width: 6px; height: 6px; background: #409eff; border-radius: 50%; }



.status-list { display: flex; flex-direction: column; gap: 10px; }

.status-row { display: flex; align-items: center; gap: 8px; font-size: 13px; padding: 8px; background: rgba(0,0,0,0.2); border-radius: 4px; }

.status-row .status-icon { color: #67c23a; }

.status-tag { margin-left: auto; font-size: 11px; padding: 2px 8px; border-radius: 10px; background: rgba(103, 194, 58, 0.2); color: #67c23a; }

.status-tag.offline { background: rgba(245, 108, 108, 0.2); color: #f56c6c; }

.status-tag.online { background: rgba(103, 194, 58, 0.2); color: #67c23a; }



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

.monitor-player-box { width: 100%; height: 100%; display: flex; flex-direction: column; background: rgba(22, 33, 52, 0.8); border: 1px solid rgba(64, 158, 255, 0.3); border-radius: 12px; overflow: hidden; transition: all 0.3s; }

.monitor-player-box.offline { border-color: #f56c6c; background: rgba(40, 10, 10, 0.8); }



/* 🔥 红框报警特效 */

.monitor-player-box.is-alarm {

  border-color: #F56C6C;

  box-shadow: 0 0 30px rgba(245, 108, 108, 0.6) inset;

  animation: flashBorder 0.8s infinite alternate;

}

@keyframes flashBorder {

  from { border-color: #F56C6C; box-shadow: 0 0 10px #F56C6C; }

  to { border-color: transparent; box-shadow: none; }

}



.player-header { height: 50px; display: flex; justify-content: space-between; align-items: center; padding: 0 20px; background: linear-gradient(90deg, rgba(64,158,255,0.1) 0%, transparent 100%); }

.header-left { display: flex; align-items: center; gap: 12px; }

.live-badge { background: #f56c6c; padding: 2px 6px; border-radius: 4px; font-size: 12px; font-weight: bold; animation: blink 2s infinite; }

.offline-badge { background: #909399; padding: 2px 6px; border-radius: 4px; font-size: 12px; font-weight: bold; }



.device-title { font-size: 18px; font-weight: 600; }

.device-id { color: #909399; font-family: monospace; }

.header-status { display: flex; align-items: center; gap: 6px; font-size: 14px; }

.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #67c23a; box-shadow: 0 0 8px #67c23a; }

.header-status.offline { color: #f56c6c; }

.header-status.offline .status-dot { background: #f56c6c; box-shadow: none; }



.player-content { flex: 1; background: #000; position: relative; overflow: hidden; display: flex; align-items: center; justify-content: center; }

.main-stream { width: 100%; height: 100%; object-fit: contain; }

.player-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.8); display: flex; flex-direction: column; align-items: center; justify-content: center; color: #909399; z-index: 10; }



/* 🔥 报警文字遮罩 */

.alarm-overlay {

  position: absolute;

  top: 20px;

  left: 50%;

  transform: translateX(-50%);

  background: rgba(245, 108, 108, 0.9);

  color: white;

  padding: 8px 20px;

  border-radius: 20px;

  display: flex;

  align-items: center;

  gap: 10px;

  font-weight: bold;

  font-size: 16px;

  z-index: 100;

  animation: blink 0.5s infinite;

}



.player-controls { height: 60px; background: rgba(10, 14, 23, 0.9); border-top: 1px solid rgba(64,158,255,0.2); display: flex; justify-content: space-between; align-items: center; padding: 0 20px; z-index: 20; }

.control-info { color: #606266; font-size: 12px; font-family: monospace; }

.control-group.right { display: flex; gap: 15px; align-items: center; }



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



/* 🔥 列表项报警闪烁 */

.device-nav-item.is-alarm {

  border: 1px solid #f56c6c;

  background: rgba(245, 108, 108, 0.1);

  animation: blink 1s infinite;

}

.nav-alarm-icon { margin-right: 10px; animation: shake 0.5s infinite; }



.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #606266; gap: 20px; }

.bottom-bar { padding: 10px; background: #0d1119; border-top: 1px solid rgba(64,158,255,0.1); text-align: center; font-size: 12px; color: #606266; flex-shrink: 0; }



@keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }

.loading-spinner.large { width: 50px; height: 50px; border: 4px solid #409eff; border-top-color: transparent; border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 10px; }

.fullscreen-video-stream { width: 100%; height: 100%; object-fit: contain; }

.fullscreen-offline { display: flex; justify-content: center; align-items: center; height: 100%; font-size: 30px; color: #f56c6c; }



@media (max-width: 1200px) { .left-panel { display: none; } }

</style>