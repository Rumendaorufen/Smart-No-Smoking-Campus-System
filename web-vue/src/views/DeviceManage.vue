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
        <div class="header-actions">
           <el-button 
             type="warning" 
             size="small" 
             plain 
             @click="handleReconnectAll"
             :loading="isGlobalRetrying"
           >
             <el-icon><Connection /></el-icon> 一键重连
           </el-button>

           <el-button circle size="small" @click="refreshAll" title="刷新所有画面">
             <el-icon><Refresh /></el-icon>
           </el-button>
        </div>
      </div>

      <div class="video-grid" v-loading="loading">
        <div 
          v-for="device in pagedDeviceList" 
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
                <el-icon :size="48" class="offline-icon" :class="{ 'error-shake': device.failTip }">
                    <component :is="device.failTip ? Warning : VideoCameraFilled" />
                </el-icon>
                
                <p class="offline-tip" :class="{ 'error-text': device.failTip }">
                    {{ device.failTip || '信号已中断' }}
                </p>
                
                <button class="retry-btn" @click="retryStream(device)">
                  <el-icon class="icon"><RefreshRight /></el-icon>
                  {{ device.failTip ? '重试连接' : '点击重连' }}
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

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[8, 12, 16, 24]"
          :background="true"
          layout="total, sizes, prev, pager, next, jumper"
          :total="totalDevices"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useDeviceStore } from '../stores/device'
import { storeToRefs } from 'pinia'
import deviceApi from '../api/device'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Plus, Monitor, Edit, Delete, Refresh, VideoCameraFilled, 
  RefreshRight, Warning, Connection
} from '@element-plus/icons-vue'

// 使用 Pinia Store
const deviceStore = useDeviceStore()
const { deviceList, loading } = storeToRefs(deviceStore)

// ========== 分页逻辑 (新增) ==========
const currentPage = ref(1)
const pageSize = ref(8) // 默认每页显示8个，正好两行

const totalDevices = computed(() => deviceList.value.length)

// 计算当前页显示的设备
const pagedDeviceList = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return deviceList.value.slice(start, end)
})

const handleSizeChange = (val: number) => {
  pageSize.value = val
  currentPage.value = 1
}

const handleCurrentChange = (val: number) => {
  currentPage.value = val
}
// ====================================

const isGlobalRetrying = computed(() => {
  return deviceList.value.some(d => d.isRetrying)
})

const handleReconnectAll = () => {
  deviceStore.reconnectAll()
}

// 弹窗相关
const dialogVisible = ref(false)
const dialogMode = ref<'add' | 'edit'>('add')
const currentId = ref<number | null>(null)
const form = ref({ name: '', rtsp_url: '' })

// 统计
const onlineCount = computed(() => deviceList.value.filter(d => d.status === 1).length)
const offlineCount = computed(() => deviceList.value.filter(d => d.status !== 1).length)

// --- Store 代理 ---
const refreshAll = () => {
  deviceStore.streamVersion++
  deviceStore.fetchDevices(false)
  ElMessage.success('正在刷新视频矩阵...')
}

const retryStream = (device: any) => {
  deviceStore.retryConnection(device.id)
}

const getStreamUrl = (id: number) => {
  return deviceStore.getStreamUrl(id)
}

const handleVideoError = (device: any) => {
  deviceStore.handleVideoError(device.id)
}

// --- CRUD ---
const openDialog = (mode: 'add' | 'edit', row?: any) => {
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
    deviceStore.fetchDevices(false) 
    deviceStore.streamVersion++
  } catch (e) {}
}

const handleDelete = (row: any) => {
  ElMessageBox.confirm(`确定删除 ${row.name}?`, '警告', { type: 'warning' })
    .then(async () => {
      const res = await deviceApi.deleteDevice(row.id)
      if (res.code === 200) {
        ElMessage.success('删除成功')
        deviceStore.fetchDevices(false)
      }
    }).catch(() => {})
}

// 辅助功能
const scrollToCard = (id: number) => {
  // 注意：如果分页了，点击侧边栏索引可能需要跳转页码
  const index = deviceList.value.findIndex(d => d.id === id)
  if (index !== -1) {
    // 计算该设备在第几页
    const targetPage = Math.ceil((index + 1) / pageSize.value)
    if (currentPage.value !== targetPage) {
      currentPage.value = targetPage
    }
    // 等待 DOM 更新后滚动
    setTimeout(() => {
      const el = document.getElementById(`card-${id}`)
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 100)
  }
}

const formatTime = (timeStr: string) => {
  if(!timeStr) return ''
  return new Date(timeStr).toLocaleDateString()
}

onMounted(() => {
  deviceStore.startPolling()
})

onUnmounted(() => {
  deviceStore.stopPolling()
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
  flex-direction: column;
  gap: 15px;
  margin-bottom: 30px;
  width: 100%;
}

.action-area .el-button {
  width: 100%;
  margin-left: 0 !important;
  margin-right: 0;
  height: 40px;
  justify-content: center;
  border-radius: 8px;
}

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
  flex-shrink: 0; /* 防止头部被压缩 */
}
.grid-header .title { font-size: 18px; font-weight: bold; }

.video-grid {
  flex: 1;
  padding: 30px;
  overflow-y: auto;
  display: grid;
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
  height: 300px; /* 固定高度防止抖动 */
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
  flex-shrink: 0;
}
.card-title { display: flex; align-items: center; gap: 8px; overflow: hidden; }
.card-title .name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.live-tag { background: #f56c6c; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold; }
.offline-tag { background: #909399; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; }
.card-time { font-size: 12px; color: #606266; flex-shrink: 0; }

.card-video {
  flex: 1; /* 撑满剩余空间 */
  background: #000;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.card-video img { width: 100%; height: 100%; object-fit: contain; }

.offline-placeholder { 
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    background: rgba(20, 20, 20, 0.6);
    color: #606266;
    gap: 8px;
}

.card-footer {
  padding: 10px 15px;
  background: rgba(255, 255, 255, 0.02);
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  flex-shrink: 0;
}
.rtsp-info {
  font-size: 12px; color: #555; width: 180px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* 错误文字样式 */
.error-text {
  color: #f56c6c !important;
  font-weight: bold;
}

.offline-icon {
  color: #4a4d52;
  margin-bottom: 5px;
  transition: color 0.3s;
}

.offline-icon.error-shake {
  color: #f56c6c;
  animation: shake 0.4s ease-in-out;
}

/* 重连按钮样式 */
.retry-btn {
  margin-top: 10px;
  background: rgba(64, 158, 255, 0.1);
  border: 1px solid rgba(64, 158, 255, 0.3);
  color: #409eff;
  padding: 6px 16px;
  border-radius: 20px;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: all 0.3s;
}

.retry-btn:hover {
  background: #409eff;
  color: white;
  border-color: #409eff;
  box-shadow: 0 0 10px rgba(64, 158, 255, 0.4);
}

.retry-mask {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.8);
  z-index: 5;
}

.retry-text {
  margin-top: 15px;
  font-size: 12px;
  color: #409eff;
  letter-spacing: 1px;
  animation: pulse 1.5s infinite;
}

.radar-spinner {
  width: 40px;
  height: 40px;
  border: 2px solid rgba(64, 158, 255, 0.3);
  border-top-color: #409eff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

/* ✅ 新增：分页器样式 */
.pagination-wrapper {
  padding: 15px 30px;
  background: rgba(22, 33, 52, 0.9);
  border-top: 1px solid rgba(64, 158, 255, 0.2);
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
}

:deep(.el-pagination.is-background .el-pager li:not(.is-disabled)) {
  background-color: #1c2538;
  color: #fff;
  border: 1px solid #363b45;
}
:deep(.el-pagination.is-background .el-pager li.is-active) {
  background-color: #409eff;
  border-color: #409eff;
}
:deep(.el-pagination.is-background .btn-prev), 
:deep(.el-pagination.is-background .btn-next) {
  background-color: #1c2538;
  color: #fff;
  border: 1px solid #363b45;
}

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse { 0% { opacity: 0.6; } 50% { opacity: 1; } 100% { opacity: 0.6; } }
@keyframes shake { 0%, 100% { transform: translateX(0); } 25% { transform: translateX(-5px); } 75% { transform: translateX(5px); } }
</style>