<template>
  <div class="user-manage-container">
    <div class="header">
      <h2>用户权限管理</h2>
      <div class="actions">
        <el-button @click="$router.push('/')" class="back-btn">返回监控</el-button>
        <el-button type="primary" @click="openDialog('add')">
          <el-icon style="margin-right:5px"><Plus /></el-icon>添加用户
        </el-button>
      </div>
    </div>

    <el-table 
      :data="filteredUserList" 
      style="width: 100%" 
      class="custom-table"
      :header-cell-style="{ background: '#1c2538', color: '#e5eaf3', borderColor: '#363b45' }"
      :cell-style="{ background: '#141a25', color: '#cfd3dc', borderColor: '#363b45' }"
      v-loading="loading"
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
      <el-table-column prop="last_login_ip" label="最后登录IP" width="140" />
      <el-table-column prop="last_login_time" label="最后登录时间" width="180">
        <template #default="scope">
          {{ formatDate(scope.row.last_login_time) }}
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="scope">
          {{ formatDate(scope.row.created_at) }}
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
import { Plus, Edit, Delete } from '@element-plus/icons-vue'

interface UserVO {
  id: number;
  username: string;
  role: string;
  status: number;
  last_login_ip?: string;
  last_login_time?: string;
  created_at: string;
}

const userList = ref<UserVO[]>([]) 
const loading = ref(false)
const dialogVisible = ref(false)
const dialogMode = ref<'add' | 'edit'>('add')
const currentEditId = ref<number | null>(null)
const form = ref({ username: '', password: '', role: 'user', status: 1 })

const filteredUserList = computed(() => {
  return userList.value.filter(user => user.username !== 'admin')
})

const loadUsers = async () => {
  loading.value = true
  try {
    const res = await userApi.getUsers()
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
      const res = await userApi.addUser(form.value)
      if (res.code === 200) ElMessage.success('添加成功')
    } else {
      if (!currentEditId.value) return
      const res = await userApi.updateUser(currentEditId.value, form.value)
      if (res.code === 200) ElMessage.success('更新成功')
    }
    dialogVisible.value = false
    loadUsers()
  } catch (error) {}
}

const handleDelete = (row: UserVO) => {
  ElMessageBox.confirm(`删除用户 "${row.username}"?`, '提示', { type: 'warning' })
    .then(async () => {
      const res = await userApi.deleteUser(row.id)
      if(res.code === 200) { ElMessage.success('删除成功'); loadUsers() }
    }).catch(() => {})
}

const formatDate = (dateStr?: string) => dateStr ? new Date(dateStr).toLocaleString() : '-'
onMounted(() => loadUsers())
</script>

<style scoped>
.user-manage-container {
  padding: 40px;
  background: #0d1119;
  min-height: 100vh;
  color: #fff;
  background-image: linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
  linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 30px 30px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  border-bottom: 1px solid rgba(64, 158, 255, 0.2);
  padding-bottom: 20px;
}

.header h2 {
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
}
.back-btn:hover {
  background: #409eff;
  border-color: #409eff;
}

.custom-table {
  background-color: transparent !important;
  --el-table-border-color: #363b45;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
}

:deep(.el-table__inner-wrapper::before) { display: none; }
:deep(.el-table__row:hover) { background-color: rgba(64, 158, 255, 0.1) !important; }

/* 🔥 统一弹窗样式 */
:deep(.custom-dialog) {
  background: #1c2538;
  border: 1px solid #363b45;
  border-radius: 8px;
}
:deep(.el-dialog__title) { color: #fff; }
:deep(.el-dialog__body) { color: #cfd3dc; padding-top: 10px; }
:deep(.el-form-item__label) { color: #cfd3dc; }
:deep(.el-input__wrapper) { background-color: rgba(0,0,0,0.3); box-shadow: 0 0 0 1px #4a4d52 inset; }
:deep(.el-input__inner) { color: white; }
</style>