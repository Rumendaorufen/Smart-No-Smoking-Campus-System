package org.example.webback.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@Data
@TableName("ai_chat_history")
public class AiChatHistory {
    private Integer id;
    private String sessionId; // 对应 conversationId
    private String message;   // LangChain 存的 JSON 字符串
}