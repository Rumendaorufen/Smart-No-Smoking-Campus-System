<template>
  <div class="user-manage-container">
    <div class="header">
      <div class="header-left">
        <h2>用户权限管理</h2>
        <el-input
          v-model="searchQuery"
          placeholder="搜索用户名..."
          prefix-icon="Search"
          clearable
          class="search-input"
          @input="handleSearch"
        />
      </div>
      <div class="actions">
        <el-button @click="$router.push('/')" class="back-btn">返回监控</el-button>
        <el-button type="primary" @click="openDialog('add')">
          <el-icon style="margin-right:5px"><Plus /></el-icon>添加用户
        </el-button>
      </div>
    </div>

    <el-table 
      :data="pagedUserList" 
      style="width: 100%" 
      class="custom-table"
      :header-cell-style="{ background: '#1c2538', color: '#e5eaf3', borderColor: '#363b45' }"
      :cell-style="{ background: '#141a25', color: '#cfd3dc', borderColor: '#363b45' }"
      v-loading="loading"
      @sort-change="handleSortChange"
    >
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名">
        <template #default="scope">
          <span style="font-weight: bold; color: #fff">{{ scope.row.username }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="role" label="角色" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.role === 'admin' ? 'danger' : 'primary'" effect="dark">
            {{ scope.row.role === 'admin' ? '管理员' : '操作员' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.status === 1 ? 'success' : 'info'" effect="plain">
            <span v-if="scope.row.status === 1">● 启用</span>
            <span v-else>○ 禁用</span>
          </el-tag>
        </template>
      </el-table-column>
      
      <el-table-column prop="lastLoginIp" label="最后登录IP" width="140" />
      
      <el-table-column 
        prop="lastLoginTime" 
        label="最后登录时间" 
        width="180" 
        sortable="custom"
      >
        <template #default="scope">
          {{ formatDate(scope.row.lastLoginTime) }}
        </template>
      </el-table-column>
      
      <el-table-column prop="createdAt" label="创建时间" width="180">
        <template #default="scope">
          {{ formatDate(scope.row.createdAt) }}
        </template>
      </el-table-column>

      <el-table-column label="操作" fixed="right" width="160">
        <template #default="scope">
          <el-button type="primary" link size="small" @click="openDialog('edit', scope.row)">
            <el-icon><Edit /></el-icon> 编辑
          </el-button>
          <el-button type="danger" link size="small" @click="handleDelete(scope.row)">
            <el-icon><Delete /></el-icon> 删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :background="true"
        layout="total, sizes, prev, pager, next, jumper"
        :total="totalUsers"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <el-dialog 
      v-model="dialogVisible" 
      :title="dialogMode === 'add' ? '添加新用户' : '编辑用户'" 
      width="450px"
      :close-on-click-modal="false"
      class="custom-dialog" 
    >
      <el-form :model="form" label-width="80px" ref="formRef">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" :disabled="dialogMode === 'edit'" />
        </el-form-item>
        <el-form-item :label="dialogMode === 'add' ? '密码' : '重置密码'" :required="dialogMode === 'add'">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="操作员 (User)" value="user" />
            <el-option label="管理员 (Admin)" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="账号状态">
          <el-radio-group v-model="form.status">
            <el-radio :label="1" border>启用</el-radio>
            <el-radio :label="0" border>禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false" class="cancel-btn">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import userApi from '../api/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Search } from '@element-plus/icons-vue'

interface UserVO {
  id: number;
  username: string;
  role: string;
  status: number;
  lastLoginIp?: string; // 🔥 驼峰
  lastLoginTime?: string; // 🔥 驼峰
  createdAt: string; // 🔥 驼峰
}

const userList = ref<UserVO[]>([]) 
const loading = ref(false)
const dialogVisible = ref(false)
const dialogMode = ref<'add' | 'edit'>('add')
const currentEditId = ref<number | null>(null)
const form = ref({ username: '', password: '', role: 'user', status: 1 })

const searchQuery = ref('')
const sortProp = ref('') 
const sortOrder = ref('') 

const currentPage = ref(1)
const pageSize = ref(10)

const processedUserList = computed(() => {
  let result = userList.value.filter(user => user.username !== 'admin')

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(user => 
      user.username.toLowerCase().includes(query)
    )
  }

  if (sortProp.value && sortOrder.value) {
    result.sort((a, b) => {
      let valA = a[sortProp.value as keyof UserVO]
      let valB = b[sortProp.value as keyof UserVO]

      if (!valA) return 1 
      if (!valB) return -1

      if (valA < valB) return sortOrder.value === 'ascending' ? -1 : 1
      if (valA > valB) return sortOrder.value === 'ascending' ? 1 : -1
      return 0
    })
  }

  return result
})

const totalUsers = computed(() => processedUserList.value.length)

const pagedUserList = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return processedUserList.value.slice(start, end)
})

const handleSearch = () => {
  currentPage.value = 1
}

const handleSortChange = ({ prop, order }: { prop: string, order: string }) => {
  sortProp.value = prop
  sortOrder.value = order
}

const handleSizeChange = (val: number) => {
  pageSize.value = val
  currentPage.value = 1
}
const handleCurrentChange = (val: number) => {
  currentPage.value = val
}

const loadUsers = async () => {
  loading.value = true
  try {
    const res: any = await userApi.getUsers()
    if (res.code === 200) userList.value = res.data
  } finally {
    loading.value = false
  }
}

const openDialog = (mode: 'add' | 'edit', row?: UserVO) => {
  dialogMode.value = mode
  dialogVisible.value = true
  if (mode === 'add') {
    form.value = { username: '', password: '', role: 'user', status: 1 }
    currentEditId.value = null
  } else if (row) {
    form.value = { username: row.username, password: '', role: row.role, status: row.status }
    currentEditId.value = row.id
  }
}

const handleSubmit = async () => {
  if (dialogMode.value === 'add' && !form.value.password) return ElMessage.warning('密码必填')
  try {
    if (dialogMode.value === 'add') {
      const res: any = await userApi.addUser(form.value)
      if (res.code === 200) ElMessage.success('添加成功')
    } else {
      if (!currentEditId.value) return
      const res: any = await userApi.updateUser(currentEditId.value, form.value)
      if (res.code === 200) ElMessage.success('更新成功')
    }
    dialogVisible.value = false
    loadUsers()
  } catch (error) {}
}

const handleDelete = (row: UserVO) => {
  ElMessageBox.confirm(`删除用户 "${row.username}"?`, '提示', { type: 'warning' })
    .then(async () => {
      const res: any = await userApi.deleteUser(row.id)
      if(res.code === 200) { ElMessage.success('删除成功'); loadUsers() }
    }).catch(() => {})
}

const formatDate = (dateStr?: string) => {
  if (!dateStr) return '-'
  // 处理 Java 可能返回的 T 分隔符格式
  return dateStr.replace('T', ' ').split('.')[0]
}

onMounted(() => loadUsers())
</script>

<style scoped>
/* 此处保留你原有的 CSS 代码，无需改动 */
.user-manage-container { padding: 40px; background: #0d1119; min-height: 100vh; color: #fff; background-size: 30px 30px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 1px solid rgba(64, 158, 255, 0.2); padding-bottom: 20px; }
.header-left { display: flex; align-items: center; gap: 20px; }
.header h2 { margin: 0; font-size: 24px; background: linear-gradient(90deg, #409eff, #fff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; white-space: nowrap; }
.search-input { width: 200px; }
:deep(.search-input .el-input__wrapper) { background-color: rgba(255, 255, 255, 0.05); box-shadow: 0 0 0 1px #363b45 inset; }
:deep(.search-input .el-input__inner) { color: #fff; }
.back-btn { background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: #fff; }
.custom-table { background-color: transparent !important; --el-table-border-color: #363b45; --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent; }
:deep(.custom-dialog) { background: #1c2538; border: 1px solid #363b45; border-radius: 8px; }
:deep(.el-dialog__title) { color: #fff; }
.pagination-wrapper { margin-top: 20px; display: flex; justify-content: flex-end; padding: 10px 0; }
</style>