package org.example.webback.service;

import org.example.webback.dto.AiChatRequest;
import org.example.webback.dto.ChatMessageDto;
import org.example.webback.entity.AiConversation;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;

public interface AiChatService {

    // 1. 新建对话 (生成 UUID 并保存)
    AiConversation createConversation(Long userId);

    // 2. 获取当前用户的对话列表
    List<AiConversation> getListByUserId(Long userId);

    // 3. 发送消息并调用 Python AI 引擎
    String chatWithAgent(Long userId, AiChatRequest request);

    // 4. 删除历史对话
    void deleteConversation(String conversationId, Long userId);

    // 获取指定对话的聊天历史记录
    List<ChatMessageDto> getHistoryMessages(String conversationId, Long userId);

    // 🚀 新增：流式对话接口
    SseEmitter chatStream(Long userId, AiChatRequest request);
}