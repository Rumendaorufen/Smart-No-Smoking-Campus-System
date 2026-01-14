import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Monitor from '../views/Monitor.vue'
// 1. 引入新页面
import UserManage from '../views/UserManage.vue'
import { ElMessage } from 'element-plus'
import DeviceManage from '../views/DeviceManage.vue'

const routes = [
  {
    path: '/',
    name: 'Monitor',
    component: Monitor,
    meta: { title: '实时监控' } // 所有人可看
  },
  {
    path: '/users',
    name: 'UserManage',
    component: UserManage,
    // 2. 标记：只有 admin 能进
    meta: { title: '用户管理', roles: ['admin'] } 
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { title: '登录' }
  },
  {
    path: '/devices',
    name: 'DeviceManage',
    component: DeviceManage,
    meta: { title: '设备管理', roles: ['admin'] } // 权限控制
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = (to.meta.title as string) || '智慧校园禁烟监控系统'
  const token = localStorage.getItem('token')
  
  // 获取当前用户信息字符串
  const userInfoStr = localStorage.getItem('userInfo')
  // 解析出对象 (防止为空)
  const userInfo = userInfoStr ? JSON.parse(userInfoStr) : null
  const userRole = userInfo ? userInfo.role : 'user'

  if (to.path !== '/login' && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/')
  } else {
    // 3. 权限校验逻辑
    if (to.meta.roles) {
      // 如果路由配置了 roles 数组，检查当前用户角色是否在其中
      const requiredRoles = to.meta.roles as string[]
      if (requiredRoles.includes(userRole)) {
        next() // 有权限，放行
      } else {
        ElMessage.error('权限不足，无法访问该页面')
        next('/') // 没权限，踢回首页
      }
    } else {
      next() // 没配置权限要求的页面，直接放行
    }
  }
})

export default router