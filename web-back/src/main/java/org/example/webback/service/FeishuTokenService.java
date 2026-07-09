package org.example.webback.service;

import org.example.webback.config.FeishuConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Map;

@Service
public class FeishuTokenService {

    private static final Logger log = LoggerFactory.getLogger(FeishuTokenService.class);
    private static final String TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal";

    @Autowired
    private FeishuConfig feishuConfig;
    @Autowired
    private RestTemplate restTemplate;

    private String cachedToken;
    private Instant tokenExpireTime;

    public String getToken() {
        if (cachedToken != null && Instant.now().isBefore(tokenExpireTime)) {
            return cachedToken;
        }
        return refreshToken();
    }

    private synchronized String refreshToken() {
        if (cachedToken != null && Instant.now().isBefore(tokenExpireTime)) {
            return cachedToken;
        }

        try {
            Map<String, String> body = Map.of(
                    "app_id", feishuConfig.getAppId(),
                    "app_secret", feishuConfig.getAppSecret()
            );
            Map result = restTemplate.postForObject(TOKEN_URL, body, Map.class);
            if (result == null || result.get("tenant_access_token") == null) {
                throw new RuntimeException("飞书 Token 响应异常: " + result);
            }

            cachedToken = (String) result.get("tenant_access_token");
            int expire = (int) result.get("expire");
            tokenExpireTime = Instant.now().plus(expire - 60, ChronoUnit.SECONDS);
            log.info("飞书 Token 刷新成功，有效期 {} 秒", expire);
            return cachedToken;
        } catch (Exception e) {
            log.warn("飞书 Token 获取失败: {}", e.getMessage());
            throw e;
        }
    }
}
