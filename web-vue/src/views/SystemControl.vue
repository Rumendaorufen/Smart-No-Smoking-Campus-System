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
            <div class="value ram-text">{{ systemStats.ram_percent }}%</div>
          </div>
          <div ref="ramChartRef" class="chart-container"></div>
          <div class="chart-sub-text">{{ systemStats.ram_used }} GB 已用</div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="status-card chart-card" shadow="hover">
          <div class="chart-header">
            <div class="label"><el-icon><Monitor /></el-icon> GPU 显存 (AI核心)</div>
            <div class="value gpu-text">{{ systemStats.gpu.mem_percent }}%</div>
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
              <div class="stat-num danger">{{ systemStats.business.today_alarms }}</div>
              <div class="stat-label">今日报警</div>
            </div>
            <div class="stat-item">
              <div class="stat-num warning">{{ systemStats.business.pending_audit }}</div>
              <div class="stat-label">待审核</div>
            </div>
          </div>
          <div class="stat-footer">系统启动于: {{ systemStats.business.boot_time.split(' ')[1] }}</div>
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
              {{ systemStats.global_ai ? '🔥 引擎运行中' : '💤 引擎已暂停' }}
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
          <div class="big-number">{{ systemStats.total_streams }}</div>
          <div class="stat-text">路摄像头正在工作</div>
        </el-card>
      </el-col>
    </el-row>

    <div class="device-list-section">
      <div class="section-header">
        <h3 class="section-title">摄像头接入矩阵</h3>
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
        <el-table-column prop="rtsp_url" label="RTSP 地址" min-width="250" show-overflow-tooltip />
        
        <el-table-column label="运行状态" width="120" align="center">
          <template #default="{ row }">
            <div class="status-indicator">
              <span class="dot" :class="row.is_running ? 'green' : 'gray'"></span>
              <span>{{ row.is_running ? '在线' : '离线' }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="接入状态" width="150" align="center">
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

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[5, 10]"
          :background="true"
          layout="total, prev, pager, next"
          :total="totalDevices"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, computed, shallowRef, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Cpu, Files, VideoCamera, Aim, Monitor, Coin, DataLine } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import * as echarts from 'echarts'

// ✅ 修复 1: 补全 Interface，添加 ai_enabled
interface Device {
  id: number
  name: string
  rtsp_url: string
  enabled: boolean
  is_running: boolean
  ai_enabled: boolean // 👈 必须加上这个
  loading?: boolean
}

const router = useRouter()
const request = axios.create({ baseURL: 'http://localhost:5000/api/v1', timeout: 5000 })

request.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
}, error => Promise.reject(error))

request.interceptors.response.use(res => res, err => {
  if (err.response?.status === 401) { router.push('/login'); }
  return Promise.reject(err)
})

const systemStats = reactive({
  cpu: 0,
  ram_percent: 0, ram_used: 0,
  total_streams: 0, global_ai: true,
  gpu: { used: 0, total: 0, percent: 0, mem_percent: 0, name: 'N/A' },
  disk: { total: 0, used: 0, free: 0, percent: 0 },
  business: { today_alarms: 0, pending_audit: 0, boot_time: '-' }
})

const deviceList = ref<Device[]>([])
const aiLoading = ref(false)
const timer = ref<number | null>(null)

// Charts
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

const initCharts = () => {
  if (cpuChartRef.value) {
    cpuChart.value = echarts.init(cpuChartRef.value)
    cpuChart.value.setOption(getChartOption('#67C23A', 'CPU'))
  }
  if (ramChartRef.value) {
    ramChart.value = echarts.init(ramChartRef.value)
    ramChart.value.setOption(getChartOption('#409EFF', 'RAM'))
  }
  if (gpuChartRef.value) {
    gpuChart.value = echarts.init(gpuChartRef.value)
    gpuChart.value.setOption(getChartOption('#E6A23C', 'VRAM'))
  }
  window.addEventListener('resize', handleResize)
}

const handleResize = () => {
  cpuChart.value?.resize(); ramChart.value?.resize(); gpuChart.value?.resize();
}

const getChartOption = (color: string, name: string) => ({
  grid: { left: 0, right: 0, top: 5, bottom: 0 },
  xAxis: { type: 'category', show: false, boundaryGap: false },
  yAxis: { type: 'value', min: 0, max: 100, show: false },
  series: [{
    name, type: 'line', showSymbol: false, smooth: true,
    lineStyle: { width: 2, color },
    areaStyle: {
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color }, { offset: 1, color: 'rgba(0,0,0,0)' }]),
      opacity: 0.3
    },
    data: new Array(maxDataPoints).fill(0)
  }]
})

const updateCharts = () => {
  history.cpu.value.push(systemStats.cpu); history.cpu.value.shift();
  history.ram.value.push(systemStats.ram_percent); history.ram.value.shift();
  history.gpu.value.push(systemStats.gpu.mem_percent); history.gpu.value.shift();

  cpuChart.value?.setOption({ series: [{ data: history.cpu.value }] })
  ramChart.value?.setOption({ series: [{ data: history.ram.value }] })
  gpuChart.value?.setOption({ series: [{ data: history.gpu.value }] })
}

const diskColor = (percentage: number) => {
  if (percentage > 90) return '#f56c6c'
  if (percentage > 70) return '#e6a23c'
  return '#67c23a'
}

const currentPage = ref(1), pageSize = ref(5)
const totalDevices = computed(() => deviceList.value.length)
const pagedDeviceList = computed(() => deviceList.value.slice((currentPage.value - 1) * pageSize.value, currentPage.value * pageSize.value))

const fetchStatus = async () => {
  try {
    const res = await request.get('/system/status')
    if (res.data.code === 200) {
      const d = res.data.data
      systemStats.cpu = d.cpu
      systemStats.ram_percent = d.ram_percent
      systemStats.ram_used = d.ram_used
      systemStats.total_streams = d.total_streams
      systemStats.gpu = d.gpu || { mem_percent: 0, used: 0, total: 0, name: 'No GPU' }
      systemStats.disk = d.disk || { percent: 0, free: 0 }
      systemStats.business = d.business || { today_alarms: 0, pending_audit: 0, boot_time: '-' }
      
      if (!aiLoading.value) systemStats.global_ai = d.global_ai
      
      // ✅ 修复 2: 显式声明 newDevices 类型，防止 TS 推断错误
      const newDevices: Device[] = d.devices
      
      newDevices.forEach(newDev => {
        // 使用可选链或非空断言并不总是完美，最稳妥的是 if 判断
        const existingDev = deviceList.value.find(o => o.id === newDev.id)
        
        if (existingDev) {
          // ✅ TS 现在知道 existingDev 肯定不是 undefined
          existingDev.name = newDev.name
          existingDev.rtsp_url = newDev.rtsp_url
          existingDev.enabled = newDev.enabled
          existingDev.is_running = newDev.is_running
          existingDev.ai_enabled = newDev.ai_enabled // 这里的报错应该消失了
        } else {
          deviceList.value.push({ ...newDev, loading: false })
        }
      })

      // 2. 清理已删除的设备 (可选)
      if (deviceList.value.length > newDevices.length) {
         const newIds = new Set(newDevices.map(d => d.id))
         // 倒序遍历删除
         for (let i = deviceList.value.length - 1; i >= 0; i--) {
            // ✅ 修复：先获取对象，TypeScript 就能正确推断类型了
            const currentItem = deviceList.value[i]
            
            // ✅ 修复：加上 currentItem && 判断，确保对象存在再访问 .id
            if (currentItem && !newIds.has(currentItem.id)) {
               deviceList.value.splice(i, 1)
            }
         }
      }
      updateCharts()
    }
  } catch (e) { console.error(e) }
}

// 参数类型
const handleDeviceToggle = async (row: Device, val: boolean | string | number) => {
  const isEnabled = !!val 
  row.loading = true
  try {
    const res = await request.post('/system/control/device', { id: row.id, enable: isEnabled })
    if (res.data.code === 200) {
      ElMessage.success(isEnabled ? `设备 ${row.name} 已启用` : `设备 ${row.name} 已停用`)
      row.enabled = isEnabled 
    } else {
      row.enabled = !isEnabled 
      ElMessage.error(res.data.msg || '操作失败')
    }
  } catch (e) { 
    row.enabled = !isEnabled
    ElMessage.error('网络请求失败') 
  } finally { 
    row.loading = false 
    setTimeout(fetchStatus, 500) 
  }
}

const handleGlobalAiToggle = async (val: boolean | string | number) => {
  const isEnabled = !!val
  aiLoading.value = true
  try {
    const res = await request.post('/system/control/global_ai', { enabled: isEnabled })
    if (res.data.code === 200) {
      ElMessage.success(`AI 引擎已${isEnabled ? '启动' : '暂停'}`)
    } else {
      systemStats.global_ai = !isEnabled; ElMessage.error(res.data.msg)
    }
  } catch (e) { systemStats.global_ai = !isEnabled; ElMessage.error('请求失败') } 
  finally { aiLoading.value = false }
}

onMounted(() => {
  fetchStatus()
  nextTick(() => initCharts())
  timer.value = window.setInterval(fetchStatus, 3000)
})

onUnmounted(() => {
  if (timer.value) clearInterval(timer.value)
  window.removeEventListener('resize', handleResize)
  cpuChart.value?.dispose(); ramChart.value?.dispose(); gpuChart.value?.dispose()
})
</script>

<style scoped>
.system-container { min-height: 100vh; background: #0d1119; color: #fff; padding: 30px; }
.page-header { display: flex; align-items: center; margin-bottom: 20px; gap: 15px; }
.page-header h2 { margin: 0; font-size: 22px; background: linear-gradient(90deg, #409eff, #fff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.back-btn { background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: #fff; }
.row-section { margin-bottom: 20px; }

/* 通用卡片 */
.status-card { 
  background: rgba(30, 35, 45, 0.6); border: 1px solid rgba(64, 158, 255, 0.1); 
  color: #fff; backdrop-filter: blur(10px); height: 160px; display: flex; flex-direction: column;
}
:deep(.el-card__body) { flex: 1; padding: 15px 20px; display: flex; flex-direction: column; justify-content: center; position: relative; }

/* 图表卡片 */
.chart-card :deep(.el-card__body) { padding: 0; }
.chart-header { position: absolute; top: 15px; left: 20px; z-index: 10; }
.chart-header .label { font-size: 14px; color: #909399; display: flex; align-items: center; gap: 5px; }
.chart-header .value { font-size: 28px; font-weight: bold; font-family: 'Courier New', monospace; margin-top: 5px; }
.cpu-text { color: #67C23A; } .ram-text { color: #409EFF; } .gpu-text { color: #E6A23C; }
.chart-container { width: 100%; height: 100%; }
.chart-sub-text { position: absolute; bottom: 10px; right: 15px; font-size: 12px; color: #909399; }

/* 信息卡片 (Info Card) */
.info-card :deep(.el-card__header) { border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding: 10px 15px; display: block; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: #909399; }

/* 磁盘信息 */
.disk-info { display: flex; align-items: center; justify-content: center; gap: 20px; }
.disk-text { text-align: left; font-size: 12px; color: #909399; }
.disk-text span { display: block; font-size: 18px; color: #fff; font-weight: bold; margin-top: 5px; }

/* 业务统计网格 */
.stats-grid { display: flex; justify-content: space-around; margin-bottom: 10px; }
.stat-item { text-align: center; }
.stat-num { font-size: 24px; font-weight: bold; }
.stat-num.danger { color: #F56C6C; } .stat-num.warning { color: #E6A23C; }
.stat-label { font-size: 12px; color: #909399; margin-top: 5px; }
.stat-footer { font-size: 11px; color: #606266; text-align: center; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px; }

/* AI 卡片 */
.ai-card.ai-active { border-color: rgba(103, 194, 58, 0.5); box-shadow: 0 0 15px rgba(103, 194, 58, 0.2) inset; }
.ai-control-box { display: flex; flex-direction: column; align-items: center; gap: 10px; }
.ai-status-text { font-weight: bold; font-size: 16px; }
.big-number { font-size: 40px; font-weight: bold; color: #409eff; margin: 10px 0; text-align: center; }
.stat-text { font-size: 12px; color: #909399; text-align: center; }

/* 列表 & 分页 */
.device-list-section { margin-top: 10px; background: rgba(22, 33, 52, 0.6); padding: 20px; border-radius: 8px; }
.section-title { margin: 0 0 15px 0; font-size: 16px; border-left: 4px solid #409eff; padding-left: 10px; }
.status-indicator { display: flex; align-items: center; gap: 6px; justify-content: center; }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.dot.green { background: #67c23a; box-shadow: 0 0 5px #67c23a; }
.dot.gray { background: #909399; }
.pagination-wrapper { margin-top: 15px; display: flex; justify-content: flex-end; }

/* 表格覆盖 */
.custom-table { background-color: transparent !important; --el-table-border-color: #363b45; --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent; }
:deep(.el-table__inner-wrapper::before) { display: none; }
:deep(.el-table__row:hover) { background-color: rgba(64, 158, 255, 0.1) !important; }
:deep(.el-pagination.is-background .el-pager li:not(.is-disabled)) { background-color: #1c2538; color: #fff; }
</style>