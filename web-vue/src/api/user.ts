import request from '../utils/request'
import type { ApiResponse } from './auth'

export default {
  // 获取用户列表
  getUsers: () => {
    return request<any, ApiResponse<any[]>>({
      url: '/api/users', // ✅ 补齐 /api 并去掉末尾 /
      method: 'get'
    })
  },

  // 添加用户
  addUser: (data: any) => {
    return request<any, ApiResponse<any>>({
      url: '/api/users', // ✅ 补齐 /api
      method: 'post',
      data
    })
  },

  // 更新用户
  updateUser: (userId: number, data: any) => {
    return request<any, ApiResponse<any>>({
      url: `/api/users/${userId}`, // ✅ 补齐 /api
      method: 'put',
      data
    })
  },

  // 删除用户
  deleteUser: (userId: number) => {
    return request<any, ApiResponse<any>>({
      url: `/api/users/${userId}`, // ✅ 补齐 /api
      method: 'delete'
    })
  }
}