<template>
  <div class="system-container">
    <div class="page-header">
      <el-button :icon="ArrowLeft" circle class="back-btn" @click="$router.push('/')" />
      <h2>🎛️ 系统控制台</h2>
    </div>

    <el-row :gutter="20" class="status-dashboard">
      <el-col :span="6">
        <el-card class="status-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>CPU 负载</span>
              <el-icon><Cpu /></el-icon>
            </div>
          </template>
          <el-progress type="dashboard" :percentage="systemStats.cpu" :color="cpuColor" />
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="status-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>内存占用</span>
              <el-icon><Files /></el-icon>
            </div>
          </template>
          <el-progress type="dashboard" :percentage="systemStats.ram_percent" :color="ramColor" />
          <div class="stat-text">{{ systemStats.ram_used }} GB 已用</div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="status-card ai-card" shadow="hover" :class="{ 'ai-active': systemStats.global_ai }">
          <template #header>
            <div class="card-header">
              <span>全局 AI 引擎</span>
              <el-icon><Aim /></el-icon>
            </div>
          </template>
          <div class="ai-control-box">
            <div class="ai-status-text">
              {{ systemStats.global_ai ? '引擎运行中' : '引擎已暂停' }}
            </div>
            <el-switch
              v-model="systemStats.global_ai"
              size="large"
              inline-prompt
              active-text="ON"
              inactive-text="OFF"
              style="--el-switch-on-color: #67c23a; --el-switch-off-color: #909399"
              :loading="aiLoading"
              @change="(val: boolean | string | number) => handleGlobalAiToggle(val)"
            />
          </div>
          <div class="stat-text-small">控制所有摄像头的检测功能</div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="status-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>活跃设备</span>
              <el-icon><VideoCamera /></el-icon>
            </div>
          </template>
          <div class="big-number">{{ systemStats.total_streams }}</div>
          <div class="stat-text">在线推流中</div>
        </el-card>
      </el-col>
    </el-row>

    <div class="device-list-section">
      <h3 class="section-title">
        摄像头接入管理
        <span class="sub-tip">（停用后，前台将无法连接该设备）</span>
      </h3>
      <el-table 
        :data="deviceList" 
        class="custom-table" 
        style="width: 100%"
        :header-cell-style="{ background: '#1c2538', color: '#e5eaf3', borderColor: '#363b45' }"
        :cell-style="{ background: '#141a25', color: '#cfd3dc', borderColor: '#363b45' }"
      >
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="name" label="设备名称" min-width="150" />
        <el-table-column prop="rtsp_url" label="RTSP 地址" min-width="250" show-overflow-tooltip />
        
        <el-table-column label="运行状态" width="120" align="center">
          <template #default="{ row }">
            <div class="status-indicator">
              <span class="dot" :class="row.is_running ? 'green' : 'gray'"></span>
              <span>{{ row.is_running ? '在线' : '离线' }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="接入状态 (启用/停用)" width="200" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.enabled"
              inline-prompt
              active-text="启用"
              inactive-text="停用"
              style="--el-switch-on-color: #409eff; --el-switch-off-color: #f56c6c"
              :loading="row.loading"
              @change="(val: boolean | string | number) => handleDeviceToggle(row, val)"
            />
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Cpu, Files, VideoCamera, Aim } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

// 1. 定义接口类型 (解决 TypeScript 报错的核心)
interface Device {
  id: number
  name: string
  rtsp_url: string
  enabled: boolean
  is_running: boolean
  ai_enabled: boolean
  loading?: boolean // 可选属性
}

const router = useRouter()

// 2. Axios 实例配置
const request = axios.create({ 
  baseURL: 'http://localhost:5000/api/v1',
  timeout: 5000 
})

request.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, error => Promise.reject(error))

request.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

const systemStats = reactive({
  cpu: 0,
  ram_percent: 0,
  ram_used: 0,
  total_streams: 0,
  global_ai: true
})

// ✅ 3. 显式指定 Ref 类型
const deviceList = ref<Device[]>([])
const aiLoading = ref(false)
const timer = ref<number | null>(null)

const cpuColor = [{ color: '#67c23a', percentage: 40 }, { color: '#e6a23c', percentage: 70 }, { color: '#f56c6c', percentage: 100 }]
const ramColor = [{ color: '#409eff', percentage: 60 }, { color: '#e6a23c', percentage: 85 }, { color: '#f56c6c', percentage: 100 }]

// 获取状态
const fetchStatus = async () => {
  try {
    const res = await request.get('/system/status')
    if (res.data.code === 200) {
      const d = res.data.data
      systemStats.cpu = d.cpu
      systemStats.ram_percent = d.ram_percent
      systemStats.ram_used = d.ram_used
      systemStats.total_streams = d.total_streams
      
      if (!aiLoading.value) {
        systemStats.global_ai = d.global_ai
      }
      
      const newDevices: Device[] = d.devices
      if (deviceList.value.length === 0) {
        deviceList.value = newDevices.map(dev => ({ ...dev, loading: false }))
      } else {
        deviceList.value = newDevices.map(newDev => {
          const oldDev = deviceList.value.find(o => o.id === newDev.id)
          return {
            ...newDev,
            loading: oldDev ? oldDev.loading : false
          }
        })
      }
    }
  } catch (e) {
    console.error("Fetch status error:", e)
  }
}

// 切换设备启用/停用
// ✅ 4. 修复 TS 类型：显式声明 val 类型
const handleDeviceToggle = async (row: Device, val: boolean | string | number) => {
  const isEnabled = !!val 
  
  row.loading = true
  try {
    const res = await request.post('/system/control/device', { id: row.id, enable: isEnabled })
    if (res.data.code === 200) {
      ElMessage.success(isEnabled ? `设备 ${row.name} 已启用` : `设备 ${row.name} 已停用`)
    } else {
      row.enabled = !isEnabled // 失败回滚
      ElMessage.error(res.data.msg || '操作失败')
    }
  } catch (e: any) {
    row.enabled = !isEnabled
    if (!axios.isAxiosError(e) || e.response?.status !== 401) {
       ElMessage.error('网络请求失败')
    }
  } finally {
    row.loading = false
    setTimeout(fetchStatus, 500)
  }
}

// 切换全局 AI
// ✅ 5. 修复 TS 类型
const handleGlobalAiToggle = async (val: boolean | string | number) => {
  const isEnabled = !!val
  aiLoading.value = true
  try {
    const res = await request.post('/system/control/global_ai', { enabled: isEnabled })
    if (res.data.code === 200) {
      ElMessage.success(`AI 引擎已${isEnabled ? '启动' : '暂停'}`)
    } else {
      systemStats.global_ai = !isEnabled
      ElMessage.error(res.data.msg)
    }
  } catch (e: any) {
    systemStats.global_ai = !isEnabled
    if (!axios.isAxiosError(e) || e.response?.status !== 401) {
       ElMessage.error('请求失败')
    }
  } finally {
    aiLoading.value = false
  }
}

onMounted(() => {
  fetchStatus()
  timer.value = window.setInterval(fetchStatus, 3000)
})

onUnmounted(() => {
  if (timer.value) clearInterval(timer.value)
})
</script>

<style scoped>
.system-container { min-height: 100vh; background: #0d1119; color: #fff; padding: 30px; }
.page-header { display: flex; align-items: center; margin-bottom: 30px; gap: 15px; }
.page-header h2 { margin: 0; background: linear-gradient(90deg, #409eff, #fff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.back-btn { background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: #fff; }
.back-btn:hover { background: #409eff; border-color: #409eff; }

/* 仪表盘 */
.status-card { background: rgba(30, 35, 45, 0.6); border: 1px solid rgba(64, 158, 255, 0.1); color: #fff; text-align: center; backdrop-filter: blur(10px); }
:deep(.el-card__header) { border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding: 10px 15px; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-size: 14px; color: #909399; }
.big-number { font-size: 40px; font-weight: bold; color: #409eff; margin: 10px 0; }
.stat-text { font-size: 12px; color: #909399; margin-top: 5px; }

/* AI 卡片特效 */
.ai-card.ai-active { border-color: rgba(103, 194, 58, 0.5); box-shadow: 0 0 15px rgba(103, 194, 58, 0.2) inset; }
.ai-control-box { display: flex; flex-direction: column; align-items: center; gap: 10px; margin: 15px 0; }
.ai-status-text { font-weight: bold; color: #fff; }
.ai-card.ai-active .ai-status-text { color: #67c23a; text-shadow: 0 0 5px #67c23a; }
.stat-text-small { font-size: 12px; color: #606266; }

/* 列表区域 */
.device-list-section { margin-top: 40px; background: rgba(22, 33, 52, 0.6); padding: 20px; border-radius: 8px; border: 1px solid rgba(64, 158, 255, 0.1); }
.section-title { margin-top: 0; margin-bottom: 20px; font-size: 18px; border-left: 4px solid #409eff; padding-left: 10px; }
.sub-tip { font-size: 12px; color: #909399; font-weight: normal; margin-left: 10px; }

/* 状态点 */
.status-indicator { display: flex; align-items: center; gap: 6px; justify-content: center; }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.dot.green { background: #67c23a; box-shadow: 0 0 5px #67c23a; }
.dot.gray { background: #909399; }

/* 表格样式 */
.custom-table { background-color: transparent !important; --el-table-border-color: #363b45; --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent; }
:deep(.el-table__inner-wrapper::before) { display: none; }
:deep(.el-table__row:hover) { background-color: rgba(64, 158, 255, 0.1) !important; }
</style>