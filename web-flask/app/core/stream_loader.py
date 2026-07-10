import cv2
import time
import threading
import os
import requests
import subprocess
import logging
import math
from collections import defaultdict
from app.core.detector import get_detector
from app.core.recorder import EvidenceRecorder
from app.core.burst_token import BurstTokenManager
from app.core.java_client import internal_headers
from config import Config
# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["OPENCV_FFMPEG_LOG_LEVEL"] = "quiet"

class SmokeEvent:
    def __init__(self):
        self.last_seen_time = time.time()
        self.frame_count = 0     
        self.is_confirmed = False 

class StreamLoader:
    # 🚀 报警确认即存快照 + 录视频（利用 processor 线程已有帧）

    def __init__(self, camera_id: int, rtsp_url: str, app=None):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.app = app
        self.lock = threading.Lock()
        
        self.detector = get_detector()
        self.recorder = EvidenceRecorder(save_dir="app/static/evidence", fps=25, pre_record_sec=2)
        
        self.running = False
        self.cap = None
        self.latest_frame = None   
        self.output_frame = None   
        self.ai_enabled = True 
        self.last_read_time = time.time()
        
        self.smoke_events = defaultdict(SmokeEvent)
        # 🚀 检测频率从 25fps 降到 2fps，累计帧数同步从 15 降到 3
        self.alarm_threshold_frames = 3
        self.lost_timeout = 1.0
        self.active_cooldowns = {}      
        self.alarm_cooldown = 300.0     
        self.alarm_radius = 200         

        self.reconnect_requested = False
        self.start_lock = threading.Lock()

        # 🚀 爆发令牌管理
        self.burst_token_holder = False
        self.burst_start_time = 0.0

    def set_ai_status(self, enabled: bool):
        with self.lock:
            self.ai_enabled = enabled
        logger.info(f"🤖 Cam {self.camera_id} AI 状态切换 -> {enabled}")

    def _update_db_status(self, status):
        """同步状态至 Java 后端 (增加严谨的超时和异常捕获)"""
        try:
            requests.post(
                Config.JAVA_STATUS_SYNC_URL,
                json={"id": self.camera_id, "status": status},
                headers=internal_headers(),
                timeout=1.0  # 给 1 秒足够了
            )
        except Exception as e: 
            # 仅仅记录，不要抛出，防止崩掉调用它的线程
            logger.debug(f"通知 Java 失败(正常现象): {e}")

    def _connect(self):
        """直连摄像头 RTSP（MediaMTX 集成推迟到 Phase 3）。"""
        try:
            if self.cap:
                self.cap.release()

            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;3000000|threads;1"

            logger.info(f"🛰️ 直连拉流: {self.rtsp_url.split('@')[-1]}")
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    with self.lock:
                        self.latest_frame = frame
                        self.last_read_time = time.time()
                    return True
            return False
        except Exception as e:
            logger.error(f"💥 连接异常: {e}")
            return False

    def _reader_thread(self):
        """🚀 改造：grab() 高频清空缓冲区 + 每 200ms retrieve() 一次，防止 OpenCV 老化延迟"""
        last_retrieve_time = 0
        RETRIEVE_INTERVAL = 0.2  # 200ms → 5 FPS

        while self.running:
            if not self.cap or not self.cap.isOpened():
                # 🚀 连接失败即停止，不自动重试
                if not self._connect():
                    with self.lock:
                        self.output_frame = None
                    self.running = False
                    break

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
                        logger.warning(f"⚠️ Cam {self.camera_id} 信号丢失，停止拉流")
                        with self.lock:
                            self.output_frame = None
                        self.running = False
                        break
                elif grabbed:
                    # 🚀 grab 成功但未到 retrieve 时机：短暂休眠防止 CPU 空转
                    time.sleep(0.005)
                else:
                    time.sleep(0.01)
            except Exception as e:
                logger.debug(f"读取线程退出捕获: {e}")
                break

    def _processor_thread(self):
        """🚀 弹性跳帧处理器：平时 2 FPS，爆发模式全帧率"""
        last_process_time = 0.0
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
            if not burst_token_holder and (now - last_process_time) < 0.5:
                # 跳过推理但仍将帧写入 buffer（保证录像连贯）
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

    def _handle_two_stage_alarm(self, frame, detections, has_burst_token, now):
        """
        两阶段置信度 + 跨帧累计确认。

        阶段 1（触发预录）：
          - 瞬时置信度 >= trigger_threshold → 获取爆发令牌，开启高帧率录制
          - 或累计置信度 >= trigger_threshold → 同上

        阶段 2（确认报警）：
          - 瞬时置信度 >= confirm_threshold → 立即确认
          - 或同一个人累计 alarm_threshold_frames 次检出 → 确认报警

        返回 (更新后的 detections, 是否有爆发令牌)
        """
        persons = [d for d in detections if d['label'] == 'person']
        cigarettes = [d for d in detections if d['label'] == 'cigarette']

        self._update_cooldowns(now, persons)

        # ── 跨帧累计 ──
        tracking_ids = set()
        max_conf = 0.0
        best_cig = None
        for cig in cigarettes:
            if cig['conf'] > max_conf:
                max_conf = cig['conf']
                best_cig = cig

            # 检出 >= trigger_threshold 的烟头，累计 frame_count
            if cig['conf'] >= self.detector.trigger_threshold:
                cid = cig.get('id', 0)
                tracking_ids.add(cid)
                event = self.smoke_events[cid]
                event.last_seen_time = now
                event.frame_count += 1

                # 路径 A：单帧高置信度 → 立即确认
                if cig['conf'] >= self.detector.confirm_threshold and not event.is_confirmed:
                    cig['is_alarm'] = True
                    event.is_confirmed = True
                    best_cig = cig
                    max_conf = cig['conf']

                # 路径 B：累计检出 N 次 → 确认（跟踪烟头）
                elif event.frame_count >= self.alarm_threshold_frames and not event.is_confirmed:
                    cig['is_alarm'] = True
                    event.is_confirmed = True
                    best_cig = cig
                    max_conf = cig['conf']

        # ── 清理过期 tracking ──
        expired_ids = [tid for tid, evt in self.smoke_events.items()
                       if tid not in tracking_ids
                       and now - evt.last_seen_time > self.lost_timeout]
        for tid in expired_ids:
            del self.smoke_events[tid]

        # ── 爆发令牌状态机 ──
        if has_burst_token:
            if now - self.burst_start_time > 8.0:
                logger.info(f"⏰ Cam {self.camera_id} 爆发令牌超时回收")
                BurstTokenManager.release(self.camera_id)
                has_burst_token = False

        # ── 确认报警（瞬时高置信度 或 累计确认） ──
        if best_cig and best_cig.get('is_alarm'):
            cbox = best_cig['box']
            c_cx, c_cy = (cbox[0] + cbox[2]) / 2, (cbox[1] + cbox[3]) / 2

            if not self._is_in_cooldown(c_cx, c_cy):
                owner_id = self._match_person_id(cbox, persons)
                evidence_frame = self._draw_ui(frame.copy(), detections)
                self._trigger_alarm_save(evidence_frame, owner_id, best_cig['conf'])
                self._add_cooldown(owner_id, c_cx, c_cy, now)
                logger.info(f"🚨 Cam {self.camera_id} 确认报警 conf={max_conf:.2f}")

            if has_burst_token:
                BurstTokenManager.release(self.camera_id)
                has_burst_token = False
            return detections, False

        # ── 阶段 1：触发预录（瞬时置信度触发） ──
        if best_cig and max_conf >= self.detector.trigger_threshold:
            if not has_burst_token:
                if BurstTokenManager.acquire(self.camera_id, now):
                    has_burst_token = True
                    self.burst_start_time = now
                    logger.info(f"🔥 Cam {self.camera_id} 获取爆发令牌 conf={max_conf:.2f}")

        return detections, has_burst_token

    def _update_cooldowns(self, current_time, persons):
        current_pids = {p['id']: p['box'] for p in persons}
        keys_to_remove = []
        for key, record in self.active_cooldowns.items():
            if current_time - record['time'] > self.alarm_cooldown:
                keys_to_remove.append(key); continue
            if isinstance(key, int) and key in current_pids:
                box = current_pids[key]
                record['pos'] = ((box[0]+box[2])/2, (box[1]+box[3])/2)
        for k in keys_to_remove: del self.active_cooldowns[k]

    def _is_in_cooldown(self, cx, cy):
        for record in self.active_cooldowns.values():
            rx, ry = record['pos']
            if math.sqrt((cx-rx)**2 + (cy-ry)**2) < self.alarm_radius: return True
        return False

    def _match_person_id(self, c_box, persons):
        c_cx, c_cy = (c_box[0]+c_box[2])/2, (c_box[1]+c_box[3])/2
        min_dist, best_id = float('inf'), None
        for p in persons:
            p_box = p['box']
            p_cx, p_cy = (p_box[0]+p_box[2])/2, (p_box[1]+p_box[3])/2
            dist = math.sqrt((c_cx-p_cx)**2 + (c_cy-p_cy)**2)
            if dist < (p_box[2]-p_box[0])*2.0 and dist < min_dist:
                min_dist, best_id = dist, p['id']
        return best_id

    def _add_cooldown(self, owner_id, cx, cy, current_time):
        key = owner_id if owner_id else f"static_{current_time}"
        self.active_cooldowns[key] = {'pos': (cx, cy), 'time': current_time}

    def _trigger_alarm_save(self, frame, owner_id, conf):
        ts = int(time.time())
        img_name = f"alarm_cam{self.camera_id}__p{owner_id or 'unk'}_{ts}.jpg"

        # 🚀 报警已确认，无条件保存快照（证据基石）
        ram_path = self.recorder.save_snapshot(frame, img_name)
        # 从内存盘迁移到 SSD（保证 Web 可访问）
        if ram_path and self.recorder.ram_disk_dir != self.recorder.save_dir:
            self.recorder.move_to_persistent(ram_path)
        snapshot_url = f"static/evidence/snapshots/{img_name}"

        # 🚀 报警确认即录视频（使用 processor 已有帧，不走第二次 RTSP 连接）
        video_name = img_name.replace('.jpg', '.mp4')
        self.recorder.start_recording(video_name, post_record_sec=5, width=640, height=480)
        logger.info(f"🎬 录像启动: {video_name}")
        video_url = f"static/evidence/{video_name}"

        # 🚀 通知 Java
        def notify_java():
            try:
                requests.post(Config.JAVA_API_URL, json={
                    "deviceId": self.camera_id, "type": "SMOKING",
                    "confidence": round(float(conf), 2),
                    "snapshotUrl": snapshot_url,
                    "videoUrl": video_url,
                    "personId": owner_id,
                    "description": f"人员{owner_id or '未知'}吸烟"
                }, headers=internal_headers(), timeout=3)
            except Exception as e:
                logger.error(f"Java 中台上报失败 CID={self.camera_id}: {e}")

        threading.Thread(target=notify_java, daemon=True).start()

    def _draw_ui(self, frame, detections):
        for det in detections:
            x1, y1, x2, y2 = det['box']
            label = det['label']
            if label == 'person':
                color = (255, 0, 0)
                text = f"Cam{self.camera_id}-P{det.get('id', 'unk')}"
            elif label == 'cigarette':
                if det.get('is_alarm'):
                    color = (0, 0, 255)
                    text = "SMOKING!"
                    h, w = frame.shape[:2]
                    cv2.rectangle(frame, (0,0), (w,h), (0,0,255), 5)
                else:
                    color = (0, 255, 255)
                    text = "cig"
            else:
                color = (0, 255, 0)
                text = label

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        return frame

    def _watchdog_thread(self):
        while self.running:
            with self.lock:
                if time.time() - self.last_read_time > 3.0:
                    logger.warning(f"🚨 Cam {self.camera_id} 超时卡死，停止")
                    self.running = False
                    break
            time.sleep(1)

    def start(self):
        with self.start_lock:
            if self.running: return True
            self.running = True
            threading.Thread(target=self._reader_thread, daemon=True).start()
            threading.Thread(target=self._processor_thread, daemon=True).start()
            threading.Thread(target=self._watchdog_thread, daemon=True).start()
            return True

    def stop(self):
        if not self.running: return
        
        # 1. 先标记停止，让 _reader_thread 的 while 循环退出
        self.running = False

        # 2. 🚀 给 FFmpeg 解码器一点缓冲时间（0.2秒），让它先停下来
        time.sleep(0.2)
        
        try:
            if self.cap:
                # 在 release 之前尝试清除缓冲区
                self.cap.release()
                self.cap = None
        except Exception as e:
            logger.error(f"⚠️ OpenCV 资源释放异常: {e}")

        with self.lock:
            self.latest_frame = None
            self.output_frame = None
        
        logger.info(f"💀 Cam {self.camera_id} 资源清理完成")

    def get_latest_frame(self):
        with self.lock:
            if time.time() - self.last_read_time > 3.0:
                return None
            f = self.output_frame if self.output_frame is not None else self.latest_frame
            return cv2.resize(f, (1280, 720)) if f is not None else None

    def get_thumbnail(self, target_width=320, target_height=240, quality=60):
        """返回当前最新帧的缩略图 bytes (JPEG)。信号丢失 >3s 返回 None。"""
        with self.lock:
            frame = self.output_frame if self.output_frame is not None else self.latest_frame
            if frame is None:
                return None
            # 🚀 信号丢失超过 3 秒则返回离线占位
            if time.time() - self.last_read_time > 3.0:
                return None
            thumb = cv2.resize(frame, (target_width, target_height))
            ret, buf = cv2.imencode('.jpg', thumb, [cv2.IMWRITE_JPEG_QUALITY, quality])
            if ret:
                return buf.tobytes()
            return None

class StreamManager:
    def __init__(self):
        self.stream_loaders = {}
        self.lock = threading.Lock()
        self.global_ai_enabled = True
        self.app = None
        self._heartbeat_interval = 1.0

    def _start_heartbeat_aggregator(self):
        """按 heartbeat interval 批量上报当前已加载设备状态。"""
        import threading
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
                            Config.JAVA_BATCH_SYNC_URL,
                            json=batch,
                            headers=internal_headers(),
                            timeout=2.0
                        )
                except Exception:
                    pass

        t = threading.Thread(target=aggregate_and_report, daemon=True)
        t.start()

    def _start_reconnect_poller(self):
        """每 30 秒自动重连离线设备（用户无需手动唤醒）。"""

        def poll():
            while True:
                time.sleep(30)
                try:
                    with self.lock:
                        offline = [cid for cid, ld in self.stream_loaders.items()
                                   if not ld.running]
                    for cid in offline:
                        with self.lock:
                            if cid not in self.stream_loaders:
                                continue
                            loader = self.stream_loaders[cid]
                            if loader.running:
                                continue
                            url = loader.rtsp_url
                            old = self.stream_loaders.pop(cid)
                            old.stop()
                        logger.info(f"🔄 自动重连 CID={cid}")
                        self.add_camera(cid, url)
                except Exception:
                    pass

        t = threading.Thread(target=poll, daemon=True)
        t.start()

    def init_app(self, app):
        self.app = app
        self._start_heartbeat_aggregator()
        self._start_reconnect_poller()
        logger.info("📡 StreamManager 关联成功")

    def add_camera(self, cid, url):
        with self.lock:
            if cid in self.stream_loaders:
                old = self.stream_loaders[cid]
                if old.running and old.latest_frame is not None and old.rtsp_url == url:
                    old.set_ai_status(self.global_ai_enabled)
                    return True
                old.stop()
                del self.stream_loaders[cid]
                time.sleep(0.1)

            l = StreamLoader(cid, url, self.app)
            l.set_ai_status(self.global_ai_enabled)
            self.stream_loaders[cid] = l  # 🚀 先存入，失败后靠 poller 重连
            if l._connect():
                if l.start(): return True
            return False

    def set_global_ai(self, enabled: bool):
        with self.lock:
            self.global_ai_enabled = enabled
            logger.info(f"🌍 全局 AI 开关设定为: {enabled}")
            for loader in self.stream_loaders.values():
                loader.set_ai_status(enabled)
        return True

    def update_active_streams(self, active_devices_dict):
        with self.lock:
            current_ids = set(self.stream_loaders.keys())
            active_ids = set(active_devices_dict.keys())
            for cid in (current_ids - active_ids):
                self.stream_loaders[cid].stop()
                del self.stream_loaders[cid]

import builtins
stream_manager = StreamManager()
builtins.GLOBAL_STREAM_MANAGER = stream_manager
