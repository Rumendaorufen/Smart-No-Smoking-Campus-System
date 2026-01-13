import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Monitor from '../views/Monitor.vue' 

const routes = [
  {
    path: '/',
    name: 'Monitor',
    component: Monitor,
    meta: { title: '实时监控', requiresAuth: true } // 标记需要登录
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { title: '登录' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 🚀 核心逻辑：全局前置守卫
router.beforeEach((to, from, next) => {
  // 1. 设置标题
  document.title = (to.meta.title as string) || '智慧校园禁烟监控系统'

  // 2. 获取 Token
  const token = localStorage.getItem('token')

  // 3. 判断逻辑
  if (to.path === '/login') {
    // 如果已登录还想去登录页 -> 踢回首页 (可选，看你需要)
    if (token) {
      next('/') 
    } else {
      next() // 没登录去登录页 -> 放行
    }
  } else {
    // 如果去的不是登录页
    if (token) {
      next() // 有 Token -> 放行
    } else {
      next('/login') // ❌ 没有 Token -> 强制跳转登录页
    }
  }
})

export default router