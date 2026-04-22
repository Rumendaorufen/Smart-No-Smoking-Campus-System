package org.example.webback.dto;

import lombok.Data;

@Data
public class AiChatResponse {
    // 返回给前端的 AI 回答文本
    private String answer;
}
