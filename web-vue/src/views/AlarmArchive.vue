<template>
  <div class="archive-container">
    <div class="page-header">
      <el-button 
        :icon="ArrowLeft" 
        circle 
        class="back-btn"
        @click="$router.push('/')" 
        title="返回监控大屏"
      />
      <h2 style="margin: 0">📂 违规历史档案</h2>
    </div>
    
    <div class="filter-bar">
      <el-form :inline="true" :model="query" class="dark-form">
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            @change="handleDateChange"
            class="dark-input"
          />
        </el-form-item>
        
        <el-form-item label="状态筛选">
          <div class="status-toggle-group">
            <el-button 
              :type="query.status === 1 ? 'danger' : ''" 
              class="toggle-btn"
              :class="{ 'is-inactive': query.status !== 1 }"
              @click="toggleStatus(1)"
            >
              已确认违规
            </el-button>
            <el-button 
              :type="query.status === 2 ? 'info' : ''" 
              class="toggle-btn"
              :class="{ 'is-inactive': query.status !== 2 }"
              @click="toggleStatus(2)"
            >
              已标记误报
            </el-button>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :icon="Search" @click="fetchData">查询</el-button>
          <el-button :icon="Refresh" class="reset-btn" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="table-wrapper">
      <el-table 
        :data="list" 
        border 
        v-loading="loading" 
        style="width: 100%"
        class="custom-table"
        :header-cell-style="{ background: '#1c2538', color: '#e5eaf3', borderColor: '#363b45' }"
        :cell-style="{ background: '#141a25', color: '#cfd3dc', borderColor: '#363b45' }"
      >
        <el-table-column prop="id" label="ID" width="80" align="center" />
        
        <el-table-column label="证据快照" width="120" align="center">
          <template #default="{ row }">
            <el-image 
              style="width: 80px; height: 50px; border-radius: 4px" 
              :src="getServerUrl(row.roi_url)" 
              :preview-src-list="[getServerUrl(row.roi_url)]"
              fit="cover" 
              preview-teleported
            />
          </template>
        </el-table-column>

        <el-table-column prop="device_name" label="设备位置" min-width="150" />
        <el-table-column prop="created_at" label="报警时间" width="180" />
        
        <el-table-column prop="status" label="审核结果" width="120" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === 1" type="danger" effect="dark">已确认</el-tag>
            <el-tag v-else-if="row.status === 2" type="info" effect="plain">误报</el-tag>
            <el-tag v-else type="warning">未知</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="auditor_name" label="审核人" width="120" />
        <el-table-column prop="audit_time" label="审核时间" width="180" />

        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openVideo(row.video_url)">录像</el-button>
            <el-popconfirm title="确定永久删除吗？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </div>

    <el-dialog v-model="videoVisible" title="录像回放" width="600px" destroy-on-close class="custom-dialog">
      <video v-if="currentVideo" :src="currentVideo" controls autoplay style="width: 100%"></video>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getArchive, deleteAlarm, type Alarm } from '../api/alert'
import { ElMessage } from 'element-plus'
import { Search, Refresh, ArrowLeft } from '@element-plus/icons-vue'

const BASE_API = 'http://localhost:5000/'
const getServerUrl = (path: string) => {
  if (!path) return ''
  return path.startsWith('http') ? path : BASE_API + path
}

const loading = ref(false)
const list = ref<Alarm[]>([])
const total = ref(0)
const dateRange = ref([])
const videoVisible = ref(false)
const currentVideo = ref('')

// status 类型定义为 number 或 undefined
const query = reactive<{
  page: number;
  page_size: number;
  status: number | undefined;
  start_time: string;
  end_time: string;
}>({
  page: 1,
  page_size: 10,
  status: undefined, // 默认为 undefined (全部)
  start_time: '',
  end_time: ''
})

const fetchData = async () => {
  loading.value = true
  try {
    const params: any = {
      page: query.page,
      page_size: query.page_size,
      start_time: query.start_time || undefined,
      end_time: query.end_time || undefined
    }
    // 只有 status 有明确值时才传
    if (query.status !== undefined) {
      params.status = query.status
    }
    const res: any = await getArchive(params)
    if (res.code === 200) {
      list.value = res.data.list
      total.value = res.data.total
    }
  } finally {
    loading.value = false
  }
}

// ✅ 新增：切换状态逻辑
// 如果点击的是当前选中的状态，则取消选中（查全部）；否则选中该状态
const toggleStatus = (val: number) => {
  if (query.status === val) {
    query.status = undefined // 取消选中 -> 查全部
  } else {
    query.status = val // 选中
  }
  // 状态改变后自动查询，不需要点查询按钮
  query.page = 1
  fetchData() 
}

const handleDateChange = (val: any) => {
  if (val) {
    query.start_time = val[0] + ' 00:00:00'
    query.end_time = val[1] + ' 23:59:59'
  } else {
    query.start_time = ''
    query.end_time = ''
  }
  fetchData()
}

const resetQuery = () => {
  query.status = undefined
  dateRange.value = []
  query.start_time = ''
  query.end_time = ''
  query.page = 1
  fetchData()
}

const handleDelete = async (id: number) => {
  try {
    const res: any = await deleteAlarm(id)
    if (res.code === 200) {
      ElMessage.success('删除成功')
      fetchData()
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

onMounted(() => fetchData())
</script>

<style scoped>
.archive-container {
  padding: 30px;
  min-height: 100vh;
  background: #0d1119;
  color: #fff;
}

.page-header {
  display: flex;
  align-items: center;
  margin-bottom: 30px;
  border-bottom: 1px solid rgba(64, 158, 255, 0.2);
  padding-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  background: linear-gradient(90deg, #409eff, #fff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.back-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  margin-right: 15px;
}
.back-btn:hover {
  background: #409eff;
  border-color: #409eff;
}

.filter-bar {
  background: rgba(22, 33, 52, 0.6);
  padding: 20px;
  border-radius: 8px;
  border: 1px solid rgba(64, 158, 255, 0.1);
  margin-bottom: 20px;
}

.reset-btn {
  background: transparent;
  border: 1px solid #4a4d52;
  color: #909399;
}
.reset-btn:hover {
  color: #409eff;
  border-color: #409eff;
}

/* ✅ 按钮组样式 */
.status-toggle-group {
  display: flex;
  gap: 10px;
}

.toggle-btn {
  /* 默认未选中状态：透明背景，带边框 */
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid #4a4d52;
  color: #909399;
  transition: all 0.3s;
}

.toggle-btn.is-inactive:hover {
  border-color: #409eff;
  color: #409eff;
}

/* 选中状态由 type 属性控制颜色，这里不需要额外写选中背景 */

:deep(.el-input__wrapper), :deep(.el-range-editor.el-input__wrapper) {
  background-color: rgba(0, 0, 0, 0.3) !important;
  box-shadow: 0 0 0 1px #4a4d52 inset !important;
}
:deep(.el-input__inner) { color: #fff; }
:deep(.el-date-editor .el-range-input) { color: #fff; }
:deep(.el-form-item__label) { color: #cfd3dc; }

/* 表格透明化 */
.custom-table {
  background-color: transparent !important;
  --el-table-border-color: #363b45;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
}
:deep(.el-table__inner-wrapper::before) { display: none; }
:deep(.el-table__row:hover) { background-color: rgba(64, 158, 255, 0.1) !important; }

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

/* 分页器暗黑适配 */
:deep(.el-pagination.is-background .el-pager li:not(.is-disabled)) {
  background-color: #1c2538;
  color: #fff;
}
:deep(.el-pagination.is-background .el-pager li.is-active) {
  background-color: #409eff;
}
:deep(.el-pagination.is-background .btn-prev), 
:deep(.el-pagination.is-background .btn-next) {
  background-color: #1c2538;
  color: #fff;
}

:deep(.custom-dialog) {
  background: #1c2538;
  border: 1px solid #363b45;
}
:deep(.el-dialog__title) { color: #fff; }
</style>