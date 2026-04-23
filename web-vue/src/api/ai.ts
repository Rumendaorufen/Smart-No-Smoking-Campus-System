// src/api/ai.ts
import request from '../utils/request'; // 替换为你项目实际的 axios 封装路径

// 定义返回体结构 (对应后端的 Result 类)
export interface Result<T> {
  code: number;
  msg: string;
  data: T;
}

// 定义会话实体
export interface AiConversation {
  id: string;
  userId: number;
  title: string;
  createdAt?: string;
}

// 1. 获取会话列表
export function getConversationList() {
  return request.get<any, Result<AiConversation[]>>('/api/ai/conversations');
}

// 2. 新建会话
export function createConversation() {
  return request.post<any, Result<AiConversation>>('/api/ai/conversations');
}

// 3. 删除会话
export function deleteConversation(id: string) {
  return request.delete<any, Result<void>>(`/api/ai/conversations/${id}`);
}

// 4. 发送消息
export function sendChatMessage(data: { conversationId: string; message: string }) {
  return request.post<any, Result<{ answer: string }>>(
    '/api/ai/conversations/chat', 
    data, 
    { 
      timeout: 120000 // 🚀 专门为这个 AI 接口设置 60 秒的超长等待时间！
    }
  );
}