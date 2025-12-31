

# 高校无烟校园智能监测系统 - 概要设计说明书

| 项目名称 | 高校无烟校园智能监测系统 (Smart No-Smoking Campus System) |
| --- | --- |
| **文档编号** | HLD-2025-NSCS-V1.0 |
| **版本号** | V 1.0 |
| **设计日期** | 2025年12月30日 |
| **密级** | 内部公开 |

---

## 1. 引言

### 1.1 设计目标

本设计旨在构建一个高内聚、低耦合、易扩展的智能化视频监控系统。重点解决**多路视频流并发处理**、**级联算法的工程化落地**以及**证据视频的实时截取与存储**问题。

### 1.2 设计原则

* **模块化：** 算法推理、业务逻辑、Web服务分离，便于独立调试。
* **实时性：** 保证报警延迟控制在秒级。
* **复用性：** 充分利用开源生态（YOLO, Flask, Vue），避免重复造轮子。

---

## 2. 系统总体架构设计

### 2.1 逻辑架构图 (Layered Architecture)

系统采用经典的 **分层架构**，自下而上分为：硬件接入层、核心算法层、业务逻辑层、表现层。

1. **表现层 (Presentation Layer):**
* **Web 前端 (Vue3 + Element Plus):** 提供实时大屏、报警弹窗、视频回放、数据报表。


2. **业务服务层 (Business Logic Layer):**
* **Web API (Flask):** 处理前端请求、用户认证、设备管理。
* **消息推送 (WebSocket):** 实现报警信息的实时推送。


3. **核心算法层 (AI Engine Layer):**
* **视频管道 (Video Pipeline):** 负责 RTSP 拉流、解码、环形缓存。
* **推理引擎 (Inference Engine):**
* *Stage 1:* YOLOv8-Pose (姿态行为初筛).
* *Stage 2:* CNN Classifier (局部吸烟确认).
* *Auxiliary:* YOLOv8-Detect (火焰烟雾检测).




4. **数据持久层 (Data Layer):**
* **MySQL:** 存储结构化数据（用户、设备、报警记录）。
* **File System:** 存储非结构化数据（证据视频片段 .mp4、抓拍图片 .jpg）。



### 2.2 物理部署架构

* **边缘计算节点 (Edge Server):** 部署 Python 后端与 AI 模型，直接接入校园局域网内的摄像头。
* **客户端 (Client):** 浏览器（PC端/移动端），通过 HTTP/WebSocket 访问服务器。

---

## 3. 核心模块划分与设计

系统核心划分为四大子系统模块。

### 3.1 视频采集与缓存模块 (Video Acquisition)

这是系统的“眼睛”，负责从摄像头获取画面并为 AI 准备数据。

* **功能描述：**
* 使用 `OpenCV` 或 `FFmpeg` 拉取 RTSP 流。
* 维护一个 **定长双端队列 (deque)** 作为“环形缓冲区”，始终保存当前时刻前 5 秒的帧数据。
* 负责视频帧的格式转换 (BGR -> RGB)。


* **关键技术：** `cv2.VideoCapture`, `collections.deque`, 多线程 (`threading`).

### 3.2 AI 智能推理模块 (Intelligent Analysis)

这是系统的“大脑”，负责实现级联检测算法。

* **功能描述：**
* **姿态分析器 (Pose Analyzer):** 运行 YOLOv8-Pose，计算手腕与嘴部欧氏距离，输出 `Is_Suspected` 信号。
* **ROI 裁剪器 (ROI Cropper):** 当 `Is_Suspected=True`，裁剪头部区域。
* **行为验证器 (Action Verifier):** 运行 CNN 分类器，判定是否存在香烟。
* **多任务调度:** 按时间片轮询，偶尔插入一次火灾检测。


* **关键技术：** `Ultralytics YOLO`, `PyTorch`, `NumPy`.

### 3.3 报警取证模块 (Evidence Generator)

这是系统的“记录员”，负责固化证据。

* **功能描述：**
* 接收 AI 模块的报警触发信号。
* **回溯录制：** 从环形缓冲区导出前 5 秒视频。
* **延时录制：** 继续录制后 5 秒视频。
* **合成存储：** 使用 `cv2.VideoWriter` 合成 10 秒 MP4 文件，写入磁盘。


* **关键技术：** 视频编解码 (Codec), 文件 I/O.

### 3.4 业务管理模块 (Business Management)

这是系统的“管家”，负责对外交互。

* **功能描述：**
* **设备管理：** 增删改查摄像头信息（RTSP地址、位置名称）。
* **报警管理：** 提供 API 供前端查询报警列表、更新审核状态。
* **实时推流：** 将 OpenCV 处理后的带有画框的视频流，通过 `Response(generate(), mimetype='multipart/x-mixed-replace...')` 推送给前端 `<img>` 标签。



---

## 4. 关键技术选型 (Tech Stack)

| 类别 | 技术/工具 | 选型理由 |
| --- | --- | --- |
| **前端框架** | **Vue.js 3 + Vite** | 响应式数据绑定，开发效率高，适合构建单页应用(SPA)。 |
| **UI 组件库** | **Element Plus** | 提供成熟的后台管理组件（表格、弹窗、表单），美观且易用。 |
| **后端框架** | **Python Flask** | 轻量级，易于集成 PyTorch 等 AI 库，适合中小型项目快速开发。 |
| **AI 框架** | **PyTorch + Ultralytics** | YOLOv8 生态完善，推理速度快，Pose 模型精度高。 |
| **CV 库** | **OpenCV (Python)** | 视频流处理的标准库，功能强大。 |
| **数据库** | **MySQL 8.0** | 关系型数据库标准，存储报警元数据稳定可靠。 |
| **ORM 框架** | **SQLAlchemy** | 简化数据库操作，避免手写 SQL 语句。 |
| **视频存储** | **本地文件系统** | 简单直接，无需搭建复杂的对象存储服务（OSS），适合校内局域网环境。 |

---

## 5. 数据库设计 (Database Design)

仅列出最核心的 **报警记录表 (alarms)** 设计。

| 字段名 (Field) | 类型 (Type) | 描述 (Description) |
| --- | --- | --- |
| `id` | INT (PK) | 自增主键 |
| `camera_id` | INT (FK) | 关联摄像头ID |
| `event_type` | ENUM | 'SMOKING' (吸烟), 'FIRE' (火灾) |
| `alert_time` | DATETIME | 报警触发时间 |
| `img_path` | VARCHAR(255) | 抓拍图片存储路径 |
| `video_path` | VARCHAR(255) | 10秒证据视频存储路径 |
| `status` | INT | 0:待审核, 1:已确认, 2:已忽略 |
| `reviewer` | VARCHAR(50) | 审核人姓名（审核后填写） |

---

## 6. 接口设计原则 (API Design)

系统 API 遵循 RESTful 规范。

* **GET /api/video_feed/<cam_id>**: 获取指定摄像头的实时监控流（MJPEG流）。
* **GET /api/alarms**: 获取报警历史记录列表（支持分页、按时间筛选）。
* **POST /api/alarms/<id>/audit**: 审核报警（提交确认或忽略的操作）。
* **GET /api/stats/summary**: 获取今日报警统计数据（用于大屏展示）。

---

## 7. 补充说明 (Implementation Notes)

1. **并发处理方案：**
* 由于 Python 的 GIL 锁限制，建议使用 **多进程 (Multiprocessing)** 而非多线程来运行 AI 推理模块，以充分利用多核 CPU。每个摄像头作为一个独立的进程运行。
* Web 服务（Flask）作为主进程，通过 `Queue` 与 AI 进程通信。


2. **走廊透视优化：**
* 在代码中设定 `MIN_BOX_HEIGHT = 50`。当检测到的人体框高度小于 50 像素时，视为距离太远，直接跳过 Stage 2 的分类，避免因像素模糊导致的误报。

