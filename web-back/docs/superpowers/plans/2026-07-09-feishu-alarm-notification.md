# 飞书告警通知实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在告警记录产生时，通过飞书自定义应用发送消息卡片到群聊，包括截图内嵌显示

**Architecture:** AlarmService.saveInternalAlarm() 在事务提交后，通过 CompletableFuture 异步调用 FeishuNotificationService；该服务编排 Token 获取、截图上传、卡片构建和 Webhook 发送三步流程，所有异常内部消化不影响主流程

**Tech Stack:** Spring Boot 3.0.2, RestTemplate, Feishu Open API, ngrok

---

## File Structure

### 新增文件（4个）

| # | 文件 | 职责 |
|---|------|------|
| 1 | `config/FeishuConfig.java` | `@ConfigurationProperties` 注入飞书配置 |
| 2 | `service/FeishuTokenService.java` | 获取并缓存 tenant_access_token |
| 3 | `service/FeishuImageService.java` | 下载截图 → 飞书上传 → 返回 image_key |
| 4 | `service/FeishuNotificationService.java` | 编排通知流程，构建卡片 JSON |

### 修改文件（3个）

| # | 文件 | 改动 |
|---|------|------|
| 5 | `application.yml` | 添加 notification.feishu.* 和 app.public-base-url |
| 6 | `config/WebMvcConfig.java` | 添加 addResourceHandlers 映射 Python 静态目录到 /static/** |
| 7 | `service/AlarmService.java` | saveInternalAlarm() 末尾异步触发飞书通知 |

---

### Task 1: FeishuConfig 配置属性类

**Files:**
- Create: `src/main/java/org/example/webback/config/FeishuConfig.java`

- [ ] **Step 1: Create FeishuConfig.java**

```java
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
```

- [ ] **Step 2: Commit**

```bash
git add src/main/java/org/example/webback/config/FeishuConfig.java
git commit -m "feat: add FeishuConfig configuration properties class"
```

---

### Task 2: application.yml 添加飞书和公网配置

**Files:**
- Modify: `src/main/resources/application.yml`

- [ ] **Step 1: 在 application.yml 末尾添加配置**

```yaml
# 5. 飞书通知配置
notification:
  feishu:
    enabled: true
    webhook-url: "https://open.feishu.cn/open-apis/bot/v2/hook/your_webhook_url"
    app-id: "cli_your_app_id"
    app-secret: "your_app_secret"

# 6. ngrok 公网地址（用于拼接截图 URL）
app:
  public-base-url: "https://your_ngrok_url.ngrok.io"
  python-static-path: D:/engineering/Smart No-Smoking Campus System/web-flask/app
```

注意：将 `app.public-base-url` 放在 `app.python-static-path` 上方，保持 `app` 前缀下的配置集中。

- [ ] **Step 2: Commit**

```bash
git add src/main/resources/application.yml
git commit -m "feat: add feishu and public-base-url config to application.yml"
```

---

### Task 3: FeishuTokenService — Token 获取与缓存

**Files:**
- Create: `src/main/java/org/example/webback/service/FeishuTokenService.java`

- [ ] **Step 1: Create FeishuTokenService.java**

```java
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
        // 双重检查：可能在等待锁期间已被其他线程刷新
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
            int expire = (int) result.get("expire"); // 单位秒，通常 7200
            tokenExpireTime = Instant.now().plus(expire - 60, ChronoUnit.SECONDS);
            log.info("飞书 Token 刷新成功，有效期 {} 秒", expire);
            return cachedToken;
        } catch (Exception e) {
            log.warn("飞书 Token 获取失败: {}", e.getMessage());
            throw e; // 由调用方处理
        }
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add src/main/java/org/example/webback/service/FeishuTokenService.java
git commit -m "feat: add FeishuTokenService with caching and auto-refresh"
```

---

### Task 4: FeishuImageService — 截图上传

**Files:**
- Create: `src/main/java/org/example/webback/service/FeishuImageService.java`

- [ ] **Step 1: Create FeishuImageService.java**

```java
package org.example.webback.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

@Service
public class FeishuImageService {

    private static final Logger log = LoggerFactory.getLogger(FeishuImageService.class);
    private static final String UPLOAD_URL = "https://open.feishu.cn/open-apis/im/v1/images";

    @Autowired
    private FeishuTokenService tokenService;
    @Autowired
    private RestTemplate restTemplate;

    /**
     * 从公网 URL 下载截图并上传到飞书
     * @return image_key，失败返回 null
     */
    public String uploadImage(String imageUrl) {
        if (imageUrl == null || imageUrl.isBlank()) return null;

        try {
            String token = tokenService.getToken();

            // 1. 下载截图
            ResponseEntity<byte[]> downloadResp = restTemplate.exchange(
                    imageUrl, HttpMethod.GET, null, byte[].class);
            byte[] imageBytes = downloadResp.getBody();
            if (imageBytes == null || imageBytes.length == 0) {
                log.warn("截图下载为空: {}", imageUrl);
                return null;
            }

            // 2. 构建 multipart 请求上传飞书
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.MULTIPART_FORM_DATA);
            headers.setBearerAuth(token);

            ByteArrayResource imageResource = new ByteArrayResource(imageBytes) {
                @Override
                public String getFilename() {
                    return "alarm_snapshot.jpg";
                }
            };

            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            body.add("image_type", "message");
            body.add("image", imageResource);

            HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

            ResponseEntity<Map> response = restTemplate.exchange(
                    UPLOAD_URL, HttpMethod.POST, requestEntity, Map.class);

            Map responseBody = response.getBody();
            if (responseBody != null && responseBody.get("data") instanceof Map) {
                Map data = (Map) responseBody.get("data");
                String imageKey = (String) data.get("image_key");
                log.debug("截图上传飞书成功, image_key: {}", imageKey);
                return imageKey;
            }

            log.warn("飞书图片上传响应异常: {}", responseBody);
            return null;
        } catch (Exception e) {
            log.warn("截图上传飞书失败: {}", e.getMessage());
            return null;
        }
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add src/main/java/org/example/webback/service/FeishuImageService.java
git commit -m "feat: add FeishuImageService for snapshot upload"
```

---

### Task 5: FeishuNotificationService — 通知编排与卡片发送

**Files:**
- Create: `src/main/java/org/example/webback/service/FeishuNotificationService.java`

- [ ] **Step 1: Create FeishuNotificationService.java**

```java
package org.example.webback.service;

import org.example.webback.config.FeishuConfig;
import org.example.webback.entity.Alarm;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

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

            restTemplate.postForEntity(feishuConfig.getWebhookUrl(), body, String.class);
            log.info("飞书告警通知已发送, alarmId={}, device={}", alarm.getId(), deviceName);
        } catch (Exception e) {
            log.error("飞书 Webhook 发送失败: {}", e.getMessage());
        }
    }

    private String resolveSnapshotUrl(String roiUrl) {
        if (roiUrl == null || roiUrl.isBlank()) return null;
        if (roiUrl.startsWith("http://") || roiUrl.startsWith("https://")) {
            return roiUrl;
        }
        // 相对路径，拼接公网地址
        String path = roiUrl.startsWith("/") ? roiUrl.substring(1) : roiUrl;
        return publicBaseUrl + "/" + path;
    }

    private Map<String, Object> buildCard(Alarm alarm, String deviceName, String imageKey) {
        List<Map<String, Object>> elements = new ArrayList<>();

        // 信息字段（两列布局）
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

        // 内嵌截图
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

        // 头部
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
}
```

- [ ] **Step 2: Commit**

```bash
git add src/main/java/org/example/webback/service/FeishuNotificationService.java
git commit -m "feat: add FeishuNotificationService with card builder and webhook sender"
```

---

### Task 6: WebMvcConfig 添加静态资源映射

**Files:**
- Modify: `src/main/java/org/example/webback/config/WebMvcConfig.java`

- [ ] **Step 1: 在 WebMvcConfig 中添加 resourceHandler 映射**

当前文件内容：
```java
@Configuration
public class WebMvcConfig implements WebMvcConfigurer {
    @Configuration
    public class RestConfig {
        @Bean
        public RestTemplate restTemplate() {
            // ... 保持不变
        }
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        // ... 保持不变
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        // ... 保持不变
    }
}
```

需要做的改动：
1. 添加 `import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;`
2. 添加 `@Value("${app.python-static-path}")` 注入
3. 添加 `addResourceHandlers()` 方法

修改后的文件关键变更：

在 `implements WebMvcConfigurer` 类中添加字段和方法：

```java
@Value("${app.python-static-path}")
private String pythonStaticPath;

@Override
public void addResourceHandlers(ResourceHandlerRegistry registry) {
    registry.addResourceHandler("/static/**")
            .addResourceLocations("file:" + pythonStaticPath + "/");
}
```

最终文件完整内容：

```java
package org.example.webback.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.ClientHttpRequestInterceptor;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.util.Collections;

@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    @Value("${app.python-static-path}")
    private String pythonStaticPath;

    @Configuration
    public class RestConfig {
        @Bean
        public RestTemplate restTemplate() {
            RestTemplate rest = new RestTemplate();
            rest.setInterceptors(Collections.singletonList(
                (ClientHttpRequestInterceptor) (request, body, execution) -> {
                    String traceId = org.slf4j.MDC.get("trace_id");
                    if (traceId != null) {
                        request.getHeaders().add("X-Trace-Id", traceId);
                    }
                    return execution.execute(request, body);
                }
            ));
            return rest;
        }
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOriginPatterns("*")
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("*")
                .allowCredentials(true)
                .maxAge(3600);
    }

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        registry.addResourceHandler("/static/**")
                .addResourceLocations("file:" + pythonStaticPath + "/");
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new JwtInterceptor())
                .addPathPatterns("/api/**")
                .excludePathPatterns(
                        "/api/auth/login",
                        "/api/internal/**",
                        "/api/monitor/stream/**",
                        "/api/internal/**",
                        "/api/monitor/devices/sync-status",
                        "/api/alerts/report",
                        "/api/logs/**"
                );
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add src/main/java/org/example/webback/config/WebMvcConfig.java
git commit -m "feat: add static resource handler for Python static directory"
```

---

### Task 7: AlarmService 集成飞书通知

**Files:**
- Modify: `src/main/java/org/example/webback/service/AlarmService.java`

- [ ] **Step 1: 注入 FeishuNotificationService 和 DeviceService**

在 `AlarmService` 类中添加字段：

```java
@Autowired
private FeishuNotificationService feishuNotificationService;
@Autowired
private DeviceService deviceService;
```

当前已注入的字段：
```java
@Autowired
private DeviceMapper deviceMapper;
@Autowired
private UserMapper userMapper;
```

- [ ] **Step 2: 添加所需的 import**

```java
import org.example.webback.service.FeishuNotificationService;
import org.example.webback.service.DeviceService;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
```

- [ ] **Step 3: 修改 saveInternalAlarm 方法**

在 `this.save(alarm);` 之后添加事务提交后异步通知：

```java
@Transactional(rollbackFor = Exception.class)
public void saveInternalAlarm(Integer deviceId, String type, Double confidence,
                              String snapshotUrl, String videoUrl) {
    Alarm alarm = new Alarm();

    alarm.setCameraId(deviceId);
    alarm.setType(type);
    alarm.setConfidence((double) confidence.floatValue());
    alarm.setRoiUrl(snapshotUrl);
    alarm.setVideoUrl(videoUrl);

    alarm.setAuditStatus(0);
    alarm.setCreatedAt(LocalDateTime.now());

    this.save(alarm);

    // 🚀 事务提交后异步发送飞书通知
    TransactionSynchronizationManager.registerSynchronization(
        new TransactionSynchronization() {
            @Override
            public void afterCommit() {
                String deviceName = "未知";
                try {
                    Device device = deviceService.getById(deviceId);
                    if (device != null) {
                        deviceName = device.getName();
                    }
                } catch (Exception e) {
                    log.warn("获取设备名称失败: {}", e.getMessage());
                }

                final String name = deviceName;
                CompletableFuture.runAsync(() ->
                    feishuNotificationService.notifyAlarm(alarm, name));
            }
        });
}
```

注意：需要添加 `import org.example.webback.entity.Device;` 和 `import java.util.concurrent.CompletableFuture;`

- [ ] **Step 4: 检查 AlarmService.java 的完整 import 列表**

```java
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.example.webback.entity.Alarm;
import org.example.webback.entity.Device;
import org.example.webback.mapper.AlarmMapper;
import org.example.webback.mapper.DeviceMapper;
import org.example.webback.mapper.UserMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.io.File;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.stream.Collectors;
```

注意：需要添加 `private static final Logger log = LoggerFactory.getLogger(AlarmService.class);`（如果还没有 logger 字段的话）。

- [ ] **Step 5: Commit**

```bash
git add src/main/java/org/example/webback/service/AlarmService.java
git commit -m "feat: integrate feishu notification into AlarmService saveInternalAlarm"
```

---

### Task 8: 验证编译

**Files:** None

- [ ] **Step 1: Maven 编译检查**

```bash
cd /d/engineering/Smart\ No-Smoking\ Campus\ System/web-back
mvn compile -q
```

预期输出：`BUILD SUCCESS`，无错误

- [ ] **Step 2: 检查文件清单**

确认以下文件全部就位：

```
src/main/java/org/example/webback/config/FeishuConfig.java      ✅ 新增
src/main/java/org/example/webback/service/FeishuTokenService.java   ✅ 新增
src/main/java/org/example/webback/service/FeishuImageService.java   ✅ 新增
src/main/java/org/example/webback/service/FeishuNotificationService.java ✅ 新增
src/main/resources/application.yml                             ✅ 修改
src/main/java/org/example/webback/config/WebMvcConfig.java      ✅ 修改
src/main/java/org/example/webback/service/AlarmService.java     ✅ 修改
```

---

### 飞书开放平台配置（手动步骤，非代码）

1. 打开 https://open.feishu.cn → 创建企业自建应用
2. 应用名称：`校园吸烟告警通知`
3. 权限管理 → 添加权限：`im:image`
4. 发布应用 → 管理员审核
5. 凭证与基础信息 → 记录 App ID 和 App Secret
6. 群聊设置 → 群机器人 → 添加机器人 → 选择刚创建的应用
7. 群机器人 → 复制 Webhook URL
8. 填入 application.yml 对应字段
