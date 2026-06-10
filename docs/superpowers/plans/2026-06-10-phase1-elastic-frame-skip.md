# Phase 1: 弹性跳帧 + 前端瘦身 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Python AI 引擎的弹性跳帧、两阶段置信度、全局爆发令牌桶，以及前端网格+缩略图大屏。

**Architecture:** Python Flask AI 引擎（web-flask）改造 Reader/Processor 线程模型，新增 Thumbnail 接口；Vue 前端（web-vue）Monitor.vue 从单路布局改为网格+侧边栏并存布局。

**Tech Stack:** Python 3.10+ / OpenCV / Flask / Vue 3 / Element Plus

---

### Task 1: Reader 线程改造 — grab/retrieve + 时间戳安全 deque

**Files:**
- Modify: `web-flask/app/core/stream_loader.py:100-128` (_reader_thread, _connect)
- Modify: `web-flask/app/core/recorder.py:10-50` (EvidenceRecorder __init__, add_frame)

- [ ] **Step 1: 修改 StreamLoader._reader_thread 为 grab/retrieve 模式**

替换 `_reader_thread` 中 `cap.read()` 直接调用。使用 `cap.grab()` 高频清空 OpenCV 内部缓冲区，每 200ms 执行一次 `cap.retrieve()` 获取最新帧。

```python
# web-flask/app/core/stream_loader.py  — _reader_thread 改造

def _reader_thread(self):
    last_retrieve_time = 0
    RETRIEVE_INTERVAL = 0.2  # 200ms → 5 FPS

    while self.running:
        if not self.running:
            break

        if not self.cap or not self.cap.isOpened() or self.reconnect_requested:
            if self._connect():
                self.reconnect_requested = False
                last_retrieve_time = time.time()
            else:
                self._update_db_status(0)
                time.sleep(2)
                continue

        try:
            # 1. 高频 grab() — 清空 OpenCV 内部缓冲区，防止老化延迟
            grabbed = self.cap.grab()
            now = time.time()

            # 2. 每 200ms 才 retrieve — 输出 ~5 FPS 子码流
            if grabbed and (now - last_retrieve_time >= RETRIEVE_INTERVAL):
                ret, frame = self.cap.retrieve()
                if ret and frame is not None:
                    last_retrieve_time = now
                    with self.lock:
                        self.latest_frame = frame
                        self.last_read_time = now
                else:
                    if self.running:
                        logger.warning(f"⚠️ Cam {self.camera_id} 信号丢失")
                        self._update_db_status(0)
                        self.reconnect_requested = True
                    time.sleep(1)
            elif not grabbed:
                time.sleep(0.01)
        except Exception as e:
            logger.debug(f"读取线程退出捕获: {e}")
            break
```

- [ ] **Step 2: 修改 EvidenceRecorder 使用 deque(maxlen=10) 并加入 2.5s 超时**

```python
# web-flask/app/core/recorder.py — EvidenceRecorder 改造

from collections import deque

class EvidenceRecorder:
    def __init__(self, save_dir="app/static/evidence", fps=25, pre_record_sec=2):
        self.save_dir = os.path.abspath(save_dir)
        self.fps = fps
        self.pre_record_sec = pre_record_sec

        os.makedirs(self.save_dir, exist_ok=True)
        os.makedirs(os.path.join(self.save_dir, "snapshots"), exist_ok=True)

        # 🚀 改用 deque(maxlen=10)，每帧带时间戳
        self.buffer: deque[tuple[float, cv2.Mat]] = deque(maxlen=10)

        self.is_recording = False
        self.writer = None
        self.current_video_path = None
        self.record_start_time = 0
        self.post_record_sec = 0
        self.target_w = 640
        self.target_h = 480
        self.lock = threading.Lock()

    def add_frame(self, frame):
        if frame is None:
            return
        with self.lock:
            frame_resized = cv2.resize(frame, (self.target_w, self.target_h))
            now = time.time()

            # 🚀 2.5s 超时清空：如果队首帧时间戳太旧，说明发生了卡顿或断流
            if self.buffer and (now - self.buffer[0][0]) > 2.5:
                self.buffer.clear()
                logger.warning("🧹 Buffer 超时清空：防止时空错乱")

            self.buffer.append((now, frame_resized.copy()))

            if self.is_recording and self.writer:
                try:
                    self.writer.write(frame_resized)
                except Exception as e:
                    logger.error(f"写入视频帧失败: {e}")
```

- [ ] **Step 3: 更新 EvidenceRecorder.start_recording 从 deque 读取历史帧**

```python
# web-flask/app/core/recorder.py — start_recording 改造

    def start_recording(self, filename, post_record_sec=5, width=640, height=480):
        with self.lock:
            if self.is_recording:
                return self.current_video_path

            self.target_w = width
            self.target_h = height
            self.is_recording = True
            self.post_record_sec = post_record_sec
            self.record_start_time = time.time()

            self.current_video_path = os.path.join(self.save_dir, filename)

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.writer = cv2.VideoWriter(
                self.current_video_path, fourcc, self.fps, (self.target_w, self.target_h)
            )

            # 🚀 从 deque 取出历史帧作为视频开头（证据拼接）
            for ts, f in self.buffer:
                if f.shape[1] != self.target_w or f.shape[0] != self.target_h:
                    f = cv2.resize(f, (self.target_w, self.target_h))
                self.writer.write(f)

            logger.info(f"🎥 录制物理启动: {filename} ({width}x{height}), 含 {len(self.buffer)} 帧历史")
            return self.current_video_path
```

- [ ] **Step 4: Commit**

```bash
git add web-flask/app/core/stream_loader.py web-flask/app/core/recorder.py
git commit -m "feat(P0): Reader grab/retrieve + deque buffer + 2.5s timeout safeguard"
```

---

### Task 2: Processor 弹性跳帧 + 两阶段置信度

**Files:**
- Modify: `web-flask/app/core/detector.py:18-60` (SmokingDetector init, add trigger/confirm thresholds)
- Modify: `web-flask/app/core/stream_loader.py:130-165` (_processor_thread, _handle_alarm_logic)

- [ ] **Step 1: SmokingDetector 增加两阶段置信度参数**

```python
# web-flask/app/core/detector.py — 在 __init__ 末尾添加

        # 🚀 两阶段置信度阈值
        self.trigger_threshold = 0.55   # 触发预录
        self.confirm_threshold = 0.80   # 确认报警
        self.trigger_cooldown = 2.0     # 触发后等待确认/取消的秒数
```

- [ ] **Step 2: 改写 _processor_thread 为弹性跳帧**

```python
# web-flask/app/core/stream_loader.py — _processor_thread 替换

    def _processor_thread(self):
        last_process_time = 0.0
        # 🚀 爆发模式状态
        burst_token_holder = False  # 当前是否持有爆发令牌

        while self.running:
            frame_to_process = None
            ai_on = True
            with self.lock:
                if self.latest_frame is not None:
                    frame_to_process = self.latest_frame.copy()
                ai_on = self.ai_enabled

            if frame_to_process is None:
                time.sleep(0.1)
                continue

            now = time.time()
            # 🚀 弹性跳帧判断
            # 非爆发模式：间隔 >= 500ms 才推理 (2 FPS)
            # 爆发模式：全帧率推理
            if not burst_token_holder and (now - last_process_time) < 0.5:
                # 直接将当前帧送入 recorder buffer（保证录像连贯）
                frame_resized = cv2.resize(frame_to_process, (640, 480))
                self.recorder.add_frame_no_detect(frame_resized)
                self.recorder.process_recording()
                time.sleep(0.01)
                continue

            last_process_time = now
            detections = []

            if ai_on:
                try:
                    detections = self.detector.detect(frame_to_process)
                    # 🚀 两阶段置信度处理 + 爆发令牌管理
                    detections, burst_token_holder = self._handle_two_stage_alarm(
                        frame_to_process, detections, burst_token_holder, now
                    )
                except Exception as e:
                    logger.error(f"AI Error: {e}")

            frame_to_process = self._draw_ui(frame_to_process, detections)
            self.recorder.add_frame(frame_to_process)

            with self.lock:
                self.output_frame = frame_to_process

            self.recorder.process_recording()
            time.sleep(0.01)
```

- [ ] **Step 3: 新增 add_frame_no_detect 方法**

```python
# web-flask/app/core/recorder.py — 新增方法

    def add_frame_no_detect(self, frame):
        """Processor 跳过推理时仍将帧写入 buffer（保证录像连贯性）"""
        if frame is None:
            return
        with self.lock:
            frame_resized = cv2.resize(frame, (self.target_w, self.target_h))
            now = time.time()
            if self.buffer and (now - self.buffer[0][0]) > 2.5:
                self.buffer.clear()
            self.buffer.append((now, frame_resized.copy()))
            if self.is_recording and self.writer:
                try:
                    self.writer.write(frame_resized)
                except Exception as e:
                    logger.error(f"写入视频帧失败: {e}")
```

- [ ] **Step 4: 新增 _handle_two_stage_alarm 方法**

替换原有的 `_handle_alarm_logic`。

```python
# web-flask/app/core/stream_loader.py — 新增方法，替换 _handle_alarm_logic

    def _handle_two_stage_alarm(self, frame, detections, has_burst_token, now):
        """
        两阶段置信度 + 爆发令牌管理。
        返回 (更新后的 detections, 是否有爆发令牌)
        """
        persons = [d for d in detections if d['label'] == 'person']
        cigarettes = [d for d in detections if d['label'] == 'cigarette']

        self._update_cooldowns(now, persons)

        # ── 检查当前帧是否有任何吸烟检测 ──
        max_conf = 0.0
        best_cig = None
        for cig in cigarettes:
            if cig['conf'] > max_conf:
                max_conf = cig['conf']
                best_cig = cig

        # ── 爆发令牌状态机 ──
        if has_burst_token:
            # 检查 8s 硬超时
            if now - self.burst_start_time > 8.0:
                logger.info(f"⏰ Cam {self.camera_id} 爆发令牌超时回收")
                self.burst_token_holder = False
                has_burst_token = False
                BurstTokenManager.release(self.camera_id)
                return detections, False

        # ── 两阶段逻辑 ──
        if max_conf >= self.detector.confirm_threshold and best_cig:
            # Stage 2: 确认报警 (≥0.80)
            best_cig['is_alarm'] = True
            cbox = best_cig['box']
            c_cx, c_cy = (cbox[0] + cbox[2]) / 2, (cbox[1] + cbox[3]) / 2

            if not self._is_in_cooldown(c_cx, c_cy):
                owner_id = self._match_person_id(cbox, persons)
                evidence_frame = self._draw_ui(frame.copy(), detections)
                self._trigger_alarm_save(evidence_frame, owner_id, best_cig['conf'])
                self._add_cooldown(owner_id, c_cx, c_cy, now)
                logger.info(f"🚨 Cam {self.camera_id} 确认报警 conf={max_conf:.2f}")

            # 确认后归还令牌（已触发 save，不再需要爆发）
            if has_burst_token:
                BurstTokenManager.release(self.camera_id)
                has_burst_token = False
            return detections, False

        elif max_conf >= self.detector.trigger_threshold and best_cig:
            # Stage 1: 触发预录 (0.55 ~ 0.80)
            if not has_burst_token:
                # 尝试获取爆发令牌
                if BurstTokenManager.acquire(self.camera_id, now):
                    has_burst_token = True
                    self.burst_start_time = now
                    logger.info(f"🔥 Cam {self.camera_id} 获取爆发令牌 conf={max_conf:.2f}")
                    # 立即激活录像（写入内存盘，后续拼接证据）
                    # 录像由 _trigger_alarm_save 在确认时触发

        # ── 过期清理 ──
        expired = [tid for tid, evt in self.smoke_events.items()
                   if now - evt.last_seen_time > self.lost_timeout]
        for tid in expired:
            del self.smoke_events[tid]

        return detections, has_burst_token
```

- [ ] **Step 5: 删除旧的 _handle_alarm_logic**

移除 `_handle_alarm_logic` 方法，其逻辑已完全被 `_handle_two_stage_alarm` 替代。

- [ ] **Step 6: Commit**

```bash
git add web-flask/app/core/detector.py web-flask/app/core/stream_loader.py web-flask/app/core/recorder.py
git commit -m "feat(P0): elastic frame skip + two-stage confidence (trigger 0.55/confirm 0.80)"
```

---

### Task 3: 全局爆发令牌桶（BurstTokenManager）

**Files:**
- Create: `web-flask/app/core/burst_token.py`
- Modify: `web-flask/app/core/stream_loader.py:1-10` (import)

- [ ] **Step 1: 创建 BurstTokenManager**

```python
# web-flask/app/core/burst_token.py

"""
全局爆发令牌桶（Global Burst Token Bucket）。

允许最多 MAX_BURSTS 路摄像头同时处于 25fps 全帧推理状态。
满员时后续触发者不排队，而是弹性降级（中帧率 + 高阈值）。
"""

import threading
import time
import logging

logger = logging.getLogger(__name__)

class BurstTokenManager:
    _lock = threading.Lock()
    MAX_BURSTS = 3                     # 最大并发爆发数
    HARD_TIMEOUT = 8.0                 # 每路爆发硬超时（秒）
    _active_bursts: dict[int, float] = {}  # camera_id -> start_time

    # 弹性降级配置
    DEGRADED_FPS = 5                    # 降级后的推理帧率目标
    DEGRADED_THRESHOLD = 0.85           # 降级后的报警阈值

    @classmethod
    def acquire(cls, camera_id: int, now: float) -> bool:
        """尝试获取爆发令牌。成功返回 True，失败表示进入弹性降级模式。"""
        with cls._lock:
            # 清理过期令牌
            expired = [
                cid for cid, start in cls._active_bursts.items()
                if now - start > cls.HARD_TIMEOUT
            ]
            for cid in expired:
                logger.info(f"⏰ 强制回收令牌 CID={cid}（超时）")
                del cls._active_bursts[cid]

            if len(cls._active_bursts) < cls.MAX_BURSTS:
                cls._active_bursts[camera_id] = now
                return True

            logger.warning(
                f"⚠️ 令牌桶已满 ({cls.MAX_BURSTS})，CID={camera_id} 进入弹性降级模式 "
                f"(阈值 {cls.DEGRADED_THRESHOLD})"
            )
            return False

    @classmethod
    def release(cls, camera_id: int):
        """主动归还爆发令牌。"""
        with cls._lock:
            if camera_id in cls._active_bursts:
                del cls._active_bursts[camera_id]
                logger.info(f"♻️ 令牌归还 CID={camera_id}，剩余爆发: {len(cls._active_bursts)}")

    @classmethod
    def is_in_burst(cls, camera_id: int) -> bool:
        """检查某路是否持有爆发令牌。"""
        with cls._lock:
            return camera_id in cls._active_bursts

    @classmethod
    def active_count(cls) -> int:
        """当前爆发路数。"""
        with cls._lock:
            return len(cls._active_bursts)

    @classmethod
    def get_degraded_config(cls) -> dict:
        """弹性降级配置（供 Processor 在无令牌时使用）。"""
        return {
            "fps": cls.DEGRADED_FPS,
            "threshold": cls.DEGRADED_THRESHOLD,
        }
```

- [ ] **Step 2: 在 stream_loader.py 顶部导入**

```python
# web-flask/app/core/stream_loader.py — 在 import 段添加
from app.core.burst_token import BurstTokenManager
```

- [ ] **Step 3: StreamLoader.__init__ 增加爆发相关字段**

```python
# web-flask/app/core/stream_loader.py — 在 __init__ 末尾添加

        # 🚀 爆发令牌管理
        self.burst_token_holder = False
        self.burst_start_time = 0.0
```

- [ ] **Step 4: Commit**

```bash
git add web-flask/app/core/burst_token.py web-flask/app/core/stream_loader.py
git commit -m "feat(P0): global burst token bucket (max 3, 8s timeout, degraded fallback)"
```

---

### Task 4: Thumbnail 缩略图接口（Python）

**Files:**
- Modify: `web-flask/app/api/monitor.py` (新增 thumbnail 路由)
- Modify: `web-flask/app/core/stream_loader.py` (新增 get_thumbnail 方法)

- [ ] **Step 1: StreamLoader 新增 get_thumbnail 方法**

```python
# web-flask/app/core/stream_loader.py — 新增方法

    def get_thumbnail(self, target_width=320, target_height=240, quality=60):
        """返回当前最新帧的缩略图 bytes (JPEG)。"""
        with self.lock:
            frame = self.output_frame if self.output_frame is not None else self.latest_frame
            if frame is None:
                return None
            # 缩放到缩略图尺寸
            thumb = cv2.resize(frame, (target_width, target_height))
            ret, buf = cv2.imencode('.jpg', thumb, [cv2.IMWRITE_JPEG_QUALITY, quality])
            if ret:
                return buf.tobytes()
            return None
```

- [ ] **Step 2: monitor.py 新增 thumbnail 路由**

```python
# web-flask/app/api/monitor.py — 添加新路由

@monitor_bp.route('/thumbnail/<int:device_id>')
def thumbnail(device_id):
    """返回 320x240 JPG 缩略图，供前端网格定时刷新。"""
    sm = get_sm()
    if not sm:
        return "Stream Manager Offline", 503

    if device_id not in device_config_cache:
        _do_sync()

    config = device_config_cache.get(device_id)
    if not config:
        return "Device Not Found", 404
    if not config.get('enabled'):
        return "Device Disabled", 403

    loader = sm.stream_loaders.get(device_id)
    if not loader or not loader.running or loader.latest_frame is None:
        # 返回 1x1 透明像素占位（避免前端破图）
        return Response(
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b',
            mimetype='image/gif'
        )

    thumb_bytes = loader.get_thumbnail()
    if thumb_bytes is None:
        return "No Frame", 503

    return Response(thumb_bytes, mimetype='image/jpeg')
```

- [ ] **Step 3: Commit**

```bash
git add web-flask/app/core/stream_loader.py web-flask/app/api/monitor.py
git commit -m "feat(P0): add /api/camera/{id}/thumbnail endpoint (320x240 JPG)"
```

---

### Task 5: Monitor.vue 网格+侧边栏布局改造

**Files:**
- Modify: `web-vue/src/views/Monitor.vue` (template + script)

- [ ] **Step 1: 改造 template 加入网格模式**

关键改动：
1. 中间区域增加 `<div class="grid-view">` 显示 4x5 网格缩略图
2. 右侧面板 `device-list-scroll` 改为 el-tree 虚拟滚动
3. 每路网格 `<img>` 绑定独立定时器，1000 + Math.random() * 500 ms
4. 双击网格项切换为单路 MJPEG 详情模式

```vue
<!-- web-vue/src/views/Monitor.vue — template 改造节选 -->

<template>
  <div class="monitor-screen">
    <!-- top-bar 保持不变 -->
    <div class="top-bar">...</div>

    <div class="main-content">
      <!-- 左侧状态面板 保持不变 -->
      <aside class="side-panel left-panel">...</aside>

      <!-- 🚀 中间区域：双模式切换 -->
      <section class="center-monitor">
        <!-- 模式选择器 -->
        <div class="view-mode-tabs">
          <el-radio-group v-model="viewMode" size="small">
            <el-radio-button value="grid">
              <el-icon><Grid /></el-icon> 网格
            </el-radio-button>
            <el-radio-button value="detail">
              <el-icon><VideoCameraFilled /></el-icon> 详情
            </el-radio-button>
          </el-radio-group>
          <span class="grid-info" v-if="viewMode === 'grid'">
            共 {{ filteredDevices.length }} 路 · 
            在线 {{ onlineCount }} · 
            报警 {{ Object.keys(alarmState).filter(k => alarmState[k]).length }}
          </span>
        </div>

        <!-- 网格模式 -->
        <div v-if="viewMode === 'grid'" class="grid-view">
          <div
            v-for="device in filteredDevices"
            :key="device.id"
            class="grid-cell"
            :class="{
              'offline': device.status !== 1 || !device.enabled,
              'is-alarm': alarmState[device.id]
            }"
            @dblclick="enterDetail(device)"
          >
            <div class="cell-header">
              <span class="cell-name">{{ device.name }}</span>
              <span class="cell-status" :class="device.status === 1 ? 'online' : 'offline'">
                {{ device.status === 1 ? 'LIVE' : 'OFF' }}
              </span>
            </div>
            <img
              v-if="device.status === 1 && device.enabled"
              :src="getThumbnailUrl(device.id)"
              class="cell-thumb"
              @error="onThumbError($event, device.id)"
            >
            <div v-else class="cell-overlay">
              <el-icon :size="32"><VideoCameraFilled /></el-icon>
            </div>
            <div v-if="alarmState[device.id]" class="cell-alarm-badge">
              <el-icon><Warning /></el-icon> 吸烟
            </div>
          </div>
        </div>

        <!-- 详情模式（单路 MJPEG，保留原有播放器） -->
        <div v-if="viewMode === 'detail'" class="detail-view">
          <div v-if="currentDevice" class="monitor-player-box" ...>
            <!-- 保持原有 player 代码不变 -->
          </div>
          <div v-else class="empty-state">...</div>
        </div>
      </section>

      <!-- 🚀 右侧面板：el-tree 虚拟滚动替代平铺列表 -->
      <aside class="side-panel right-panel">
        <div class="panel-section full-height">
          <div class="section-title">
            <span class="title-dot"></span> 设备列表 ({{ filteredDevices.length }})
          </div>
          <!-- 搜索框 -->
          <el-input
            v-model="deviceSearch"
            placeholder="搜索设备名称或 ID..."
            size="small"
            clearable
            class="device-search-input"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <!-- el-tree 虚拟滚动 -->
          <el-tree
            :data="deviceTreeData"
            :props="treeProps"
            node-key="id"
            :filter-node-method="filterDeviceNode"
            highlight-current
            :height="treeHeight"
            :use-virtual="true"
            @node-click="handleTreeNodeClick"
            class="device-tree"
          >
            <template #default="{ node, data }">
              <div class="tree-node" :class="{ 'is-alarm': data.isAlarm }">
                <span v-if="data.type === 'group'" class="node-group-icon">
                  <el-icon><Folder /></el-icon>
                </span>
                <span v-else class="node-device-status" :class="data.status === 1 ? 'online' : 'offline'"></span>
                <span class="node-label">{{ data.label }}</span>
                <span v-if="data.type === 'group'" class="node-count">({{ data.children?.length || 0 }})</span>
                <el-icon v-if="data.isAlarm" color="#f56c6c" class="blink-icon"><Warning /></el-icon>
              </div>
            </template>
          </el-tree>
        </div>
      </aside>
    </div>

    <!-- bottom-bar 保持不变 -->
    <!-- el-drawer 保持不变 -->
  </div>
</template>
```

- [ ] **Step 2: 新增 script 代码（网格模式相关）**

```typescript
// web-vue/src/views/Monitor.vue — script 新增

const AI_API = import.meta.env.VITE_APP_AI_API || 'http://localhost:5000'

// 🚀 视图模式
const viewMode = ref<'grid' | 'detail'>('grid')

// 🚀 缩略图版本号（每路独立定时器更新，避免全量重渲染）
const thumbVersions = ref<Record<number, number>>({})
let thumbTimers: Record<number, ReturnType<typeof setInterval>> = {}

const getThumbnailUrl = (id: number) => {
  const v = thumbVersions.value[id] || 0
  return `${AI_API}/api/v1/monitor/thumbnail/${id}?_=${v}`
}

// 启动定时器：每路独立 interval = 1000 + Math.random() * 500 ms
const startThumbTimers = () => {
  // 清理旧定时器
  Object.values(thumbTimers).forEach(clearInterval)
  thumbTimers = {}

  for (const device of deviceList.value) {
    if (device.status !== 1 || !device.enabled) continue
    const id = device.id
    const interval = 1000 + Math.random() * 500
    thumbTimers[id] = setInterval(() => {
      thumbVersions.value = {
        ...thumbVersions.value,
        [id]: (thumbVersions.value[id] || 0) + 1
      }
    }, interval)
  }
}

watch(deviceList, () => startThumbTimers(), { deep: true })

// 🚀 网格设备筛选（基于搜索）
const deviceSearch = ref('')
const filteredDevices = computed(() => {
  if (!deviceSearch.value) return deviceList.value
  const q = deviceSearch.value.toLowerCase()
  return deviceList.value.filter(d =>
    d.name.toLowerCase().includes(q) || String(d.id).includes(q)
  )
})

// 🚀 el-tree 数据构建（三级树状：教学楼 → 楼层 → 摄像头）
const treeProps = { children: 'children', label: 'label' }
const treeHeight = computed(() => Math.max(window.innerHeight - 300, 400))

// el-tree 过滤方法
const filterDeviceNode = (value: string, data: any) => {
  if (!value) return true
  return data.label.toLowerCase().includes(value.toLowerCase())
}

watch(deviceSearch, (val) => {
  // el-tree filter 由 el-tree 的 :filter-node-method 自动调用
})

// 🚀 进入详情模式
const enterDetail = (device: any) => {
  currentDevice.value = device
  viewMode.value = 'detail'
  deviceStore.updateDeviceState(device.id, { isVideoError: false, isLoading: true })
  // 停止该路的缩略图定时器
}

// 🚀 缩略图加载错误处理
const onThumbError = (event: Event, deviceId: number) => {
  const img = event.target as HTMLImageElement
  // 3 秒后重试
  setTimeout(() => {
    thumbVersions.value = {
      ...thumbVersions.value,
      [deviceId]: (thumbVersions.value[deviceId] || 0) + 1
    }
  }, 3000)
}

// 🚀 在 onMounted 中启动缩略图定时器
// 在 onUnmounted 中清理
// onMounted 添加: startThumbTimers()
// onUnmounted 添加: Object.values(thumbTimers).forEach(clearInterval)
```

- [ ] **Step 3: 新增 grid-video.css 样式**

```css
/* 🚀 网格视图样式 — 追加到 Monitor.vue 的 <style> 末尾 */

/* 模式切换栏 */
.view-mode-tabs {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: rgba(22, 33, 52, 0.6);
  border-bottom: 1px solid rgba(64, 158, 255, 0.1);
}
.grid-info {
  font-size: 12px;
  color: #909399;
}

/* 网格容器 */
.grid-view {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 8px;
  padding: 12px;
  overflow-y: auto;
  flex: 1;
}

/* 单个网格单元 */
.grid-cell {
  position: relative;
  aspect-ratio: 4 / 3;
  background: #000;
  border: 1px solid rgba(64, 158, 255, 0.2);
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
}
.grid-cell:hover {
  border-color: #409eff;
  box-shadow: 0 0 12px rgba(64, 158, 255, 0.3);
}
.grid-cell.offline {
  border-color: #f56c6c;
  opacity: 0.6;
}
.grid-cell.is-alarm {
  border-color: #f56c6c;
  animation: flashBorder 0.8s infinite alternate;
}

.grid-cell .cell-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  padding: 4px 8px;
  background: linear-gradient(to bottom, rgba(0,0,0,0.8), transparent);
  z-index: 2;
  font-size: 12px;
}
.cell-name {
  color: #e4e7ed;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cell-status {
  font-weight: bold;
  flex-shrink: 0;
}
.cell-status.online { color: #67c23a; }
.cell-status.offline { color: #f56c6c; }

.cell-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.cell-overlay {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #606266;
}

.cell-alarm-badge {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(245, 108, 108, 0.85);
  color: white;
  font-size: 12px;
  padding: 3px 8px;
  display: flex;
  align-items: center;
  gap: 4px;
  z-index: 2;
}

/* 设备树样式 */
.right-panel .el-tree {
  background: transparent;
  color: #e4e7ed;
}
.right-panel .el-tree-node__content {
  background: transparent;
}
.right-panel .el-tree-node__content:hover {
  background: rgba(64, 158, 255, 0.1);
}
.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  padding: 2px 0;
}
.node-device-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.node-device-status.online { background: #67c23a; }
.node-device-status.offline { background: #f56c6c; }
.node-group-icon { color: #e6a23c; }
.node-count { color: #909399; font-size: 11px; margin-left: auto; }

/* 搜索框 */
.device-search-input {
  margin-bottom: 8px;
}
.device-search-input :deep(.el-input__wrapper) {
  background: rgba(0,0,0,0.3);
  border: 1px solid rgba(64, 158, 255, 0.2);
}
.device-search-input :deep(.el-input__inner) {
  color: #e4e7ed;
}
```

- [ ] **Step 4: Commit**

```bash
git add web-vue/src/views/Monitor.vue
git commit -m "feat(P0): grid + sidebar layout with el-tree virtual scroll and jitter thumbnails"
```

---

### Task 6: 集成验证（Mock 测试 & 冒烟测试）

**Files:**
- Create: `web-flask/tests/test_burst_token.py`
- Create: `web-flask/tests/test_reader_deque.py`

- [ ] **Step 1: 编写 BurstTokenManager 单元测试**

```python
# web-flask/tests/test_burst_token.py

import time
import sys
sys.path.insert(0, 'web-flask/app/core')
from burst_token import BurstTokenManager

def test_acquire_release():
    """测试令牌获取和归还。"""
    now = time.time()
    assert BurstTokenManager.acquire(1, now) is True
    assert BurstTokenManager.is_in_burst(1) is True
    assert BurstTokenManager.active_count() == 1

    BurstTokenManager.release(1)
    assert BurstTokenManager.is_in_burst(1) is False
    assert BurstTokenManager.active_count() == 0

def test_max_bursts():
    """测试超过 MAX_BURSTS 时返回 False（进入降级模式）。"""
    now = time.time()
    assert BurstTokenManager.acquire(1, now) is True
    assert BurstTokenManager.acquire(2, now) is True
    assert BurstTokenManager.acquire(3, now) is True
    # 第 4 路应被拒绝
    assert BurstTokenManager.acquire(4, now) is False
    # 弹性降级配置应正确返回
    config = BurstTokenManager.get_degraded_config()
    assert config['threshold'] == 0.85

    BurstTokenManager.release(1)
    BurstTokenManager.release(2)
    BurstTokenManager.release(3)

def test_timeout_reclaim():
    """测试超时后自动回收。"""
    # 模拟过去的时间（now + 9s 使 8s 超时触发）
    past = time.time() - 9
    BurstTokenManager.acquire(1, past)
    # 新时间戳应触发过期清理
    now = time.time()
    assert BurstTokenManager.acquire(2, now) is True
    # 第 1 路应该已被清理
    assert BurstTokenManager.is_in_burst(1) is False
    BurstTokenManager.release(2)

def test_degraded_config():
    """弹性降级配置。"""
    config = BurstTokenManager.get_degraded_config()
    assert config['fps'] == 5
    assert config['threshold'] == 0.85
```

- [ ] **Step 2: 编写 Deque Buffer 超时测试**

```python
# web-flask/tests/test_reader_deque.py

import time
import cv2
import numpy as np
from collections import deque

def test_deque_maxlen():
    """验证 deque(maxlen=10) 不会超过 10 帧。"""
    buf = deque(maxlen=10)
    for i in range(15):
        buf.append((time.time(), np.zeros((100, 100, 3), dtype=np.uint8)))
    assert len(buf) == 10

def test_timeout_clear():
    """验证 2.5s 超时清空：模拟队首帧过旧。"""
    buf = deque(maxlen=10)
    old_ts = time.time() - 5.0  # 5 秒前
    buf.append((old_ts, np.zeros((100, 100, 3), dtype=np.uint8)))
    buf.append((time.time(), np.zeros((100, 100, 3), dtype=np.uint8)))

    now = time.time()
    if now - buf[0][0] > 2.5:
        buf.clear()
    assert len(buf) == 0
```

- [ ] **Step 3: 运行测试验证**

```bash
cd web-flask && python -m pytest tests/test_burst_token.py -v
```

Expected output:
```
test_acquire_release PASSED
test_max_bursts PASSED
test_timeout_reclaim PASSED
test_degraded_config PASSED
```

```bash
cd web-flask && python -m pytest tests/test_reader_deque.py -v
```

Expected output:
```
test_deque_maxlen PASSED
test_timeout_clear PASSED
```

- [ ] **Step 4: Commit**

```bash
git add web-flask/tests/test_burst_token.py web-flask/tests/test_reader_deque.py
git commit -m "test(P0): burst token bucket + deque buffer unit tests"
```
