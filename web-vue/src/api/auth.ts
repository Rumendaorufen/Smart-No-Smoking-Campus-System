// 引入封装好的 axios 实例
// 如果你的编辑器报错找不到模块，请确保 src/utils/request.ts 存在
// 也可以尝试改为 import request from '../utils/request'
import request from '../utils/request'
export interface ApiResponse<T = any> {
  code: number
  msg: string
  data: T
}

// 定义登录参数接口
export interface LoginData {
  username: string;
  password: string;
}

// 定义用户信息接口
export interface UserInfo {
  id: number;
  username: string;
  real_name?: string;
  role: string;
  status: number;
  avatar?: string;
  last_login_time?: string;
  last_login_ip?: string;
}

// 定义登录响应结构 (根据后端返回的 data 结构)
export interface LoginResult {
  token: string;
  userInfo: UserInfo;
}

export default {
  /**
   * 用户登录
   * @param data {username, password}
   */
  login(data: LoginData) {
    return request({
      url: '/auth/login', // 对应后端路由 /api/v1/auth/login
      method: 'post',
      data
    })
  },

  /**
   * 退出登录
   */
  logout() {
    return request({
      url: '/auth/logout',
      method: 'post'
    })
  },

  /**
   * 获取当前用户信息
   * (用于页面刷新后，通过 Token 重新拉取用户信息)
   */
  getUserInfo() {
    return request({
      url: '/auth/me',
      method: 'get'
    })
  }
}