package org.example.webback.controller;

import jakarta.servlet.http.HttpServletRequest;
import org.example.webback.common.Result;
import org.example.webback.dto.AiChatRequest;
import org.example.webback.dto.AiChatResponse;
import org.example.webback.dto.ChatMessageDto;
import org.example.webback.entity.AiConversation;
import org.example.webback.service.AiChatService;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;

@RestController
@RequestMapping("/api/ai/conversations")
public class AiChatController {

    private final AiChatService aiChatService;

    public AiChatController(AiChatService aiChatService) {
        this.aiChatService = aiChatService;
    }

//    // 💡 模拟当前登录用户，方便联调测试。测试完记得替换为真实鉴权逻辑！
//    private Long getCurrentUserId() {
//        return 1L;
//    }
// 🚀 替换为真实的获取用户 ID 逻辑
    private Long getCurrentUserId() {
        // 从 Spring 上下文中获取当前的 HTTP 请求对象
        ServletRequestAttributes attributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        if (attributes != null) {
            HttpServletRequest request = attributes.getRequest();
            // 获取 JwtInterceptor 拦截器里塞进去的 uid
            Object uid = request.getAttribute("uid");
            if (uid != null) {
                return Long.valueOf(uid.toString());
            }
        }
        // 理论上如果 JwtInterceptor 正常工作，不会走到这里。走到这里说明没有经过拦截器或未登录。
        throw new RuntimeException("未能获取到当前登录用户信息，请重新登录");
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
     * 核心：AI 流式对话接口
     */
    @PostMapping(value = "/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter chatStream(@RequestBody AiChatRequest request) {
        return aiChatService.chatStream(getCurrentUserId(), request);
    }

    /**
     * 4. 删除历史对话
     */
    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable String id) {
        aiChatService.deleteConversation(id, getCurrentUserId());
        return Result.success();
    }

    @GetMapping("/{id}/messages")
    public Result<List<ChatMessageDto>> getMessages(@PathVariable String id) {
        return Result.success(aiChatService.getHistoryMessages(id, getCurrentUserId()));
    }
}
