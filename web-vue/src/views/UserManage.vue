<template>
  <div class="user-manage-container">
    <div class="header">
      <h2>用户权限管理</h2>
      <div class="actions">
        <el-button @click="$router.push('/')">返回监控</el-button>
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

      <el-table-column prop="last_login_ip" label="最后登录IP" width="140">
        <template #default="scope">
          {{ scope.row.last_login_ip || '-' }}
        </template>
      </el-table-column>

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
          <el-button 
            type="danger" link size="small" 
            @click="handleDelete(scope.row)"
          >
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
          <el-input 
            v-model="form.username" 
            placeholder="请输入用户名" 
            :disabled="dialogMode === 'edit'" 
          />
        </el-form-item>

        <el-form-item :label="dialogMode === 'add' ? '密码' : '重置密码'" :required="dialogMode === 'add'">
          <el-input 
            v-model="form.password" 
            type="password" 
            :placeholder="dialogMode === 'add' ? '请输入密码' : '不修改请留空'" 
            show-password 
          />
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
        <el-button @click="dialogVisible = false">取消</el-button>
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

// 定义接口，对应数据库字段
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

// 表单数据
const form = ref({
  username: '',
  password: '',
  role: 'user',
  status: 1
})

// ✅ 计算属性：过滤掉管理员账号 (admin)
const filteredUserList = computed(() => {
  return userList.value.filter(user => user.username !== 'admin')
})

// 加载数据
const loadUsers = async () => {
  loading.value = true
  try {
    const res = await userApi.getUsers()
    if (res.code === 200) {
      userList.value = res.data
    }
  } finally {
    loading.value = false
  }
}

// 打开弹窗
const openDialog = (mode: 'add' | 'edit', row?: UserVO) => {
  dialogMode.value = mode
  dialogVisible.value = true
  
  if (mode === 'add') {
    form.value = { username: '', password: '', role: 'user', status: 1 }
    currentEditId.value = null
  } else if (row) {
    // 编辑模式：回显数据，密码置空
    form.value = { 
      username: row.username, 
      password: '', // 密码不回显
      role: row.role, 
      status: row.status 
    }
    currentEditId.value = row.id
  }
}

// 提交表单 (添加或编辑)
const handleSubmit = async () => {
  if (dialogMode.value === 'add' && !form.value.password) {
    return ElMessage.warning('新增用户必须填写密码')
  }

  try {
    if (dialogMode.value === 'add') {
      const res = await userApi.addUser(form.value)
      if (res.code === 200) ElMessage.success('添加成功')
    } else {
      // 编辑模式
      if (!currentEditId.value) return
      const res = await userApi.updateUser(currentEditId.value, form.value)
      if (res.code === 200) ElMessage.success('更新成功')
    }
    dialogVisible.value = false
    loadUsers()
  } catch (error) {}
}

const handleDelete = (row: UserVO) => {
  ElMessageBox.confirm(
    `确定要删除用户 "${row.username}" 吗？`, 
    '危险操作', 
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
  ).then(async () => {
    const res = await userApi.deleteUser(row.id)
    if(res.code === 200) {
      ElMessage.success('删除成功')
      loadUsers()
    }
  }).catch(() => {})
}

// 时间格式化辅助函数
const formatDate = (dateStr?: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}

onMounted(() => loadUsers())
</script>

<style scoped>
.user-manage-container {
  padding: 40px;
  background: #0d1119;
  min-height: 100vh;
  color: #fff;
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

/* 深色表格样式 */
.custom-table {
  background-color: transparent !important;
  --el-table-border-color: #363b45;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
}

:deep(.el-table__inner-wrapper::before) {
  display: none;
}
:deep(.el-table__row:hover) {
  background-color: rgba(64, 158, 255, 0.1) !important;
}
</style>