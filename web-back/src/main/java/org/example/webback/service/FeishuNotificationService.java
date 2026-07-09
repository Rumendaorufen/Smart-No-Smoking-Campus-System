package org.example.webback.service;

import org.example.webback.config.FeishuConfig;
import org.example.webback.entity.Alarm;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.http.ResponseEntity;
import org.springframework.web.client.RestTemplate;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Service
public class FeishuNotificationService {

    private static final Logger log = LoggerFactory.getLogger(FeishuNotificationService.class);

    @Autowired
    private FeishuConfig feishuConfig;
    @Autowired
    private FeishuImageService feishuImageService;
    @Autowired
    private RestTemplate restTemplate;

    @Value("${app.public-base-url}")
    private String publicBaseUrl;

    @jakarta.annotation.PostConstruct
    public void init() {
        log.info("飞书通知服务已加载, enabled={}, webhookUrl={}", feishuConfig.isEnabled(), feishuConfig.getWebhookUrl());
    }

    public void notifyAlarm(Alarm alarm, String deviceName) {
        if (!feishuConfig.isEnabled()) {
            log.debug("飞书通知已禁用");
            return;
        }

        String imageKey = null;
        try {
            String snapshotUrl = resolveSnapshotUrl(alarm.getRoiUrl());
            if (snapshotUrl != null) {
                imageKey = feishuImageService.uploadImage(snapshotUrl);
            }
        } catch (Exception e) {
            log.warn("截图处理失败，将发送无图卡片: {}", e.getMessage());
        }

        try {
            Map<String, Object> card = buildCard(alarm, deviceName, imageKey);
            Map<String, Object> body = new HashMap<>();
            body.put("msg_type", "interactive");
            body.put("card", card);

            // 飞书签名校验（如果配置了 signSecret）
            addSignature(body);

            ResponseEntity<String> response = restTemplate.postForEntity(
                    feishuConfig.getWebhookUrl(), body, String.class);
            log.info("飞书 Webhook 响应: status={}, body={}", response.getStatusCode(), response.getBody());
            if (response.getBody() != null && !response.getBody().contains("\"code\":0")) {
                log.error("飞书 Webhook 返回错误: {}", response.getBody());
            } else {
                log.info("飞书告警通知已发送, alarmId={}, device={}", alarm.getId(), deviceName);
            }
        } catch (Exception e) {
            log.error("飞书 Webhook 发送失败: {}", e.getMessage());
        }
    }

    private String resolveSnapshotUrl(String roiUrl) {
        if (roiUrl == null || roiUrl.isBlank()) return null;
        if (roiUrl.startsWith("http://") || roiUrl.startsWith("https://")) {
            return roiUrl;
        }
        String path = roiUrl.startsWith("/") ? roiUrl.substring(1) : roiUrl;
        return publicBaseUrl + "/" + path;
    }

    private Map<String, Object> buildCard(Alarm alarm, String deviceName, String imageKey) {
        List<Map<String, Object>> elements = new ArrayList<>();

        Map<String, Object> div = new HashMap<>();
        div.put("tag", "div");
        div.put("fields", Arrays.asList(
                field("**摄像头**\n" + (deviceName != null ? deviceName : "未知")),
                field("**告警类型**\n" + (alarm.getType() != null ? alarm.getType() : "未知")),
                field("**置信度**\n" + String.format("%.1f%%", alarm.getConfidence() != null ? alarm.getConfidence() * 100 : 0)),
                field("**时间**\n" + (alarm.getCreatedAt() != null ?
                        alarm.getCreatedAt().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")) : "未知"))
        ));
        elements.add(div);

        if (imageKey != null) {
            Map<String, Object> img = new HashMap<>();
            img.put("tag", "img");
            img.put("img_key", imageKey);
            Map<String, Object> alt = new HashMap<>();
            alt.put("tag", "plain_text");
            alt.put("content", "告警截图");
            img.put("alt", alt);
            elements.add(img);
        }

        Map<String, Object> header = new HashMap<>();
        Map<String, Object> title = new HashMap<>();
        title.put("tag", "plain_text");
        title.put("content", "🚨 吸烟告警");
        header.put("title", title);
        header.put("template", "red");

        Map<String, Object> card = new HashMap<>();
        card.put("header", header);
        card.put("elements", elements);

        return card;
    }

    private Map<String, Object> field(String content) {
        Map<String, Object> text = new HashMap<>();
        text.put("tag", "lark_md");
        text.put("content", content);

        Map<String, Object> field = new HashMap<>();
        field.put("is_short", true);
        field.put("text", text);
        return field;
    }

    private void addSignature(Map<String, Object> body) {
        String secret = feishuConfig.getSignSecret();
        if (secret == null || secret.isBlank()) return;

        try {
            long timestamp = System.currentTimeMillis() / 1000;
            String stringToSign = timestamp + "\n" + secret;

            Mac mac = Mac.getInstance("HmacSHA256");
            SecretKeySpec keySpec = new SecretKeySpec(
                    stringToSign.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
            mac.init(keySpec);
            byte[] signBytes = mac.doFinal(new byte[0]);
            String sign = Base64.getEncoder().encodeToString(signBytes);

            body.put("timestamp", String.valueOf(timestamp));
            body.put("sign", sign);
        } catch (NoSuchAlgorithmException | InvalidKeyException e) {
            log.warn("飞书签名计算失败: {}", e.getMessage());
        }
    }
}
