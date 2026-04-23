<template>
  <div class="ai-chat-container">
    <div class="sidebar">
      <div class="sidebar-header">
        <el-button type="primary" class="new-chat-btn" @click="handleCreateChat">
          <el-icon><Plus /></el-icon> 新建对话
        </el-button>
      </div>
      
      <el-scrollbar class="conversation-list">
        <div 
          v-for="item in conversationList" 
          :key="item.id"
          :class="['conversation-item', { active: currentConversationId === item.id }]"
          @click="selectConversation(item.id)"
        >
          <span class="title">{{ item.title || '新对话' }}</span>
          <el-button 
            link 
            type="danger" 
            :icon="Delete" 
            @click.stop="handleDeleteChat(item.id)" 
          />
        </div>
      </el-scrollbar>
    </div>

    <div class="chat-main">
      <template v-if="currentConversationId">
        <el-scrollbar class="message-area" ref="scrollbarRef">
          <div class="message-list">
            <div 
              v-for="(msg, index) in messageList" 
              :key="index"
              :class="['message-item', msg.role]"
            >
              <div class="avatar">
                {{ msg.role === 'user' ? '我' : 'AI' }}
              </div>
              
              <div class="bubble" :class="{ 'error-bubble': msg.isError }">
                <template v-if="msg.role === 'user'">
                  {{ msg.content }}
                </template>
                
                <!-- <template v-else>
                  <div class="markdown-body" v-html="md.render(formatMarkdown(msg.content))"></div>
                </template> -->
                
                <template v-else>
                  <div v-if="msg.isThinking" class="thinking-status">
                    <span class="loading-dots">⏳</span> 
                    AI 正在深度分析中... 
                    <span class="time-count">已耗时 {{ msg.thinkTime }} 秒</span>
                  </div>
                  
                  <div class="markdown-body" v-html="md.render(formatMarkdown(msg.content))"></div>
                </template>

                <div v-if="msg.isError" class="retry-action">
                  <el-button 
                    type="danger" 
                    link 
                    size="small" 
                    @click="retryMessage(msg.originalText)"
                  >
                    <el-icon><RefreshRight /></el-icon> 重新发送
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </el-scrollbar>

        <div class="input-area">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="3"
            placeholder="输入您的问题，比如：今天有几个报警？ (按 Enter 发送)"
            resize="none"
            :disabled="isTyping"
            @keydown.enter.prevent="() => handleSendMessage()"
          />
          <div class="action-bar">
            <el-button type="primary" :loading="isTyping" @click="() => handleSendMessage()">
              发送
            </el-button>
          </div>
        </div>
      </template>
      
      <div v-else class="empty-state">
        <el-empty description="请选择或新建一个对话开始分析" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, onBeforeUnmount } from 'vue';
import { Plus, Delete, RefreshRight } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import MarkdownIt from 'markdown-it';
import { 
  getConversationList, 
  createConversation, 
  getConversationMessages,
  deleteConversation, 
  type AiConversation 
} from '../api/ai'; 

// --- Markdown 配置 ---
const md = new MarkdownIt({ html: true, breaks: true, linkify: true });

// 🚀 核心：修复 Markdown 表格渲染，确保表格前有空行
const formatMarkdown = (content: string) => {
  if (!content) return '';
  
  // 1. 还原后端传来的换行符
  let text = content.replace(/<<br>>/g, '\n');
  
  // 2. 仅在“上一行不是换行也不是表格线”的情况下，给表格首行加上前置空行
  // 这样既能保证表格独立，又不会切断表格内部的行
  text = text.replace(/([^\n|])\n\|/g, '$1\n\n|');
  
  return text;
};
// --- 状态定义 ---
const conversationList = ref<AiConversation[]>([]);
const currentConversationId = ref<string>('');
const inputText = ref('');
const isTyping = ref(false);
const scrollbarRef = ref<any>(null);

// --- 计时器状态 ---
const waitSeconds = ref(0);
let timerInterval: ReturnType<typeof setInterval> | null = null;

// 开启计时器，并动态更新对应气泡的文本
const startWaitingTimer = (aiIdx: number) => {
  waitSeconds.value = 0;
  timerInterval = setInterval(() => {
    waitSeconds.value++;
    // 动态更新气泡内容，显示已等待的秒数
    if (messageList.value[aiIdx]) {
      messageList.value[aiIdx].content = `> ⏳ *AI 正在连接数据分析引擎，已等待 ${waitSeconds.value} 秒...*`;
    }
  }, 1000);
};

// 停止计时器
const stopWaitingTimer = () => {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
};

interface ChatMessage {
  role: 'user' | 'ai';
  content: string;
  isError?: boolean;
  originalText?: string;
  isThinking?: boolean; // 🚀 新增：是否正在思考
  thinkTime?: number;   // 🚀 新增：思考耗时
}
const messageList = ref<ChatMessage[]>([]);

// --- 逻辑实现 ---

// 初始化加载会话列表
const fetchConversations = async () => {
  try {
    const res = await getConversationList();
    if (res.code === 200) {
      conversationList.value = res.data;
    }
  } catch (error) {
    ElMessage.error('加载会话列表失败');
  }
};

// 新建对话
const handleCreateChat = async () => {
  try {
    const res = await createConversation();
    if (res.code === 200) {
      conversationList.value.unshift(res.data);
      selectConversation(res.data.id);
    }
  } catch (error) {
    ElMessage.error('新建对话失败');
  }
};

// 选择对话并加载历史记录
const selectConversation = async (id: string) => {
  if (currentConversationId.value === id && messageList.value.length > 0) return;
  
  currentConversationId.value = id;
  messageList.value = []; 
  
  try {
    const res = await getConversationMessages(id);
    if (res.code === 200 && res.data) {
      messageList.value = res.data;
      scrollToBottom();
    }
  } catch (error) {
    ElMessage.error('加载历史聊天记录失败');
  }
};

// 删除对话
const handleDeleteChat = (id: string) => {
  ElMessageBox.confirm('确定要删除这个对话吗？', '提示', { type: 'warning' })
    .then(async () => {
      const res = await deleteConversation(id);
      if (res.code === 200) {
        ElMessage.success('删除成功');
        if (currentConversationId.value === id) {
          currentConversationId.value = '';
          messageList.value = [];
        }
        fetchConversations();
      }
    }).catch(() => {});
};

// 🚀 核心：流式发送消息逻辑
const handleSendMessage = async (retryText?: string) => {
  const text = retryText || inputText.value;
  const trimmedText = text.trim();
  
  if (!trimmedText || isTyping.value) return;

  // 1. 用户消息上屏
  if (!retryText) {
    messageList.value.push({ role: 'user', content: trimmedText });
  }
  inputText.value = '';
  isTyping.value = true;
  scrollToBottom();

  // 2. 预埋 AI 气泡，并初始化思考状态
  const aiIdx = messageList.value.push({ 
    role: 'ai', 
    content: '',
    isThinking: true, // 标记正在思考
    thinkTime: 0      // 初始化耗时
  }) - 1;

  // 🚀 启动计时器：每秒更新一次当前消息的 thinkTime
  let timerInterval = setInterval(() => {
    if (messageList.value[aiIdx]) {
      messageList.value[aiIdx].thinkTime++;
    }
  }, 1000);

  // 定义停止计时的内部函数
  const stopTimer = () => {
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
    if (messageList.value[aiIdx]) {
      messageList.value[aiIdx].isThinking = false;
    }
  };

  try {
    const JAVA_BASE = import.meta.env.VITE_APP_BASE_API || 'http://localhost:8080';
    
    const response = await fetch(`${JAVA_BASE}/api/ai/conversations/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
      },
      body: JSON.stringify({
        conversationId: currentConversationId.value,
        message: trimmedText
      })
    });

    if (!response.ok) throw new Error(`服务器异常: ${response.status}`);
    if (!response.body) throw new Error('浏览器不支持流式传输');

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let done = false;
    let buffer = ''; 

    while (!done) {
      const { value, done: readerDone } = await reader.read();
      done = readerDone;

      if (value) {
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';
        
        for (const event of events) {
          const lines = event.split('\n');
          for (const line of lines) {
            if (line.startsWith('data:')) {
              let content = line.replace(/^data:\s?/, '').replace(/<<br>>/g, '\n').replace(/<<sp>>/g, ' ');
              
              // 🚀 关键改进：停止计时的判断逻辑
              // 如果内容不为空，且不包含“分析中”相关的标记（即 AI 开始说人话了）
              if (content.trim() !== '' && !content.includes('正在分析')) {
                stopTimer(); 
              }
              
              messageList.value[aiIdx]!.content += content;
              scrollToBottom();
            }
          }
        }
      }
    }

    fetchConversations();

  } catch (error: any) {
    console.error('流式通讯失败:', error);
    stopTimer(); // 报错也要停止
    messageList.value[aiIdx]!.isError = true;
    messageList.value[aiIdx]!.content = '网络连接异常或服务器处理超时 🔌';
    messageList.value[aiIdx]!.originalText = trimmedText;
  } finally {
    stopTimer(); // 确保万无一失
    isTyping.value = false;
    scrollToBottom();
  }
};

const retryMessage = (text?: string) => {
  if (text) handleSendMessage(text);
};

const scrollToBottom = async () => {
  await nextTick();
  if (scrollbarRef.value) {
    scrollbarRef.value.setScrollTop(99999);
  }
};

onMounted(() => {
  fetchConversations();
});
onBeforeUnmount(() => {
  stopWaitingTimer();
});
</script>

<style scoped>
/* ==================================================
    🚀 1. 基础布局与侧边栏 (保持科技感)
   ================================================== */
.ai-chat-container {
  display: flex;
  height: 100%;
  background-color: transparent;
  color: #e4e7ed;
}

.sidebar {
  width: 240px;
  background-color: rgba(22, 33, 52, 0.4);
  border-right: 1px solid rgba(64, 158, 255, 0.1);
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
}

.new-chat-btn {
  width: 100%;
}

.conversation-item {
  padding: 12px 16px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #a3a6ad;
  border-left: 3px solid transparent;
  transition: all 0.2s;
}

.conversation-item:hover {
  background-color: rgba(64, 158, 255, 0.08);
}

.conversation-item.active {
  background: linear-gradient(90deg, rgba(64, 158, 255, 0.15) 0%, transparent 100%);
  color: #409eff;
  border-left: 3px solid #409eff;
}

.title {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ==================================================
    🚀 2. 聊天区域与气泡 (优化对齐与间距)
   ================================================== */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.message-area {
  flex: 1;
  padding: 20px;
}

.message-item {
  display: flex;
  margin-bottom: 24px;
  align-items: flex-start; /* 确保头像和气泡顶端对齐 */
}

.message-item.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 12px;
  font-size: 14px;
  flex-shrink: 0;
}

.message-item.user .avatar {
  background-color: rgba(64, 158, 255, 0.15);
  color: #409eff;
  border-color: rgba(64, 158, 255, 0.4);
}

.bubble {
  max-width: 75%;
  padding: 12px 16px;
  border-radius: 8px;
  background-color: rgba(22, 33, 52, 0.8);
  border: 1px solid rgba(64, 158, 255, 0.2);
  color: #e4e7ed;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  line-height: 1.6;
}

.message-item.user .bubble {
  background-color: rgba(64, 158, 255, 0.15);
  border-color: rgba(64, 158, 255, 0.4);
}

.bubble.error-bubble {
  background-color: rgba(245, 108, 108, 0.1);
  color: #f56c6c;
  border-color: rgba(245, 108, 108, 0.3);
}

/* ==================================================
    🚀 3. Markdown 内容渲染 (核心深度修复)
   ================================================== */
:deep(.markdown-body) {
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}

/* 段落间距 */
:deep(.markdown-body p) {
  margin: 0 0 12px 0;
  white-space: pre-wrap;
}

:deep(.markdown-body p:last-child) {
  margin-bottom: 0;
}

/* 强调色 */
:deep(.markdown-body strong) {
  color: #409eff;
  font-weight: 600;
}

/* 列表修复：确保圆点显示且有缩进 */
:deep(.markdown-body ul),
:deep(.markdown-body ol) {
  padding-left: 2em !important;
  margin: 12px 0 !important;
}

:deep(.markdown-body ul) {
  list-style-type: disc !important;
}

:deep(.markdown-body ol) {
  list-style-type: decimal !important;
}

:deep(.markdown-body li) {
  display: list-item !important;
  margin-bottom: 6px;
}

/* 表格修复：深色科技感边框 */
:deep(.markdown-body table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  background-color: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(64, 158, 255, 0.2);
  border-radius: 4px;
  overflow: hidden;
}

:deep(.markdown-body th) {
  background-color: rgba(64, 158, 255, 0.15);
  color: #409eff;
  font-weight: 600;
  padding: 10px 14px;
  border: 1px solid rgba(64, 158, 255, 0.1);
  text-align: left;
}

:deep(.markdown-body td) {
  padding: 8px 14px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  color: #e4e7ed;
}

/* ==================================================
    🚀 4. 输入区域 (解决变白问题)
   ================================================== */
.input-area {
  padding: 16px;
  background-color: rgba(22, 33, 52, 0.6);
  border-top: 1px solid rgba(64, 158, 255, 0.1);
  backdrop-filter: blur(10px);
}

:deep(.el-textarea__inner) {
  background-color: rgba(0, 0, 0, 0.3) !important;
  border: 1px solid rgba(64, 158, 255, 0.2) !important;
  color: #e4e7ed !important;
  box-shadow: none !important;
}

/* 🚀 核心：解决禁用状态（正在思考时）背景变白的问题 */
:deep(.el-textarea.is-disabled .el-textarea__inner) {
  background-color: rgba(0, 0, 0, 0.3) !important;
  border-color: rgba(64, 158, 255, 0.1) !important;
  color: #606266 !important;
  cursor: not-allowed;
}

.action-bar {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}

/* 状态展示 */
.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.retry-action {
  margin-top: 8px;
  border-top: 1px solid rgba(245, 108, 108, 0.2);
  padding-top: 8px;
}

/* 🚀 思考计时器样式 */
.thinking-status {
  display: flex;
  align-items: center;
  font-size: 13px;
  color: #409eff;
  background-color: rgba(64, 158, 255, 0.1);
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 10px;
  border: 1px dashed rgba(64, 158, 255, 0.3);
  animation: pulse 2s infinite;
}

.thinking-status .loading-dots {
  margin-right: 8px;
  animation: rotate 2s linear infinite;
}

.thinking-status .time-count {
  margin-left: auto;
  font-family: monospace;
  font-weight: bold;
  color: #e6a23c;
  background: rgba(230, 162, 60, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(64, 158, 255, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(64, 158, 255, 0); }
  100% { box-shadow: 0 0 0 0 rgba(64, 158, 255, 0); }
}

@keyframes rotate {
  100% { transform: rotate(360deg); }
}
</style>