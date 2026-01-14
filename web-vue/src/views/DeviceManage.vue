<template>
  <div class="device-manage-container">
    
    <div class="sidebar">
      <div class="sidebar-header">
        <h2>设备管理中心</h2>
        <div class="subtitle">Device Management</div>
      </div>

      <div class="stats-card">
        <div class="stat-item">
          <span class="label">在线设备</span>
          <span class="value online">{{ onlineCount }}</span>
        </div>
        <div class="divider"></div>
        <div class="stat-item">
          <span class="label">离线/故障</span>
          <span class="value offline">{{ offlineCount }}</span>
        </div>
      </div>

      <div class="action-area">
        <el-button type="primary" class="add-btn" @click="openDialog('add')">
          <el-icon><Plus /></el-icon> 新增监控设备
        </el-button>
        <el-button class="back-btn" @click="$router.push('/')">
          <el-icon><Monitor /></el-icon> 返回监控大屏
        </el-button>
      </div>

      <div class="mini-list-title">设备索引</div>
      <div class="mini-device-list">
        <div 
          v-for="item in deviceList" 
          :key="item.id" 
          class="mini-item"
          :class="{ 'is-offline': item.status !== 1 }"
          @click="scrollToCard(item.id)"
        >
          <div class="status-dot"></div>
          <span class="name">{{ item.name }}</span>
          <span class="id">#{{ item.id }}</span>
        </div>
      </div>
    </div>

    <div class="main-grid-area">
      <div class="grid-header">
        <span class="title">实时预览矩阵</span>
        <el-button circle size="small" @click="refreshAll" title="刷新所有画面">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>

      <div class="video-grid" v-loading="loading">
        <div 
          v-for="device in deviceList" 
          :key="device.id" 
          :id="'card-' + device.id"
          class="video-card"
          :class="{ 'offline': device.status !== 1 }"
        >
          <div class="card-header">
            <div class="card-title">
              <span class="live-tag" v-if="device.status === 1">LIVE</span>
              <span class="offline-tag" v-else>OFF</span>
              <span class="name">{{ device.name }}</span>
            </div>
            <div class="card-time">{{ formatTime(device.created_at) }}</div>
          </div>

          <div class="card-video">
  
            <img 
                v-if="device.status === 1"
                :src="getStreamUrl(device.id)" 
                loading="lazy"
                @error="handleVideoError(device)"
            />

            <div v-else-if="device.isRetrying" class="retry-mask">
                <div class="radar-spinner"></div>
                <div class="retry-text">正在建立连接...</div>
            </div>

            <div v-else class="offline-placeholder">
                <el-icon :size="48" class="offline-icon"><VideoCameraFilled /></el-icon>
                <p class="offline-tip">信号中断</p>
                
                <button class="retry-btn" @click="retryStream(device)">
                <el-icon class="icon"><RefreshRight /></el-icon>
                点击重连
                </button>
            </div>
            
            </div>

          <div class="card-footer">
            <div class="rtsp-info" :title="device.rtsp_url">
              {{ device.rtsp_url }}
            </div>
            <div class="card-actions">
              <el-button type="primary" circle size="small" @click="openDialog('edit', device)">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button type="danger" circle size="small" @click="handleDelete(device)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
        </div>

        <div v-if="deviceList.length === 0 && !loading" class="empty-grid">
          <el-empty description="暂无设备，请点击左侧添加" />
        </div>
      </div>
    </div>

    <el-dialog 
      v-model="dialogVisible" 
      :title="dialogMode === 'add' ? '添加监控设备' : '编辑设备配置'" 
      width="500px"
      :close-on-click-modal="false"
      class="custom-dialog"
    >
      <el-form :model="form" label-width="90px">
        <el-form-item label="设备名称" required>
          <el-input v-model="form.name" placeholder="例如：东门大厅摄像头" />
        </el-form-item>
        <el-form-item label="RTSP地址" required>
          <el-input 
            v-model="form.rtsp_url" 
            type="textarea" 
            :rows="3" 
            placeholder="rtsp://admin:password@ip:port/stream" 
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue' // ✅ 新增 onUnmounted
import deviceApi from '../api/device'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Plus, Monitor, Edit, Delete, Refresh, VideoCameraFilled 
} from '@element-plus/icons-vue'

interface DeviceVO {
  id: number;
  name: string;
  rtsp_url: string;
  status: number; // 1在线 0离线
  created_at: string;
  isRetrying?: boolean; // ✅ 新增：标记该设备是否正在重连
  failTip?: string;     // ✅ 新增：专门存失败提示文案
}

const deviceList = ref<DeviceVO[]>([])
const loading = ref(false)
const streamVersion = ref(0) 

// 弹窗相关
const dialogVisible = ref(false)
const dialogMode = ref<'add' | 'edit'>('add')
const currentId = ref<number | null>(null)
const form = ref({ name: '', rtsp_url: '' })

// ✅ 新增：轮询定时器变量
let pollTimer: any = null

// 计算属性
const onlineCount = computed(() => deviceList.value.filter(d => d.status === 1).length)
const offlineCount = computed(() => deviceList.value.filter(d => d.status !== 1).length)

// ✅ 改造：支持静默加载 (isSilent)
// isSilent = true 时，不显示加载转圈，用于后台轮询
const loadDevices = async (isSilent = false) => {
  if (!isSilent) {
    loading.value = true
  }
  
  try {
    const res = await deviceApi.getDevices()
    if (res.code === 200) {
      // 对比新旧数据，只有状态变了才会有视觉变化
      deviceList.value = res.data
    }
  } catch (e) {
    console.error(e)
  } finally {
    if (!isSilent) {
      loading.value = false
    }
  }
}

// 获取流地址
const getStreamUrl = (id: number) => {
  return `${import.meta.env.VITE_API_BASE_URL}/monitor/stream/${id}?v=${streamVersion.value}`
}

// 视频加载失败处理
const handleVideoError = (device: DeviceVO) => {
  if (device.status === 1) {
    device.status = 0
  }
}

// 手动刷新所有流
const refreshAll = () => {
  streamVersion.value = Date.now()
  loadDevices(false) // 手动点击时，显示 loading 动画
  ElMessage.success('正在刷新视频矩阵...')
}

// 尝试单个重连
// 2. 重写重连逻辑：失败 0 延迟，成功才给一点动画缓冲
const retryStream = async (device: DeviceVO) => {
  // 1. 初始化状态
  device.isRetrying = true;
  device.failTip = ''; // 清空之前的错误
  
  try {
    // 发起请求
    const res = await deviceApi.getStreamStatus(device.id);

    if (res.code === 200 && res.data.status === 1) {
      // ✅ 成功分支：给 500ms 缓冲，让用户看清“连接成功”的动画，避免闪烁
      setTimeout(() => {
        device.status = 1;
        device.isRetrying = false;
        streamVersion.value++; 
        loadDevices(true);
      }, 500);
    } else {
      // ❌ 失败分支：不等待！立即显示错误
      device.failTip = '无法连接设备'; // 设置错误文案
      device.isRetrying = false;     // 立即停止转圈
    }
  } catch (e) {
    // ❌ 网络错误：立即显示
    device.failTip = '网络请求超时';
    device.isRetrying = false;
  }
}

// 滚动定位
const scrollToCard = (id: number) => {
  const el = document.getElementById(`card-${id}`)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

// CRUD 操作 (保持不变)
const openDialog = (mode: 'add' | 'edit', row?: DeviceVO) => {
  dialogMode.value = mode
  dialogVisible.value = true
  if (mode === 'edit' && row) {
    currentId.value = row.id
    form.value = { name: row.name, rtsp_url: row.rtsp_url }
  } else {
    currentId.value = null
    form.value = { name: '', rtsp_url: '' }
  }
}

const handleSubmit = async () => {
  if (!form.value.name || !form.value.rtsp_url) return ElMessage.warning('请填写完整')
  try {
    if (dialogMode.value === 'add') {
      const res = await deviceApi.addDevice(form.value)
      if (res.code === 200) ElMessage.success('添加成功')
    } else {
      if (!currentId.value) return
      const res = await deviceApi.updateDevice(currentId.value, form.value)
      if (res.code === 200) ElMessage.success('更新成功')
    }
    dialogVisible.value = false
    loadDevices(false) // 提交后刷新显示 loading
    streamVersion.value++
  } catch (e) {}
}

const handleDelete = (row: DeviceVO) => {
  ElMessageBox.confirm(`确定删除 ${row.name}?`, '警告', { type: 'warning' })
    .then(async () => {
      const res = await deviceApi.deleteDevice(row.id)
      if (res.code === 200) {
        ElMessage.success('删除成功')
        loadDevices(false)
      }
    }).catch(() => {})
}

const formatTime = (timeStr: string) => {
  if(!timeStr) return ''
  return new Date(timeStr).toLocaleDateString()
}

// ✅ 生命周期管理
onMounted(() => {
  loadDevices(false) // 第一次加载，显示 Loading
  
  // 启动轮询：每 3 秒悄悄请求一次最新状态
  pollTimer = setInterval(() => {
    loadDevices(true) // 这里的 true 表示静默加载，不闪烁
  }, 3000)
})

onUnmounted(() => {
  // 离开页面时销毁定时器，否则会报错或占用资源
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.device-manage-container {
  display: flex;
  height: 100vh;
  background: #0d1119;
  color: #fff;
  overflow: hidden;
}

/* 左侧侧边栏 */
.sidebar {
  width: 280px;
  background: rgba(22, 33, 52, 0.95);
  border-right: 1px solid rgba(64, 158, 255, 0.2);
  display: flex;
  flex-direction: column;
  padding: 20px;
  flex-shrink: 0;
  z-index: 10;
}

.sidebar-header h2 { margin: 0; font-size: 20px; color: #409eff; }
.subtitle { font-size: 12px; color: #909399; margin-bottom: 20px; letter-spacing: 1px; }

.stats-card {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  padding: 15px;
  display: flex;
  justify-content: space-around;
  margin-bottom: 20px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.stat-item { display: flex; flex-direction: column; align-items: center; }
.stat-item .label { font-size: 12px; color: #909399; margin-bottom: 5px; }
.stat-item .value { font-size: 20px; font-weight: bold; }
.value.online { color: #67c23a; }
.value.offline { color: #f56c6c; }
.divider { width: 1px; background: rgba(255, 255, 255, 0.1); }

.action-area {
  display: flex;
  flex-direction: column; /* 垂直排列 */
  gap: 15px;              /* 按钮之间的间距 */
  margin-bottom: 30px;
  width: 100%;            /* 确保容器占满 */
}

.action-area .el-button {
  width: 100%;            /* 让按钮撑满容器宽度 */
  margin-left: 0 !important; /* 🛑 核心修复：清除 Element Plus 默认的左边距 */
  margin-right: 0;
  height: 40px;           /* 统一高度 */
  justify-content: center; /*以此确保文字/图标居中 */
  border-radius: 8px;     /* 可选：加一点圆角更好看 */
}

/* 单独定制返回按钮样式 */
.back-btn {
  background: transparent !important;
  border: 1px solid rgba(144, 147, 153, 0.5) !important;
  color: #909399 !important;
}

.back-btn:hover {
  border-color: #409eff !important;
  color: #409eff !important;
  background: rgba(64, 158, 255, 0.1) !important;
}
.mini-list-title { font-size: 12px; color: #606266; margin-bottom: 10px; font-weight: bold; }
.mini-device-list { flex: 1; overflow-y: auto; padding-right: 5px; }
/* 隐藏滚动条但保留功能 */
.mini-device-list::-webkit-scrollbar { width: 4px; }
.mini-device-list::-webkit-scrollbar-thumb { background: #333; border-radius: 2px; }

.mini-item {
  display: flex; align-items: center; padding: 10px;
  border-radius: 6px; cursor: pointer; transition: all 0.2s;
  margin-bottom: 5px;
}
.mini-item:hover { background: rgba(64, 158, 255, 0.1); }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: #67c23a; margin-right: 10px; }
.is-offline .status-dot { background: #f56c6c; }
.mini-item .name { font-size: 13px; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mini-item .id { font-size: 12px; color: #606266; }

/* 右侧主区域 */
.main-grid-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-image: radial-gradient(rgba(64, 158, 255, 0.05) 1px, transparent 1px);
  background-size: 20px 20px;
  overflow: hidden;
}

.grid-header {
  height: 60px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 30px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.grid-header .title { font-size: 18px; font-weight: bold; }

.video-grid {
  flex: 1;
  padding: 30px;
  overflow-y: auto;
  display: grid;
  /* 响应式网格：最小宽度300px，自动填满 */
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
  align-content: start;
}

/* 视频卡片样式 */
.video-card {
  background: rgba(30, 35, 45, 0.8);
  border: 1px solid rgba(64, 158, 255, 0.2);
  border-radius: 12px;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
}

.video-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.4);
  border-color: #409eff;
}

.video-card.offline { border-color: #f56c6c; opacity: 0.8; }

.card-header {
  padding: 10px 15px;
  background: rgba(0, 0, 0, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-title { display: flex; align-items: center; gap: 8px; }
.live-tag { background: #f56c6c; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold; }
.offline-tag { background: #909399; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; }
.card-time { font-size: 12px; color: #606266; }

.card-video {
  height: 180px; /* 固定高度，保证网格整齐 */
  background: #000;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-video img { width: 100%; height: 100%; object-fit: contain; }

.offline-placeholder { text-align: center; color: #606266; font-size: 12px; display: flex; flex-direction: column; align-items: center; gap: 10px; }

.card-footer {
  padding: 10px 15px;
  background: rgba(255, 255, 255, 0.02);
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}
.rtsp-info {
  font-size: 12px; color: #555; width: 180px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
</style>