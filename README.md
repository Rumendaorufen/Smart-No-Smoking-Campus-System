# 高校无烟校园智能监测系统

## 项目简介
高校无烟校园智能监测系统是一套基于 B/S 架构的智能监控系统，旨在通过 AI 技术实时监测校园内的吸烟行为，实现秒级报警推送及完整的证据链回溯。系统支持多路视频流并发处理，为校园禁烟管理提供高效、智能的解决方案。

## 技术栈

### 前端
- Vue 3 (Composition API)
- TypeScript
- Vite
- Element Plus
- Pinia
- ECharts

### 后端
- Python 3.9
- Flask
- Flask-SocketIO (WebSocket)

### AI 核心
- PyTorch
- YOLOv8 (Object Detection)
- OpenCV
- Multiprocessing

### 数据库
- MySQL 8.0 (业务数据)
- Local FS (视频/图片存储)

## 系统架构

```mermaid
[浏览器/前端 Vue3]  <--(WebSocket 报警推送)--  [Flask Web 服务]  <--(Queue)--  [AI 独立进程]
       |                                          |                             |
    (HTTP请求)                                (SQL读写)                     (RTSP拉流)
       |                                          |                             |
       v                                          v                             v
[Nginx/Web服务器]  ------------------------>  [MySQL 数据库]             [监控摄像头]
                                                  ^
                                                  |
                                            [文件系统 (视频/图片)]
```

## 项目结构

```
Smart No-Smoking Campus System/
├── report/                      # 项目文档
│   ├── 可行性分析报告.md
│   ├── 概要设计说明书.md
│   ├── 详细设计说明书.md
│   └── 软件需求规格说明书.md
├── web-flask/                   # 后端工程
│   ├── app/
│   │   ├── api/                 # API 蓝图
│   │   │   ├── alert.py         # 报警管理
│   │   │   ├── auth.py          # 登录认证
│   │   │   └── monitor.py       # 实时流与设备管理
│   │   ├── core/                # 核心算法与工具
│   │   │   ├── best.pt          # 最佳模型权重
│   │   │   ├── detector.py      # 统一检测器封装
│   │   │   ├── detector_cls.py  # CNN 分类器封装 (历史版本)
│   │   │   ├── detector_pose.py # YOLO-Pose 封装 (历史版本)
│   │   │   ├── recorder.py      # 证据视频合成
│   │   │   └── stream_loader.py # 视频流加载与环形缓存
│   │   ├── models/              # SQLAlchemy 模型
│   │   │   ├── __init__.py
│   │   │   ├── db_config.py     # 数据库配置
│   │   │   └── devices.py       # 设备模型
│   │   ├── sockets/             # WebSocket 事件处理
│   │   │   └── events.py        # Socket 事件定义
│   │   ├── __init__.py
│   │   └── model.py             # 模型管理
│   ├── config.py                # 配置文件
│   ├── run.py                   # 启动入口
│   ├── yolov8n-pose.pt          # YOLOv8-Pose 模型权重
│   └── yolov8n.pt               # YOLOv8 目标检测模型权重
└── web-vue/                     # 前端工程
    ├── .vscode/                 # VS Code 配置
    │   └── extensions.json
    ├── public/                  # 公共资源
    │   └── vite.svg
    ├── src/
    │   ├── api/                 # Axios 接口层
    │   │   └── device.ts        # 设备管理 API
    │   ├── assets/              # 静态资源
    │   │   └── vue.svg
    │   ├── components/          # 公共组件
    │   │   └── HelloWorld.vue   # 示例组件
    │   ├── views/               # 页面视图
    │   │   └── Monitor.vue      # 实时监控墙
    │   ├── App.vue              # 根组件
    │   ├── main.ts              # 应用入口
    │   └── style.css            # 全局样式
    ├── .env                     # 环境变量
    ├── .gitignore               # Git 忽略文件
    ├── index.html               # HTML 模板
    ├── package.json             # 项目依赖
    ├── package-lock.json        # 依赖锁定文件
    ├── tsconfig.json            # TypeScript 配置
    ├── tsconfig.app.json        # TypeScript 应用配置
    ├── tsconfig.node.json       # TypeScript Node 配置
    └── vite.config.ts           # Vite 配置
```

## 快速开始

### 前提条件
- Python 3.9+
- Node.js 16+
- MySQL 8.0
- CUDA 11.0+ (可选，用于 GPU 加速)

### 后端部署

1. 进入后端目录
```bash
cd web-flask
```

2. 创建并激活虚拟环境
```bash
python -m venv env
# Windows
env\Scripts\activate
# Linux/macOS
source env/bin/activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置数据库
修改 `config.py` 中的数据库连接信息

5. 启动服务
```bash
python run.py
```

### 前端部署

1. 进入前端目录
```bash
cd web-vue
```

2. 安装依赖
```bash
npm install
```

3. 启动开发服务器
```bash
npm run dev
```

4. 构建生产版本
```bash
npm run build
```

## 功能模块

### 1. 实时监控
- 多路视频流并发展示
- 智能吸烟行为检测
- 实时报警闪烁提示
- 支持摄像头切换与缩放

### 2. 报警管理
- 秒级报警推送
- 证据视频自动录制
- 报警信息分类管理
- 支持报警审核与处理

### 3. 数据统计
- 实时数据大屏
- 历史报警记录查询
- 统计报表生成
- 可视化图表展示

### 4. 设备管理
- 摄像头设备管理
- 视频流配置
- 设备状态监控

## API 接口

### 实时流
- `GET /api/v1/monitor/stream/<device_id>` - 获取设备视频流

### 报警管理
- `GET /api/v1/alerts?page=1&status=0` - 获取待审核报警列表
- `POST /api/v1/alerts/<id>/audit` - 提交审核结果

### 统计数据
- `GET /api/v1/stats/dashboard` - 获取大屏统计数据

## 核心算法

### 算法迭代说明
项目早期版本采用"Pose 关键点 + CNN 分类"方案，但在处理"手部遮挡"、"进食"等复杂场景时存在较高误报率。当前版本已全面升级为 **YOLOv8 端到端目标检测** 方案，通过引入负样本训练（Hard Negative Mining），显著提升了对吸烟行为的抗干扰识别能力。

### 吸烟检测流程
1. **视频流预处理**：对 RTSP 视频流进行抽帧处理（降低计算负载），调整分辨率至模型输入标准（640x640）。
2. **端到端检测**：使用微调后的 YOLOv8n/s 模型对图像进行单阶段推理，直接输出物体类别（cigarette）及边界框。
3. **置信度过滤**：
   - 过滤置信度 < 0.25 的低质量目标。
   - 针对特定困难样本（如模糊、远距离），结合时序逻辑（连续 N 帧检测到）进行二次确认，防止闪烁误报。
4. **报警触发**：当画面中检测到"cigarette"标签且置信度达标时，立即通过 WebSocket 向前端推送报警信息。
5. **证据固化**：后台进程自动截取报警前 5 秒至后 5 秒的视频流，合成 mp4 文件并写入数据库。

## 部署说明

### 生产环境部署

1. **后端部署**
   - 使用 Gunicorn + Nginx 部署 Flask 应用
   - 配置 Supervisor 管理进程
   - 开启多进程处理 AI 推理任务

2. **前端部署**
   - 将构建产物部署到 Nginx 服务器
   - 配置 HTTPS
   - 启用 gzip 压缩

3. **数据库优化**
   - 定期清理过期报警数据
   - 建立合理索引
   - 配置主从复制（可选）

### 性能优化建议
- 前端使用 `v-show` 而非 `v-if` 切换视频格
- 后端将视频合成任务放在独立进程中执行
- 调整 AI 推理的 batch size 和置信度阈值
- 合理配置视频流的分辨率和帧率

## 开发指南

### 代码规范
- 前端：遵循 ESLint + Prettier 规范
- 后端：遵循 PEP 8 规范

### 开发流程
1. 从 develop 分支创建 feature 分支
2. 完成功能开发并编写测试
3. 提交代码并发起 Pull Request
4. 代码审查通过后合并到 develop 分支
5. 定期从 develop 分支合并到 master 分支

## 许可证

本项目采用 MIT 许可证，详情请查看 LICENSE 文件。

## 联系方式

- 项目负责人：[负责人姓名]
- 技术支持：[支持邮箱]
- 文档地址：[文档链接]

## 更新日志

### v3.1 (2026-01-10)
- **算法重构**：弃用 Pose+Cls 方案，全面迁移至 YOLOv8 目标检测方案。
- **精度提升**：解决了手部遮挡、进食等场景下的误报问题。
- **性能优化**：引入 GPU (CUDA) 加速支持，大幅提升推理帧率。

### v3.0 (2025-12-30)
- 全栈整合版发布
- 优化了 AI 检测算法
- 新增数据大屏功能
- 改进了前端交互体验

### v2.0 (2025-11-15)
- 实现了 WebSocket 实时推送
- 优化了视频流处理性能
- 新增了设备管理模块

### v1.0 (2025-10-01)
- 项目初始化
- 实现了基础的吸烟检测功能
- 完成了前后端基础架构搭建
