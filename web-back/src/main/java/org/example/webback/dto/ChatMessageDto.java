package org.example.webback.dto;

import lombok.Data;

@Data
public class ChatMessageDto {
    private String role;    // "user" 或 "ai"
    private String content; // 具体的聊天内容
}