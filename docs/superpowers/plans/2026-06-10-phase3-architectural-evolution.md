# Phase 3: 架构蜕变 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ImDisk 内存盘保护 SSD 寿命，多进程分片推理突破 GIL 瓶颈，WebSocket 增量推送消除前端轮询，虚拟滚动解决 AiChat 内存泄漏。

**Architecture:** Python 拆为 Master（轻量 Flask）+ Workers（多进程分片推理）；Java 新增 WebSocket 增量推送替代轮询；前端 AiChat.vue 引入虚拟滚动。

**Tech Stack:** ImDisk Toolkit / Python multiprocessing / Spring WebSocket / vue-virtual-scroller

---

### Task 1: ImDisk 内存盘集成

**Files:**
- Create: `scripts/setup_imdisk.bat` (一键创建 R:\ 盘)
- Modify: `web-flask/app/core/recorder.py` (证据路径改为 R:\)

- [ ] **Step 1: 编写 ImDisk 初始化脚本**

```bat
@echo off
REM scripts/setup_imdisk.bat
REM 创建 2GB 内存盘 R:\ 用于临时证据存储

setlocal
set RAMDISK_SIZE=2048  rem MB
set RAMDISK_LETTER=R

echo [ImDisk] 正在创建 %RAMDISK_SIZE%MB 内存盘 %RAMDISK_LETTER%:\ ...

:: 如果已存在，先卸载
imdisk -d -m %RAMDISK_LETTER%:\ 2>nul

:: 创建新内存盘
imdisk -a -s %RAMDISK_SIZE%M -m %RAMDISK_LETTER%:\ -p "/fs:ntfs /q /y"

if %errorlevel% equ 0 (
    echo [ImDisk] 内存盘创建成功: %RAMDISK_LETTER%:\ (%RAMDISK_SIZE%MB)
    :: 创建证据目录结构
    mkdir %RAMDISK_LETTER%:\evidence\snapshots 2>nul
) else (
    echo [ImDisk] 创建失败！请确保已安装 ImDisk Toolkit
    exit /b 1
)
```

- [ ] **Step 2: 修改 EvidenceRecorder 支持内存盘路径**

```python
# web-flask/app/core/recorder.py — 改造

class EvidenceRecorder:
    def __init__(self, save_dir="app/static/evidence", fps=25, pre_record_sec=2,
                 ram_disk_dir="R:/evidence"):
        self.save_dir = os.path.abspath(save_dir)        # SSD 长期存储
        self.ram_disk_dir = ram_disk_dir                 # 内存盘临时存储
        self.fps = fps
        self.pre_record_sec = pre_record_sec

        os.makedirs(self.save_dir, exist_ok=True)
        os.makedirs(os.path.join(self.save_dir, "snapshots"), exist_ok=True)
        os.makedirs(self.ram_disk_dir, exist_ok=True)
        os.makedirs(os.path.join(self.ram_disk_dir, "snapshots"), exist_ok=True)

        # 🚀 所有预录临时文件写入内存盘
        self.buffer: deque[tuple[float, cv2.Mat]] = deque(maxlen=10)
        # ... 其余不变 ...

    def start_recording(self, filename, post_record_sec=5, width=640, height=480):
        """录像先写入内存盘（R:\）。"""
        with self.lock:
            if self.is_recording:
                return self.current_video_path
            # ... 初始化逻辑不变 ...
            # 🚀 路径指向内存盘
            self.current_video_path = os.path.join(self.ram_disk_dir, filename)
            # ...

    def save_snapshot(self, frame, filename):
        """快照写入内存盘。"""
        if frame is None:
            return
        snapshot_dir = os.path.join(self.ram_disk_dir, "snapshots")
        save_path = os.path.join(snapshot_dir, filename)
        cv2.imwrite(save_path, frame)
        return save_path

    def move_to_persistent(self, ram_path: str) -> str:
        """
        确诊报警后，将证据从内存盘剪切到 SSD 长期存储。
        返回最终路径。IOThrottle 管理并发限流。
        """
        if not ram_path or not os.path.exists(ram_path):
            return ram_path

        rel_path = os.path.relpath(ram_path, self.ram_disk_dir)
        persistent_path = os.path.join(self.save_dir, rel_path)
        os.makedirs(os.path.dirname(persistent_path), exist_ok=True)
        os.replace(ram_path, persistent_path)
        logger.info(f"📦 证据移至 SSD: {persistent_path}")
        return persistent_path
```

- [ ] **Step 3: 在确认报警时触发 move_to_persistent**

```python
# web-flask/app/core/stream_loader.py — 在 _trigger_alarm_save 中

        # 确认后，将快照从内存盘移至 SSD
        if conf >= self.EVIDENCE_SNAPSHOT_THRESHOLD:
            ram_snapshot = os.path.join(self.recorder.ram_disk_dir, "snapshots", img_name)
            self.recorder.move_to_persistent(ram_snapshot)

        # 视频完成后再移动
        if conf >= self.EVIDENCE_VIDEO_THRESHOLD:
            ram_video = os.path.join(self.recorder.ram_disk_dir, video_name)
            # FFmpeg 录像线程完成后调用 move_to_persistent
```

- [ ] **Step 4: Commit**

```bash
git add scripts/setup_imdisk.bat web-flask/app/core/recorder.py
git commit -m "feat(P2): ImDisk RAM disk integration, evidence temp path on R:, move_to_persistent on confirm"
```

---

### Task 2: 多进程分片推理（Master-Workers）

**Files:**
- Create: `web-flask/app/core/worker_manager.py` (Worker 进程管理器)
- Create: `web-flask/app/core/worker_main.py` (Worker 子进程入口)
- Modify: `web-flask/app/core/stream_loader.py` (StreamManager 改造为跨进程通信)
- Modify: `web-flask/app/__init__.py` (启动 Master 时衍生 Workers)

- [ ] **Step 1: 创建 Worker 子进程入口**

```python
# web-flask/app/core/worker_main.py

"""
Worker 子进程入口。

每个 Worker 拥有独立的：
- StreamManager + SmokingDetector
- GPU 绑定 (CUDA_VISIBLE_DEVICES)
- camera_id 分片
"""

import os
import sys
import time
import multiprocessing
import builtins

def worker_main(worker_id: int, camera_ids: list[int],
                gpu_device: str, alarm_queue: multiprocessing.Queue):
    """
    Worker 子进程主函数。
    启动后绑定 GPU，创建自己的 StreamManager 并启动指定 camera_ids 的流。

    🚀 Worker 为纯推理进程，不发起任何 HTTP 网络请求。
    所有报警事件通过 alarm_queue 上报给 Master 统一转发。
    """
    # 🚀 绑定指定 GPU
    os.environ["CUDA_VISIBLE_DEVICES"] = gpu_device

    # 延迟导入（确保 GPU 绑定后才初始化 PyTorch/YOLO）
    from app.core.stream_loader import StreamManager

    sm = StreamManager()
    builtins.GLOBAL_STREAM_MANAGER = sm

    # 🚀 将 alarm_queue 注入到每个 StreamLoader 的 _trigger_alarm_save 中
    # 当 Worker 内触发报警时，只做：
    #   1. 快照/录像写入 ImDisk 内存盘
    #   2. 将报警字典通过 alarm_queue.put(payload) 发送
    # 绝不调用 requests.post (由 Master 集中上报，防双重上报防网络卡顿)
    sm.set_alarm_queue(alarm_queue)

    # 启动分配到的摄像头
    for cid in camera_ids:
        # 从共享状态获取 RTSP URL（通过 multiprocessing.Manager 或共享 dict）
        url = get_camera_url(cid)
        if url:
            sm.add_camera(cid, url)

    # 持续运行
    while True:
        # 检查 queue 是否有 Master 指令（增删摄像头、切换 AI 开关等）
        time.sleep(1)
```

- [ ] **Step 2: 创建 WorkerManager（Master 进程）**

```python
# web-flask/app/core/worker_manager.py

"""
Master 进程的 Worker 管理器。

启动时根据 GPU 和 camera 总量，将摄像头分片到多个 Worker 进程。
"""

import multiprocessing
import os
import logging
import time
from typing import List

logger = logging.getLogger(__name__)

class WorkerManager:
    """
    Worker 进程生命周期管理。
    - 启动 N 个 Worker 子进程
    - 每进程绑定不同 GPU
    - camera_id 通过取模分片
    """

    def __init__(self, camera_count: int = 200,
                 workers_per_gpu: int = 4,
                 gpu_devices: List[str] = None):

        self.camera_count = camera_count
        self.workers_per_gpu = workers_per_gpu
        self.gpu_devices = gpu_devices or ["0"]  # 默认单卡
        self.workers: List[multiprocessing.Process] = []
        self.alarm_queue = multiprocessing.Queue(maxsize=1000)

        # camera_id -> Worker 映射
        self.camera_worker_map: dict[int, int] = {}

    def start(self):
        """启动所有 Worker 进程。"""
        total_workers = self.workers_per_gpu * len(self.gpu_devices)
        cams_per_worker = max(1, self.camera_count // total_workers)

        for wi in range(total_workers):
            gpu_idx = wi // self.workers_per_gpu
            gpu_dev = self.gpu_devices[gpu_idx]

            # 计算分片
            start_id = wi * cams_per_worker + 1
            end_id = (wi + 1) * cams_per_worker + 1 if wi < total_workers - 1 else self.camera_count + 1
            assigned_ids = list(range(start_id, end_id))

            for cid in assigned_ids:
                self.camera_worker_map[cid] = wi

            # 启动 Worker
            p = multiprocessing.Process(
                target=self._worker_bootstrap,
                args=(wi, assigned_ids, gpu_dev, self.alarm_queue),
                daemon=True
            )
            p.start()
            self.workers.append(p)
            logger.info(f"🧠 Worker[{wi}] 已启动: GPU={gpu_dev}, cameras={len(assigned_ids)}路")

        # 启动报警事件消费线程
        self._start_alarm_consumer()

    def _worker_bootstrap(self, worker_id, camera_ids, gpu_device, alarm_queue):
        """Worker 入口包装（设置环境变量后导入实际模块）。"""
        os.environ["CUDA_VISIBLE_DEVICES"] = gpu_device
        from app.core.worker_main import worker_main
        worker_main(worker_id, camera_ids, gpu_device, alarm_queue)

    def _start_alarm_consumer(self):
        """消费 Worker 上报的报警事件。"""
        def consumer():
            while True:
                try:
                    alarm = self.alarm_queue.get(timeout=1)
                    # 🚀 Master 统一处理：先迁移证据到 SSD，再转发 Java
                    self._handle_alarm(alarm)
                except Exception:
                    pass
        t = threading.Thread(target=consumer, daemon=True)
        t.start()

    def _handle_alarm(self, alarm: dict):
        """
        Master 统一处理报警事件。
        - 将证据从 ImDisk 内存盘剪切到 SSD（受 IOThrottle 限流）
        - 单点转发给 Java 中台（消除双重上报）
        """
        # 1. 迁移证据到 SSD
        ram_path = alarm.get("ram_evidence_path")
        if ram_path:
            try:
                from app.core.recorder import move_to_persistent
                move_to_persistent(ram_path)
            except Exception as e:
                logger.error(f"证据迁移失败: {e}")

        # 2. 单点转发 Java（只有 Master 做这件事）
        import requests
        try:
            requests.post(
                "http://localhost:8080/api/alerts/report",
                json=alarm.get("java_payload", {}),
                timeout=3
            )
        except Exception as e:
            # 🚀 Master 层记录失败日志，可据此实现重试队列
            logger.error(f"Java 中台上报失败: {e}")

    def stop(self):
        """停止所有 Worker。"""
        for p in self.workers:
            if p.is_alive():
                p.terminate()
                p.join(timeout=5)
        logger.info("🛑 所有 Worker 已终止")
```

- [ ] **Step 3: 修改 Flask 启动入口（⚠️ Windows spawn 安全结构）**

```python
# web-flask/app/__init__.py — create_app 中不启动 Worker

def create_app():
    app = Flask(__name__)
    # ... 现有初始化代码（注册蓝图、配置等）...
    app.register_blueprint(monitor_bp, url_prefix='/api/v1/monitor')
    return app
```

```python
# web-flask/app.py 或 web-flask/run.py — 主进程入口

"""
🚀 Windows 多进程安全启动结构。

⚠️ 关键约束：
1. WorkerManager 的初始化必须在 if __name__ == '__main__' 块内，
   绝不能放在 create_app() 中。Windows 的 spawn 机制会重新运行
   模块顶级代码，如果在 create_app 中启动 Workers，子进程会递归
   衍生孙子进程，导致进程爆炸。

2. app.run() 必须关闭 debug 和 reloader：
   debug=True 会启用 Werkzeug reloader，它在 Windows 下会触发
   二次 spawn，同样导致多进程混乱。
"""

from app import create_app
from app.core.worker_manager import WorkerManager

app = create_app()

if __name__ == '__main__':
    # 🚀 只有真正的顶级主进程入口才衍生 Worker
    # 子进程被 spawn 时不会进入此分支，完美免疫递归爆炸
    print("[Master] 正在初始化多进程视觉分片引擎...")
    worker_mgr = WorkerManager(camera_count=200, workers_per_gpu=4)
    worker_mgr.start()

    # 🚀 启动 Flask Master Web 服务
    # debug=False + use_reloader=False 防止 Windows 二次 spawn
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
```

- [ ] **Step 4: Commit**

```bash
git add web-flask/app/core/worker_manager.py web-flask/app/core/worker_main.py web-flask/app/__init__.py
git commit -m "feat(P2): multi-process inference - Master/Worker architecture with GPU binding"
```

---

### Task 3: WebSocket 增量推送（Java + Vue）

**Files:**
- Modify: `web-back/.../config/WebSocketConfig.java` (新增设备状态 Topic)
- Modify: `web-back/.../service/DeviceService.java` (状态变更时推送)
- Modify: `web-vue/src/stores/device.ts` (WebSocket 订阅替代轮询)
- Modify: `web-vue/src/views/Monitor.vue` (初始化全量 + WebSocket 增量)

- [ ] **Step 1: Java 新增设备状态 WebSocket Topic**

```java
// web-back/.../config/WebSocketConfig.java — 在 configureMessageBroker 中

@Override
public void configureMessageBroker(MessageBrokerRegistry registry) {
    // 新增设备状态 Topic
    registry.enableSimpleBroker("/topic/alarm", "/topic/device-status");
    registry.setApplicationDestinationPrefixes("/app");
}
```

- [ ] **Step 2: DeviceService 在状态变更时主动推送**

```java
// web-back/.../service/DeviceService.java — 注入 SimpMessagingTemplate

import org.springframework.messaging.simp.SimpMessagingTemplate;

@Service
public class DeviceService {

    @Autowired
    private SimpMessagingTemplate messagingTemplate;

    @PostMapping("/api/monitor/devices/batch-sync")
    public Result batchSync(@RequestBody List<Map<String, Object>> batch) {
        // ... 比对逻辑不变 ...
        if (!changes.isEmpty()) {
            // 🚀 推送给所有前端
            messagingTemplate.convertAndSend("/topic/device-status", changes);
        }
        return Result.success();
    }
}
```

- [ ] **Step 3: 前端订阅 /topic/device-status 替代轮询**

```typescript
// web-vue/src/stores/device.ts — 改造

export const useDeviceStore = defineStore('device', () => {
  const deviceList = ref<Device[]>([])
  let stompClient: any = null

  // 🚀 初始化：全量 HTTP 获取
  const fetchAllDevices = async () => {
    const res = await axios.get(`${JAVA_BASE}/api/monitor/devices/all`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.data.code === 200) {
      deviceList.value = res.data.data
    }
  }

  // 🚀 WebSocket 增量订阅（替代定时轮询）
  const subscribeDeviceStatus = () => {
    if (!stompClient || !stompClient.connected) return

    stompClient.subscribe('/topic/device-status', (message: any) => {
      const changes = JSON.parse(message.body)
      for (const change of changes) {
        const idx = deviceList.value.findIndex(d => d.id === change.id)
        if (idx !== -1) {
          deviceList.value[idx].status = change.status
        }
      }
    })
  }

  // 🚀 重连兜底（全量对账）
  const handleReconnect = async () => {
    await fetchAllDevices()  // 断连补全
    subscribeDeviceStatus()  // 恢复增量
  }

  return { deviceList, fetchAllDevices, subscribeDeviceStatus, handleReconnect }
})
```

- [ ] **Step 4: 前端 Monitor.vue 集成**

```typescript
// web-vue/src/views/Monitor.vue — onMounted

onMounted(async () => {
  // 1. 全量获取设备列表（仅一次）
  await deviceStore.fetchAllDevices()

  // 2. 建立 WebSocket 连接
  initWebSocket()

  // 3. 订阅增量推送
  deviceStore.subscribeDeviceStatus()

  // 4. 不再需要定时轮询
  // 移除 deviceStore.startPolling() 调用
})
```

- [ ] **Step 5: Commit**

```bash
git add web-back/src/main/java/org/example/webback/config/WebSocketConfig.java \
      web-back/src/main/java/org/example/webback/service/DeviceService.java \
      web-vue/src/stores/device.ts \
      web-vue/src/views/Monitor.vue
git commit -m "feat(P2): WebSocket /topic/device-status push + frontend subscribe (replace polling)"
```

---

### Task 4: AiChat.vue 虚拟滚动

**Files:**
- Modify: `web-vue/src/views/AiChat.vue` (引入 vue-virtual-scroller)

- [ ] **Step 1: 安装依赖**

```bash
cd web-vue
npm install vue-virtual-scroller
```

- [ ] **Step 2: 改造 AiChat.vue 消息列表为虚拟滚动**

```vue
<!-- web-vue/src/views/AiChat.vue — template 改造 -->

<template>
  <div class="ai-chat-container">
    <!-- sidebar 保持不变 -->
    <div class="sidebar">...</div>

    <div class="chat-main">
      <template v-if="currentConversationId">
        <!-- 🚀 虚拟滚动替代 el-scrollbar -->
        <DynamicScroller
          class="message-area"
          :items="messageList"
          :min-item-size="80"
          page-mode
          ref="scrollerRef"
        >
          <template v-slot="{ item, index, active }">
            <DynamicScrollerItem
              :item="item"
              :active="active"
              :size-dependencies="[item.content]"
              :data-index="index"
            >
              <div :class="['message-item', item.role]">
                <div class="avatar">{{ item.role === 'user' ? '我' : 'AI' }}</div>
                <div class="bubble" :class="{ 'error-bubble': item.isError }">
                  <div v-if="item.role === 'user'">{{ item.content }}</div>
                  <template v-else>
                    <!-- markdown 渲染保持不变 -->
                    <div v-if="item.isThinking" class="thinking-status">...</div>
                    <div class="markdown-body" v-html="md.render(formatMarkdown(item.content))"></div>
                  </template>
                </div>
              </div>
            </DynamicScrollerItem>
          </template>
        </DynamicScroller>

        <!-- input-area 保持不变 -->
        <div class="input-area">...</div>
      </template>
    </div>
  </div>
</template>
```

```typescript
// web-vue/src/views/AiChat.vue — script 改造

import { DynamicScroller, DynamicScrollerItem } from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'

// 🚀 替换 scrollbarRef 为 scrollerRef
const scrollerRef = ref<any>(null)

// 🚀 消息 ID 生成器（vue-virtual-scroller 要求每个 item 必须有唯一 id）
let msgIdCounter = 0
const genMsgId = () => `msg_${Date.now()}_${++msgIdCounter}`

// --------------------------------------------------
// 🚀 重要：修改所有 messageList.value.push() 调用点，
// 强制每条消息携带唯一 id：
//
// messageList.value.push({
//   id: genMsgId(),  // <-- 虚拟滚动保命 id
//   role: 'user',
//   content: trimmedText
// })
// --------------------------------------------------

const scrollToBottom = async () => {
  await nextTick()
  if (scrollerRef.value) {
    scrollerRef.value.scrollToItem(messageList.value.length - 1)
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add web-vue/src/views/AiChat.vue
git commit -m "feat(P2): virtual scrolling for AiChat message list (vue-virtual-scroller)"
```
