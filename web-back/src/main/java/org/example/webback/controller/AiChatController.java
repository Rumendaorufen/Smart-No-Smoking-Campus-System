package org.example.webback.controller;

import org.example.webback.common.Result;
import org.example.webback.dto.AiChatRequest;
import org.example.webback.dto.AiChatResponse;
import org.example.webback.entity.AiConversation;
import org.example.webback.service.AiChatService;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/ai/conversations")
public class AiChatController {

    private final AiChatService aiChatService;

    public AiChatController(AiChatService aiChatService) {
        this.aiChatService = aiChatService;
    }

    // 💡 模拟当前登录用户，方便联调测试。测试完记得替换为真实鉴权逻辑！
    private Long getCurrentUserId() {
        return 1L;
    }

    /**
     * 1. 获取当前用户的对话列表 (用于渲染左侧侧边栏)
     */
    @GetMapping
    public Result<List<AiConversation>> getList() {
        return Result.success(aiChatService.getListByUserId(getCurrentUserId()));
    }

    /**
     * 2. 新建对话 (点击“新建对话”按钮时调用)
     */
    @PostMapping
    public Result<AiConversation> create() {
        return Result.success(aiChatService.createConversation(getCurrentUserId()));
    }

    /**
     * 3. 发送聊天消息 (核心对话接口)
     */
    @PostMapping("/chat")
    public Result<AiChatResponse> chat(@RequestBody AiChatRequest request) {
        // 校验参数
        if (request.getConversationId() == null || request.getMessage() == null) {
            return Result.error("conversationId 和 message 不能为空");
        }

        String answer = aiChatService.chatWithAgent(getCurrentUserId(), request);

        AiChatResponse response = new AiChatResponse();
        response.setAnswer(answer);
        return Result.success(response);
    }

    /**
     * 4. 删除历史对话
     */
    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable String id) {
        aiChatService.deleteConversation(id, getCurrentUserId());
        return Result.success();
    }
}
