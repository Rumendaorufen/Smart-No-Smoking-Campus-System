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
            @click="openAuditDialog(item, 2)"
          >
            <el-icon><Close /></el-icon> 误报
          </el-button>
          <el-button 
            class="action-btn approve" 
            type="primary"
            @click="openAuditDialog(item, 1)"
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

    <el-dialog
      v-model="auditDialogVisible"
      :title="auditForm.status === 1 ? '确认违规' : '标记误报'"
      width="400px"
      class="custom-dialog"
    >
      <el-form :model="auditForm" label-position="top">
        <el-alert
          v-if="auditForm.status === 1"
          title="即将将此记录归档为【真实违规】"
          type="error"
          :closable="false"
          style="margin-bottom: 15px"
        />
        <el-alert
          v-else
          title="即将将此记录归档为【误报】，系统将学习此样本"
          type="info"
          :closable="false"
          style="margin-bottom: 15px"
        />

        <el-form-item label="处理备注 (选填)">
          <el-input 
            v-model="auditForm.remark" 
            type="textarea" 
            :rows="3" 
            placeholder="请输入备注信息，例如：画面模糊、工作人员误触发等..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="auditDialogVisible = false" class="cancel-btn">取消</el-button>
        <el-button 
          :type="auditForm.status === 1 ? 'danger' : 'primary'" 
          @click="confirmAudit"
          :loading="submitting"
        >
          确定提交
        </el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getPendingAlerts, submitAudit, type Alarm } from '../api/alert'
import { ElMessage } from 'element-plus'
import { VideoPlay, Location, Check, Close, ArrowLeft, Refresh } from '@element-plus/icons-vue'

const BASE_API = 'http://localhost:5000/' 
const getServerUrl = (path: string) => {
  if (!path) return ''
  return path.startsWith('http') ? path : BASE_API + path
}

const loading = ref(false)
const submitting = ref(false) // 提交按钮loading
const list = ref<Alarm[]>([])
const total = ref(0)
const videoVisible = ref(false)
const currentVideo = ref('')

// ✅ 新增：审核弹窗状态
const auditDialogVisible = ref(false)
const auditForm = reactive({
  id: 0,
  status: 1, // 1:违规, 2:误报
  remark: ''
})

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

// ✅ 修改：点击按钮打开弹窗，而不是直接提交
const openAuditDialog = (item: Alarm, status: number) => {
  auditForm.id = item.id
  auditForm.status = status
  auditForm.remark = '' // 清空备注
  auditDialogVisible.value = true
}

// ✅ 新增：确认提交逻辑
const confirmAudit = async () => {
  submitting.value = true
  try {
    const res: any = await submitAudit(auditForm.id, { 
      status: auditForm.status,
      remark: auditForm.remark // 📝 这里把 remark 发给后端
    })
    
    if (res.code === 200) {
      ElMessage.success(auditForm.status === 1 ? '已确认违规' : '已标记为误报')
      // 从列表中移除
      list.value = list.value.filter(i => i.id !== auditForm.id)
      total.value--
      auditDialogVisible.value = false
    }
  } catch (error) {
    console.error(error)
  } finally {
    submitting.value = false
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
/* 保持原有样式不变 */
.audit-container {
  padding: 30px;
  min-height: 100vh;
  background: #0d1119;
  color: #fff;
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

/* 深色模式下的 Dialog 样式 */
:deep(.custom-dialog) {
  background: #1c2538;
  border: 1px solid #363b45;
  border-radius: 8px;
}
:deep(.el-dialog__title) { color: #fff; }
:deep(.el-dialog__body) { color: #cfd3dc; padding-top: 10px; }
:deep(.el-form-item__label) { color: #cfd3dc; }
:deep(.el-textarea__inner) {
  background-color: rgba(0, 0, 0, 0.3);
  box-shadow: 0 0 0 1px #4a4d52 inset;
  color: #fff;
  border: none;
}
:deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px #409eff inset;
}
.cancel-btn {
  background: transparent;
  border: 1px solid #4a4d52;
  color: #909399;
}
.cancel-btn:hover {
  border-color: #409eff;
  color: #409eff;
}
</style>