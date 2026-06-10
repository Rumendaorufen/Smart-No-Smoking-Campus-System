# 200+ 路摄像头升级设计方案

记录时间：2026-06-10
基于版本：当前 4 路摄像头架构

## 问题回顾

当前系统运行在 4 路摄像头基线，升级到 200+ 路时面临 11 个核心痛点，根因链路如下：

```
GPU 算力不够 → 推理延迟高 → 帧缓冲堆积 → 内存爆
                   ↓
              漏检/误报增多
                   ↓
              报警频率异常 → 磁盘 IO 压力 → MySQL 响应慢
                                   ↓
              前端轮询全量 ←── Java 线程排队 → WebSocket 延迟
                                   ↓
              前端 MJPEG 连接上限 → 画面空白
```

## 三阶段演进策略

### Phase 1 — 急速救火（P0，2 周内）

目标：防止服务器宕机、消除前端死连、保证系统基本可用。

#### 1.1 Python AI 降采样与弹性跳帧

**Reader 层改造**

- 不使用 `cv2.VideoCapture.read()` 直接拉全帧率。改为 `grab()` + 每 200ms `retrieve()` 的高频清空策略，防止 OpenCV 内部帧缓冲区老化导致画面延迟。
- 拉取摄像头子码流（D1/CIF 分辨率，5-8 FPS），单帧 ~50KB。
- Pre-record buffer 采用 `collections.deque(maxlen=10)` 强行限制容量。每帧入队时记录时间戳，与当前时间差超过 2.5s 则自动清空队列，防止"时空错乱"导致录像拼接错误。
- 200 路 buffer 内存上限：10 帧 × 50KB × 200 = ~100MB。

**Processor 层改造**

- **弹性跳帧**：平时每秒调用 2 次 `detector.detect()`（间隔 ≥ 500ms 才处理，其余直接 `continue`），GPU 占用释放 90%。
- **两阶段置信度**（作用：触发预录 vs 确认报警，与 Phase 2.4 的证据永久保留门限是两套独立阈值）：
  - 触发阈值 0.55：单帧烟雾置信度超过 0.55，立即激活高帧率录制。先录再说。录像写入内存盘（ImDisk）。
  - 确认阈值 0.80：后续帧将置信度冲到 0.80 以上，Java 推送正式报警。2 秒内回落则静默取消，从内存盘删除临时文件。
- **证据拼接**：报警视频文件由两部分组成——pre-record buffer 中的低帧率历史帧作为开头 + 激活后的 25fps 实时流追加。保证"点火瞬间"不丢失。

**全局爆发令牌桶（Global Burst Token Bucket）**

- 最大并发爆发数：3 路
- 满员时后续触发者进入中帧率模式（5-10 FPS），阈值动态抬升至 0.85，防止误报占坑
- 每路爆发令牌硬超时 8s，超时强制回收，切回 2-3 FPS 采样
- 使用 `threading.Semaphore(3)` 实现

#### 1.2 前端瘦身

**架构改造**

- Monitor.vue 从单路播放器+侧边栏改为4x5网格+侧边栏并存布局
- 侧边栏使用 el-tree 虚拟滚动（`use-virtual`），展开分组不卡顿

**Thumbnail 缩略图接口**

- Python 新增 `GET /api/camera/{id}/thumbnail`，从 `latest_frame` 缩放到 320x240，JPEG 质量 60% 压缩，返回 `image/jpeg`
- 网格模式下所有 `<img>` 标签定时刷新该接口

**刷新策略**

- 每路 `<img>` 独立定时器，间隔 = `1000 + Math.random() * 500` ms，用随机 jitter 打散 HTTP 并发
- 双击某路摄像头进入详情时关闭缩略图定时器，切换为单路 MJPEG 长连接

**安全兜底**

- Buffer: `deque(maxlen=10)` + 2.5s 超时清空
- 防止 OpenCV 缓冲老化：Reader 高频 `grab()` + 定时 `retrieve()`

---

### Phase 2 — 全链路降载（P1，1 个月内）

目标：削减网络带宽、降低磁盘 I/O、减轻中台压力。

#### 2.1 MediaMTX 媒体网关 + 录像直写

**部署架构**

- 部署 MediaMTX（Go，单二进制，内存占用 < 50MB）作为 RTSP 代理网关
- MediaMTX 维持 200 路摄像头发起的 RTSP 长连接，零 CPU 消耗（纯网络报文拷贝）
- Python AI 引擎从本地代理拉流：`rtsp://127.0.0.1:8554/cam/{id}`（子码流）

**子码流/主码流分离**

- Reader 线程始终拉子码流端口（5-8 FPS，低分辨率推理用）
- 报警录像则录制主码流：`ffmpeg -i rtsp://127.0.0.1:8554/cam/{id}_main ...`

**录像直写（替代 OpenCV VideoWriter mp4v）**

- 放弃 OpenCV 的 mp4v → H.264 两次编解码。改用 `subprocess` 调用 FFmpeg
- FFmpeg 命令必须加 `-noaccurate_seek` 处理 I 帧对齐。如果绿屏严重，则回退 `-preset superfast` 快速转码

#### 2.2 I/O 限流与降权

**快照特权通道**

- 快照（JPG）通过 Python 内存 Bytes 同步写入，单文件仅数百 KB，耗时 < 5ms
- 确认报警后快照立刻落盘，即使后续视频排队时服务崩溃，核心证据已安全获取

**视频从内存盘剪切到 SSD 的全局 Semaphore 限流**

- Phase 3.1 的 ImDisk 内存盘解决临时文件的写入，但确诊报警后仍需将视频从 `R:\` 剪切到物理 SSD。
- `threading.Semaphore(2)` 强行将全系统同时向物理 SSD 写盘（移动）的并发数限制为 2
- 超额任务在内存盘队列中排队，MediaMTX 后台流缓冲保证晚 1-2s 写入不会丢失画面
- 直接将 SSD 并发写入压力拦腰斩断

**Windows 进程 I/O 降权**

每块 SSD 在承受 MySQL、系统日志、数据库等日常吞吐。必须防止 FFmpeg 写盘时把 MySQL 的 I/O 挤死。

```python
import subprocess

# Below Normal 优先级，确保 FFmpeg 不和服务核心组件抢夺 I/O
CREATE_BELOW_NORMAL_PRIORITY_CLASS = 0x00004000

process = subprocess.Popen(
    ["ffmpeg", "-i", "rtsp://...", "-vcodec", "copy", "output.mp4"],
    creationflags=CREATE_BELOW_NORMAL_PRIORITY_CLASS
)
```

**录像子进程超时守护**

- 使用 `subprocess.run(timeout=15)` 启动 FFmpeg 录像
- 15 秒内未自行退出，发送 SIGKILL 强制抹除（Windows 下 `taskkill /F /PID`）
- 防止网络断开导致 FFmpeg 死锁进程堆积

#### 2.3 心跳批量聚合 + 增量对账轮询

**Python 心跳改造**

- 移除每路 StreamLoader 独立调用的 `_update_db_status`
- StreamManager 增加聚合定时器：每 3s 将 200 路状态打包为 `[{id, status}, ...]` 批量 POST 到 Java

**Java 增量对账接口**

- 新增 `GET /api/monitor/devices?version={clientVersion}`
- Java 内存维护 `ConcurrentHashMap<Long, DeviceState>`，心跳不落 MySQL
- 返回格式：无变更返回 `[]`（HTTP 200）；有变更返回 `[{id, status, version}, ...]`
- 前端收到增量后原地更新本地 reactive 状态

#### 2.4 证据分级 + 自动清理

**分级策略**（这是永久保留门限，与 Phase 1 的 0.55/0.80 预录触发门限是两套独立阈值）

| 置信度区间 | 保留内容 |
|-----------|---------|
| ≥ 0.85 | 1 张高清快照 + 10 秒短视频 |
| 0.65 ~ 0.85 | 仅 1 张快照，不录视频 |
| < 0.65 | 不保留任何证据 |

> 逻辑关系：Phase 1 的 0.55 触发预录（所有疑似都先录到内存盘），Phase 2.4 的 0.65/0.85 决定最终哪些从内存盘移到 SSD 永久保留。低于 0.65 的直接从内存盘删除，不碰物理盘。

**生命周期管理**

Java 定时任务（每天凌晨 3 点）：
- 未确认/误报记录：关联视频和快照 7 天后物理删除
- 已确认违规记录：快照永久保留，视频文件 90 天后自动清理

---

### Phase 3 — 架构蜕变（P2，长期演进）

目标：生产级底座，支撑未来更大规模的园区业务。

#### 3.1 内存盘托管（ImDisk）保护 SSD 寿命

**问题背景**

两阶段置信度机制下，置信度 > 0.55 会频繁触发"疑似预录"。这些临时视频如果直接写入 SSD，每天成千上万次创建+删除的擦写放大效应，会在几个月内将学校唯一的 SSD 写死（TBW 耗尽）。

**解法：ImDisk 内存盘**

- 使用 ImDisk Toolkit 从物理内存划出 2GB 虚拟盘（挂载为 `R:\`）
- 所有预录、临时视频、待确认快照 100% 写入 `R:\`（纯内存操作，读写 GB/s，对 SSD 零消耗）
- 只有置信度最终 ≥ 0.80 确诊报警时，后台线程才将视频从 `R:\` 剪切移动到物理 SSD 长期存储区
- 误报/未确认的临时文件直接从内存盘删除，不碰物理盘

#### 3.2 Python 多进程分片推理

**Master-Workers 架构**

- **Master 进程**（Flask）：极度轻量。只负责接收 Java 控制指令、心跳聚合上报、Thumbnail 服务。不碰任何帧的 AI 推理。
- **Worker 进程**（3-4 个）：通过 `multiprocessing.spawn` 派生，每个 Worker 独立拥有：
  - 自己的 StreamManager 和 SmokingDetector 实例
  - 自己的数据库连接池
  - 自己的显卡绑定（`os.environ["CUDA_VISIBLE_DEVICES"]`）
  - RTX 3060 12GB 可划分为 3-4 个分片，每片 3-4GB

**动态负载均衡**

- Master 启动时将 camera_id 均分绑定到各 Worker（`camera_id % num_workers`）
- 推理期间 Worker 完全闭环，只在触发报警时通过 `multiprocessing.Queue` 上报事件给 Master
- 未来增加显卡时只需增加 Worker 进程并调整 `CUDA_VISIBLE_DEVICES`

#### 3.3 WebSocket 增量推送

**Java 端改造**

- 引入 Spring WebSocket 模块，维护设备状态缓存 `ConcurrentHashMap<Long, DeviceState>`
- Python 批量心跳到达后，Java 先比对内存缓存：
  - 无变化 → 完全静默
  - 有变化 → 更新缓存 → `SimpMessagingTemplate.convertAndSend("/topic/device-status", delta)`
- 心跳路径不写 MySQL，降低磁盘争抢

**前端消塔**

- 初始化：一次 HTTP `GET /api/monitor/devices/all` 获取全量列表构建 el-tree
- 后续：WebSocket 订阅 `/topic/device-status`，收到 `{id, status}` 增量直接修改 Vue reactive 状态
- 大屏和侧边栏秒级联动闪红/置灰

**WebSocket 重连兜底（全量对账）**

- 前端 `onclose` → `onopen` 恢复时，自动触发一次 `GET /api/monitor/devices/all` 全量刷新
- 补齐断连期间错失的所有状态变更

#### 3.4 虚拟滚动

- AiChat.vue 消息列表：引入 `vue-virtual-scroller`，DOM 只渲染可视区域 ~15 条
- 侧边栏设备列表：el-tree 开启 `use-virtual`（已在 Phase 1.2 实现）

---

## 优先级与依赖关系

```
Phase 1 (P0, 2周)
├── 1.1 弹性跳帧 + 令牌桶 + 两阶段置信度
│   └── Reader grab/retrieve + Buffer deque + 2.5s 超时
├── 1.2 前端网格 + Thumbnail + el-tree 虚拟滚动
│   └── 随机 jitter 打散 HTTP 并发
│
Phase 2 (P1, 1个月)
├── 2.1 MediaMTX 网关 + 子/主码流分离
├── 2.2 I/O 限流 + 降权 + 录像超时守护
│   ├── Semaphore(2) 视频并发限流
│   ├── Windows Below Normal 进程优先级
│   └── timeout=15 + SIGKILL 僵尸清理
├── 2.3 心跳批量 + 增量对账
└── 2.4 证据分级 + 自动清理
│
Phase 3 (P2, 长期)
├── 3.1 ImDisk 内存盘托管   ← SSD 保命关键
├── 3.2 多进程分片推理
│   └── Master-Workers + CUDA_VISIBLE_DEVICES
├── 3.3 WebSocket 增量推送
│   └── 重连全量对账兜底
└── 3.4 虚拟滚动 (AiChat)
```

## 关键风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| FFmpeg 录像进程僵尸 | `timeout=15` + SIGKILL 守护 |
| OpenCV 帧缓冲老化 | `grab()` + 每 200ms `retrieve()` 清空 |
| Buffer 时间戳错乱 | `deque(maxlen=10)` + 2.5s 超时丢帧 |
| WebSocket 断连漏事件 | 重连后全量对账 HTTP GET |
| GPU 并发爆发雪崩 | 令牌桶 3 路上限 + 8s 硬超时 + 弹性降级阈值 |
| I 帧不对齐导致绿屏 | `-noaccurate_seek` + 退 `-preset superfast` |
| SSD 高频擦写耗尽 TBW | ImDisk 2GB 内存盘中转，确诊后才落物理盘 |
| 多路同时写盘挤死 MySQL | Semaphore(2) 限流 + Windows Below Normal 降权 |
