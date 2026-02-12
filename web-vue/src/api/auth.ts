import request from '../utils/request'

export interface ApiResponse<T = any> {
  code: number
  msg: string
  data: T
}

export interface LoginData {
  username: string;
  password: string;
}

export interface UserInfo {
  id: number;
  username: string;
  role: string;
  status: number;
  lastLoginTime?: string; // ✅ 驼峰
  lastLoginIp?: string;    // ✅ 驼峰
}

export interface LoginResult {
  token: string;
  userInfo: UserInfo;
}

export default {
  login(data: LoginData) {
    return request({
      url: '/api/auth/login', // ✅ 补齐 /api
      method: 'post',
      data
    })
  },

  logout() {
    return request({
      url: '/api/auth/logout', // ✅ 补齐 /api
      method: 'post'
    })
  },

  getUserInfo() {
    return request({
      url: '/api/auth/me', // ✅ 补齐 /api
      method: 'get'
    })
  }
}