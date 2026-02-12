import request from '../utils/request'

// 定义报警记录的数据结构 (适配 Java 驼峰)
export interface Alarm {
  id: number
  deviceId: number     // ✅ 驼峰
  deviceName: string   // ✅ 驼峰
  type: string
  confidence: number
  videoUrl: string     // ✅ 驼峰
  roiUrl: string       // ✅ 驼峰
  auditStatus: number  // ✅ 适配 Java: auditStatus
  statusText: string   // ✅ 驼峰
  createdAt: string    // ✅ 驼峰
  auditorName?: string // ✅ 驼峰
  auditTime?: string   // ✅ 驼峰
  auditRemark?: string // ✅ 驼峰
}

// 1. 获取待审核列表
export const getPendingAlerts = (params: { page: number; pageSize: number }) => {
  return request.get('/api/alerts/pending', { params }) // ✅ 补齐 /api
}

// 2. 提交审核结果
export const submitAudit = (id: number, data: { status: number; remark?: string }) => {
  return request.post(`/api/alerts/${id}/audit`, data) // ✅ 补齐 /api
}

// 3. 获取历史归档
export const getArchive = (params: any) => {
  return request.get('/api/alerts/archive', { params }) // ✅ 补齐 /api
}

// 4. 删除记录
export const deleteAlarm = (id: number) => {
  return request.delete(`/api/alerts/${id}`) // ✅ 补齐 /api
}