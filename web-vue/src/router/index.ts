import { createRouter, createWebHistory } from 'vue-router'
// 引入你的页面组件
// 注意：请确保这些文件在 views 目录下存在，如果你的文件名不一样，请修改这里
import Login from '../views/Login.vue'
import Monitor from '../views/Monitor.vue' // 你的监控大屏页面

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { title: '登录 - 智慧校园禁烟监控系统' }
  },
  {
    path: '/',
    name: 'Monitor',
    component: Monitor,
    meta: { title: '实时监控' }
  }
]

const router = createRouter({
  // 使用 HTML5 History 模式 (URL 不带 # 号)
  history: createWebHistory(),
  routes
})

// 🚀 全局路由守卫：核心安全逻辑
router.beforeEach((to, from, next) => {
  // 1. 设置网页标题
  document.title = (to.meta.title as string) || '智慧校园禁烟监控系统'

  // 2. 获取 Token
  const token = localStorage.getItem('token')

  // 3. 鉴权逻辑
  if (to.path !== '/login' && !token) {
    // 如果要去非登录页，且没有 Token -> 强制跳转到登录页
    next('/login')
  } else if (to.path === '/login' && token) {
    // 如果已登录还想去登录页 -> 强制跳回首页
    next('/')
  } else {
    // 放行
    next()
  }
})

export default router