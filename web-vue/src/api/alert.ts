// src/api/alert.ts
import request from '../utils/request'

// 定义报警记录的数据结构 (对应后端的 to_dict)
export interface Alarm {
  id: number
  device_id: number
  device_name: string
  type: string
  confidence: number
  video_url: string
  roi_url: string // 特写图
  status: number // 0:待审, 1:确认, 2:误报
  status_text: string
  created_at: string
  auditor_name?: string
  audit_time?: string
  audit_remark?: string
}

export interface AlarmListResponse {
  list: Alarm[]
  total: number
  pages: number
  current_page: number
}

// 1. 获取待审核列表
export const getPendingAlerts = (params: { page: number; page_size: number }) => {
  return request.get('/alerts/pending', { params })
}

// 2. 提交审核结果
export const submitAudit = (id: number, data: { status: number; remark?: string }) => {
  return request.post(`/alerts/${id}/audit`, data)
}

// 3. 获取历史归档
export const getArchive = (params: any) => {
  return request.get('/alerts/archive', { params })
}

// 4. 删除记录
export const deleteAlarm = (id: number) => {
  return request.delete(`/alerts/${id}`)
}