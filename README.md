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

**核心突破**：

- 采用**级联 ROI 检测 + Batch 批处理 + FP16 半精度**，单张 RTX 3060 即可承载多路并发
- 引入**大模型 SQL Agent**，用自然语言直接查询报警数据，无需编写 SQL
- Java 中台统一鉴权与业务编排，Python 专注于 AI 推理，职责清晰

## 系统架构

```
                    ┌──────────────────────────────────┐
                    │     Vue 3 前端大屏 (port 5173)     │
                    │  Monitor / Audit / Archive / Chat │
                    └──────────┬──────────┬────────────┘
                               │ HTTP     │ SockJS/STOMP
                               ▼          ▼
                    ┌──────────────────────────────────┐
                    │   Java Spring Boot 中台 (port 8080)│
                    │  鉴权 / CRUD / WebSocket / SSE代理 │
                    └────┬──────┬──────┬───────────────┘
                         │      │      │
              ┌──────────┘      │      └──────────┐
              ▼                 ▼                  ▼
    ┌─────────────────┐  ┌───────────┐  ┌───────────────────┐
    │ Python AI 引擎   │  │ MySQL 8.0 │  │ Python AI Agent   │
    │ YOLOv8 + Flask   │  │ (port 3308)│  │ LangChain + LLM   │
    │ (port 5000)      │  └───────────┘  │ (port 5050)       │
    └────────┬─────────┘                  └───────────────────┘
             │ RTSP
             ▼
    ┌─────────────────┐
    │   IP 摄像头 x N   │
    └─────────────────┘
```

### 服务职责

| 服务 | 端口 | 技术栈 | 核心职责 |
|------|------|--------|----------|
| **web-vue** | 5173 | Vue 3 + Element Plus + Pinia + ECharts | 监控大屏、报警仲裁、设备管理、AI 对话 |
| **web-back** | 8080 | Spring Boot 3 + MyBatis-Plus + WebSocket | 鉴权、业务 CRUD、SSE 代理、设备状态同步 |
| **web-flask** | 5000 | Flask + YOLOv8 + OpenCV | RTSP 拉流、吸烟检测、证据录制、全局 AI 控制 |
| **web-agent** | 5050 | Flask + LangChain + SQLDatabaseToolkit | 自然语言→SQL→数据分析报告 |

### AI 推理管线（web-flask）

```
RTSP 流 → TCP 握手(单线程解码) → 全局单例检测器
                                      │
                    ┌─────────────────┘
                    ▼
         Stage 1: YOLOv8s 全局找人 (ByteTrack 追踪)
                    │
                    ▼
         裁切人物上半身 ROI + 30% Padding
                    │
                    ▼
         Batch 打包 → Stage 2: best.pt 找烟 (FP16)
                    │
                    ▼
         惯性追踪防闪烁 (3帧记忆) → 15帧确认报警
                    │
                    ▼
         预录缓冲(2s)+后录(5s) → FFmpeg H.264 → 推送到 Java
```

## 功能特性

### 实时监控
- 多路 RTSP 视频流并发处理，支持 MJPEG 流推送至浏览器
- 设备在线/离线状态实时检测，掉线自动重连
- WebSocket 实时推送报警弹窗，设备列表 5 秒轮询

### AI 吸烟检测
- 双模型级联检测（YOLOv8s 找人 + best.pt 找烟）
- ByteTrack 人员追踪，支持移动吸烟去重（动态冷却圈）
- GPU FP16 半精度加速，推理延迟 < 300ms
- 检测框惯性平滑，消除闪烁

### 证据链管理
- 报警触发时自动保存快照（JPG）和录像（MP4），均带 AI 检测框
- 2 秒预录缓冲 + 5 秒后录，FFmpeg 自动转码 H.264
- 已确认违规永久保留，误报 30 天后自动清理

### 报警仲裁（Human-in-the-Loop）
- 待审核列表卡片式展示，支持确认/误报快速操作
- 历史档案多维度检索（时间、设备、审核人、状态）
- 审核结果可修正，支持物理删除记录及关联文件

### AI 数据分析助手
- 自然语言提问，Agent 自动生成 SQL 并查询
- 基于 4 个只读视图的安全查询（报警详情/日统计/设备排名/审核统计）
- 流式 SSE 输出，Markdown 表格和列表渲染
- 多会话管理，对话历史持久化

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
│   │   │   └── recorder.py        # EvidenceRecorder (预录缓冲+FFmpeg转码)
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
│   └── smart_campus_smoking.sql   # 完整建表/视图/测试数据
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
| Node.js | 16+ | web-vue |
| MySQL | 8.0 | 业务数据库 |
| CUDA | 11.8+ (可选) | GPU 推理加速 |
| FFmpeg | 任意 | 证据视频转码 |

### 1. 数据库初始化

```bash
# 在 MySQL 中执行建库脚本
mysql -u root -p -P 3308 < db/smart_campus_smoking.sql
```

脚本包含：5 张基表（users/devices/alarms/ai_conversations/ai_chat_history）、4 个 AI 只读视图、测试数据。

### 2. 启动 Python AI 引擎（web-flask）

```bash
cd web-flask
pip install -r requirements.txt
# 修改 config.py 中的数据库连接和 Java 地址
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
# 修改 src/main/resources/application.yml 中的数据库连接
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

默认账号：`admin` / 密码见数据库 users 表。

## 配置说明

### web-flask (`config.py`)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SQLALCHEMY_DATABASE_URI` | `mysql+pymysql://root:...@localhost:3308/smart_campus_smoking` | 数据库连接 |
| `JAVA_API_URL` | `http://localhost:8080/api/internal/alarm/report` | 报警上报地址 |
| `JAVA_DEVICE_LIST_URL` | `http://localhost:8080/api/monitor/devices` | 设备同步地址 |
| `BUFFER_SIZE` | `150` | 视频帧缓存大小 |

### web-agent (`.env`)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENAI_API_KEY` | - | LLM API 密钥（必填） |
| `OPENAI_MODEL` | `gpt-4o-mini` | 模型名称 |
| `OPENAI_BASE_URL` | - | API 代理地址（可选） |
| `DB_URI` | `mysql+pymysql://ai_reader:...@localhost:3308/smart_campus_smoking` | 数据库连接 |
| `DB_INCLUDE_TABLES` | 4 个 `ai_*` 视图 | 允许查询的视图列表 |
| `AGENT_PORT` | `5050` | 服务端口 |

### web-back (`application.yml`)

| 配置项 | 说明 |
|--------|------|
| `spring.datasource` | 数据库连接（url/username/password） |
| `spring.data.redis` | Redis 连接 |
| `spring.data.mongodb` | MongoDB 连接（可选） |
| `ai.agent.url` | Python AI Agent 地址 (`http://127.0.0.1:5050/api/agent/chat`) |
| `app.python-static-path` | web-flask 的 `app/` 目录绝对路径 |

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
| `POST` | `/api/monitor/devices/sync-status` | Python 状态同步（内部） |
| `GET` | `/api/internal/devices` | 设备列表（内部白名单） |
| `POST` | `/api/internal/alarm/report` | 报警上报（内部） |
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

### Python AI 引擎 (5000)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/monitor/stream/{id}` | 视频流 (MJPEG) |
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

## 开发日志索引

| 文档 | 内容 |
|------|------|
| [开发计划](development%20log/开发计划.md) | 初始 8 周开发计划、里程碑、风险评估 |
| [抽烟监测优化](development%20log/抽烟监测优化.md) | 级联检测、Batch/FP16、全局单例、显存优化 |
| [修改模型文档](development%20log/修改模型文档.md) | Pose+分类器 → 端到端双模型升级 (v2→v3.1) |
| [人物锁定](development%20log/人物锁定.md) | 动态冷却圈：解决移动吸烟和 ID 跳变重复报警 |
| [仲裁与抽烟记录设计](development%20log/仲裁于抽烟记录设计文档.md) | 报警状态机、审核系统、存储清理策略 |
| [摄像头连接测试修复](development%20log/摄像头连接测试修复.md) | 智能握手、网络熔断、Pinia 状态防抖 |
| [SpringBoot 迁移](development%20log/springboot迁移.md) | Java 中台集成：内部通道、状态同步、FFmpeg 死锁修复 |
| [web-agent 安全加固](development%20log/web-agent%20测试与数据库权限加固.md) | 最小权限、视图隔离、三层防注入 |
| [web-agent 流式输出](development%20log/web-agent流式输出.md) | SSE 断包/空格裁切/异步生命周期 排查与修复 |
| [历史记录测试](development%20log/历史记录列表测试.md) | 对话记忆架构升级：手动注入法绕过 LangChain 黑盒 |

## 开源协议

本项目采用 MIT 许可证。
