# Phase 2: 全链路降载 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 引入 MediaMTX 媒体网关解除 OpenCV 高并发拉流崩溃，实现 FFmpeg 直写 H.264 消除二次转码，心跳批量聚合+增量对账降低 Java QPS，证据分级+自动清理控制磁盘增长。

**Architecture:** 单机部署 MediaMTX（RTSP 纯代理），Python 从本地代理拉流替代直连摄像头；录像从 OpenCV mp4v 切换为 FFmpeg subprocess；Java 新增增量对账接口；证据分级在 Python 端判断，生命周期由 Java 定时任务执行。

**Tech Stack:** MediaMTX (Go binary) / Python 3.10+ / OpenCV / FFmpeg / Java Spring Boot + MyBatis

---

### Task 1: MediaMTX 部署与配置

**Files:**
- Create: `web-flask/mediamtx.yml` (MediaMTX 配置文件)
- Create: `web-flask/scripts/start_mediamtx.bat` (Windows 启动脚本)

- [ ] **Step 1: 编写 MediaMTX 配置文件**

```yml
# web-flask/mediamtx.yml

# MediaMTX 配置 — 200 路 RTSP 纯代理，零 CPU 转发
rtsp: true
rtspAddress: ":8554"
rtmp: false    # 禁用 RTMP，无二次转码
hls: false     # 禁用 HLS
webrtc: false  # 禁用 WebRTC
api: false     # 禁用 API 接口

# 日志
logLevel: error
logDestinations: ["file"]
logFile: "logs/mediamtx.log"

# 路径配置：所有 /cam/ 前缀的路径都作为纯 RTSP 代理
paths:
  cam_{id}:
    source: ondemand  # 按需拉流，节省带宽
    sourceOnDemandStartAfter: 2s
    sourceOnDemandCloseAfter: 10s
  cam_{id}_main:
    source: ondemand
    sourceOnDemandStartAfter: 2s
    sourceOnDemandCloseAfter: 10s
```

> 注意：MediaMTX 的路径配置需要根据实际摄像头 RTSP 地址动态设置。上述配置为框架模板。实际部署时，启动 MediaMTX 后通过 REST API 或配置文件按摄像头添加源。

- [ ] **Step 2: 编写 Windows 启动脚本**

```bat
@echo off
REM web-flask/scripts/start_mediamtx.bat
REM MediaMTX 启动脚本 — 在后台静默运行

setlocal
cd /d "%~dp0.."
mkdir logs 2>nul

echo [MediaMTX] 正在启动 RTSP 代理网关... > con
start /B /MIN mediamtx.exe mediamtx.yml
if %errorlevel% equ 0 (
    echo [MediaMTX] 启动成功，监听端口 8554 > con
) else (
    echo [MediaMTX] 启动失败，请检查 mediamtx.exe 是否存在 > con
    exit /b 1
)
```

- [ ] **Step 3: 添加 MediaMTX 版本号到依赖文档**

在 `web-flask/README.md` 或 `web-flask/requirements.txt` 添加注释，说明 MediaMTX 版本要求（v1.9.0+）。

- [ ] **Step 4: Commit**

```bash
git add web-flask/mediamtx.yml web-flask/scripts/start_mediamtx.bat
git commit -m "feat(P1): add MediaMTX config and startup script for RTSP proxy gateway"
```

---

### Task 2: Python 切换为本地 MediaMTX 代理拉流 + 子/主码流分离

**Files:**
- Modify: `web-flask/app/core/stream_loader.py` (_connect 中改用本地代理地址)

- [ ] **Step 1: 修改 _connect 使用本地 MediaMTX 代理地址**

StreamLoader 的 `rtsp_url` 仍然由 Java 同步传递原始摄像头地址，但在 `_connect` 中自动转换为本地 MediaMTX 代理地址。主码流和子码流通过 URL 后缀区分。

```python
# web-flask/app/core/stream_loader.py — _connect 改造

    MEDIATIMX_HOST = "127.0.0.1"
    MEDIATIMX_PORT = 8554

    def _get_proxy_url(self, main_stream=False):
        """
        将原始 RTSP 地址转换为本地 MediaMTX 代理地址。
        子码流 : rtsp://127.0.0.1:8554/cam/{id}_sub
        主码流 : rtsp://127.0.0.1:8554/cam/{id}_main
        """
        suffix = "_main" if main_stream else "_sub"
        return f"rtsp://{self.MEDIATIMX_HOST}:{self.MEDIATIMX_PORT}/cam/{self.camera_id}{suffix}"

    def _connect(self):
        """从本地 MediaMTX 代理拉流。"""
        try:
            if self.cap:
                self.cap.release()

            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;3000000|threads;1"

            # 🚀 改用本地 MediaMTX 代理子码流
            proxy_url = self._get_proxy_url(main_stream=False)
            logger.info(f"🛰️ 代理拉流: {proxy_url}")
            self.cap = cv2.VideoCapture(proxy_url, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    with self.lock:
                        self.latest_frame = frame
                        self.last_read_time = time.time()
                    self._update_db_status(1)
                    return True
            return False
        except Exception as e:
            logger.error(f"💥 代理连接异常: {e}")
            return False

    # 🚀 新增：报警录像时使用主码流
    def get_main_stream_url(self):
        """返回主码流代理地址，供 FFmpeg 录像使用。"""
        return self._get_proxy_url(main_stream=True)
```

- [ ] **Step 2: 修改 _trigger_alarm_save 使用主码流 FFmpeg**

```python
# web-flask/app/core/stream_loader.py — _trigger_alarm_save 改造

    def _trigger_alarm_save(self, frame, owner_id, conf):
        ts = int(time.time())
        img_name = f"alarm_cam{self.camera_id}__p{owner_id or 'unk'}_{ts}.jpg"
        self.recorder.save_snapshot(frame, img_name)

        # 🚀 改用 FFmpeg 从主码流直写 H.264，放弃 OpenCV mp4v
        video_name = img_name.replace('.jpg', '.mp4')
        video_path = os.path.join(self.recorder.save_dir, video_name)
        main_url = self.get_main_stream_url()

        def record_video():
            try:
                cmd = [
                    'ffmpeg', '-y',
                    '-rtsp_transport', 'tcp',
                    '-i', main_url,
                    '-vcodec', 'copy',
                    '-ss', '0',
                    '-noaccurate_seek',
                    '-t', '10',
                    video_path
                ]
                # 🚀 15 秒超时 + Windows 低优先级
                CREATE_BELOW_NORMAL = 0x00004000
                subprocess.run(
                    cmd,
                    timeout=15,
                    creationflags=CREATE_BELOW_NORMAL,
                    capture_output=True,
                    text=True
                )
                logger.info(f"🎥 FFmpeg 录像完成: {video_name}")
            except subprocess.TimeoutExpired:
                logger.error(f"⏰ FFmpeg 录像超时 CID={self.camera_id}，强制终止")
            except Exception as e:
                logger.error(f"⚠️ 录像异常: {e}")

        threading.Thread(target=record_video, daemon=True).start()

        def notify_java():
            try:
                requests.post("http://localhost:8080/api/alerts/report", json={
                    "deviceId": self.camera_id, "type": "SMOKING",
                    "confidence": round(float(conf), 2),
                    "snapshotUrl": f"static/evidence/snapshots/{img_name}",
                    "videoUrl": f"static/evidence/{video_name}",
                    "personId": owner_id,
                    "description": f"人员{owner_id or '未知'}吸烟"
                }, timeout=3)
            except:
                pass
        threading.Thread(target=notify_java, daemon=True).start()
```

- [ ] **Step 3: 删除 recorder.py 中过时的 _convert_to_h264 和 mp4v 相关代码**

移除 `EvidenceRecorder._convert_to_h264` 方法（已被 FFmpeg 直写替代）。
移除 `EvidenceRecorder.stop_recording` 中对 `_convert_to_h264` 的调用（方法签名保留但清理内部逻辑）。

```python
# web-flask/app/core/recorder.py — 清理

    def stop_recording(self):
        """保持方法签名兼容，但内部逻辑简化（不再需要转码）。"""
        with self.lock:
            if not self.is_recording or self.writer is None:
                return
            self.writer.release()
            self.writer = None
            self.is_recording = False
        logger.info(f"🛑 录制闭合: {os.path.basename(self.current_video_path)}")

# 🚀 删除 _convert_to_h264 方法（FFmpeg 直写已替代其功能）
```

- [ ] **Step 4: Commit**

```bash
git add web-flask/app/core/stream_loader.py web-flask/app/core/recorder.py
git commit -m "feat(P1): switch to local MediaMTX proxy, main/sub stream separation, ffmpeg direct H.264 write"
```

---

### Task 3: 录像 I/O 限流 + 超时守护

**Files:**
- Create: `web-flask/app/core/io_throttle.py` (全局 Semaphore 和超时管理)
- Modify: `web-flask/app/core/stream_loader.py` (集成 I/O 限流)

- [ ] **Step 1: 创建 IOThrottle 模块**

```python
# web-flask/app/core/io_throttle.py

"""
全局 I/O 限流管理器。

限制并发写盘操作数，防止多路同时录像挤死 SSD。
"""

import threading
import subprocess
import logging
import os
import signal

logger = logging.getLogger(__name__)

class IOThrottle:
    """
    写盘限流令牌桶。
    - max_concurrent: 最大并发写盘数（默认 2）
    - 提供 safe_run 包装方法自动管理
    """

    _semaphore = threading.Semaphore(2)
    _active_pids: set[int] = set()
    _lock = threading.Lock()

    @classmethod
    def acquire(cls) -> bool:
        """获取写盘令牌。阻塞直到有可用槽位。"""
        acquired = cls._semaphore.acquire(blocking=True, timeout=30)
        if acquired:
            logger.debug(f"🔑 IO 令牌获取成功 (活跃: {cls.active_count()})")
        else:
            logger.error("💥 IO 令牌等待超时 (30s)")
        return acquired

    @classmethod
    def release(cls):
        """归还写盘令牌。"""
        cls._semaphore.release()

    @classmethod
    def active_count(cls) -> int:
        with cls._lock:
            return len(cls._active_pids)

    @classmethod
    def run_ffmpeg(cls, cmd: list, timeout: int = 15) -> bool:
        """
        带限流和超时的 FFmpeg 执行包装。

        1. 获取写盘令牌
        2. 设置 Windows Below Normal 优先级
        3. 启动进程并在超时后强制终止
        """
        if not cls.acquire():
            return False

        process = None
        try:
            CREATE_BELOW_NORMAL = 0x00004000
            process = subprocess.Popen(
                cmd,
                creationflags=CREATE_BELOW_NORMAL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            with cls._lock:
                cls._active_pids.add(process.pid)

            process.wait(timeout=timeout)
            return process.returncode == 0

        except subprocess.TimeoutExpired:
            logger.warning(f"⏰ FFmpeg 超时 ({timeout}s)，强制终止 PID={process.pid}")
            if process:
                try:
                    # Windows 下使用 taskkill
                    subprocess.run(
                        ['taskkill', '/F', '/T', '/PID', str(process.pid)],
                        capture_output=True
                    )
                except Exception as e:
                    logger.error(f"终止失败: {e}")
            return False

        except Exception as e:
            logger.error(f"FFmpeg 异常: {e}")
            return False

        finally:
            if process:
                with cls._lock:
                    cls._active_pids.discard(process.pid)
            cls.release()
```

- [ ] **Step 2: 在 stream_loader.py 中集成 IOThrottle**

修改 `_trigger_alarm_save` 中的 `record_video` 函数，改用 `IOThrottle.run_ffmpeg`。

```python
# web-flask/app/core/stream_loader.py — record_video 改用 IOThrottle

from app.core.io_throttle import IOThrottle

# 在 _trigger_alarm_save 的 record_video 函数中：

        def record_video():
            cmd = [
                'ffmpeg', '-y',
                '-rtsp_transport', 'tcp',
                '-i', main_url,
                '-vcodec', 'copy',
                '-ss', '0',
                '-noaccurate_seek',
                '-t', '10',
                video_path
            ]
            success = IOThrottle.run_ffmpeg(cmd, timeout=15)
            if success:
                logger.info(f"🎥 录像完成: {video_name}")
            else:
                logger.warning(f"⚠️ 录像失败或超时: {video_name}")
```

- [ ] **Step 3: Commit**

```bash
git add web-flask/app/core/io_throttle.py web-flask/app/core/stream_loader.py
git commit -m "feat(P1): IOThrottle with Semaphore(2) + ffmpeg timeout+SIGKILL + Below Normal priority"
```

---

### Task 4: 心跳批量聚合 + Java 增量对账接口

**Files:**
- Modify: `web-flask/app/core/stream_loader.py` (移除独立心跳，StreamManager 新增批量上报)
- Modify: `web-back/src/main/java/org/example/webback/controller/DeviceController.java` (增量对账接口)
- Modify: `web-back/src/main/java/org/example/webback/service/DeviceService.java` (状态缓存)

- [ ] **Step 1: StreamManager 增加批量心跳聚合定时器**

```python
# web-flask/app/core/stream_loader.py — StreamManager 新增

import threading
import time

class StreamManager:
    def __init__(self):
        # ... 原有初始化代码 ...
        self._heartbeat_timer = None
        self._heartbeat_interval = 3.0

    def _start_heartbeat_aggregator(self):
        """每 3 秒批量上报 200 路状态。"""

        def aggregate_and_report():
            while True:
                time.sleep(self._heartbeat_interval)
                try:
                    batch = []
                    with self.lock:
                        for cid, loader in self.stream_loaders.items():
                            status = 1 if (loader.running
                                           and loader.latest_frame is not None
                                           and not loader.reconnect_requested) else 0
                            batch.append({"id": cid, "status": status})

                    if batch:
                        requests.post(
                            "http://localhost:8080/api/monitor/devices/batch-sync",
                            json=batch,
                            timeout=2.0
                        )
                except Exception:
                    pass  # 上报失败不阻塞

        t = threading.Thread(target=aggregate_and_report, daemon=True)
        t.start()
```

同时在 `StreamManager.init_app` 中调用 `_start_heartbeat_aggregator()`。

- [ ] **Step 2: 移除 StreamLoader 中的独立 _update_db_status 调用**

- `_connect()` 中移除 `self._update_db_status(1)`
- `_reader_thread` 中移除 `self._update_db_status(0)` 和相关调用
- `_watchdog_thread` 中移除 `self._update_db_status(0)`
- 保留 `_update_db_status` 方法本身但标记为 deprecated 注释（兼容过渡期）

- [ ] **Step 3: Java 新增增量对账接口**

```java
// web-back/.../controller/DeviceController.java — 新增方法

@GetMapping("/api/monitor/devices")
public Result getDevicesDelta(@RequestParam(value = "version", defaultValue = "0") long clientVersion) {
    // 获取当前全局版本号（每次设备状态变更时递增）
    DeviceSyncInfo delta = deviceService.getDevicesSince(clientVersion);
    if (delta == null || delta.getChanges().isEmpty()) {
        return Result.success(new ArrayList<>());  // 无变更返回空数组
    }
    return Result.success(delta.getChanges());
}
```

- [ ] **Step 4: Java 设备状态缓存 + 版本号管理**

```java
// web-back/.../service/DeviceService.java — 新增

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Service
public class DeviceService {

    // 🚀 内存状态缓存（心跳不落 MySQL）
    private final ConcurrentHashMap<Long, DeviceState> deviceStatusCache = new ConcurrentHashMap<>();
    private final AtomicLong globalVersion = new AtomicLong(0);

    @Data
    public static class DeviceState {
        private long id;
        private int status;
        private long version;
    }

    @Data
    public static class DeviceSyncInfo {
        private List<DeviceState> changes;
        private long currentVersion;
    }

    /**
     * 批量心跳上报（替代每路独立调用）
     */
    @PostMapping("/api/monitor/devices/batch-sync")
    public Result batchSync(@RequestBody List<Map<String, Object>> batch) {
        List<DeviceState> changes = new ArrayList<>();
        for (Map<String, Object> item : batch) {
            long id = ((Number) item.get("id")).longValue();
            int status = ((Number) item.get("status")).intValue();

            DeviceState prev = deviceStatusCache.get(id);
            if (prev == null || prev.status != status) {
                long ver = globalVersion.incrementAndGet();
                DeviceState state = new DeviceState();
                state.setId(id);
                state.setStatus(status);
                state.setVersion(ver);
                deviceStatusCache.put(id, state);
                changes.add(state);
            }
        }
        return Result.success();
    }

    /**
     * 获取增量变更（前端轮询用）
     */
    public DeviceSyncInfo getDevicesSince(long clientVersion) {
        long currentVer = globalVersion.get();
        if (clientVersion >= currentVer) {
            return null;  // 无变更
        }
        List<DeviceState> changes = new ArrayList<>();
        for (DeviceState state : deviceStatusCache.values()) {
            if (state.getVersion() > clientVersion) {
                changes.add(state);
            }
        }
        DeviceSyncInfo info = new DeviceSyncInfo();
        info.setChanges(changes);
        info.setCurrentVersion(currentVer);
        return info;
    }
}
```

- [ ] **Step 5: 前端对应增量接口调用**

前端 Monitor.vue 需要将原有的全量轮询改为带 version 的增量轮询：

```typescript
// web-vue/src/stores/device.ts — 新增增量轮询

const LOCAL_VERSION_KEY = 'device_local_version'
const localVersion = ref(parseInt(localStorage.getItem(LOCAL_VERSION_KEY) || '0', 10))

const fetchDevicesDelta = async () => {
  try {
    const res = await axios.get(`${JAVA_BASE}/api/monitor/devices`, {
      params: { version: localVersion.value },
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.data.code === 200) {
      const delta = res.data.data
      if (delta.length === 0) return  // 无变更，不更新
      for (const change of delta) {
        // 原地更新设备列表中的对应项
        const idx = deviceList.value.findIndex(d => d.id === change.id)
        if (idx !== -1) {
          deviceList.value[idx].status = change.status
        }
        // 更新本地版本号
        if (change.version > localVersion.value) {
          localVersion.value = change.version
        }
      }
      localStorage.setItem(LOCAL_VERSION_KEY, String(localVersion.value))
    }
  } catch (e) {
    // 静默处理
  }
}
```

- [ ] **Step 6: Commit**

```bash
git add web-flask/app/core/stream_loader.py \
      web-back/src/main/java/org/example/webback/controller/DeviceController.java \
      web-back/src/main/java/org/example/webback/service/DeviceService.java \
      web-vue/src/stores/device.ts
git commit -m "feat(P1): batch heartbeat + incremental diff polling + Java memory state cache"
```

---

### Task 5: 证据分级 + Java 自动清理定时任务

**Files:**
- Modify: `web-flask/app/core/stream_loader.py` (_trigger_alarm_save 按置信度分支)
- Modify: `web-back/.../service/EvidenceCleanupService.java` (新建清理服务)
- Modify: `web-back/.../config/ScheduledConfig.java` (定时任务配置)

- [ ] **Step 1: _trigger_alarm_save 增加证据分级分支**

```python
# web-flask/app/core/stream_loader.py — 证据分级

    # 🚀 证据分级阈值（与 Phase 1 的 0.55/0.80 预录门限不同）
    EVIDENCE_VIDEO_THRESHOLD = 0.85    # ≥0.85: 快照 + 视频
    EVIDENCE_SNAPSHOT_THRESHOLD = 0.65 # 0.65~0.85: 仅快照
    # < 0.65: 不保留（已在 Phase 1 中过滤）

    def _trigger_alarm_save(self, frame, owner_id, conf):
        ts = int(time.time())
        img_name = f"alarm_cam{self.camera_id}__p{owner_id or 'unk'}_{ts}.jpg"

        # 🚀 所有 ≥0.65 的都保存快照
        if conf >= self.EVIDENCE_SNAPSHOT_THRESHOLD:
            self.recorder.save_snapshot(frame, img_name)

        # 🚀 仅 ≥0.85 录制视频
        if conf >= self.EVIDENCE_VIDEO_THRESHOLD:
            video_name = img_name.replace('.jpg', '.mp4')
            video_path = os.path.join(self.recorder.save_dir, video_name)
            main_url = self.get_main_stream_url()

            def record_video():
                cmd = [
                    'ffmpeg', '-y',
                    '-rtsp_transport', 'tcp',
                    '-i', main_url,
                    '-vcodec', 'copy',
                    '-ss', '0',
                    '-noaccurate_seek',
                    '-t', '10',
                    video_path
                ]
                IOThrottle.run_ffmpeg(cmd, timeout=15)

            threading.Thread(target=record_video, daemon=True).start()

        # 🚀 通知 Java（快照 URL 和 videoUrl 按分级结果传递）
        def notify_java():
            try:
                payload = {
                    "deviceId": self.camera_id,
                    "type": "SMOKING",
                    "confidence": round(float(conf), 2),
                    "snapshotUrl": f"static/evidence/snapshots/{img_name}" if conf >= self.EVIDENCE_SNAPSHOT_THRESHOLD else "",
                    "videoUrl": f"static/evidence/{video_name}" if conf >= self.EVIDENCE_VIDEO_THRESHOLD else "",
                    "personId": owner_id,
                    "description": f"人员{owner_id or '未知'}吸烟"
                }
                requests.post("http://localhost:8080/api/alerts/report", json=payload, timeout=3)
            except:
                pass
        threading.Thread(target=notify_java, daemon=True).start()
```

- [ ] **Step 2: 删除旧的 _trigger_alarm_save 方法**

确认已用新版替换。

- [ ] **Step 3: Java 创建证据自动清理定时任务**

```java
// web-back/.../service/EvidenceCleanupService.java

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import java.io.File;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;

/**
 * 证据文件生命周期管理。
 * - 未确认/misreport: 7 天后删除关联证据
 * - 已确认: 视频 90 天后删除，快照永久保留
 */
@Service
public class EvidenceCleanupService {

    private static final String EVIDENCE_DIR = "app/static/evidence";

    @Scheduled(cron = "0 0 3 * * ?")  // 每天凌晨 3 点
    public void cleanupEvidence() {
        // 1. 查询 7 天前仍未确认的报警记录
        //    UPDATE alarms SET evidence_deleted=1 WHERE ...
        //    同时删除关联文件

        // 2. 查询 90 天前已确认的报警记录
        //    删除其 video 文件，保留 snapshot

        // 由 MyBatis 查询 + 文件系统遍历实现
    }
}
```

注意：实际文件删除操作需要 MyBatis 查询配合。先清理文件，再标记数据库记录。

- [ ] **Step 4: Commit**

```bash
git add web-flask/app/core/stream_loader.py \
      web-back/src/main/java/org/example/webback/service/EvidenceCleanupService.java
git commit -m "feat(P1): evidence grading (0.65 snapshot / 0.85 video) + auto cleanup scheduled task"
```
