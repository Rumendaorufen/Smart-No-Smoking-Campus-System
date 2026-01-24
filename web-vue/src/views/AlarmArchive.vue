<template>
  <div class="archive-container">
    <div class="page-header">
      <el-button :icon="ArrowLeft" circle class="back-btn" @click="$router.push('/')" title="返回监控大屏" />
      <h2 style="margin: 0">📂 违规历史档案</h2>
    </div>
    
    <div class="filter-bar">
      <el-form :inline="true" :model="query" class="dark-form">
         <el-form-item label="设备检索">
          <el-input v-model="query.device_name" placeholder="输入设备名称" class="dark-input" clearable @keyup.enter="fetchData" @clear="fetchData" style="width: 180px" />
        </el-form-item>
        <el-form-item label="审核人">
          <el-input 
            v-model="query.auditor_name" 
            placeholder="审核员姓名" 
            class="dark-input" 
            clearable 
            @keyup.enter="fetchData" 
            @clear="fetchData" 
            style="width: 120px" 
          />
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始" end-placeholder="结束" value-format="YYYY-MM-DD" @change="handleDateChange" class="dark-input" style="width: 240px" />
        </el-form-item>
        <el-form-item label="状态筛选">
          <div class="status-toggle-group">
            <el-button :type="query.status === 1 ? 'danger' : ''" class="toggle-btn" :class="{ 'is-inactive': query.status !== 1 }" @click="toggleStatus(1)">已确认</el-button>
            <el-button :type="query.status === 2 ? 'info' : ''" class="toggle-btn" :class="{ 'is-inactive': query.status !== 2 }" @click="toggleStatus(2)">已误报</el-button>
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
            <el-image style="width: 80px; height: 50px; border-radius: 4px" :src="getServerUrl(row.roi_url)" :preview-src-list="[getServerUrl(row.roi_url)]" fit="cover" preview-teleported />
          </template>
        </el-table-column>
        <el-table-column prop="device_name" label="设备位置" min-width="150" />
        <el-table-column prop="created_at" label="报警时间" width="170" />
        <el-table-column prop="status" label="审核结果" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === 1" type="danger" effect="dark">已确认</el-tag>
            <el-tag v-else-if="row.status === 2" type="info" effect="plain">误报</el-tag>
            <el-tag v-else type="warning">未知</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="auditor_name" label="审核人" width="100" />
        <el-table-column prop="audit_time" label="审核时间" width="170" />
        <el-table-column prop="audit_remark" label="审核备注" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.audit_remark">{{ row.audit_remark }}</span>
            <span v-else style="color: #606266; font-style: italic">无</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="220" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openVideo(row.video_url)">录像</el-button>
            
            <el-button 
              v-if="canEdit(row)" 
              link 
              type="warning" 
              @click="openEditDialog(row)"
            >
              修改
            </el-button>
            
            <el-popconfirm 
              v-if="isAdmin" 
              title="确定永久删除吗？" 
              @confirm="handleDelete(row.id)"
            >
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination v-model:current-page="query.page" v-model:page-size="query.page_size" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next, jumper" background @size-change="fetchData" @current-change="fetchData" />
      </div>
    </div>

    <el-dialog v-model="videoVisible" title="录像回放" width="600px" destroy-on-close class="custom-dialog">
      <video v-if="currentVideo" :src="currentVideo" controls autoplay style="width: 100%"></video>
    </el-dialog>

    <el-dialog v-model="editDialogVisible" title="修正审核结果" width="400px" class="custom-dialog">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="当前状态">
          <el-tag v-if="currentEditRow?.status === 1" type="danger">已确认违规</el-tag>
          <el-tag v-else-if="currentEditRow?.status === 2" type="info">已标记误报</el-tag>
        </el-form-item>
        <el-form-item label="修正为">
          <el-radio-group v-model="editForm.status">
            <el-radio :label="1" border>确认违规</el-radio>
            <el-radio :label="2" border>标记误报</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.remark" type="textarea" placeholder="请输入修改原因（选填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false" class="cancel-btn">取消</el-button>
        <el-button type="primary" @click="submitEdit">保存修正</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { getArchive, deleteAlarm, submitAudit, type Alarm } from '../api/alert'
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

// ✅ 1. 获取用户信息
const userInfoStr = localStorage.getItem('userInfo')
const currentUser = userInfoStr ? JSON.parse(userInfoStr) : { role: 'user', id: -1 } // 默认ID防错
const isAdmin = computed(() => currentUser.role === 'admin')

// ✅ 2. 新增：判断是否有权限修改某行数据
// 逻辑：如果是Admin，返回true；如果不是Admin，判断 row.auditor_id 是否等于当前用户ID
const canEdit = (row: any) => {
 // 1. 如果是管理员，直接允许
  if (isAdmin.value) return true
  
  // 2. 如果这行数据还没人审核（auditor_id 为 null），谁都不能改（或者你可以允许当前用户去"认领"）
  if (!row.auditor_id) return false

  // 3. 判断当前用户ID 是否等于 审核人ID
  // ✅ 使用 String() 强转，防止 int vs string 的类型问题
  return String(row.auditor_id) === String(currentUser.id)
}

const editDialogVisible = ref(false)
const currentEditRow = ref<Alarm | null>(null)
const editForm = reactive({
  status: 1,
  remark: ''
})

const query = reactive({
  page: 1,
  page_size: 10,
  status: undefined as number | undefined,
  device_name: '',
  auditor_name: '', // ✅ 新增字段
  start_time: '',
  end_time: ''
})

// ... (fetchData, toggleStatus, handleDateChange, resetQuery 保持不变) ...
const fetchData = async () => {
  loading.value = true
  try {
    const params: any = {
      page: query.page,
      page_size: query.page_size,
      start_time: query.start_time || undefined,
      end_time: query.end_time || undefined,
      device_name: query.device_name || undefined,
      auditor_name: query.auditor_name || undefined // ✅ 传递字段给后端
    }
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

const toggleStatus = (val: number) => {
  if (query.status === val) { query.status = undefined } else { query.status = val }
  query.page = 1
  fetchData()
}

const handleDateChange = (val: any) => {
  if (val) { query.start_time = val[0] + ' 00:00:00'; query.end_time = val[1] + ' 23:59:59' } 
  else { query.start_time = ''; query.end_time = '' }
  fetchData()
}

const resetQuery = () => {
  query.status = undefined; query.device_name = '';query.auditor_name = ''; // ✅ 清空审核人 dateRange.value = []; 
  query.start_time = ''; query.end_time = ''; query.page = 1; fetchData()
}

const handleDelete = async (id: number) => {
  try {
    const res: any = await deleteAlarm(id)
    if (res.code === 200) {
      ElMessage.success('删除成功')
      fetchData()
    }
  } catch (error) { console.error(error) }
}

const openVideo = (url: string) => {
  if (!url) return
  let cleanUrl = url.replace('http://localhost:5000/', '')
  currentVideo.value = `http://localhost:5000/api/v1/monitor/video/${cleanUrl}`
  videoVisible.value = true
}

const openEditDialog = (row: Alarm) => {
  currentEditRow.value = row
  editForm.status = row.status
  editForm.remark = row.audit_remark || ''
  editDialogVisible.value = true
}

const submitEdit = async () => {
  if (!currentEditRow.value) return
  try {
    const res: any = await submitAudit(currentEditRow.value.id, {
      status: editForm.status,
      remark: editForm.remark
    })
    if (res.code === 200) {
      ElMessage.success('修正成功')
      editDialogVisible.value = false
      fetchData()
    }
  } catch (e) {}
}

onMounted(() => fetchData())
</script>

<style scoped>
/* 保持原有样式不变 */
.archive-container { padding: 30px; min-height: 100vh; background: #0d1119; color: #fff; }
.page-header { display: flex; align-items: center; margin-bottom: 30px; border-bottom: 1px solid rgba(64, 158, 255, 0.2); padding-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 24px; background: linear-gradient(90deg, #409eff, #fff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.back-btn { background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: #fff; margin-right: 15px; }
.back-btn:hover { background: #409eff; border-color: #409eff; }
.filter-bar { background: rgba(22, 33, 52, 0.6); padding: 20px; border-radius: 8px; border: 1px solid rgba(64, 158, 255, 0.1); margin-bottom: 20px; }
.reset-btn { background: transparent; border: 1px solid #4a4d52; color: #909399; }
.reset-btn:hover { color: #409eff; border-color: #409eff; }
.status-toggle-group { display: flex; gap: 10px; }
.toggle-btn { background: rgba(0, 0, 0, 0.2); border: 1px solid #4a4d52; color: #909399; transition: all 0.3s; }
.toggle-btn.is-inactive:hover { border-color: #409eff; color: #409eff; }

:deep(.el-input__wrapper), :deep(.el-range-editor.el-input__wrapper), :deep(.el-textarea__inner) {
  background-color: rgba(0, 0, 0, 0.3) !important;
  box-shadow: 0 0 0 1px #4a4d52 inset !important;
  color: #fff;
}
:deep(.el-input__inner) { color: #fff; }
:deep(.el-date-editor .el-range-input) { color: #fff; }
:deep(.el-form-item__label) { color: #cfd3dc; }

.custom-table { background-color: transparent !important; --el-table-border-color: #363b45; --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent; }
:deep(.el-table__inner-wrapper::before) { display: none; }
:deep(.el-table__row:hover) { background-color: rgba(64, 158, 255, 0.1) !important; }

.pagination { margin-top: 20px; display: flex; justify-content: flex-end; }
:deep(.el-pagination.is-background .el-pager li:not(.is-disabled)) { background-color: #1c2538; color: #fff; }
:deep(.el-pagination.is-background .el-pager li.is-active) { background-color: #409eff; }
:deep(.el-pagination.is-background .btn-prev), :deep(.el-pagination.is-background .btn-next) { background-color: #1c2538; color: #fff; }

:deep(.custom-dialog) { background: #1c2538; border: 1px solid #363b45; }
:deep(.el-dialog__title) { color: #fff; }
.cancel-btn { background: transparent; border-color: #4a4d52; color: #cfd3dc; }
.cancel-btn:hover { border-color: #409eff; color: #409eff; }
</style>