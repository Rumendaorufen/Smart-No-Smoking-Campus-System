<template>
  <div class="audit-container">
    <div class="header">
      <div class="header-left">
        <el-button 
          :icon="ArrowLeft" 
          circle 
          class="back-btn"
          @click="$router.push('/')" 
          title="返回监控大屏"
        />
        <div class="title-box">
          <h2>⚖️ 报警仲裁台</h2>
          <span class="sub-title">Pending Audit: {{ total }}</span>
        </div>
      </div>
      
      <el-button type="primary" class="refresh-btn" @click="fetchData" :loading="loading">
        <el-icon><Refresh /></el-icon> 刷新列表
      </el-button>
    </div>

    <el-empty v-if="!loading && list.length === 0" description="暂无待审核记录，喝杯咖啡吧 ☕️" />

    <div v-else class="card-grid">
      <div 
        v-for="item in list" 
        :key="item.id" 
        class="audit-card" 
      >
        <div class="card-header">
          <el-tag effect="dark" type="danger" class="alarm-tag">疑似吸烟</el-tag>
          <span class="time">{{ item.created_at }}</span>
        </div>

        <div class="media-content">
          <div class="image-wrapper">
            <el-image 
              :src="getServerUrl(item.roi_url)" 
              :preview-src-list="[getServerUrl(item.roi_url)]"
              fit="cover"
              class="evidence-img"
              loading="lazy"
              preview-teleported
            >
              <template #placeholder>
                <div class="image-slot">加载中...</div>
              </template>
            </el-image>
            
            <div class="video-overlay">
               <el-button 
                 type="primary" 
                 circle
                 class="play-btn"
                 @click="openVideo(item.video_url)"
               >
                 <el-icon><VideoPlay /></el-icon>
               </el-button>
            </div>
          </div>

          <div class="meta-info">
            <div class="info-row">
              <el-icon><Location /></el-icon> 
              <span>{{ item.device_name }}</span>
            </div>
            <div class="info-row">
              <span>AI置信度:</span>
              <span :class="getConfClass(item.confidence)">
                {{ (item.confidence * 100).toFixed(1) }}%
              </span>
            </div>
          </div>
        </div>

        <div class="actions">
          <el-button 
            class="action-btn reject" 
            plain 
            @click="handleAudit(item, 2)"
          >
            <el-icon><Close /></el-icon> 误报
          </el-button>
          <el-button 
            class="action-btn approve" 
            type="primary"
            @click="handleAudit(item, 1)"
          >
            <el-icon><Check /></el-icon> 确认违规
          </el-button>
        </div>
      </div>
    </div>

    <el-dialog 
      v-model="videoVisible" 
      title="证据录像回放" 
      width="600px" 
      destroy-on-close
      class="custom-dialog"
    >
      <video v-if="currentVideo" :src="currentVideo" controls autoplay style="width: 100%"></video>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getPendingAlerts, submitAudit, type Alarm } from '../api/alert'
import { ElMessage } from 'element-plus'
import { VideoPlay, Location, Check, Close, ArrowLeft, Refresh } from '@element-plus/icons-vue'

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

const handleAudit = async (item: Alarm, status: number) => {
  try {
    const res: any = await submitAudit(item.id, { status })
    if (res.code === 200) {
      ElMessage.success(status === 1 ? '已确认违规' : '已标记为误报')
      list.value = list.value.filter(i => i.id !== item.id)
      total.value--
    }
  } catch (error) {
    console.error(error)
  }
}

const openVideo = (url: string) => {
  if (!url) return
  let cleanUrl = url.replace('http://localhost:5000/', '')
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
  padding: 30px;
  min-height: 100vh;
  background: #0d1119;
  color: #fff;
  /* 背景纹理 */
  background-image: radial-gradient(rgba(64, 158, 255, 0.05) 1px, transparent 1px);
  background-size: 20px 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(64, 158, 255, 0.2);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.back-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
}
.back-btn:hover {
  background: #409eff;
  border-color: #409eff;
}

.title-box h2 {
  margin: 0;
  font-size: 24px;
  background: linear-gradient(90deg, #409eff, #fff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.sub-title {
  font-size: 12px;
  color: #909399;
  letter-spacing: 1px;
}

.refresh-btn {
  background: linear-gradient(90deg, #409eff, #337ecc);
  border: none;
}

/* 卡片网格 */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 25px;
}

.audit-card {
  background: rgba(30, 35, 45, 0.6);
  border: 1px solid rgba(64, 158, 255, 0.2);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s;
  backdrop-filter: blur(10px);
  display: flex;
  flex-direction: column;
}

.audit-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  border-color: #409eff;
}

.card-header {
  padding: 12px 15px;
  background: rgba(0, 0, 0, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.time {
  font-size: 12px;
  color: #909399;
  font-family: monospace;
}

.media-content {
  padding: 15px;
}

.image-wrapper {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  height: 180px;
  background: #000;
}

.evidence-img {
  width: 100%;
  height: 100%;
  opacity: 0.9;
  transition: opacity 0.3s;
}

.video-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
  opacity: 0;
  transition: opacity 0.3s;
}

.image-wrapper:hover .video-overlay {
  opacity: 1;
}

.play-btn {
  font-size: 24px;
  width: 50px;
  height: 50px;
}

.meta-info {
  margin-top: 15px;
  font-size: 14px;
  color: #cfd3dc;
}

.info-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
}

.text-success { color: #67C23A; font-weight: bold; }
.text-warning { color: #E6A23C; font-weight: bold; }
.text-danger { color: #F56C6C; font-weight: bold; text-shadow: 0 0 5px rgba(245, 108, 108, 0.5); }

.actions {
  margin-top: auto;
  padding: 15px;
  display: flex;
  gap: 10px;
  background: rgba(0, 0, 0, 0.2);
}

.action-btn {
  flex: 1;
}
.action-btn.reject {
  background: transparent;
  border-color: #f56c6c;
  color: #f56c6c;
}
.action-btn.reject:hover {
  background: #f56c6c;
  color: #fff;
}

/* 深色模式下的 Dialog 样式修正 */
:deep(.custom-dialog) {
  background: #1c2538;
  border: 1px solid #363b45;
}
:deep(.el-dialog__title) { color: #fff; }
</style>