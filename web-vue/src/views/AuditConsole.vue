<!-- web-vue\src\views\AuditConsole.vue -->
<template>
  <div class="audit-container">
    <div class="header">
      <h2>⚖️ 报警仲裁台 ({{ total }} 条待处理)</h2>
      <el-button type="primary" @click="fetchData" :loading="loading">刷新列表</el-button>
    </div>

    <el-empty v-if="!loading && list.length === 0" description="暂无待审核记录，喝杯咖啡吧 ☕️" />

    <div v-else class="card-grid">
      <el-card 
        v-for="item in list" 
        :key="item.id" 
        class="audit-card" 
        shadow="hover"
      >
        <template #header>
          <div class="card-header">
            <el-tag effect="dark" type="danger">疑似吸烟</el-tag>
            <span class="time">{{ item.created_at }}</span>
          </div>
        </template>

        <div class="media-content">
          <el-image 
            :src="getServerUrl(item.roi_url)" 
            :preview-src-list="[getServerUrl(item.roi_url)]"
            fit="cover"
            class="evidence-img"
            loading="lazy"
          >
            <template #placeholder>
              <div class="image-slot">加载中...</div>
            </template>
          </el-image>

          <div class="video-actions">
             <el-button 
               type="primary" 
               link 
               icon="VideoPlay" 
               @click="openVideo(item.video_url)"
             >
               查看录像回放
             </el-button>
          </div>

          <div class="meta-info">
            <p><el-icon><Location /></el-icon> {{ item.device_name }}</p>
            <p>
              AI置信度: 
              <span :class="getConfClass(item.confidence)">
                {{ (item.confidence * 100).toFixed(1) }}%
              </span>
            </p>
          </div>
        </div>

        <div class="actions">
          <el-button-group class="btn-group">
            <el-button 
              type="danger" 
              plain 
              icon="Close" 
              @click="handleAudit(item, 2)"
            >
              误报
            </el-button>
            <el-button 
              type="success" 
              icon="Check" 
              @click="handleAudit(item, 1)"
            >
              确认违规
            </el-button>
          </el-button-group>
        </div>
      </el-card>
    </div>

    <el-dialog v-model="videoVisible" title="证据录像回放" width="600px" destroy-on-close>
      <video v-if="currentVideo" :src="getServerUrl(currentVideo)" controls autoplay style="width: 100%"></video>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getPendingAlerts, submitAudit, type Alarm } from '../api/alert'
import { ElMessage } from 'element-plus'
import { VideoPlay, Location, Check, Close } from '@element-plus/icons-vue'

// 基础 URL (用于拼接图片路径)
// 如果你的图片是 static/evidence/...，这里需要拼上后端地址
const BASE_API = 'http://localhost:5000/' 
const getServerUrl = (path: string) => {
  if (!path) return ''
  return path.startsWith('http') ? path : BASE_API + path
}

const loading = ref(false)
const list = ref<Alarm[]>([])
const total = ref(0)
const videoVisible = ref(false)
const currentVideo = ref('')

// 获取数据
const fetchData = async () => {
  loading.value = true
  try {
    const res: any = await getPendingAlerts({ page: 1, page_size: 50 })
    if (res.code === 200) {
      list.value = res.data.list
      total.value = res.data.total
    }
  } finally {
    loading.value = false
  }
}

// 提交审核
const handleAudit = async (item: Alarm, status: number) => {
  try {
    const res: any = await submitAudit(item.id, { status })
    if (res.code === 200) {
      ElMessage.success(status === 1 ? '已确认违规' : '已标记为误报')
      // 从列表中移除该项 (前端假删除，优化体验)
      list.value = list.value.filter(i => i.id !== item.id)
      total.value--
    }
  } catch (error) {
    console.error(error)
  }
}

// 修改 openVideo 方法
const openVideo = (url: string) => {
  if (!url) return
  
  // 1. 这里的 url 是数据库里的 "static/evidence/xxx.mp4"
  // 2. 我们把它转换成后端刚才写的 API 地址
  //    目标地址: http://localhost:5000/api/v1/monitor/video/static/evidence/xxx.mp4
  
  // 确保 url 不带 http 开头 (如果是相对路径)
  let cleanUrl = url.replace('http://localhost:5000/', '')
  
  // 拼接 API 路径
  currentVideo.value = `http://localhost:5000/api/v1/monitor/video/${cleanUrl}`
  
  videoVisible.value = true
}

const getConfClass = (conf: number) => {
  if (conf > 0.8) return 'text-success'
  if (conf > 0.5) return 'text-warning'
  return 'text-danger'
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.audit-container {
  padding: 20px;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); /* 响应式网格 */
  gap: 20px;
}
.audit-card {
  transition: all 0.3s;
}
.audit-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0,0,0,0.1);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.media-content {
  text-align: center;
}
.evidence-img {
  width: 100%;
  height: 200px;
  border-radius: 4px;
  margin-bottom: 10px;
}
.meta-info {
  margin-top: 10px;
  text-align: left;
  font-size: 14px;
  color: #666;
}
.actions {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
.btn-group {
  width: 100%;
}
.btn-group .el-button {
  width: 50%;
}
.text-success { color: #67C23A; font-weight: bold; }
.text-warning { color: #E6A23C; font-weight: bold; }
.text-danger { color: #F56C6C; font-weight: bold; }
</style>