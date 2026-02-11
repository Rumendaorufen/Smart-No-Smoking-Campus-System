package org.example.webback.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        // 注册端点，前端连接地址: ws://localhost:8080/ws
        registry.addEndpoint("/ws")
                .setAllowedOriginPatterns("*") // 允许跨域
                .withSockJS(); // 开启 SockJS 支持
    }

    @Override
    public void configureMessageBroker(MessageBrokerRegistry registry) {
        // 客户端订阅路径前缀，例如: /topic/alarm
        registry.enableSimpleBroker("/topic");
        // 客户端发送消息前缀 (本项目暂时用不到，主要是服务端推给客户端)
        registry.setApplicationDestinationPrefixes("/app");
    }
}