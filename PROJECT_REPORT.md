# 🎓 智慧校园无烟监控系统 - 完整项目报告

> **项目版本**: v3.3 (最新) | **生成日期**: 2026-04-22  
> **技术栈**: Vue 3 + Spring Boot 3 + Flask + YOLOv8 + MySQL 8.0  
> **项目路径**: `d:\engineering\Smart No-Smoking Campus System`

---

## 📋 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [技术栈详解](#3-技术栈详解)
4. [目录结构](#4-目录结构)
5. [数据库设计](#5-数据库设计)
6. [前端架构分析](#6-前端架构分析)
7. [后端架构分析](#7-后端架构分析)
8. [AI检测核心模块](#8-ai检测核心模块)
9. [核心业务流程](#9-核心业务流程)
10. [API接口文档](#10-api接口文档)
11. [配置说明](#11-配置说明)
12. [开发指南](#12-开发指南)
13. [已知问题与优化建议](#13-已知问题与优化建议)
14. [后续开发路线图](#14-后续开发路线图)

---

## 1. 项目概述

### 1.1 项目背景

随着高校禁烟政策的推进，传统的人工巡检方式已无法满足大规模校园的禁烟管理需求。本项目利用**AI深度学习技术**对校园内的RTSP监控视频流进行实时分析，精准识别吸烟行为，实现**秒级报警推送**和**完整证据链回溯**。

### 1.2 核心目标

| 目标指标 | 具体要求 |
|---------|---------|
| 检测准确率 | ≥90% (实际达到70-80%) |
| 报警延迟 | <300ms (FP16加速) |
| 并发能力 | 单卡RTX 3060支持多路视频流 |
| 证据保存 | 10秒视频 + 特写截图 |
| 用户角色 | 管理员(admin) / 普通用户(user) |

### 1.3 技术突破点

✅ **级联ROI检测**: 解决"远处烟头像素极小(<10px)难以识别"的痛点  
✅ **Batch批处理推理**: 多路视频显存占用降低60%  
✅ **FP16半精度加速**: 延迟压缩至300ms以内  
✅ **惯性追踪防闪烁**: 消除检测框抖动现象  
✅ **人机回环仲裁**: 人工审核AI报警结果，确保数据准确性  

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                          前端展示层 (Vue 3)                         │
│  ┌───────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌────────┐ │
│  │ Monitor   │ │ Device   │ │ User      │ │ Audit    │ │System  │ │
│  │ 监控墙    │ │ Manage   │ │ Manage    │ │ Console  │ │Control │ │
│  └─────┬─────┘ └────┬─────┘ └─────┬─────┘ └────┬─────┘ └───┬────┘ │
│        │            │            │            │           │       │
│        └────────────┴────────────┴────────────┴───────────┘       │
│                           HTTP/WebSocket                            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────┼─────────────────────────────────────┐
│                     后端服务层 (Spring Boot 3)                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  ┌───────────┐  │
│  │Controller   │  │ Service      │  │ Security   │  │ WebSocket │  │
│  │(REST API)   │  │(Business)    │  │(JWT Auth)  │  │(STOMP)    │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬─────┘  └─────┬─────┘  │
│         │                │                 │               │        │
│  ┌──────┴──────┐  ┌──────┴───────┐  ┌──────┴─────┐         │        │
│  │ MyBatis-Plus│  │ Redis Cache  │  │ MongoDB    │         │        │
│  │ (ORM)       │  │ (Session)    │  │ (Logs)     │         │        │
│  └──────┬──────┘  └──────────────┘  └────────────┘         │        │
│         │                                                  │        │
└─────────┼──────────────────────────────────────────────────┼────────┘
          │              HTTP/Internal API                   │
          └──────────────────────┬───────────────────────────┘
                                 │
┌────────────────────────────────┼────────────────────────────────────┐
│                    AI计算层 (Python Flask)                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────────┐   │
│  │ StreamLoader    │  │ SmokingDetector │  │ EvidenceRecorder  │   │
│  │ (视频流管理)    │  │ (YOLO级联检测)  │  │ (证据录制)        │   │
│  └────────┬────────┘  └────────┬────────┘  └────────┬──────────┘   │
│           │                    │                     │              │
│  ┌────────┴────────┐  ┌───────┴────────┐  ┌─────────┴──────────┐   │
│  │ RTSP Camera     │  │ GPU (CUDA)     │  │ Local File System  │   │
│  │ (监控摄像头)    │  │ (PyTorch+YOLO) │  │ (证据存储)         │   │
│  └─────────────────┘  └────────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 三层架构说明

#### 第一层：前端展示层 (web-vue)
- **技术**: Vue 3 + TypeScript + Vite + Element Plus + Pinia + ECharts
- **职责**: 
  - 实时视频监控展示
  - 设备/用户管理界面
  - 报警审核与历史档案查看
  - 系统状态控制面板
- **通信**: HTTP REST API + STOMP WebSocket (SockJS)

#### 第二层：后端服务层 (web-back)
- **技术**: Spring Boot 3.0.2 + MyBatis-Plus + Spring Security + JWT
- **职责**:
  - 用户认证与权限控制 (JWT Token)
  - 业务数据CRUD操作 (设备/用户/报警记录)
  - 接收Python AI引擎的报警数据
  - WebSocket实时推送给前端
- **端口**: 8080

#### 第三层：AI计算层 (web-flask)
- **技术**: Python Flask + PyTorch 2.0 + YOLOv8 + OpenCV 4.x
- **职责**:
  - RTSP视频流拉取与解码
  - YOLO级联检测 (人员定位 → ROI裁剪 → 烟头识别)
  - 报警逻辑判断与证据录制
  - 与Java后端通信 (HTTP POST)
- **端口**: 5000

---

## 3. 技术栈详解

### 3.1 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue.js | ^3.5.24 | 渐进式JavaScript框架 |
| TypeScript | ~5.9.3 | 类型安全的JavaScript超集 |
| Vite | ^7.2.4 | 新一代前端构建工具 |
| Element Plus | ^2.13.0 | Vue 3组件库 |
| Pinia | ^3.0.4 | Vue官方状态管理库 |
| Vue Router | ^4.6.4 | 路由管理 |
| Axios | ^1.13.2 | HTTP客户端 |
| ECharts | ^6.0.0 | 数据可视化图表库 |
| SockJS-client | ^1.6.1 | WebSocket兼容库 |
| STOMP.js | ^2.3.3 | WebSocket消息协议 |

### 3.2 后端技术栈 (Java)

| 技术 | 版本 | 用途 |
|------|------|------|
| Java | 17 | 编程语言 |
| Spring Boot | 3.0.2 | 应用框架 |
| MyBatis-Plus | 3.5.5 | ORM框架 |
| Spring Security | - | 安全认证框架 |
| JWT (jjwt) | - | JSON Web Token认证 |
| MySQL Connector | runtime | MySQL驱动 |
| Spring Data Redis | - | Redis缓存 |
| Spring Data MongoDB | - | MongoDB日志存储 |
| Lombok | optional | 代码简化注解 |
| Hutool | 5.8.26 | Java工具集 |
| OSHI Core | 6.4.10 | 系统硬件信息获取 |

### 3.3 AI技术栈 (Python)

| 技术 | 用途 |
|------|------|
| Python 3.9+ | 编程语言 |
| PyTorch 2.0+ | 深度学习框架 |
| CUDA 11.x | GPU加速计算 |
| YOLOv8 (ultralytics) | 目标检测模型 |
| OpenCV 4.x | 计算机视觉处理 |
| Flask | Web框架 |
| Flask-SocketIO | WebSocket支持 |
| NumPy | 数值计算 |
| Multiprocessing | 多进程并行 |

---

## 4. 目录结构

```
Smart No-Smoking Campus System/
│
├── 📁 db/                              # 数据库脚本
│   └── init.sql                        # MySQL初始化脚本 (表结构+测试数据)
│
├── 📁 development log/                 # 开发日志与技术文档
│   ├── 开发计划.md                     # 8周开发计划 (里程碑/任务分解)
│   ├── springboot迁移.md               # Java-Python集成迁移总结
│   ├── 人物锁定.md                     # 人物追踪算法设计
│   ├── 仲裁于抽烟记录设计文档.md        # 报警仲裁系统设计
│   ├── 修改模型文档.md                 # AI模型重构日志
│   ├── 抽烟监测优化.md                 # 性能优化报告
│   └── 摄像头连接测试修复.md            # RTSP连接稳定性修复
│
├── 📁 report/                          # 项目正式文档
│   ├── 软件需求规格说明书 (SRS).md      # 需求规格说明书
│   ├── 概要设计说明书 (HLD).md          # 高层设计文档
│   ├── 详细设计说明书.md                # 详细设计文档
│   └── 可行性分析报告.md                # 可行性分析
│
├── 📁 web-vue/                         # ⭐ 前端工程 (Vue 3)
│   ├── src/
│   │   ├── api/                        # API接口封装
│   │   │   ├── auth.ts                 # 认证API (登录/登出)
│   │   │   ├── device.ts               # 设备管理API
│   │   │   ├── user.ts                 # 用户管理API
│   │   │   └── alert.ts                # 报警管理API
│   │   │
│   │   ├── views/                      # 页面组件
│   │   │   ├── Login.vue               # 登录页面
│   │   │   ├── Monitor.vue             # ⭐ 实时监控主页面
│   │   │   ├── DeviceManage.vue        # 设备管理页面
│   │   │   ├── UserManage.vue          # 用户管理页面
│   │   │   ├── AuditConsole.vue        # 报警仲裁台
│   │   │   ├── AlarmArchive.vue        # 违规历史档案
│   │   │   └── SystemControl.vue       # 系统控制面板
│   │   │
│   │   ├── router/index.ts             # 路由配置 (含权限守卫)
│   │   ├── stores/device.ts            # Pinia设备状态管理
│   │   ├── utils/request.ts            # Axios请求封装
│   │   ├── App.vue                     # 根组件
│   │   └── main.ts                     # 应用入口
│   │
│   ├── .env                            # 环境变量配置
│   ├── package.json                    # NPM依赖配置
│   └── vite.config.ts                  # Vite构建配置
│
├── 📁 web-back/                        # ⭐ Java后端工程 (Spring Boot)
│   └── src/main/java/org/example/webback/
│       ├── common/
│       │   └── Result.java             # 统一响应封装类
│       │
│       ├── config/
│       │   ├── JwtInterceptor.java     # JWT拦截器 (认证校验)
│       │   ├── SecurityConfig.java     # Spring Security配置
│       │   ├── WebMvcConfig.java       # MVC配置 (跨域/白名单)
│       │   ├── MyBatisConfig.java      # MyBatis配置
│       │   └── WebSocketConfig.java    # WebSocket/STOMP配置
│       │
│       ├── controller/
│       │   ├── AuthController.java     # 认证控制器
│       │   ├── UserController.java     # 用户管理控制器
│       │   ├── DeviceController.java   # 设备管理控制器
│       │   ├── AlarmController.java    # ⭐ 报警管理控制器
│       │   ├── InternalController.java # ⭐ 内部通信控制器 (接收Python报警)
│       │   └── SystemController.java   # 系统状态控制器
│       │
│       ├── service/
│       │   ├── AuthService.java        # 认证服务
│       │   ├── UserService.java        # 用户服务
│       │   ├── DeviceService.java      # 设备服务
│       │   ├── AlarmService.java       # ⭐ 报警服务 (审核/存档)
│       │   └── SystemMonitorService.java # 系统监控服务
│       │
│       ├── entity/
│       │   ├── User.java               # 用户实体
│       │   ├── Device.java             # 设备实体
│       │   └── Alarm.java              # ⭐ 报警实体
│       │
│       ├── mapper/
│       │   ├── UserMapper.java         # 用户Mapper
│       │   ├── DeviceMapper.java       # 设备Mapper
│       │   └── AlarmMapper.java        # 报警Mapper
│       │
│       ├── dto/
│       │   └── AlarmReportDTO.java     # ⭐ 报警上报DTO (Python→Java)
│       │
│       └── WebBackApplication.java    # Spring Boot启动类
│
│   └── src/main/resources/
│       └── application.yml             # ⭐ 应用配置文件
│
├── 📁 web-flask/                       # ⭐ Python AI引擎 (Flask)
│   ├── app/
│   │   ├── __init__.py                 # Flask应用工厂
│   │   ├── model.py                    # SQLAlchemy数据模型
│   │   ├── config.py                   # ⭐ Flask配置
│   │   ├── run.py                      # 应用启动入口
│   │   │
│   │   ├── api/
│   │   │   ├── monitor.py              # ⭐ 监控API (设备同步/流管理/AI开关)
│   │   │   └── system.py               # 系统状态API
│   │   │
│   │   └── core/                       # 🔥 AI核心算法
│   │       ├── detector.py             # ⭐⭐ YOLO级联检测器 (单例/Batch/FP16)
│   │       ├── stream_loader.py        # ⭐⭐ 视频流管理器 (RTSP拉流/多线程)
│   │       ├── recorder.py             # 证据录制模块 (视频合成)
│   │       └── best.pt                 # 训练好的烟头检测模型权重
│   │
│   ├── yolov8n.pt                      # YOLOv8n预训练模型 (人员检测)
│   ├── yolov8s.pt                      # YOLOv8s预训练模型
│   └── yolov8n-pose.pt                 # YOLOv8姿态估计模型 (备用)
│
└── README.md                           # 项目说明文档
```

---

## 5. 数据库设计

### 5.1 数据库概览

- **数据库名**: `smart_campus_smoking`
- **MySQL版本**: 8.0.34
- **端口**: 3308
- **字符集**: utf8mb4 (支持emoji和特殊字符)

### 5.2 ER关系图

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    users    │       │   devices   │       │   alarms    │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │◄──┐   │ id (PK)     │◄──┐   │ id (PK)     │
│ username    │   │   │ name        │   │   │ camera_id   │(FK)
│ password    │   │   │ rtsp_url    │   │   │ type        │
│ role        │   │   │ area_config │   │   │ confidence  │
│ status      │   │   │ created_at  │   │   │ created_at  │
│ last_login_ │   │   │ updated_at  │   │   │ video_url   │
│   ip/time   │   │   │ status      │   │   │ roi_url     │
│ created_at  │   │   │ enabled     │   │   │ audit_status│
└─────────────┘   │   └─────────────┘   │   │ auditor_id  │(FK)
                  │                     │   │ audit_time  │
                  │                     │   │ audit_remark│
                  │                     │   └─────────────┘
                  │                     │
                  └─────(审核人)────────┘
```

### 5.3 表结构详解

#### 5.3.1 users 表 (用户表)

```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '用户主键',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '登录账号',
    password VARCHAR(255) NOT NULL COMMENT '加密密码(scrypt)',
    role VARCHAR(20) NOT NULL DEFAULT 'user' COMMENT '角色: admin/user',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '状态: 1-启用, 0-禁用',
    last_login_ip VARCHAR(50) COMMENT '最后登录IP',
    last_login_time DATETIME COMMENT '最后登录时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX uk_username (username)  -- 账号唯一索引
);
```

**字段说明**:
- `password`: 使用scrypt算法加密 (参数: 32768:8:1)
- `role`: `admin`(管理员) 或 `user`(普通用户)
- 默认账号: `admin` (密码需查看init.sql中的hash值)

**示例数据**:
| id | username | role | status |
|----|----------|------|--------|
| 1 | admin | admin | 1 |
| 2 | user_01 | user | 1 |
| 3-11 | user_02~10 | user | 1 |

---

#### 5.3.2 devices 表 (设备/摄像头表)

```sql
CREATE TABLE devices (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '设备ID',
    name VARCHAR(100) NOT NULL COMMENT '设备名称',
    rtsp_url VARCHAR(500) NOT NULL COMMENT 'RTSP视频流地址',
    area_config JSON COMMENT 'ROI区域坐标(扩展字段)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    status INT DEFAULT 1 COMMENT '在线状态: 1-在线, 0-离线',
    enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用: 1-启用, 0-停用'
);
```

**关键字段**:
- `rtsp_url`: RTSP协议地址格式: `rtsp://用户名:密码@IP:端口/路径`
- `status`: 由Python AI引擎实时更新 (在线/离线)
- `enabled`: 由管理员手动控制 (启用/停用)

**示例数据**:
| id | name | rtsp_url | status | enabled |
|----|------|----------|--------|---------|
| 40 | 手机1 | rtsp://admin:admin@192.168.1.6:8554/live | 0 | 0 |
| 41 | 手机2 | rtsp://admin:admin@192.168.110.107:8554/live | 0 | 0 |
| 42 | 一楼 | rtsp://rtsp:12345678@192.168.110.208:554/... | 0 | 0 |

---

#### 5.3.3 alarms 表 (报警记录表) ⭐核心表

```sql
CREATE TABLE alarms (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    camera_id INT NOT NULL COMMENT '摄像头ID(FK->devices.id)',
    type ENUM('SMOKING','FIRE') NOT NULL COMMENT '报警类型',
    confidence FLOAT NOT NULL COMMENT '置信度(0-1)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '报警时间',
    video_url VARCHAR(255) NOT NULL COMMENT '证据视频路径',
    roi_url VARCHAR(255) NOT NULL COMMENT '特写截图路径',
    audit_status TINYINT NOT NULL DEFAULT 0 COMMENT '审核状态',
    auditor_id INT NULL COMMENT '审核人ID(FK->users.id)',
    audit_time DATETIME NULL COMMENT '审核时间',
    audit_remark VARCHAR(255) NULL COMMENT '审核备注',
    
    INDEX idx_camera_id (camera_id),
    INDEX idx_create_time (created_at),
    INDEX idx_audit_status (audit_status),
    CONSTRAINT fk_alarms_devices FOREIGN KEY (camera_id) REFERENCES devices(id) ON DELETE CASCADE,
    CONSTRAINT fk_alarms_users FOREIGN KEY (auditor_id) REFERENCES users(id) ON DELETE SET NULL
);
```

**审核状态机 (audit_status)**:
```
0 (待审核) ──► 1 (已确认违规) ──► 永久保留作为证据
     │
     ├──► 2 (误报/负样本) ──► 保留30天后自动清理
     │
     └──► 9 (已忽略)
```

**索引设计**:
- `idx_camera_id`: 按摄像头查询报警记录
- `idx_create_time`: 按时间范围查询
- `idx_audit_status`: 按审核状态筛选 (待审核/已确认/误报)

---

## 6. 前端架构分析

### 6.1 技术选型理由

| 选择 | 理由 |
|------|------|
| Vue 3 Composition API | 更好的TypeScript支持, 逻辑复用性更强 |
| Pinia | Vue 3官方推荐, 更简洁的API |
| Element Plus | 企业级UI组件库, 丰富的表单/表格组件 |
| ECharts | 强大的数据可视化能力, 用于统计图表 |
| STOMP over SockJS | WebSocket消息协议, 支持 topic订阅模式 |

### 6.2 路由配置 ([router/index.ts](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-vue/src/router/index.ts))

```typescript
const routes = [
  { path: '/', component: Monitor, meta: { title: '实时监控' } },
  { path: '/login', component: Login, meta: { title: '登录' } },
  { path: '/devices', component: DeviceManage, meta: { roles: ['admin'] } },  // 仅管理员
  { path: '/users', component: UserManage, meta: { roles: ['admin'] } },      // 仅管理员
  { path: '/audit', component: AuditConsole, meta: { requiresAuth: true } },
  { path: '/archive', component: AlarmArchive, meta: { requiresAuth: true } },
  { path: '/system', component: SystemControl, meta: { roles: ['admin'] } }   // 仅管理员
]
```

**路由守卫逻辑**:
1. 未登录用户访问非登录页 → 重定向到 `/login`
2. 已登录用户访问登录页 → 重定向到 `/`
3. 访问需要特定角色的页面 → 检查 `localStorage.userInfo.role`

### 6.3 核心页面功能

#### 6.3.1 Monitor.vue (实时监控主页面) ⭐⭐⭐

**文件位置**: [Monitor.vue](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-vue/src/views/Monitor.vue)

**功能模块**:

```
┌─────────────────────────────────────────────────────────────────┐
│  Top Bar: Logo | 在线/离线/总数 | 时间 | 快捷按钮(仲裁/历史/系统) │
├──────────┬──────────────────────────────┬───────────────────────┤
│ Left     │     Center (视频播放器)      │ Right (设备列表)      │
│ Panel    │  ┌──────────────────────┐    │  ┌─────────────────┐  │
│          │  │  LIVE/OFFLINE 状态   │    │  │ 手机1  [在线]   │  │
│ 运行状态  │  │  ┌────────────────┐  │    │  │ 手机2  [离线]   │  │
│ 视频流服务│  │  │                │  │    │  │ 一楼   [在线]   │  │
│ AI引擎   │  │  │   视频画面      │  │    │  │ ...             │  │
│ WebSocket│  │  │                │  │    │  └─────────────────┘  │
│          │  │  └────────────────┘  │    │                       │
│ 快速管理  │  │  URL | 全屏按钮      │    │                       │
│          │  └──────────────────────┘    │                       │
│ 用户信息  │                               │                       │
└──────────┴───────────────────────────────┴───────────────────────┘
│  Bottom Bar: © 2026 智慧校园禁烟监控系统                          │
└─────────────────────────────────────────────────────────────────┘
```

**核心技术实现**:

1️⃣ **视频流展示**
```typescript
// 通过<img>标签加载MJPEG流 (带版本号防缓存)
const getStreamUrl = (id: number) => 
  `${AI_API}/api/v1/monitor/stream/${id}?v=${deviceStore.streamVersion}`
```

2️⃣ **WebSocket实时报警**
```typescript
// 使用STOMP协议订阅 /topic/alarm
stompClient.subscribe('/topic/alarm', (res) => {
  handleIncomingAlarm(JSON.parse(res.body))
})
// 收到报警后显示ElNotification通知 + 8秒红色边框闪烁
```

3️⃣ **系统状态轮询** (每3秒)
```typescript
// 同步AI开关状态、视频流数量等
const fetchSystemStatus = async () => {
  const res = await axios.get(`${JAVA_BASE}/api/system/status`)
  systemStatus.globalAi = data.global_ai  // AI引擎开关
}
setInterval(fetchSystemStatus, 3000)
```

4️⃣ **设备状态管理** (Pinia Store)
```typescript
// stores/device.ts 管理:
// - 设备列表获取/刷新
// - 在线状态轮询
// - 视频错误处理
// - 重连机制
```

---

#### 6.3.2 其他重要页面

| 页面 | 文件 | 功能描述 | 权限 |
|------|------|---------|------|
| **Login.vue** | [Login.vue](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-vue/src/views/Login.vue) | 用户登录表单 (用户名/密码) | 所有人 |
| **DeviceManage.vue** | [DeviceManage.vue](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-vue/src/views/DeviceManage.vue) | CRUD管理摄像头设备 | admin |
| **UserManage.vue** | [UserManage.vue](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-vue/src/views/UserManage.vue) | CRUD管理系统用户 | admin |
| **AuditConsole.vue** | [AuditConsole.vue](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-vue/src/views/AuditConsole.vue) | 人工审核AI报警 (确认/误报/忽略) | 已登录用户 |
| **AlarmArchive.vue** | [AlarmArchive.vue](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-vue/src/views/AlarmArchive.vue) | 查询历史违规记录 (支持筛选) | 已登录用户 |
| **SystemControl.vue** | [SystemControl.vue](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-vue/src/views/SystemControl.vue) | AI引擎开关/系统资源监控 | admin |

### 6.4 API请求封装 ([utils/request.ts](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-vue/src/utils/request.ts))

```typescript
// Axios实例配置
const service = axios.create({
  baseURL: import.meta.env.VITE_APP_BASE_API || 'http://localhost:8080',
  timeout: 10000
})

// 请求拦截器: 自动添加JWT Token
service.interceptors.request.use(config => {
  config.headers.Authorization = `Bearer ${localStorage.getItem('token')}`
  return config
})

// 响应拦截器: 统一错误处理 + 401跳转登录
service.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      router.push('/login')  // Token过期, 跳转登录
    }
    return Promise.reject(error)
  }
)
```

### 6.5 环境变量配置 (.env)

```env
VITE_APP_BASE_API=http://localhost:8080    # Java后端地址
VITE_APP_AI_API=http://localhost:5000      # Python AI引擎地址
```

---

## 7. 后端架构分析

### 7.1 Spring Boot项目结构

采用标准的 **Controller → Service → Mapper** 三层架构：

```
Controller (接收请求/参数校验)
    ↓
Service (业务逻辑处理)
    ↓
Mapper (MyBatis-Plus数据访问)
    ↓
MySQL Database
```

### 7.2 安全认证机制

#### JWT认证流程:

```
1. 用户登录 (POST /api/auth/login)
   ↓
2. 服务端验证用户名密码 (scrypt hash比对)
   ↓
3. 生成JWT Token (包含userId, role, exp)
   ↓
4. 返回Token给前端 (localStorage存储)
   ↓
5. 后续请求携带 Header: Authorization: Bearer <token>
   ↓
6. JwtInterceptor 拦截验证:
   - 解析Token
   - 验证签名和过期时间
   - 将userId存入 RequestAttribute
   ↓
7. Controller通过 @RequestAttribute("uid") 获取当前用户
```

**关键配置文件**:
- [JwtInterceptor.java](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-back/src/main/java/org/example/webback/config/JwtInterceptor.java): JWT拦截器
- [SecurityConfig.java](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-back/src/main/java/org/example/webback/config/SecurityConfig.java): Spring Security配置 (放行登录/内部接口)
- [WebMvcConfig.java](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-back/src/main/java/org/example/webback/config/WebMvcConfig.java): MVC配置 (CORS/白名单路径)

### 7.3 统一响应格式 ([Result.java](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-back/src/main/java/org/example/webback/common/Result.java))

```java
public class Result<T> {
    private int code;      // 200=成功, 400=参数错误, 401=未授权, 403=禁止, 500=服务器错误
    private String msg;    // 提示信息
    private T data;        // 业务数据
    
    public static <T> Result<T> success(T data) { ... }
    public static Result<?> success(String msg) { ... }
    public static Result<?> error(int code, String msg) { ... }
}
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "操作成功",
  "data": { ... }
}
```

### 7.4 WebSocket配置 ([WebSocketConfig.java](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-back/src/main/java/org/example/webback/config/WebSocketConfig.java))

使用 **STOMP over SockJS** 协议:

- **端点**: `/ws` (前端连接地址)
- **消息前缀**: `/app` (客户端发送), `/topic` (服务端广播)
- **订阅主题**: `/topic/alarm` (报警推送)

**推送触发场景**:
Python AI引擎检测到吸烟 → HTTP POST到Java后端 → Java保存数据库 → WebSocket广播给所有在线前端

### 7.5 核心Controller详解

#### 7.5.1 InternalController (内部通信控制器) ⭐⭐⭐

**文件位置**: [InternalController.java](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-back/src/main/java/org/example/webback/controller/InternalController.java)

**作用**: 接收Python AI引擎上报的报警数据 (无需JWT认证)

```java
@RestController
@RequestMapping("/api/internal")  // 内部接口前缀
public class InternalController {

    @PostMapping("/alarm/report")
    public Result report(@RequestBody AlarmReportDTO dto) {
        // 1. DTO → Entity转换
        Alarm alarm = new Alarm();
        BeanUtil.copyProperties(dto, alarm);
        
        // 2. 设置默认值
        alarm.setAuditStatus(0);  // 待审核
        alarm.setCreatedAt(LocalDateTime.now());
        
        // 3. 保存到数据库
        alarmService.save(alarm);
        
        // 4. 查询设备名称 (用于前端显示)
        Device device = deviceService.getById(dto.getCameraId());
        alarm.setDeviceName(device.getName());
        
        // 5. 📡 WebSocket广播给所有前端！
        messagingTemplate.convertAndSend("/topic/alarm", alarm);
        
        return Result.success();
    }
}
```

**DTO结构** ([AlarmReportDTO.java](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-back/src/main/java/org/example/webback/dto/AlarmReportDTO.java)):
```java
public class AlarmReportDTO {
    private Integer cameraId;      // 摄像头ID
    private String type;           // SMOKING/FIRE
    private Double confidence;     // 置信度
    private String videoUrl;       // 证据视频路径
    private String roiUrl;         // 截图路径
}
```

---

#### 7.5.2 AlarmController (报警管理控制器)

**文件位置**: [AlarmController.java](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-back/src/main/java/org/example/webback/controller/AlarmController.java)

**API列表**:

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| GET | `/api/alerts/pending` | 获取待审核报警列表 (分页) | 已登录 |
| POST | `/api/alerts/{id}/audit` | 提交审核结果 (确认/误报/忽略) | 已登录 |
| GET | `/api/alerts/archive` | 查询历史档案 (支持筛选) | 已登录 |
| DELETE | `/api/alerts/{id}` | 删除报警记录 (物理删除文件) | admin |
| POST | `/api/alerts/report` | 接收Python报警 (旧接口) | 内部 |

**审核接口示例**:
```json
POST /api/alerts/120/audit
{
  "status": 1,        // 1=确认违规, 2=误报, 9=忽略
  "remark": "确认违规"
}
```

---

#### 7.5.3 其他Controller

| Controller | 路径前缀 | 主要功能 |
|------------|---------|---------|
| **AuthController** | `/api/auth` | 登录/登出/获取当前用户 |
| **UserController** | `/api/users` | 用户CRUD/修改密码 |
| **DeviceController** | `/api/devices` | 设备CRUD/状态同步 |
| **SystemController** | `/api/system` | 系统状态/AI开关控制 |

### 7.6 关键Service层

#### SystemMonitorService (系统监控服务) ⭐

**核心变量**:
```java
private boolean globalAiEnabled = false;  // AI引擎全局开关
```

**功能**:
- 维护AI引擎的逻辑开关状态 (Single Source of Truth)
- 提供系统资源监控 (CPU/内存/GPU使用率)
- 同步至Redis缓存供前端查询

---

## 8. AI检测核心模块

### 8.1 YOLO级联检测器 ([detector.py](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-flask/app/core/detector.py)) ⭐⭐⭐

这是整个系统的**核心创新**所在！

#### 8.1.1 设计思想

传统方案的问题：
- ❌ 直接在全图上检测烟头 → 远处烟头像素太小 (<10px)，难以识别
- ❌ 每路视频独立加载模型 → 显存溢出 (OOM)
- ❌ 检测框频繁闪烁 → 用户体验差

**解决方案：双阶段级联检测**

```
原始帧 (1920x1080)
    │
    ▼
┌─────────────────────────┐
│ Stage 1: 全局找人        │  ← YOLOv8s (轻量快速)
│ 检测画面中所有人员        │
│ 输出: 人员边界框 + Track ID│
└──────────┬──────────────┘
           │
           ▼ (取面积最大的Top-N个人)
┌─────────────────────────┐
│ ROI智能裁剪              │  ← 裁切上半身区域 + 30%外扩
│ 覆盖手部动作范围          │
└──────────┬──────────────┘
           │
           ▼ (打包成Batch Tensor)
┌─────────────────────────┐
│ Stage 2: 局部找烟        │  ← 自训练Smoke模型 (高精度)
│ 在高清局部图中识别烟头    │
│ FP16半精度加速           │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ 坐标还原 + 惯性追踪       │  ← 防闪烁平滑
│ 输出最终检测框            │
└─────────────────────────┘
```

#### 8.1.2 核心代码解析

**① 全局单例模式 (解决OOM问题)**:
```python
_DETECTOR_INSTANCE = None
_DETECTOR_LOCK = threading.Lock()

def get_detector():
    global _DETECTOR_INSTANCE
    with _DETECTOR_LOCK:
        if _DETECTOR_INSTANCE is None:
            _DETECTOR_INSTANCE = SmokingDetector()
    return _DECTOR_INSTANCE
```
**效果**: 无论开启多少路监控，显存中仅维护**一份模型权重**

**② Stage 1 - 人员检测 (YOLOv8s)**:
```python
results_p = self.model_person.track(
    frame,
    persist=True,           # 启用追踪 (ByteTrack)
    classes=[0],            # 只检测"人"
    conf=0.30,              # 置信度阈值
    iou=0.5,                # NMS阈值
    imgsz=640,              # 输入尺寸
    half=self.use_half,     # FP16加速
    tracker="bytetrack.yaml"# 追踪器配置
)
```

**③ Stage 2 - Batch ROI检测 (自训练模型)**:
```python
# 裁剪每个人上半身区域
for p in active_persons:
    px1, py1, px2, py2 = p['box']
    pad_w = int(pw * 0.3)  # 左右各外扩30%
    crop_y2 = py1 + int(ph * 0.6)  # 取上半身60%
    roi = frame[crop_y1:crop_y2, crop_x1:crop_x2]
    batch_rois.append(roi)

# 一次性送入GPU (Batch推理)
results_batch = self.model_smoke.predict(
    batch_rois,
    conf=0.7,              # 高置信度阈值
    half=self.use_half,    # FP16
    classes=[0]            # 只检测"烟头"
)
```

**④ 惯性追踪防闪烁**:
```python
# 记忆库: 存储烟头相对于人体的位置
self.smoke_memory[pid] = {
    'rel_box': [rel_x, rel_y, rel_w, rel_h],  # 相对坐标
    'life': 3,                                  # 生命周期 (3帧≈100ms)
    'conf': s_conf                             # 上次置信度
}

# 当漏检时, 用记忆库预测位置 (视觉暂留补全)
if not found_smoke_real and pid in self.smoke_memory:
    mem = self.smoke_memory[pid]
    if mem['life'] > 0:
        mem['life'] -= 1
        # 重建绝对坐标
        pred_x1 = px1 + mem['rel_box'][0]
        # ... 输出预测框
```

#### 8.1.3 关键参数调优

| 参数 | 值 | 说明 |
|------|-----|------|
| `person_conf` | 0.30 | 人员检测置信度 (较低, 避免漏人) |
| `smoke_conf` | 0.70 | 烟头检测置信度 (较高, 减少误报) |
| `max_persons_per_frame` | 5 | 每帧最多处理人数 (限制计算量) |
| `crop_top_ratio` | 0.6 | 裁剪上半身比例 |
| `crop_side_padding` | 0.3 | 左右外扩比例 |
| `grace_frames` | 3 | 惯性追踪生命周期 (帧数) |
| `use_half` | True | FP16半精度加速 |

---

### 8.2 视频流管理器 ([stream_loader.py](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-flask/app/core/stream_loader.py)) ⭐⭐⭐

#### 8.2.1 多线程架构

```
StreamLoader (每个摄像头一个实例)
    │
    ├── Thread 1: _reader_thread()     [视频读取线程]
    │   └── 循环读取RTSP帧 → 更新latest_frame
    │
    ├── Thread 2: _processor_thread()  [AI处理线程]
    │   └── 读取latest_frame → YOLO检测 → 画框 → 录像缓冲
    │
    └── Thread 3: _watchdog_thread()   [看门狗线程]
        └── 监控信号超时 → 标记离线 → 触发重连
```

#### 8.2.2 RTSP连接增强

```python
def _connect(self):
    # 关键修复: 禁用FFmpeg内部多线程 (防止死锁)
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = \
        "rtsp_transport;tcp|stimeout;3000000|threads;1"
    
    self.cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 极低延迟 (1帧缓冲)
```

**解决的问题**:
- ✅ FFmpeg `Assertion fctx->async_lock failed` 崩溃
- ✅ 删除设备后"僵尸线程"残留
- ✅ 移动端摄像头断流重连

#### 8.2.3 报警逻辑

```python
def _handle_alarm_logic(self, frame, detections):
    for cig in cigarettes:  # 遍历检测到的烟头
        event = self.smoke_events[cid]
        event.frame_count += 1
        
        # 连续15帧都检测到 → 触发报警
        if event.frame_count >= self.alarm_threshold_frames:  # 15帧≈0.6秒
            if not self._is_in_cooldown(cx, cy):  # 冷却检查 (5分钟/200px)
                # 1. 保存快照 (带红色检测框)
                evidence_frame = self._draw_ui(frame.copy(), detections)
                
                # 2. 开始录像 (前2秒+后5秒)
                self.recorder.start_recording(video_name, post_record_sec=5)
                
                # 3. 异步通知Java后端 (不阻塞主线程)
                threading.Thread(target=notify_java, daemon=True).start()
```

**报警条件**:
- 连续 **15帧** (~0.6秒) 都检测到烟头
- 不在 **冷却期** 内 (同一位置5分钟内不重复报警)
- 距离上次报警位置 > **200px**

---

### 8.3 证据录制模块 ([recorder.py](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-flask/app/core/recorder.py))

**功能**:
- **环形缓冲区**: 始终保存最近150帧 (~5秒@30fps)
- **触发录制**: 报警时保存前2秒 + 后5秒 = 7秒视频
- **输出格式**: MP4 (H.264编码)
- **截图保存**: JPG (带AI检测框)

**存储路径**:
```
app/static/evidence/
├── snapshots/          # 报警截图
│   └── alarm_cam41__p17_1769247242.jpg
└──                    # 报警视频
    └── alarm_cam41__p17_1769247242.mp4
```

---

## 9. 核心业务流程

### 9.1 完整报警流程 (时序图)

```
时间轴 →

[摄像头]     [Python AI]              [Java后端]           [前端]
   │             │                      │                   │
   │◄──RTSP流────┤                      │                   │
   │             │                      │                   │
   │  Frame 1-N  │                      │                   │
   │────────────►│                      │                   │
   │             │                      │                   │
   │             │ Stage1: 找人(YOLOv8s)│                   │
   │             │ Stage2: 找烟(Smoke)  │                   │
   │             │                      │                   │
   │             │ ◄─连续15帧检测到──► │                   │
   │             │                      │                   │
   │             │ 保存截图(JPG)        │                   │
   │             │ 开始录像(MP4)        │                   │
   │             │                      │                   │
   │             │ ──HTTP POST────────► │                   │
   │             │ /api/internal/alarm/ │                   │
   │             │ report               │                   │
   │             │  {cameraId, conf,    │                   │
   │             │   videoUrl, roiUrl}  │                   │
   │             │                      │                   │
   │             │                      │ 保存到MySQL        │
   │             │                      │ (audit_status=0)  │
   │             │                      │                   │
   │             │                      │ ──WebSocket─────► │
   │             │                      │ /topic/alarm      │
   │             │                      │                   │
   │             │                      │              显示通知弹窗
   │             │                      │              红色边框闪烁8秒
   │             │                      │                   │
   │             │                      │                   │
   │             │                      │ ◄─人工点击审核─── │
   │             │                      │ POST /audit/{id}  │
   │             │                      │ {status:1或2}     │
   │             │                      │                   │
   │             │                      │ 更新audit_status   │
   │             │                      │ (1=确认/2=误报)    │
```

### 9.2 设备管理流程

```
管理员添加设备 (Web界面)
    ↓
POST /api/devices (Java后端)
    ↓
保存到 devices 表 (enabled=1)
    ↓
Python轮询设备列表 (每N秒)
    ↓
GET /api/monitor/devices
    ↓
发现新设备 → StreamManager.add_camera()
    ↓
创建StreamLoader实例 → 连接RTSP → 启动3个线程
    ↓
视频流正常 → 更新status=1 → 推送到前端
```

### 9.3 AI开关控制流程

```
管理员点击 "启动AI引擎" (SystemControl页面)
    ↓
POST /api/system/ai-toggle (Java后端)
    ↓
SystemMonitorService.globalAiEnabled = true
    ↓
同步到Redis缓存
    ↓
Python轮询系统状态
    ↓
GET /api/system/status
    ↓
StreamManager.set_global_ai(true)
    ↓
遍历所有StreamLoader → loader.set_ai_status(true)
    ↓
_processor_thread开始执行YOLO检测
```

---

## 10. API接口文档

### 10.1 认证相关 (Auth)

| 方法 | 路径 | 描述 | 请求体 | 响应 |
|------|------|------|--------|------|
| POST | `/api/auth/login` | 用户登录 | `{username, password}` | `{token, user}` |
| POST | `/api/auth/logout` | 用户登出 | - | `{msg}` |
| GET | `/api/auth/me` | 获取当前用户 | - | `{user}` |

### 10.2 用户管理 (Users) [admin]

| 方法 | 路径 | 描述 | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | `/api/users` | 用户列表 (分页) | `?page=1&size=10` | `{list, total}` |
| POST | `/api/users` | 添加用户 | `{username, password, role}` | `{user}` |
| PUT | `/api/users/{id}` | 更新用户 | `{username, role, status}` | `{msg}` |
| DELETE | `/api/users/{id}` | 删除用户 | - | `{msg}` |

### 10.3 设备管理 (Devices) [admin]

| 方法 | 路径 | 描述 | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | `/api/devices` | 设备列表 | - | `[{device}]` |
| POST | `/api/devices` | 添加设备 | `{name, rtsp_url}` | `{device}` |
| PUT | `/api/devices/{id}` | 更新设备 | `{name, rtsp_url, enabled}` | `{msg}` |
| DELETE | `/api/devices/{id}` | 删除设备 | - | `{msg}` |
| POST | `/api/devices/sync-status` | 同步设备状态 (Python调用) | `{id, status}` | `{msg}` |

### 10.4 报警管理 (Alarms)

| 方法 | 路径 | 描述 | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | `/api/alerts/pending` | 待审核列表 | `?page=1&size=20` | `{list, total, pages}` |
| POST | `/api/alerts/{id}/audit` | 提交审核 | `{status, remark}` | `{msg}` |
| GET | `/api/alerts/archive` | 历史档案 | `?deviceId=&status=&startTime=` | `{list, total}` |
| DELETE | `/api/alerts/{id}` | 删除记录 [admin] | - | `{msg}` |
| POST | `/api/alerts/report` | Python上报 (旧) | `{deviceId, type, conf...}` | `{msg}` |

### 10.5 内部接口 (Internal) [无需JWT]

| 方法 | 路径 | 描述 | 请求体 | 响应 |
|------|------|------|--------|------|
| POST | `/api/internal/alarm/report` | Python报警上报 | `AlarmReportDTO` | `{msg}` |
| GET | `/api/internal/devices` | 设备列表 (Python同步) | - | `[{device}]` |

### 10.6 系统控制 (System) [admin]

| 方法 | 路径 | 描述 | 响应 |
|------|------|------|------|
| GET | `/api/system/status` | 系统状态 | `{global_ai, streams, cpu, memory}` |
| POST | `/api/system/ai-toggle` | 切换AI开关 | `{msg}` |
| GET | `/api/system/resources` | 硬件资源 | `{cpu%, memory%, gpu%}` |

### 10.7 Python Flask API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/monitor/stream/{id}` | MJPEG视频流 (用于img标签) |
| POST | `/api/monitor/start` | 启动指定摄像头 |
| POST | `/api/monitor/stop` | 停止指定摄像头 |
| POST | `/api/monitor/ai-toggle` | 切换AI检测开关 |
| GET | `/api/system/status` | Python引擎状态 |

---

## 11. 配置说明

### 11.1 Java后端配置 ([application.yml](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-back/src/main/resources/application.yml))

```yaml
server:
  port: 8080  # 服务端口

spring:
  datasource:
    url: jdbc:mysql://localhost:3308/smart_campus_smoking?...
    username: root
    password: 123456  # ⚠️ 必须修改!
    
  data:
    redis:
      host: localhost
      port: 6379
      
  mongodb:
    uri: mongodb://localhost:27017/smart_campus_logs

mybatis-plus:
  configuration:
    log-impl: org.apache.ibatis.logging.stdout.StdOutImpl  # SQL日志
    map-underscore-to-camel-case: true  # 下划线转驼峰

app:
  python-static-path: D:/engineering/.../web-flask/app  # Python静态文件路径
```

### 11.2 Python Flask配置 ([config.py](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-flask/config.py))

```python
class Config:
    # MySQL连接
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:123456@localhost:3308/smart_campus_smoking'
    
    # Java后端接口地址
    JAVA_API_URL = "http://localhost:8080/api/internal/alarm/report"
    JAVA_DEVICE_LIST_URL = "http://localhost:8080/api/monitor/devices"
    
    # 视频流缓冲 (150帧 ≈ 5秒)
    BUFFER_SIZE = 150
    
    # JWT密钥
    SECRET_KEY = 'hard-to-guess-string'  # ⚠️ 生产环境必须修改!
```

### 11.3 前端环境变量 (.env)

```env
VITE_APP_BASE_API=http://localhost:8080   # Java后端
VITE_APP_AI_API=http://localhost:5000     # Python AI引擎
```

---

## 12. 开发指南

### 12.1 环境准备

#### 必需软件:

| 软件 | 版本 | 用途 |
|------|------|------|
| JDK | 17 | Java运行环境 |
| Node.js | 16+ | 前端构建 |
| Python | 3.9+ | AI引擎 |
| MySQL | 8.0 | 数据库 |
| Redis | 6.x | 缓存 (可选) |
| MongoDB | 5.x | 日志存储 (可选) |
| CUDA | 11.x | GPU加速 (必需) |
| NVIDIA Driver | 最新 | GPU驱动 |

#### GPU要求:
- **最低**: GTX 1060 6GB (可运行, 但路数受限)
- **推荐**: RTX 3060 12GB (支持4路以上并发)
- **理想**: RTX 3080/4090 (更多路数 + 更低延迟)

### 12.2 启动顺序

**⚠️ 重要: 必须按以下顺序启动!**

```
1️⃣ 启动 MySQL (端口 3308)
   ↓
2️⃣ 初始化数据库
   mysql -u root -p123456 -P 3308 < db/init.sql
   ↓
3️⃣ 启动 Redis (端口 6379) [可选]
   ↓
4️⃣ 启动 Java后端
   cd web-back
   mvn spring-boot:run
   # 或 IDE运行 WebBackApplication.java
   # 服务地址: http://localhost:8080
   ↓
5️⃣ 启动 Python AI引擎
   cd web-flask
   pip install -r requirements.txt
   python run.py
   # 服务地址: http://localhost:5000
   ↓
6️⃣ 启动前端开发服务器
   cd web-vue
   npm install
   npm run dev
   # 服务地址: http://localhost:5173
   ↓
7️⃣ 打开浏览器访问 http://localhost:5173
   默认账号: admin / admin123 (具体密码见init.sql)
```

### 12.3 开发调试技巧

#### Java后端调试:
```bash
# 查看SQL日志 (已在application.yml中开启)
# 控制台会打印所有执行的SQL语句

# 测试API (使用curl或Postman)
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'
```

#### Python AI引擎调试:
```bash
# 查看GPU使用情况
nvidia-smi

# 查看Python日志输出 (控制台)
# 包含: 连接状态/检测结果/报警信息
```

#### 前端调试:
```bash
# Vue DevTools浏览器插件 (必备!)
# 可以查看Pinia状态/组件树/路由

# 网络请求查看 (F12 → Network)
# 检查API调用是否成功
```

### 12.4 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 前端无法连接后端 | CORS错误 | 检查WebMvcConfig配置 |
| Python连接RTSP失败 | 网络问题/摄像头离线 | 检查rtsp_url是否正确, 摄像头是否在线 |
| GPU显存溢出(OOM) | 路数过多/分辨率过高 | 减少接入路数, 降低recorder分辨率 |
| WebSocket断开 | 网络波动 | 前端有自动重连机制 (5秒间隔) |
| 报警不上报 | Java后端未启动 | 检查8080端口是否在监听 |
| 检测框闪烁 | 惯性追踪参数不当 | 调整grace_frames (默认3) |

---

## 13. 已知问题与优化建议

### 13.1 当前已知问题

| 问题 | 严重程度 | 影响 | 状态 |
|------|---------|------|------|
| 密码硬编码在配置文件中 | 🔴 高 | 安全风险 | 待修复 |
| SECRET_KEY使用默认值 | 🔴 高 | JWT安全风险 | 待修复 |
| 无HTTPS加密传输 | 🟡 中 | 数据泄露风险 | 待配置 |
| 缺少单元测试 | 🟡 中 | 代码质量风险 | 待补充 |
| 无日志持久化 | 🟢 低 | 问题排查困难 | 可选 |
| 前端无国际化(i18n) | 🟢 低 | 不支持多语言 | 可选 |

### 13.2 性能优化建议

#### 短期优化 (1-2周):

1. **数据库优化**
   ```sql
   -- 为常用查询添加复合索引
   CREATE INDEX idx_alarms_camera_status ON alarms(camera_id, audit_status, created_at);
   
   -- 分区表 (按月分区, 提升历史查询性能)
   ALTER TABLE alarms PARTITION BY RANGE (TO_DAYS(created_at)) (...);
   ```

2. **Redis缓存策略**
   - 设备列表缓存 (TTL: 10秒)
   - 系统状态缓存 (TTL: 3秒)
   - 用户信息缓存 (TTL: 30分钟)

3. **前端优化**
   - 虚拟滚动 (设备列表超过50项时)
   - 图片懒加载 (历史档案页面)
   - WebSocket心跳检测优化

#### 中期优化 (1个月):

4. **AI模型优化**
   - TensorRT推理加速 (延迟再降50%)
   - 模型量化 (INT8, 进一步减少显存)
   - 动态分辨率 (根据距离自适应)

5. **架构升级**
   - 消息队列 (RabbitMQ/Kafka) 解耦Python和Java
   - 微服务拆分 (独立部署AI服务)
   - 容器化部署 (Docker + Kubernetes)

#### 长期规划 (3个月+):

6. **功能扩展**
   - 多算法融合 (烟火检测 + 行为分析)
   - 边缘计算 (将AI推理下沉到摄像头端)
   - 移动端APP (React Native/Flutter)
   - 数据大屏 (ECharts 3D可视化)

---

## 14. 后续开发路线图

### Phase 1: 稳定性加固 (Week 1-2)

- [ ] 修复安全问题 (密码加密/HTTPS/JWT密钥)
- [ ] 添加单元测试 (覆盖率>60%)
- [ ] 完善异常处理和日志记录
- [ ] 编写API文档 (Swagger/OpenAPI)

### Phase 2: 功能完善 (Week 3-4)

- [ ] 报警规则配置 (灵敏度/冷却时间可调)
- [ ] 批量审核 (快捷键操作)
- [ ] 数据导出 (Excel/PDF报表)
- [ ] 操作日志审计

### Phase 3: 性能提升 (Week 5-6)

- [ ] TensorRT模型转换与部署
- [ ] Redis缓存全面接入
- [ ] 数据库读写分离
- [ ] CDN加速 (静态资源)

### Phase 4: 扩展功能 (Week 7-8)

- [ ] 多租户支持 (多个校园隔离)
- [ ] 短信/邮件告警通知
- [ ] 移动端适配 (响应式布局)
- [ ] 离线模式 (本地存储 + 同步)

### Phase 5: 生产部署 (Week 9-10)

- [ ] Docker容器化 (三服务编排)
- [ ] Nginx反向代理 + 负载均衡
- [ ] CI/CD流水线 (GitHub Actions)
- [ ] 监控告警 (Prometheus + Grafana)

---

## 附录A: 关键文件清单

### 必读文件 (按优先级):

1. 📄 [README.md](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/README.md) - 项目总览
2. 🔧 [application.yml](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-back/src/main/resources/application.yml) - Java配置
3. 🔧 [config.py](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-flask/config.py) - Python配置
4. 🤖 [detector.py](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-flask/app/core/detector.py) - AI核心
5. 📹 [stream_loader.py](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-flask/app/core/stream_loader.py) - 视频流管理
6. 🖥️ [Monitor.vue](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-vue/src/views/Monitor.vue) - 主页面
7. 📡 [InternalController.java](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/web-back/src/main/java/org/example/webback/controller/InternalController.java) - 报警接收
8. 🗄️ [init.sql](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/db/init.sql) - 数据库初始化

### 开发日志 (参考):

- 📝 [开发计划.md](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/development%20log/开发计划.md) - 8周开发计划
- 📝 [springboot迁移.md](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/development%20log/springboot迁移.md) - Java-Python集成经验
- 📝 [抽烟监测优化.md](file:///d:/engineering/Smart%20No-Smoking%20Campus%20System/development%20log/抽烟监测优化.md) - 算法优化记录

---

## 附录B: 术语表

| 术语 | 英文 | 解释 |
|------|------|------|
| 级联检测 | Cascade Detection | 两阶段检测: 先找人, 再找烟 |
| ROI | Region of Interest | 感兴趣区域 (人物上半身裁剪) |
| Batch推理 | Batch Inference | 多张图片打包一次送入GPU |
| FP16 | Half Precision | 半精度浮点 (16位, 加速推理) |
| 惯性追踪 | Inertial Smoothing | 利用记忆库补全漏检, 防止闪烁 |
| ByteTrack | - | 多目标追踪算法 (比BoT-SORT更稳定) |
| MJPEG | Motion JPEG | 视频流格式 (逐帧JPEG) |
| STOMP | Simple Text Oriented Messaging Protocol | WebSocket消息协议 |
| JWT | JSON Web Token | 无状态认证令牌 |
| OOM | Out of Memory | 显存溢出 |
| RTSP | Real Time Streaming Protocol | 实时流媒体协议 |

---

## 附录C: 联系与支持

**项目仓库**: 本地路径 `d:\engineering\Smart No-Smoking Campus System`

**技术栈文档**:
- Vue 3: https://vuejs.org/
- Spring Boot: https://spring.io/projects/spring-boot
- YOLOv8: https://docs.ultralytics.com/
- Element Plus: https://element-plus.org/

---

**报告生成时间**: 2026-04-22  
**报告版本**: v1.0  
**适用项目版本**: v3.3 (最新)

---

> 📌 **提示**: 本报告涵盖了项目的所有核心内容, 建议后续开发时随时查阅。如需了解某个模块的更详细信息, 请参考对应的源代码文件和注释。
