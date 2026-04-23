package org.example.webback.service;

import cn.hutool.core.util.IdUtil;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.webback.dto.AiChatRequest;
import org.example.webback.dto.ChatMessageDto;
import org.example.webback.entity.AiChatHistory;
import org.example.webback.entity.AiConversation;
import org.example.webback.mapper.AiChatHistoryMapper;
import org.example.webback.mapper.AiConversationMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor // Lombok 注解，自动注入 final 修饰的 Bean
public class AiChatServiceImpl implements AiChatService {

    private final AiConversationMapper conversationMapper;
    private final RestTemplate restTemplate; // 用于发 HTTP 请求给 Python
    private final AiChatHistoryMapper chatHistoryMapper;

    // 从 application.yml 读取 Python 服务的地址
    // 稍后我们需要在 yml 里配置： ai.agent.url: http://127.0.0.1:5050/api/agent/chat
    @Value("${ai.agent.url}")
    private String pythonAgentUrl;

    @Override
    public AiConversation createConversation(Long userId) {
        AiConversation conversation = new AiConversation();
        // 🚀 使用 Hutool 生成无横线的简洁 UUID
        conversation.setId(IdUtil.simpleUUID());
        conversation.setUserId(userId);
        conversation.setTitle("新对话");

        conversationMapper.insert(conversation);
        return conversation;
    }

    @Override
    public List<AiConversation> getListByUserId(Long userId) {
        // 🚀 使用 MyBatis-Plus 的 Lambda 查询，按更新时间倒序排列
        return conversationMapper.selectList(
                new LambdaQueryWrapper<AiConversation>()
                        .eq(AiConversation::getUserId, userId)
                        .orderByDesc(AiConversation::getUpdatedAt)
        );
    }

    @Override
    public String chatWithAgent(Long userId, AiChatRequest request) {
        // 1. 安全校验：确认这个 conversationId 是否合法且属于当前用户
        AiConversation conversation = conversationMapper.selectById(request.getConversationId());
        if (conversation == null || !conversation.getUserId().equals(userId)) {
            throw new RuntimeException("非法操作：该对话不存在或无权访问");
        }

        // 🚀 新增逻辑：首轮对话自动生成标题
        // 判断如果当前标题还是默认的 "新对话"，说明这是这批对话的第一条消息
        if ("新对话".equals(conversation.getTitle())) {
            String firstMessage = request.getMessage().trim();
            // 截取用户提问的前 15 个字符作为标题（如果超长就加省略号，防止侧边栏撑爆）
            String newTitle = firstMessage.length() > 15 ? firstMessage.substring(0, 15) + "..." : firstMessage;

            conversation.setTitle(newTitle);
            // 将新标题更新到数据库中
            conversationMapper.updateById(conversation);
        }
        
        // 2. 构造发给 Python 的 JSON 载荷
        Map<String, Object> payload = new HashMap<>();
        payload.put("message", request.getMessage());
        payload.put("conversationId", request.getConversationId());

        try {
            log.info("正在将请求转发给 Python Agent: {}", payload);
            // 3. 发起 POST 请求
            Map<String, Object> response = restTemplate.postForObject(pythonAgentUrl, payload, Map.class);

            // 4. 解析 Python 端的返回结果
            if (response != null && Integer.valueOf(200).equals(response.get("code"))) {
                Map<String, Object> data = (Map<String, Object>) response.get("data");
                return (String) data.get("answer");
            } else {
                log.error("Python AI 引擎返回错误: {}", response);
                throw new RuntimeException("AI 服务异常，请稍后再试");
            }
        } catch (Exception e) {
            log.error("调用 Python AI 引擎失败", e);
            throw new RuntimeException("无法连接到 AI 分析引擎，请检查服务状态");
        }
    }

    @Override
    public void deleteConversation(String conversationId, Long userId) {
        // 1. 安全校验
        AiConversation conversation = conversationMapper.selectById(conversationId);
        if (conversation == null || !conversation.getUserId().equals(userId)) {
            throw new RuntimeException("非法操作：无权删除该对话");
        }

        // 2. 逻辑删除会话记录
        conversationMapper.deleteById(conversationId);

        // 💡 进阶提示：如果有 ai_chat_history 的 Mapper，你可以在这里顺便把底层的历史记录也删掉
         chatHistoryMapper.delete(new LambdaQueryWrapper<AiChatHistory>().eq(AiChatHistory::getSessionId, conversationId));
    }

    @Override
    public List<ChatMessageDto> getHistoryMessages(String conversationId, Long userId) {
        // 1. 安全校验：确认对话属于当前用户
        AiConversation conversation = conversationMapper.selectById(conversationId);
        if (conversation == null || !conversation.getUserId().equals(userId)) {
            throw new RuntimeException("非法操作：无权访问该对话");
        }

        // 2. 按时间顺序查询该对话的所有聊天记录
        List<AiChatHistory> rawHistories = chatHistoryMapper.selectList(
                new LambdaQueryWrapper<AiChatHistory>()
                        .eq(AiChatHistory::getSessionId, conversationId)
                        .orderByAsc(AiChatHistory::getId)
        );

        // 3. 解析 LangChain 存入的 JSON
        List<ChatMessageDto> resultList = new ArrayList<>();
        for (AiChatHistory history : rawHistories) {
            try {
                // LangChain 的格式类似: {"type": "human", "data": {"content": "今天有几个报警"}}
                JSONObject jsonObj = JSONUtil.parseObj(history.getMessage());
                String type = jsonObj.getStr("type");
                String content = jsonObj.getJSONObject("data").getStr("content");

                ChatMessageDto dto = new ChatMessageDto();
                dto.setRole("human".equals(type) ? "user" : "ai");
                dto.setContent(content);
                resultList.add(dto);
            } catch (Exception e) {
                log.error("解析聊天记录JSON失败, id: {}", history.getId(), e);
            }
        }
        return resultList;
    }
}