<template>
  <div class="system-container">
    <div class="page-header">
      <el-button :icon="ArrowLeft" circle class="back-btn" @click="$router.push('/')" />
      <h2>🎛️ 系统全景控制台</h2>
    </div>

    <el-row :gutter="20" class="row-section">
      <el-col :span="8">
        <el-card class="status-card chart-card" shadow="hover">
          <div class="chart-header">
            <div class="label"><el-icon><Cpu /></el-icon> CPU 负载</div>
            <div class="value cpu-text">{{ systemStats.cpu }}%</div>
          </div>
          <div ref="cpuChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="status-card chart-card" shadow="hover">
          <div class="chart-header">
            <div class="label"><el-icon><Files /></el-icon> 内存使用</div>
            <div class="value ram-text">{{ systemStats.ramPercent }}%</div>
          </div>
          <div ref="ramChartRef" class="chart-container"></div>
          <div class="chart-sub-text">{{ systemStats.ramUsed }} GB 已用</div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="status-card chart-card" shadow="hover">
          <div class="chart-header">
            <div class="label"><el-icon><Monitor /></el-icon> GPU 显存 (AI核心)</div>
            <div class="value gpu-text">{{ systemStats.gpu.memPercent }}%</div>
          </div>
          <div ref="gpuChartRef" class="chart-container"></div>
          <div class="chart-sub-text">
            {{ systemStats.gpu.name }} ({{ systemStats.gpu.used }}/{{ systemStats.gpu.total }} GB)
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="row-section">
      <el-col :span="6">
        <el-card class="status-card info-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>磁盘存储 (Evidence)</span>
              <el-icon><Coin /></el-icon>
            </div>
          </template>
          <div class="disk-info">
            <el-progress 
              type="circle" 
              :percentage="systemStats.disk.percent" 
              :color="diskColor"
              :width="100"
            />
            <div class="disk-text">
              剩余 <span>{{ systemStats.disk.free }} GB</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="status-card info-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>今日概览</span>
              <el-icon><DataLine /></el-icon>
            </div>
          </template>
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-num danger">{{ systemStats.business.todayAlarms }}</div>
              <div class="stat-label">今日报警</div>
            </div>
            <div class="stat-item">
              <div class="stat-num warning">{{ systemStats.business.pendingAudit }}</div>
              <div class="stat-label">待审核</div>
            </div>
          </div>
          <div class="stat-footer">系统启动于: {{ systemStats.business.bootTime }}</div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="status-card ai-card" shadow="hover" :class="{ 'ai-active': systemStats.globalAi }">
          <template #header>
            <div class="card-header">
              <span>全局 AI 引擎</span>
              <el-icon><Aim /></el-icon>
            </div>
          </template>
          <div class="ai-control-box">
            <div class="ai-status-text">
              {{ systemStats.globalAi ? '🔥 引擎运行中' : '💤 引擎已暂停' }}
            </div>
            <el-switch
              v-model="systemStats.globalAi"
              size="large"
              inline-prompt
              active-text="ON"
              inactive-text="OFF"
              style="--el-switch-on-color: #67c23a; --el-switch-off-color: #f56c6c"
              :loading="aiLoading"
              :before-change="handleBeforeAiChange"
            />
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="status-card info-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>在线推流</span>
              <el-icon><VideoCamera /></el-icon>
            </div>
          </template>
          <div class="big-number">{{ systemStats.totalStreams }}</div>
          <div class="stat-text">路摄像头正在工作</div>
        </el-card>
      </el-col>
    </el-row>

    <div class="device-list-section">
      <div class="section-header">
        <h3 class="section-title">摄像头接入矩阵</h3>
        <div class="batch-actions">
          <el-button type="success" size="small" plain :icon="VideoPlay" @click="handleBatchToggle(true)" :loading="batchLoading">一键开启全部</el-button>
          <el-button type="danger" size="small" plain :icon="SwitchButton" @click="handleBatchToggle(false)" :loading="batchLoading">一键暂停全部</el-button>
        </div>
      </div>

      <el-table 
        :data="pagedDeviceList" 
        class="custom-table" 
        style="width: 100%"
        :header-cell-style="{ background: '#1c2538', color: '#e5eaf3', borderColor: '#363b45' }"
        :cell-style="{ background: '#141a25', color: '#cfd3dc', borderColor: '#363b45' }"
      >
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="name" label="设备名称" min-width="150" />
        <el-table-column prop="rtspUrl" label="RTSP 地址" min-width="250" show-overflow-tooltip />
        
        <el-table-column label="运行状态" width="120" align="center">
          <template #default="{ row }">
            <div class="status-indicator">
              <span class="dot" :class="row.status === 1 ? 'green' : 'gray'"></span>
              <span>{{ row.status === 1 ? '在线' : '离线' }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="接入控制" width="150" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.enabled"
              inline-prompt
              active-text="启用"
              inactive-text="停用"
              style="--el-switch-on-color: #409eff; --el-switch-off-color: #f56c6c"
              :loading="row.loading"
              @change="(val: any) => handleDeviceToggle(row, val)"
            />
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[5, 10]" :background="true" layout="total, prev, pager, next" :total="totalDevices" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, computed, shallowRef, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Cpu, Files, VideoCamera, Aim, Monitor, Coin, DataLine, VideoPlay, SwitchButton } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import * as echarts from 'echarts'

interface Device {
  id: number; name: string; rtspUrl: string; enabled: boolean; status: number; loading?: boolean;
}

const router = useRouter()

// 🚀 API 配置核心
const JAVA_BASE = import.meta.env.VITE_APP_BASE_API || 'http://localhost:8080'
const AI_BASE = import.meta.env.VITE_APP_AI_API || 'http://localhost:5000'

const javaRequest = axios.create({ baseURL: `${JAVA_BASE}/api`, timeout: 8000 })
const aiRequest = axios.create({ baseURL: AI_BASE, timeout: 1500 }) // 短超时探测

const tokenInterceptor = (config: any) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
}
javaRequest.interceptors.request.use(tokenInterceptor)
aiRequest.interceptors.request.use(tokenInterceptor)

const systemStats = reactive({
  cpu: 0,
  ramPercent: 0, ramUsed: 0,
  totalStreams: 0, globalAi: false,
  gpu: { used: 0, total: 0, memPercent: 0, name: 'N/A' },
  disk: { total: 0, used: 0, free: 0, percent: 0 },
  business: { todayAlarms: 0, pendingAudit: 0, bootTime: '-' }
})

const deviceList = ref<Device[]>([])
const aiLoading = ref(false), batchLoading = ref(false)
const timer = ref<number | null>(null)

// --- ECharts 逻辑 ---
const cpuChartRef = ref(null), ramChartRef = ref(null), gpuChartRef = ref(null)
const cpuChart = shallowRef<echarts.ECharts | null>(null)
const ramChart = shallowRef<echarts.ECharts | null>(null)
const gpuChart = shallowRef<echarts.ECharts | null>(null)
const maxDataPoints = 60
const history = { 
  cpu: ref(new Array(maxDataPoints).fill(0)), 
  ram: ref(new Array(maxDataPoints).fill(0)), 
  gpu: ref(new Array(maxDataPoints).fill(0)) 
}

const getChartOption = (color: string) => ({
  grid: { left: 0, right: 0, top: 5, bottom: 0 },
  xAxis: { type: 'category', show: false, boundaryGap: false },
  yAxis: { type: 'value', min: 0, max: 100, show: false },
  series: [{ 
    type: 'line', showSymbol: false, smooth: true, 
    lineStyle: { width: 2, color }, 
    areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color }, { offset: 1, color: 'transparent' }]), opacity: 0.3 }, 
    data: new Array(maxDataPoints).fill(0) 
  }]
})

const initCharts = () => {
  if (cpuChartRef.value) cpuChart.value = echarts.init(cpuChartRef.value); cpuChart.value?.setOption(getChartOption('#67C23A'))
  if (ramChartRef.value) ramChart.value = echarts.init(ramChartRef.value); ramChart.value?.setOption(getChartOption('#409EFF'))
  if (gpuChartRef.value) gpuChart.value = echarts.init(gpuChartRef.value); gpuChart.value?.setOption(getChartOption('#E6A23C'))
}

const updateCharts = () => {
  history.cpu.value.push(systemStats.cpu); history.cpu.value.shift()
  history.ram.value.push(systemStats.ramPercent); history.ram.value.shift()
  history.gpu.value.push(systemStats.gpu.memPercent); history.gpu.value.shift()
  cpuChart.value?.setOption({ series: [{ data: history.cpu.value }] })
  ramChart.value?.setOption({ series: [{ data: history.ram.value }] })
  gpuChart.value?.setOption({ series: [{ data: history.gpu.value }] })
}

// --- 🚀 业务控制逻辑：解决 Python 离线回跳 ---

const handleBeforeAiChange = async () => {
  const target = !systemStats.globalAi
  aiLoading.value = true
  try {
    const res = await aiRequest.post('/api/v1/system/global_ai', { enabled: target })
    if (res.data.code === 200) {
      javaRequest.post('/system/control/global_ai_db', { enabled: target })
      return true
    }
    throw new Error()
  } catch (e) {
    ElMessage.error('❌ 指令拦截：AI 服务器处于下线状态')
    systemStats.globalAi = false // 强制数据层保持 false
    return false // 物理拦截滑动
  } finally {
    aiLoading.value = false
  }
}

const fetchStatus = async () => {
  let isAiServerAlive = false
  try {
    await aiRequest.get('/api/v1/system/global_ai')
    isAiServerAlive = true
  } catch (e) {
    isAiServerAlive = false
  }

  try {
    const res = await javaRequest.get('/system/status')
    if (res.data.code === 200) {
      const d = res.data.data
      systemStats.cpu = d.cpu || 0
      systemStats.ramPercent = d.ramPercent || 0
      systemStats.ramUsed = d.ramUsed || 0
      systemStats.gpu = d.gpu || systemStats.gpu
      systemStats.disk = d.disk || systemStats.disk
      
      const biz = d.business || {}
      systemStats.business.todayAlarms = biz.todayAlarms || 0
      systemStats.business.pendingAudit = biz.pendingAudit || 0
      systemStats.business.bootTime = biz.bootTime || '-'
      
      if (!aiLoading.value) {
        if (!isAiServerAlive) {
          systemStats.globalAi = false // Python 挂了，强制 OFF
        } else {
          systemStats.globalAi = !!(d.global_ai ?? d.globalAi)
        }
      }
      deviceList.value = (biz.devices || []).map((dev: any) => ({ ...dev, loading: false }))
      systemStats.totalStreams = deviceList.value.filter(d => d.status === 1).length
      updateCharts()
    }
  } catch (e) {}
}

const handleDeviceToggle = async (row: Device, val: boolean) => {
  row.loading = true
  try {
    const res = await javaRequest.put(`/monitor/devices/${row.id}`, { enabled: val })
    if (res.data.code === 200) ElMessage.success(`${row.name} 已更新`)
    else row.enabled = !val
  } catch (e) { row.enabled = !val }
  finally { row.loading = false }
}

const handleBatchToggle = async (enable: boolean) => {
  const targets = deviceList.value.filter(d => d.enabled !== enable)
  if (targets.length === 0) return ElMessage.info('状态无需变更')
  try {
    await ElMessageBox.confirm(`确定批量操作？`)
    batchLoading.value = true
    await Promise.all(targets.map(d => javaRequest.put(`/monitor/devices/${d.id}`, { enabled: enable })))
    fetchStatus()
  } catch {}
  finally { batchLoading.value = false }
}

const diskColor = (p: number) => p > 90 ? '#f56c6c' : (p > 70 ? '#e6a23c' : '#67c23a')
const currentPage = ref(1), pageSize = ref(5)
const totalDevices = computed(() => deviceList.value.length)
const pagedDeviceList = computed(() => deviceList.value.slice((currentPage.value - 1) * pageSize.value, currentPage.value * pageSize.value))

onMounted(() => {
  fetchStatus()
  nextTick(() => initCharts())
  timer.value = window.setInterval(fetchStatus, 3000)
  window.addEventListener('resize', () => {
    cpuChart.value?.resize(); ramChart.value?.resize(); gpuChart.value?.resize();
  })
})

onUnmounted(() => {
  if (timer.value) clearInterval(timer.value)
  cpuChart.value?.dispose(); ramChart.value?.dispose(); gpuChart.value?.dispose()
})
</script>

<style scoped>
.system-container { min-height: 100vh; background: #0d1119; color: #fff; padding: 30px; font-family: 'PingFang SC', sans-serif; }
.page-header { display: flex; align-items: center; margin-bottom: 20px; gap: 15px; }
.page-header h2 { margin: 0; font-size: 22px; background: linear-gradient(90deg, #409eff, #fff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.back-btn { background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: #fff; }
.row-section { margin-bottom: 20px; }
.status-card { background: rgba(30, 35, 45, 0.6); border: 1px solid rgba(64, 158, 255, 0.1); color: #fff; backdrop-filter: blur(10px); height: 160px; display: flex; flex-direction: column; border-radius: 12px; }
:deep(.el-card__body) { flex: 1; padding: 15px 20px; display: flex; flex-direction: column; justify-content: center; position: relative; }
.chart-card :deep(.el-card__body) { padding: 0; overflow: hidden; }
.chart-header { position: absolute; top: 15px; left: 20px; z-index: 10; pointer-events: none; }
.chart-header .label { font-size: 13px; color: #909399; display: flex; align-items: center; gap: 5px; }
.chart-header .value { font-size: 28px; font-weight: bold; font-family: 'Courier New', monospace; margin-top: 5px; }
.cpu-text { color: #67C23A; } .ram-text { color: #409EFF; } .gpu-text { color: #E6A23C; }
.chart-container { width: 100%; height: 100%; }
.chart-sub-text { position: absolute; bottom: 10px; right: 15px; font-size: 11px; color: #606266; }
.info-card :deep(.el-card__header) { border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding: 10px 15px; display: block; font-size: 13px; color: #909399; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.disk-info { display: flex; align-items: center; justify-content: center; gap: 20px; }
.disk-text { text-align: left; font-size: 12px; color: #909399; }
.disk-text span { display: block; font-size: 18px; color: #fff; font-weight: bold; margin-top: 5px; }
.stats-grid { display: flex; justify-content: space-around; margin-bottom: 10px; }
.stat-item { text-align: center; }
.stat-num { font-size: 24px; font-weight: bold; }
.stat-num.danger { color: #F56C6C; } .stat-num.warning { color: #E6A23C; }
.stat-label { font-size: 12px; color: #909399; margin-top: 5px; }
.stat-footer { font-size: 11px; color: #606266; text-align: center; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px; }
.ai-card.ai-active { border-color: rgba(103, 194, 58, 0.5); box-shadow: 0 0 15px rgba(103, 194, 58, 0.2) inset; }
.ai-control-box { display: flex; flex-direction: column; align-items: center; gap: 10px; }
.ai-status-text { font-weight: bold; font-size: 16px; letter-spacing: 1px; }
.big-number { font-size: 44px; font-weight: 800; color: #409eff; text-align: center; font-family: 'Arial Black'; }
.stat-text { font-size: 12px; color: #909399; text-align: center; margin-top: 5px; }
.device-list-section { margin-top: 20px; background: rgba(22, 33, 52, 0.4); padding: 25px; border-radius: 12px; border: 1px solid rgba(64, 158, 255, 0.1); }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-left: 4px solid #409eff; padding-left: 15px; }
.section-title { margin: 0; font-size: 17px; font-weight: 600; }
.batch-actions { display: flex; gap: 12px; }
.status-indicator { display: flex; align-items: center; gap: 8px; justify-content: center; }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.dot.green { background: #67c23a; box-shadow: 0 0 8px #67c23a; }
.dot.gray { background: #909399; }
.pagination-wrapper { margin-top: 20px; display: flex; justify-content: flex-end; }
.custom-table { background-color: transparent !important; --el-table-border-color: #363b45; --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent; }
:deep(.el-table__inner-wrapper::before) { display: none; }
:deep(.el-table__row:hover) { background-color: rgba(64, 158, 255, 0.1) !important; }
:deep(.el-pagination.is-background .el-pager li:not(.is-disabled)) { background-color: #1c2538; color: #fff; }
</style>