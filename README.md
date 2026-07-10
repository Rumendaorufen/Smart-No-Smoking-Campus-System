# 智慧校园禁烟监控系统

> 基于 AI 视觉分析 + 大模型数据问答的实时吸烟行为监测平台 | 秒级报警 | 证据回溯 | 四服务协同架构

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Java](https://img.shields.io/badge/Java-17-orange.svg)
![Spring Boot](https://img.shields.io/badge/Spring_Boot-3.0.2-green.svg)
![Vue](https://img.shields.io/badge/Vue-3.x-4FC08D.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-ee4c2c.svg)
![YOLOv8](https://img.shields.io/badge/YOLO-v8-yellow.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.3-1c3c3c.svg)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 目录

- [项目简介](#项目简介)
- [系统架构](#系统架构)
- [功能特性](#功能特性)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [API 概览](#api-概览)
- [开发日志索引](#开发日志索引)
- [开源协议](#开源协议)

## 项目简介

智慧校园禁烟监控系统是一套完整的 AI 视觉监测与数据分析平台。系统通过 **四服务协同架构**（Python AI 引擎 + Java 业务中台 + LangChain 智能问答 + Vue3 前端大屏），实现对校园 RTSP 监控视频流的实时吸烟行为识别、报警推送、人工仲裁以及自然语言数据分析。

**当前实现能力**：

- 采用**级联 ROI 检测 + Batch 批处理 + FP16 半精度**；`200+` 路是扩容设计目标，当前提交没有对应的可复现压测结论
- **弹性跳帧**：常态约 2 FPS 推理；爆发令牌会取消 0.5 秒跳帧限制，但 reader 当前约 5 FPS，因此并非 25 FPS 输入
- **两阶段置信度**：0.40 进入候选/触发 + 0.60 单帧确认或跨帧累计确认
- 引入**大模型 SQL Agent**，用自然语言直接查询报警数据，无需编写 SQL
- Java 中台统一鉴权与业务编排，Python 专注于 AI 推理，职责清晰

## 系统架构

```mermaid
graph TD
    %% 节点定义
    Vue["Vue 3 前端大屏 (port 5173)<br>Monitor / Audit / Archive / Chat"]
    Spring["Java Spring Boot 中台 (port 8080)<br>鉴权 / CRUD / WebSocket / SSE代理"]
    
    AIEngine["Python AI 引擎 (port 5000)<br>YOLOv8 + Flask"]
    DB[("MySQL 8.0 (port 3308)")]
    AIAgent["Python AI Agent (port 5050)<br>LangChain + LLM"]
    
    Camera["IP 摄像头 x N"]

    %% 连线关系
    Vue -- "HTTP / SockJS / STOMP" --> Spring
    
    Spring --> AIEngine
    Spring --> DB
    Spring --> AIAgent
    
    AIEngine -- "RTSP" --> Camera
```

### 服务职责

| 服务 | 端口 | 技术栈 | 核心职责 |
|------|------|--------|----------|
| **web-vue** | 5173 | Vue 3 + Element Plus + Pinia + ECharts | 监控网格大屏、报警仲裁、设备管理、AI 对话、缩略图网格 |
| **web-back** | 8080 | Spring Boot 3 + MyBatis-Plus + WebSocket + STOMP | 鉴权、业务 CRUD、SSE 代理、设备状态同步、WebSocket 增量推送、批量心跳接收 |
| **web-flask** | 5000 | Flask + YOLOv8 + OpenCV | RTSP 拉流(grab/retrieve)、弹性跳帧推理、爆发令牌桶、两阶段置信度、证据录制(RAM→SSD)、缩略图接口、自动重连巡检 |
| **web-agent** | 5050 | Flask + LangChain + SQLDatabaseToolkit | 自然语言→SQL→数据分析报告（流式 SSE） |

### AI 推理管线（web-flask）

```
RTSP 流 → grab/retrieve (5 FPS) → 全局单例检测器
                                          │
                        ┌─────────────────┘
                        ▼
             弹性跳帧 (常态约 2 FPS / 爆发上限受 5 FPS reader 限制)
                        │
                        ▼
             Stage 1: YOLOv8s 全局找人 (ByteTrack)
                        │
                        ▼
             裁切人物上半身 ROI + 30% Padding
                        │
                        ▼
             Batch 打包 → Stage 2: best.pt 找烟 (FP16, conf≥0.40)
                        │
                        ▼
             两阶段置信度 + 爆发令牌桶 (最多 3 路同时爆发)
                        │
                        ▼
             跨帧累计确认 (3次检出 / 1.5s) → 报警
                        │
                        ▼
             快照(R:\→SSD) + 视频(5s, mp4v→H264) → Java
```

## 功能特性

### 实时监控
- 多路 RTSP 视频流并发处理（grab/retrieve，5 FPS）
- 网格模式（缩略图 JPG 定时刷新 + jitter 打散并发） + 详情模式（单路 MJPEG）
- 弹性跳帧：常态约 2 FPS；爆发令牌取消处理器跳帧，但当前 reader 约 5 FPS（最多 3 路同时持有令牌）
- 设备在线/离线状态实时检测，自动重连巡检（每 30s）
- WebSocket 实时推送报警弹窗 + 设备状态增量推送

### AI 吸烟检测
- 双模型级联检测（YOLOv8s 找人 + best.pt 找烟，候选 conf≥0.40）
- ByteTrack 人员追踪，支持移动吸烟去重（动态冷却圈）
- 两阶段置信度：单帧 ≥0.60 立即确认 / 同一人持续检出 3 次确认
- GPU FP16 半精度加速，batch ROI 推理，惯性平滑防闪烁

### 证据链管理
- 报警确认即无条件保存快照 + 录像（5 秒 H.264）
- ImDisk 内存盘（R:\) 中转：临时文件纯内存操作，确诊后才迁移到 SSD
- 3 层 IO 保护：Semaphore(2) 并发限流 + RAM 盘中转 + Below Normal 进程优先级
- 多路并发录像（`dict` 管理多个 VideoWriter），同一秒多个报警各自录制
- 自动清理：未确认 7 天删除 / 已确认 90 天删除视频保留快照

### 报警仲裁（Human-in-the-Loop）
- 待审核列表卡片式展示，支持确认/误报快速操作
- 历史档案多维度检索（时间、设备、审核人、状态）
- 审核结果可修正，支持物理删除记录及关联文件

### AI 数据分析助手
- 自然语言提问，Agent 自动生成 SQL 并查询
- 基于 4 个只读视图的安全查询（报警详情/日统计/设备排名/审核统计）
- 流式 SSE 输出，Markdown 表格和列表渲染
- 多会话管理，对话历史持久化

### 飞书告警通知
- 新告警产生时自动发送飞书消息卡片到群聊
- 卡片包含：设备名称 / 告警类型 / 置信度 / 时间 / 内嵌截图
- 基于飞书开放平台自定义应用，通过 Webhook 机器人发送卡片
- HMAC-SHA256 签名校验保障 webhook 安全
- 截图自动上传飞书图床（需 `im:resource` 权限）
- 异步非阻塞发送，不影响告警入库主流程
- 支持 `enabled` 开关，随时启停
- 公网地址通过 ngrok 隧道暴露本地静态资源

### 集中化日志（MongoDB）
- **MongoAppender**：Java 中台通过 Logback 自定义 Appender 异步写入 MongoDB
- **MongoHandler**：Python 引擎异步日志写入同一 MongoDB 集合
- **TraceId 传播**：HTTP 请求头 `X-Trace-Id` 在服务间透传，端到端链路追踪
- **前端日志**：浏览器日志通过 `POST /api/logs` 采集

### 系统管控
- CPU / 内存 / GPU / 磁盘 实时图表（ECharts）
- 全局 AI 引擎一键开关，单设备启停控制
- 用户权限管理（管理员 / 操作员），JWT 认证

## 项目结构

```
Smart No-Smoking Campus System/
├── web-vue/                       # Vue 3 前端 (port 5173)
│   ├── src/
│   │   ├── views/
│   │   │   ├── Monitor.vue        # 主监控大屏
│   │   │   ├── AuditConsole.vue   # 报警仲裁台
│   │   │   ├── AlarmArchive.vue   # 历史档案
│   │   │   ├── SystemControl.vue  # 系统控制台
│   │   │   ├── DeviceManage.vue   # 设备管理
│   │   │   ├── UserManage.vue     # 用户管理
│   │   │   ├── AiChat.vue         # AI 对话界面
│   │   │   └── Login.vue          # 登录页
│   │   ├── api/                   # Axios 接口封装
│   │   ├── router/                # 路由 + 权限守卫
│   │   ├── stores/                # Pinia 状态管理
│   │   └── utils/                 # 请求拦截器
│   ├── vite.config.ts             # Vite 配置 (代理 /api → 8080)
│   └── package.json
│
├── web-back/                      # Java Spring Boot 中台 (port 8080)
│   └── src/main/
│       ├── java/org/example/webback/
│       │   ├── controller/        # 7 个控制器
│       │   │   ├── AlarmController    # 报警审核/档案/上报
│       │   │   ├── DeviceController   # 设备 CRUD/状态同步
│       │   │   ├── AiChatController   # AI 对话/流式代理
│       │   │   ├── AuthController     # JWT 登录认证
│       │   │   ├── SystemController   # 系统状态/全局AI开关
│       │   │   ├── UserController     # 用户管理
│       │   │   └── InternalController # Python 内部上报/WebSocket
│       │   ├── service/           # 业务逻辑层
│       │   ├── entity/            # 实体类 (MyBatis-Plus)
│       │   ├── dto/               # 数据传输对象
│       │   ├── mapper/            # 数据访问层
│       │   └── config/            # Security/WebSocket/JWT/MyBatis
│       └── resources/
│           └── application.yml    # 数据源/Redis/MongoDB/AI地址
│
├── web-flask/                     # Python AI 引擎 (port 5000)
│   ├── app/
│   │   ├── core/
│   │   │   ├── stream_loader.py   # StreamLoader + StreamManager(全局)
│   │   │   ├── detector.py        # SmokingDetector (双模型级联+Batch+FP16)
│   │   │   ├── recorder.py        # EvidenceRecorder (预录缓冲+并发录像)
│   │   │   ├── burst_token.py     # 爆发令牌桶 (全局 Semaphore)
│   │   │   ├── io_throttle.py     # IO 限流 (Semaphore+taskkill)
│   │   │   ├── worker_manager.py  # 实验性多进程管理器（当前入口未启用）
│   │   │   └── worker_main.py     # 实验性 Worker 入口（尚未接入动态设备）
│   │   ├── api/
│   │   │   ├── monitor.py         # 视频流/设备同步/点火保护
│   │   │   └── system.py          # 全局AI开关
│   │   └── __init__.py            # Flask 工厂函数
│   ├── yolov8s.pt                 # 人员检测模型
│   ├── yolov8m.pt                 # 中型模型 (备用)
│   ├── yolov8n.pt                 # Nano 模型 (备用)
│   ├── yolov8n-pose.pt            # 姿态模型 (旧版遗留)
│   ├── best.pt                    # 自定义烟头模型 (位于 app/core/)
│   ├── run.py                     # 启动入口
│   └── config.py                  # 数据库/Java地址配置
│
├── web-agent/                     # AI 数据分析助手 (port 5050)
│   ├── app.py                     # Flask 入口 (SSE 流式接口)
│   ├── agent_service.py           # LangChain Agent 构建/问答/流式
│   ├── prompt.py                  # SQL Agent 系统提示词 (含Schema)
│   ├── db_toolkit.py              # SQLDatabase 初始化
│   ├── config.py                  # 环境变量配置 (dataclass)
│   └── test_sql_agent.py          # 命令行测试入口
│
├── db/                            # 数据库
│   └── smart_campus_smoking.sql   # 完整建表/视图（不含账号和业务种子数据）
│
├── development log/               # 开发日志
│   ├── 开发计划.md                # 初始 8 周开发计划
│   ├── 抽烟监测优化.md            # AI 算法优化报告
│   ├── 修改模型文档.md            # v2→v3.1 模型重构日志
│   ├── 人物锁定.md                # 动态冷却圈技术方案
│   ├── 仲裁于抽烟记录设计文档.md  # 报警仲裁系统设计
│   ├── 摄像头连接测试修复.md      # 连接稳定性优化
│   ├── springboot迁移.md          # Java 迁移集成总结
│   ├── web-agent 测试与数据库权限加固.md
│   ├── web-agent流式输出.md       # SSE 流式输出排查
│   └── 历史记录列表测试.md        # 对话记忆架构升级
│
└── report/                        # 项目报告文档
```

## 快速开始

### 环境要求

| 软件 | 版本要求 | 用途 |
|------|----------|------|
| Python | 3.9+ | web-flask, web-agent |
| Java JDK | 17+ | web-back |
| Node.js | 20+（建议） | web-vue（Vite 7） |
| MySQL | 8.0 | 业务数据库 |
| CUDA | 11.8+ (可选) | GPU 推理加速 |
| FFmpeg | 任意 | 证据视频 H.264 编码（full build 可选） |
| ImDisk Toolkit | 最新 | 内存盘 R:\（可选，无则自动回退 SSD） |

### 1. 数据库初始化

```bash
# 在 MySQL 中执行建库脚本
mysql -u root -p -P 3308 < db/smart_campus_smoking.sql
```

脚本包含：5 张基表（users/devices/alarms/ai_conversations/ai_chat_history）和 4 个 AI 只读视图；当前脚本不再附带测试账号或业务数据。

### 2. 启动 Python AI 引擎（web-flask）

```bash
cd web-flask
pip install -r requirements.txt
# 按 .env.example 创建本地 .env；PyTorch/CUDA 按运行机器单独核对
python run.py
# 服务运行在 http://0.0.0.0:5000
```

### 3. 启动 AI 数据分析助手（web-agent）

```bash
cd web-agent
cp .env.example .env
# 编辑 .env: 填入 OPENAI_API_KEY, DB_URI
pip install -r requirements.txt
python app.py
# 服务运行在 http://0.0.0.0:5050
```

### 4. 启动 Java 业务中台（web-back）

```bash
cd web-back
# 复制 src/main/resources/application.yml.example 为 application.yml
# 修改数据库连接
# 以及 ai.agent.url 和 app.python-static-path
mvn spring-boot:run
# 服务运行在 http://localhost:8080
```

### 5. 启动前端大屏（web-vue）

```bash
cd web-vue
npm install
npm run dev
# 开发环境运行在 http://localhost:5173
```

初始化脚本不创建默认账号，需要通过受控初始化流程写入 BCrypt 密码用户。

## 配置说明

### web-flask (`.env` / `config.py`)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | 模板值 | 预留数据库连接；当前视觉主链路不直接访问 MySQL |
| `JAVA_BASE_URL` | 无默认值 | Java 中台地址；报警、设备同步和心跳路径由代码统一拼接 |
| `SECRET_KEY` | 模板值 | 本地必须覆盖 |
| `MONGODB_LOG_URI` | 模板值 | Python 集中日志连接 |
| `INTERNAL_API_TOKEN` | 无默认值 | Flask 调用 Java 内部接口的共享服务令牌，至少 32 字符 |

> Flask 到 Java 的内部调用统一从 `JAVA_BASE_URL`/各端点环境变量读取，并携带 `X-Internal-Token`。

### web-agent (`.env`)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENAI_API_KEY` | - | LLM API 密钥（必填） |
| `OPENAI_MODEL` | `gpt-4o-mini` | 模型名称 |
| `OPENAI_BASE_URL` | - | API 代理地址（可选） |
| `DB_URI` | `mysql+pymysql://ai_reader:...@localhost:3308/smart_campus_smoking` | 数据库连接 |
| `DB_INCLUDE_TABLES` | 4 个 `ai_*` 视图 | 允许查询的视图列表 |
| `AGENT_PORT` | `5050` | 服务端口 |

### web-back (`application.yml.example` → 本地 `application.yml`)

| 配置项 | 说明 |
|--------|------|
| `spring.datasource` | 数据库连接（url/username/password） |
| `spring.data.redis` | Redis 连接 |
| `spring.data.mongodb` | MongoDB 连接（可选） |
| `ai.agent.url` | Python AI Agent 地址 (`http://127.0.0.1:5050/api/agent/chat`) |
| `notification.feishu.enabled` | 飞书通知总开关（true/false） |
| `notification.feishu.webhook-url` | 飞书群机器人 Webhook 地址 |
| `notification.feishu.app-id` | 飞书开放平台应用 App ID |
| `notification.feishu.app-secret` | 飞书开放平台应用 App Secret |
| `notification.feishu.sign-secret` | 飞书签名校验密钥（如开启） |
| `app.public-base-url` | ngrok 公网地址，用于拼接截图 URL |

### web-vue (`.env`)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VITE_APP_BASE_API` | `http://localhost:8080` | Java 中台地址 |
| `VITE_APP_AI_API` | `http://localhost:5000` | Python AI 引擎地址 |

## API 概览

### Java 中台 (8080)

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/auth/login` | 用户登录 |
| `GET` | `/api/auth/me` | 获取当前用户信息 |
| `GET` | `/api/monitor/devices` | 设备列表（需认证） |
| `POST` | `/api/monitor/devices` | 添加设备（admin） |
| `PUT` | `/api/monitor/devices/{id}` | 更新设备（admin） |
| `DELETE` | `/api/monitor/devices/{id}` | 删除设备（admin） |
| `POST` | `/api/monitor/devices/sync-status` | Python 状态同步（内部，旧） |
| `POST` | `/api/monitor/devices/batch-sync` | Python 批量心跳（当前聚合循环约每 1s） |
| `GET` | `/api/monitor/devices/delta` | 增量对账接口（带 version 参数） |
| `GET` | `/api/internal/devices` | 设备列表（需要 `X-Internal-Token`） |
| `POST` | `/api/internal/alarm/report` | 视觉服务报警上报（需要 `X-Internal-Token`） |
| `GET` | `/api/alerts/pending` | 待审核报警 |
| `POST` | `/api/alerts/{id}/audit` | 提交审核 |
| `GET` | `/api/alerts/archive` | 历史档案查询 |
| `DELETE` | `/api/alerts/{id}` | 物理删除（admin） |
| `GET` | `/api/ai/conversations` | AI 对话列表 |
| `POST` | `/api/ai/conversations` | 新建 AI 对话 |
| `POST` | `/api/ai/conversations/chat` | AI 同步问答 |
| `POST` | `/api/ai/conversations/chat/stream` | AI 流式问答 (SSE) |
| `GET` | `/api/ai/conversations/{id}/messages` | 对话历史 |
| `GET` | `/api/system/status` | 系统状态（含 AI 开关） |
| `POST` | `/api/system/control/global_ai_db` | 同步 AI 开关状态 |
| `GET` | `/actuator/health` | Spring Boot 健康检查（AIOps 监控用） |
| `GET` | `/actuator/metrics` | 运行时性能指标（AIOps 监控用） |
| `POST` | `/api/logs` | 前端日志采集 |

### Python AI 引擎 (5000)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/health` | 服务健康检查（含 GPU 利用率、活跃流数） |
| `GET` | `/api/v1/metrics` | 实时性能指标（JSON） |
| `GET` | `/api/v1/monitor/stream/{id}` | 视频流 (MJPEG) |
| `GET` | `/api/v1/monitor/thumbnail/{id}` | 缩略图 (320x240 JPG) |
| `POST` | `/api/v1/monitor/sync` | 触发设备同步 |
| `GET` | `/api/v1/system/global_ai` | 获取全局 AI 状态 |
| `POST` | `/api/v1/system/global_ai` | 设置全局 AI 开关 |

### Python AI Agent (5050)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查 |
| `POST` | `/api/agent/chat` | 同步问答 |
| `POST` | `/api/agent/chat/stream` | 流式问答 (SSE) |

## 数据库

### 基表

| 表名 | 说明 |
|------|------|
| `users` | 用户表（Bcrypt 密码、JWT 认证） |
| `devices` | 设备表（RTSP 地址、启停状态） |
| `alarms` | 报警记录表（状态机：0待审/1确认/2误报/9忽略） |
| `ai_conversations` | AI 对话会话表（UUID、逻辑删除） |
| `ai_chat_history` | AI 聊天记录表（LangChain JSON 格式） |

### AI 专用视图

| 视图 | 说明 |
|------|------|
| `ai_alarm_detail_view` | 报警详情（含设备名、审核人、延迟分钟） |
| `ai_alarm_daily_stats_view` | 每日报警统计趋势 |
| `ai_device_alarm_rank_view` | 设备报警排名 |
| `ai_audit_stats_view` | 审核人员工作效率统计 |

### 安全设计

AI Agent 使用专用账号 `ai_reader`，仅拥有 4 个视图的 `SELECT` + `SHOW VIEW` 权限和 `ai_chat_history` 的 `SELECT/INSERT` 权限。即使 LLM 被诱导生成恶意 SQL，MySQL 引擎层也会直接拒绝。

## 开源协议

本项目采用 MIT 许可证。
