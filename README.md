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
- YOLOv8-Pose
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
│   │   │   ├── auth.py          # 登录认证
│   │   │   ├── monitor.py       # 实时流与设备管理
│   │   │   └── alert.py         # 报警管理
│   │   ├── core/                # 核心算法与工具
│   │   │   ├── stream_loader.py # 视频流加载与环形缓存
│   │   │   ├── detector_pose.py # YOLO-Pose 封装
│   │   │   ├── detector_cls.py  # CNN 分类器封装
│   │   │   └── recorder.py      # 证据视频合成
│   │   ├── models/              # SQLAlchemy 模型
│   │   └── sockets/             # WebSocket 事件处理
│   ├── env/                     # 虚拟环境
│   ├── static/                  # 静态资源
│   │   ├── evidence/            # 报警视频 (.mp4)
│   │   └── snapshots/           # 抓拍图片 (.jpg)
│   ├── config.py                # 配置文件
│   └── run.py                   # 启动入口
└── web-vue/                     # 前端工程
    ├── src/
    │   ├── api/                 # Axios 接口层
    │   │   ├── user.ts
    │   │   ├── device.ts
    │   │   └── alarm.ts
    │   ├── components/          # 公共组件
    │   │   ├── VideoGrid.vue    # 监控宫格组件
    │   │   └── AuditModal.vue   # 审核弹窗组件
    │   ├── layout/              # 页面布局
    │   ├── router/              # 路由配置
    │   ├── store/               # Pinia 状态管理
    │   │   ├── user.ts
    │   │   └── socket.ts
    │   ├── utils/               # 工具函数
    │   ├── views/               # 页面视图
    │   │   ├── Dashboard.vue    # 数据大屏
    │   │   ├── Monitor.vue      # 实时监控墙
    │   │   └── AlarmAudit.vue   # 报警审核
    │   └── App.vue
    ├── .env                     # 环境变量
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

### 吸烟检测流程
1. **姿态初筛**：使用 YOLOv8-Pose 检测人体关键点，计算手腕与鼻子距离
2. **局部精细分类**：截取头部扩充区域，送入 CNN 进行精细分类
3. **报警判断**：若分类结果为吸烟且置信度 > 0.85，触发报警
4. **证据录制**：自动合成 10 秒视频（前 5 秒缓存 + 后 5 秒实时流）

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
