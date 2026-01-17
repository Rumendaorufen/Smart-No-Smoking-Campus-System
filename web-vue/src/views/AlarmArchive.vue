<template>
  <div class="archive-container">
    <h2>📂 违规历史档案</h2>
    
    <el-card class="filter-card">
      <el-form :inline="true" :model="query">
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            @change="handleDateChange"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部状态" clearable>
            <el-option label="已确认违规" :value="1" />
            <el-option label="已标记误报" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="fetchData">查询</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="table-card">
      <el-table :data="list" border stripe v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        
        <el-table-column label="证据快照" width="120">
          <template #default="{ row }">
            <el-image 
              style="width: 80px; height: 60px" 
              :src="getServerUrl(row.roi_url)" 
              :preview-src-list="[getServerUrl(row.roi_url)]"
              fit="cover" 
              preview-teleported
            />
          </template>
        </el-table-column>

        <el-table-column prop="device_name" label="设备位置" min-width="120" />
        <el-table-column prop="created_at" label="报警时间" width="180" />
        
        <el-table-column prop="status" label="审核结果" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.status === 1" type="danger">已确认</el-tag>
            <el-tag v-else-if="row.status === 2" type="info">误报</el-tag>
            <el-tag v-else type="warning">未知</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="auditor_name" label="审核人" width="120" />
        <el-table-column prop="audit_time" label="审核时间" width="180" />

        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openVideo(row.video_url)">查看录像</el-button>
            <el-popconfirm title="确定删除这条记录吗？证据文件也将被永久删除。" @confirm="handleDelete(row.id)">
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
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <el-dialog v-model="videoVisible" title="录像回放" width="600px" destroy-on-close>
      <video v-if="currentVideo" :src="getServerUrl(currentVideo)" controls autoplay style="width: 100%"></video>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getArchive, deleteAlarm, type Alarm } from '../api/alert'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'

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

const query = reactive({
  page: 1,
  page_size: 10,
  status: undefined,
  start_time: '',
  end_time: ''
})

const fetchData = async () => {
  loading.value = true
  try {
    const res: any = await getArchive(query)
    if (res.code === 200) {
      list.value = res.data.list
      total.value = res.data.total
    }
  } finally {
    loading.value = false
  }
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

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.archive-container {
  padding: 20px;
}
.filter-card {
  margin-bottom: 20px;
}
.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>