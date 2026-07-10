# 飞书告警通知设计文档

> 文档状态：历史设计/实施记录。本文保留当时的目标、步骤和代码片段，不代表当前运行基线。
> 当前行为请以仓库根目录 `README.md`、现行配置模板和源代码为准；文中的端口、路径、性能指标或配置文件可能已随实现演进。


> 在告警记录产生时，通过飞书自定义应用发送消息卡片到群聊

## 1. 需求

| 项目 | 决定 |
|------|------|
| 触发时机 | 新告警产生时（仅创建，不含审核变更） |
| 消息格式 | 飞书消息卡片（interactive） |
| 卡片内容 | 设备名称 + 告警类型 + 置信度 + 时间 + 内嵌截图 |
| 接入方式 | 飞书开放平台自定义应用 + Webhook 发送 |
| 公网访问 | ngrok 隧道暴露本地 8080 端口 |

## 2. 整体架构

```
Python AI 引擎
  │  POST /api/alerts/report  {snapshotUrl, deviceId, type, confidence}
  ▼
AlarmController → AlarmService.saveInternalAlarm()
                          │
                          ├── 1. 保存告警到 MySQL (@Transactional)
                          │
                          └── 2. afterCommit() → CompletableFuture.runAsync()
                                │
                                └── FeishuNotificationService.notifyAlarm()
                                      │
                                      ├─ FeishuTokenService.getToken()
                                      │    → POST /open-apis/auth/v3/tenant_access_token/internal
                                      │    → 缓存 tenant_access_token（2h，提前 60s 刷新）
                                      │
                                      ├─ FeishuImageService.uploadImage(snapshotUrl)
                                      │    → 下载截图（ngrok URL 或本地）
                                      │    → POST /open-apis/im/v1/images (multipart, Bearer token)
                                      │    → 返回 image_key
                                      │
                                      └─ POST webhook-url (interactive card)
                                           → 卡片引用 image_key 内嵌显示
```

## 3. 文件清单

### 新增文件

| 文件 | 职责 |
|------|------|
| `config/FeishuConfig.java` | `@ConfigurationProperties` 飞书配置属性注入 |
| `service/FeishuTokenService.java` | Tenant Access Token 获取与缓存 |
| `service/FeishuImageService.java` | 截图下载 → 飞书上传 → 返回 image_key |
| `service/FeishuNotificationService.java` | 编排流程 + 构建卡片 + Webhook 发送 |

### 修改文件

| 文件 | 改动 |
|------|------|
| `application.yml` | 添加 `notification.feishu.*`、`app.public-base-url` |
| `WebMvcConfig.java` | `addResourceHandlers()` 暴露 Python 静态目录 |
| `AlarmService.java` | `saveInternalAlarm()` 末尾注册 `afterCommit` 异步通知 |

## 4. 配置

### application.yml

```yaml
notification:
  feishu:
    enabled: true
    webhook-url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxx"
    app-id: "cli_xxxxxxxxxxxxxx"
    app-secret: "xxxxxxxxxxxxxxxxxxxxxxxx"

app:
  public-base-url: "https://xxxx.ngrok.io"
  python-static-path: D:/engineering/Smart No-Smoking Campus System/web-flask/app
```

### FeishuConfig.java

```java
@ConfigurationProperties(prefix = "notification.feishu")
@Data
@Component
public class FeishuConfig {
    private String webhookUrl;
    private String appId;
    private String appSecret;
    private boolean enabled = true;
}
```

## 5. 组件详细设计

### 5.1 FeishuTokenService

获取 `tenant_access_token`，内部自动缓存，2 小时过期前 60s 刷新。

- **接口**: `POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`
- **请求体**: `{ "app_id": "...", "app_secret": "..." }`
- **响应**: `{ "code": 0, "tenant_access_token": "...", "expire": 7200 }`
- **缓存策略**: 内存缓存 `cachedToken` + `tokenExpireTime`，每次调用 `getToken()` 自动判断

### 5.2 FeishuImageService

将公网可访问的截图上传到飞书，获取 `image_key`。

- **接口**: `POST https://open.feishu.cn/open-apis/im/v1/images`
- **请求头**: `Authorization: Bearer {token}`, `Content-Type: multipart/form-data`
- **参数**: `image_type=message`, `image=@alarm.jpg`
- **响应**: `{ "code": 0, "data": { "image_key": "img_xxxxx" } }`
- **失败处理**: 抛异常，由调用方捕获降级

### 5.3 FeishuNotificationService

编排通知流程。

```java
public void notifyAlarm(Alarm alarm, String deviceName)
```

**流程**:
1. 检查 `enabled` 开关
2. `resolveSnapshotUrl()` 处理截图 URL（相对路径拼接公网地址）
3. 调用 `FeishuImageService.uploadImage()` 上传截图 → 获取 `image_key`
4. 上传失败：日志 warn，降级为无图卡片
5. 构建飞书卡片 JSON（header: red + 各字段 + img 元素）
6. POST 到 `webhook-url`

**绝不向上抛异常**：所有异常内部消化，不影响告警入库主流程。

### 5.4 飞书卡片模板

```json
{
  "msg_type": "interactive",
  "card": {
    "header": {
      "title": { "tag": "plain_text", "content": "🚨 吸烟告警" },
      "template": "red"
    },
    "elements": [
      {
        "tag": "div",
        "fields": [
          { "is_short": true, "text": { "tag": "lark_md", "content": "**摄像头**\n3号楼东侧走廊" } },
          { "is_short": true, "text": { "tag": "lark_md", "content": "**告警类型**\nSMOKING" } },
          { "is_short": true, "text": { "tag": "lark_md", "content": "**置信度**\n92.5%" } },
          { "is_short": true, "text": { "tag": "lark_md", "content": "**时间**\n2026-07-09 14:32:18" } }
        ]
      },
      {
        "tag": "img",
        "img_key": "img_xxxxx",
        "alt": { "tag": "plain_text", "content": "告警截图" }
      }
    ]
  }
}
```

### 5.5 AlarmService 集成

在 `saveInternalAlarm()` 末尾，事务提交后异步触发通知：

```java
TransactionSynchronizationManager.registerSynchronization(
    new TransactionSynchronization() {
        @Override public void afterCommit() {
            String deviceName = deviceService.getById(deviceId).getName();
            CompletableFuture.runAsync(() ->
                feishuNotificationService.notifyAlarm(alarm, deviceName));
        }
    });
```

## 6. 静态资源映射

在 WebMvcConfig 添加：

```java
@Override
public void addResourceHandlers(ResourceHandlerRegistry registry) {
    registry.addResourceHandler("/static/**")
            .addResourceLocations("file:" + pythonStaticPath + "/");
}
```

配合 ngrok `https://xxxx.ngrok.io/static/**` 可公网访问截图。
JWT/Security 层已有 `/static/**` 放行，无需重复配置。

## 7. 错误处理策略

| 场景 | 处理方式 |
|------|----------|
| 飞书 Token 获取失败 | 日志 warn，跳过本次通知，下次调用自动重试 |
| 截图上传飞书失败 | 日志 warn，降级发送无图卡片 |
| Webhook 发送失败 | 日志 error，不重试 |
| 飞书配置关闭 | 直接 return，零开销 |
| snpshotUrl 为空 | 跳过上传步骤，发送无图卡片 |

所有异常在 `FeishuNotificationService` 内部消化，绝不抛出。

## 8. 飞书开放平台配置步骤

1. 打开 [飞书开放平台](https://open.feishu.cn) → 创建企业自建应用
2. 应用名称：`校园吸烟告警通知`
3. 权限管理 → 添加权限：
   - `im:image`（上传图片）
4. 发布应用 → 管理员审核通过
5. 凭证与基础信息 → 获取 `App ID` 和 `App Secret`
6. 群聊 → 设置 → 群机器人 → 添加机器人 → 选择刚创建的应用
7. 群机器人 → 复制 Webhook URL

## 9. 后续可扩展方向

- 审核状态变更时也通知（如确认/误报）
- 按告警类型/摄像头分组聚合，避免告警风暴
- 增加 @责任人 提醒
- 添加"一键审核"交互按钮
