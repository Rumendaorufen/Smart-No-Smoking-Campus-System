package org.example.webback.dto;

import lombok.Data;

@Data
public class AiChatRequest {
    // 用户输入的提问，比如："今天有几个报警？"
    private String message;

    // 当前对话的唯一标识 UUID
    private String conversationId;
}