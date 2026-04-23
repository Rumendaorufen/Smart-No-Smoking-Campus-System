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
                {{ msg.content }}
                
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
            
            <div v-if="isTyping" class="message-item ai">
              <div class="avatar">AI</div>
              <div class="bubble typing">正在思考中...</div>
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
import { ref, onMounted, nextTick } from 'vue';
// 🚀 修改点 3：引入 RefreshRight 图标
import { Plus, Delete, RefreshRight } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { 
  getConversationList, 
  createConversation, 
  getConversationMessages,
  deleteConversation, 
  sendChatMessage,
  type AiConversation
} from '../api/ai'; 

// --- 状态定义 ---
const conversationList = ref<AiConversation[]>([]);
const currentConversationId = ref<string>('');
const inputText = ref('');
const isTyping = ref(false);
const scrollbarRef = ref<any>(null);

// 🚀 修改点 4：增强前端消息结构
interface ChatMessage {
  role: 'user' | 'ai';
  content: string;
  isError?: boolean;      // 标记是否为报错气泡
  originalText?: string;  // 报错时存下用户的提问
}
const messageList = ref<ChatMessage[]>([]);

// --- 方法实现 ---

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

// 选择某一个对话
// 选择某一个对话
const selectConversation = async (id: string) => {
  // 如果点击的是当前已经在看的对话，不重复加载
  if (currentConversationId.value === id) return;
  
  currentConversationId.value = id;
  // 先清空屏幕，显示空白态或加载中状态
  messageList.value = []; 
  
  try {
    // 🚀 去后端拉取该对话的真实历史记录！
    const res = await getConversationMessages(id);
    if (res.code === 200 && res.data) {
      // 将历史记录直接赋值给屏幕渲染
      messageList.value = res.data;
      // 滚动到底部查看最新消息
      scrollToBottom();
    }
  } catch (error) {
    ElMessage.error('加载历史聊天记录失败');
  }
};

// 删除对话
const handleDeleteChat = (id: string) => {
  ElMessageBox.confirm('确定要删除这个对话吗？历史记录将无法恢复。', '提示', {
    type: 'warning'
  }).then(async () => {
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

// 🚀 修改点 5：支持重试与异常捕获的发送逻辑
const handleSendMessage = async (retryText?: string) => {
  // 如果传了重试文本就用重试的，否则读取输入框的值
  const text = retryText || inputText.value;
  const trimmedText = text.trim();
  
  if (!trimmedText || isTyping.value) return;

  // 1. 将用户问题上屏并清空输入框 (重试时不重复上屏)
  if (!retryText) {
    messageList.value.push({ role: 'user', content: trimmedText });
  }
  inputText.value = '';
  isTyping.value = true;
  scrollToBottom();

  // 2. 调用后端接口
  try {
    const res = await sendChatMessage({
      conversationId: currentConversationId.value,
      message: trimmedText
    });
    
    if (res.code === 200) {
      messageList.value.push({ role: 'ai', content: res.data.answer });
    } else {
      // 后端业务拦截报错
      messageList.value.push({ 
        role: 'ai', 
        content: `抱歉，服务出现异常：${res.msg}`,
        isError: true,
        originalText: trimmedText
      });
    }
  } catch (error: any) {
    // 捕获前端 Axios 超时或网络异常
    const isTimeout = error.message && error.message.toLowerCase().includes('timeout');
    const friendlyMsg = isTimeout 
      ? '抱歉，当前查询的数据量较大，我思考得太久大脑短路了 🤯。请稍后再试，或者尝试缩小查询的时间范围。' 
      : '抱歉，网络似乎开小差了，无法连接到 AI 分析引擎 🔌。';

    messageList.value.push({ 
      role: 'ai', 
      content: friendlyMsg, 
      isError: true, 
      originalText: trimmedText 
    });
  } finally {
    isTyping.value = false;
    scrollToBottom();
  }
};

// 一键重试逻辑
const retryMessage = (text?: string) => {
  if (text) {
    handleSendMessage(text);
  }
};

// 自动滚动到最新消息
const scrollToBottom = async () => {
  await nextTick();
  if (scrollbarRef.value) {
    scrollbarRef.value.setScrollTop(99999);
  }
};

// --- 生命周期 ---
onMounted(() => {
  fetchConversations();
});
</script>

<style scoped>
/* 根容器：去掉白色，改为透明以继承抽屉的暗黑底色 */
.ai-chat-container {
  display: flex;
  height: 100%; 
  border: none;
  overflow: hidden;
  background-color: transparent;
  color: #e4e7ed;
}

/* 左侧边栏：采用与大屏 Panel 相同的半透明背景 */
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

/* 历史会话列表：科技风 Hover 与 Active 效果 */
.conversation-item {
  padding: 12px 16px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s;
  color: #a3a6ad;
  border-left: 3px solid transparent;
}

.conversation-item:hover {
  background-color: rgba(64, 158, 255, 0.08);
  color: #e4e7ed;
}

.conversation-item.active {
  background: linear-gradient(90deg, rgba(64,158,255,0.15) 0%, transparent 100%);
  color: #409eff;
  border-left: 3px solid #409eff;
}

.title {
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 聊天主体区域 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: transparent;
}

.message-area {
  flex: 1;
  padding: 20px;
}

.message-item {
  display: flex;
  margin-bottom: 20px;
}

.message-item.user {
  flex-direction: row-reverse;
}

/* 头像配色适配 */
.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #a3a6ad;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 12px;
  font-size: 14px;
}

.message-item.user .avatar {
  background-color: rgba(64, 158, 255, 0.15);
  color: #409eff;
  border-color: rgba(64, 158, 255, 0.4);
}

/* 气泡配色：使用科技蓝边框和暗色背景 */
.bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 8px;
  background-color: rgba(22, 33, 52, 0.8);
  border: 1px solid rgba(64, 158, 255, 0.2);
  line-height: 1.5;
  word-break: break-all;
  color: #e4e7ed;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}

/* 用户气泡的高亮效果 */
.message-item.user .bubble {
  background-color: rgba(64, 158, 255, 0.15);
  border-color: rgba(64, 158, 255, 0.4);
  color: #fff;
}

/* 错误状态的气泡暗黑适配 */
.bubble.error-bubble {
  background-color: rgba(245, 108, 108, 0.1);
  color: #f56c6c;
  border: 1px solid rgba(245, 108, 108, 0.3);
}

.retry-action {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed rgba(245, 108, 108, 0.3);
  text-align: right;
}

/* 底部输入框区域：毛玻璃效果 */
.input-area {
  padding: 16px;
  background-color: rgba(22, 33, 52, 0.6);
  border-top: 1px solid rgba(64, 158, 255, 0.1);
  backdrop-filter: blur(10px);
}

/* 🚀 核心：深度覆盖 Element Plus 的默认白底 Input */
:deep(.el-textarea__inner) {
  background-color: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(64, 158, 255, 0.2);
  color: #e4e7ed;
  box-shadow: none;
}

:deep(.el-textarea__inner:focus) {
  border-color: #409eff;
  box-shadow: inset 0 0 5px rgba(64, 158, 255, 0.2);
}

:deep(.el-textarea__inner::placeholder) {
  color: #606266;
}

:deep(.el-input__count) {
  background: transparent;
  color: #909399;
}

.action-bar {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}

/* 空状态的文字颜色适配 */
.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

:deep(.el-empty__description p) {
  color: #606266;
}

/* 美化滚动条 */
:deep(.el-scrollbar__bar.is-vertical > div) {
  background-color: rgba(64, 158, 255, 0.3);
}
</style>