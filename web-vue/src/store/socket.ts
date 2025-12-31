// WebSocket 全局状态
import { defineStore } from 'pinia'
import { io } from 'socket.io-client'

export const useSocketStore = defineStore('socket', {
  state: () => ({
    socket: null as any
  }),
  actions: {
    init() {
      // WebSocket 初始化逻辑
    }
  }
})
