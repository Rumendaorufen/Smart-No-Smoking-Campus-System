package org.example.webback.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "notification.feishu")
public class FeishuConfig {
    private String webhookUrl;
    private String appId;
    private String appSecret;
    private boolean enabled = true;
}
