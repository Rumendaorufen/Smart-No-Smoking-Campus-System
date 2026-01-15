import request from '../utils/request'
// ✅ 关键修改：加上 'type' 关键字
import type { ApiResponse } from './auth'

export default {
  // 获取用户列表
  getUsers: () => {
    return request<any, ApiResponse<any[]>>({
      url: '/users/', 
      method: 'get'
    })
  },

  // 添加用户
  addUser: (data: any) => {
    return request<any, ApiResponse<any>>({
      url: '/users/',
      method: 'post',
      data
    })
  },

  // ✅ 新增：更新用户
  updateUser: (userId: number, data: any) => {
    return request<any, ApiResponse<any>>({
      url: `/users/${userId}`,
      method: 'put',
      data
    })
  },

  // 删除用户
  deleteUser: (userId: number) => {
    return request<any, ApiResponse<any>>({
      url: `/users/${userId}`,
      method: 'delete'
    })
  }
}