<!-- web-vue\src\views\Login.vue -->
<template>
  <div class="login-container">
    <div class="bg-decoration circle-1"></div>
    <div class="bg-decoration circle-2"></div>
    <div class="grid-overlay"></div>

    <div class="login-box">
      <div class="login-header">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
          </svg>
        </div>
        <h2 class="system-title">智慧校园禁烟监控系统</h2>
        <p class="sub-title">Smart Campus No-Smoking Monitor</p>
      </div>

      <el-form 
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
        size="large"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input 
            v-model="loginForm.username" 
            placeholder="管理员账号"
            :prefix-icon="User"
            autocomplete="off"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input 
            v-model="loginForm.password" 
            type="password" 
            placeholder="密码"
            :prefix-icon="Lock"
            show-password
            autocomplete="off"
          />
        </el-form-item>

        <el-form-item>
          <el-button 
            type="primary" 
            :loading="loading" 
            class="login-btn" 
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '立即登录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <div class="tech-lines">
          <span></span><span></span><span></span>
        </div>
        <p>&copy; 2026 智能视觉分析技术支持</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import authApi from '../api/auth'

const router = useRouter()
const loginFormRef = ref<FormInstance>()
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const loginRules = reactive<FormRules>({
  username: [
    { required: true, message: '请输入管理员账号', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 5, message: '密码长度不能小于5位', trigger: 'blur' }
  ]
})

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const res: any = await authApi.login(loginForm)
        
        // Java 返回结构: { code: 200, data: { token: "...", userInfo: {...} } }
        if (res.code === 200) {
          ElMessage.success('登录成功')
          
          // 存 Token
          localStorage.setItem('token', res.data.token)
          // 存用户信息
          localStorage.setItem('userInfo', JSON.stringify(res.data.userInfo))
          
          setTimeout(() => {
            router.push('/')
          }, 500)
        }
      } catch (error) {
        console.error('Login error:', error)
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  width: 100%;
  background: #0d1119;
  /* 网格背景 */
  background-image: 
    linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 30px 30px;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  overflow: hidden;
  color: #fff;
}

/* 动态背景光晕 */
.bg-decoration {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.3;
  z-index: 0;
  animation: float 10s infinite ease-in-out;
}

.circle-1 {
  width: 500px;
  height: 500px;
  background: #409eff;
  top: -100px;
  left: -100px;
}

.circle-2 {
  width: 400px;
  height: 400px;
  background: #67c23a;
  bottom: -50px;
  right: -50px;
  animation-delay: -5s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(20px, 30px); }
}

.login-box {
  width: 420px;
  padding: 45px 40px;
  background: rgba(22, 33, 52, 0.7);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(64, 158, 255, 0.2);
  border-radius: 16px;
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.3);
  z-index: 1;
  text-align: center;
  position: relative;
}

/* 顶部光条装饰 */
.login-box::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, #409eff, transparent);
}

.login-header {
  margin-bottom: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.logo-icon {
  width: 54px;
  height: 54px;
  background: linear-gradient(135deg, #409eff 0%, #337ecc 100%);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 0 25px rgba(64, 158, 255, 0.4);
  margin-bottom: 20px;
  transform: rotate(-5deg);
  transition: transform 0.3s;
}

.login-box:hover .logo-icon {
  transform: rotate(0deg) scale(1.05);
}

.logo-icon svg {
  width: 32px;
  height: 32px;
}

.system-title {
  font-size: 26px;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(90deg, #ffffff, #c0c4cc);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 1px;
}

.sub-title {
  margin: 10px 0 0;
  font-size: 12px;
  color: #606266;
  text-transform: uppercase;
  letter-spacing: 2px;
  font-family: 'Arial', sans-serif;
}

.login-form {
  margin-top: 25px;
}

/* 深度选择器修改 Element 样式以适配暗黑主题 */
:deep(.el-input__wrapper) {
  background-color: rgba(0, 0, 0, 0.2) !important;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1) inset !important;
  padding: 8px 15px;
  transition: all 0.3s;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #409eff inset !important;
  background-color: rgba(64, 158, 255, 0.05) !important;
}

:deep(.el-input__inner) {
  color: #fff !important;
  height: 36px;
}

/* 去掉浏览器自动填充的黄色/白色背景 */
:deep(.el-input__inner:-webkit-autofill) {
  -webkit-box-shadow: 0 0 0 1000px #1a1f2e inset !important;
  -webkit-text-fill-color: #fff !important;
  transition: background-color 5000s ease-in-out 0s;
}

.login-btn {
  width: 100%;
  padding: 24px 0;
  font-size: 16px;
  letter-spacing: 4px;
  background: linear-gradient(90deg, #409eff, #337ecc);
  border: none;
  margin-top: 15px;
  transition: all 0.3s;
  font-weight: 600;
}

.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(64, 158, 255, 0.4);
}

.login-footer {
  margin-top: 40px;
  font-size: 12px;
  color: #606266;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.tech-lines {
  display: flex;
  gap: 4px;
}

.tech-lines span {
  width: 4px;
  height: 4px;
  background: #606266;
  border-radius: 50%;
  opacity: 0.5;
}
</style>