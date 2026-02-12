# web-flask/app/core/stream_loader.py

import cv2
import time
import threading
import os
import requests
import logging
import math
import socket
from collections import defaultdict
from app.core.detector import get_detector
from app.core.recorder import EvidenceRecorder

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["OPENCV_FFMPEG_LOG_LEVEL"] = "quiet"

# 🚀 辅助类：用于追踪烟头出现的持续性
class SmokeEvent:
    def __init__(self):
        self.last_seen_time = time.time()
        self.frame_count = 0     
        self.is_confirmed = False 

class StreamLoader:
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
        
        # 🚀 报警判定参数 (从你的旧代码迁移)
        self.smoke_events = defaultdict(SmokeEvent)
        self.alarm_threshold_frames = 15 # 连续15帧才算报警
        self.lost_timeout = 2.0         # 烟头消失2秒后清除事件
        self.active_cooldowns = {}      # 动态冷却字典
        self.alarm_cooldown = 300.0     # 5分钟冷却
        self.alarm_radius = 200         # 200像素范围判定为同一地点

        self.reconnect_requested = False
        self.start_lock = threading.Lock() 

    def set_ai_status(self, enabled: bool):
        self.ai_enabled = enabled
        logger.info(f"🤖 Cam {self.camera_id} AI Status -> {enabled}")

    def _update_db_status(self, status):
        def notify_java():
            try:
                java_sync_url = "http://localhost:8080/api/monitor/devices/sync-status"
                requests.post(java_sync_url, json={"id": self.camera_id, "status": status}, timeout=1)
            except: pass
        threading.Thread(target=notify_java, daemon=True).start()

    def _check_network_quick(self):
        try:
            parts = self.rtsp_url.split('@')[-1].split('/')[0].split(':')
            ip = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 554
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                return s.connect_ex((ip, port)) == 0
        except: return False

    def _connect(self):
        try:
            if self.cap: self.cap.release()
            if not self._check_network_quick():
                self._update_db_status(0)
                return False
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;2000000|probesize;32768"
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) 
                logger.info(f"✅ Cam {self.camera_id} 连接成功")
                return True
            self._update_db_status(0)
            return False
        except Exception: return False

    def _reader_thread(self):
        while self.running:
            if not self.cap or not self.cap.isOpened() or self.reconnect_requested:
                if not self._connect():
                    time.sleep(5); continue
                self.reconnect_requested = False

            try:
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    if time.time() - self.last_read_time > 10.0: self._update_db_status(1)
                    with self.lock:
                        self.latest_frame = frame
                        self.last_read_time = time.time()
                else:
                    self.reconnect_requested = True
                    time.sleep(1)
            except: time.sleep(1)

    def _processor_thread(self):
        while self.running:
            frame_to_process = None
            with self.lock:
                if self.latest_frame is not None:
                    frame_to_process = self.latest_frame.copy()
            
            if frame_to_process is None:
                time.sleep(0.1); continue

            # 1. 录像缓冲
            self.recorder.add_frame(frame_to_process)
            self.recorder.process_recording(frame_to_process)

            # 2. AI 核心逻辑处理
            detections = []
            if self.ai_enabled:
                try:
                    # 获取原始检测结果 (人 + 烟)
                    detections = self.detector.detect(frame_to_process)
                    # 🚀 运行报警判定逻辑
                    detections = self._handle_alarm_logic(frame_to_process, detections)
                except Exception as e:
                    logger.error(f"AI Logic Error Cam {self.camera_id}: {e}")

            # 3. 绘图与推流输出
            final_view = self._draw_ui(frame_to_process, detections)
            with self.lock:
                self.output_frame = cv2.resize(final_view, (1280, 720))
            time.sleep(0.03)

    # 🚀 从旧代码迁移：报警核心逻辑判定
    def _handle_alarm_logic(self, frame, detections):
        current_time = time.time()
        persons = [d for d in detections if d['label'] == 'person']
        cigarettes = [d for d in detections if d['label'] == 'cigarette']
        
        # A. 更新冷却状态
        self._update_cooldowns(current_time, persons)

        # B. 判定每个检测到的烟头
        for cig in cigarettes:
            cid = cig.get('id', 0)
            cbox = cig['box']
            
            event = self.smoke_events[cid]
            event.last_seen_time = current_time
            event.frame_count += 1
            
            # 只有达到帧数阈值才准备报警
            if event.frame_count >= self.alarm_threshold_frames:
                cig['is_alarm'] = True # 给 UI 绘图用
                
                if not event.is_confirmed:
                    # 检查冷却
                    c_cx, c_cy = (cbox[0]+cbox[2])/2, (cbox[1]+cbox[3])/2
                    if not self._is_in_cooldown(c_cx, c_cy):
                        event.is_confirmed = True
                        owner_id = self._match_person_id(cbox, persons)
                        logger.warning(f"🔥 [ALARM] Cam {self.camera_id} 检测到吸烟行为！")
                        # 触发截图、录像、上报
                        self._trigger_alarm_save(frame, owner_id, cig['conf'])
                        # 记录冷却
                        self._add_cooldown(owner_id, c_cx, c_cy, current_time)
            else:
                cig['is_alarm'] = False

        # C. 清理过期事件
        expired = [tid for tid, evt in self.smoke_events.items() if current_time - evt.last_seen_time > self.lost_timeout]
        for tid in expired: del self.smoke_events[tid]
        
        return detections

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

    # 🚀 触发上报
    def _trigger_alarm_save(self, frame, owner_id, conf):
        """
        🚀 报警核心：仅保存物理文件，并通知 Java 存储数据库
        """
        ts = int(time.time())
        # 文件名前缀，包含摄像头ID和时间戳
        prefix = f"alarm_cam{self.camera_id}_p{owner_id if owner_id else 'unk'}_{ts}"
        
        # 1. 保存截图到 snapshots 目录
        img_name = f"{prefix}.jpg"
        self.recorder.save_snapshot(frame, img_name)
        
        # 2. 开启录像（5秒后自动停止并转码）
        video_name = f"{prefix}.mp4"
        h, w = frame.shape[:2]
        self.recorder.start_recording(video_name, post_record_sec=5, width=w, height=h)
        
        # 3. 异步通知 Java 后端
        def notify_java_to_save_db():
            # 延迟 1 秒发送，确保录像文件已经初始化创建
            time.sleep(1)
            
            # 🚀 构造 Java 能够通过 Web 访问到的相对路径
            # 假设你的 Flask 静态目录映射在 /static/
            snapshot_url = f"/static/evidence/snapshots/{img_name}"
            video_url = f"/static/evidence/{video_name}"

            try:
                java_alarm_url = "http://localhost:8080/api/alerts/report"
                payload = {
                    "deviceId": self.camera_id,      # 摄像头ID
                    "type": "SMOKING",              # 报警类型
                    "confidence": round(float(conf), 2), # 置信度
                    "snapshotUrl": snapshot_url,     # 截图访问路径
                    "videoUrl": video_url,           # 视频访问路径
                    "personId": owner_id,            # 匹配到的人员ID（如果有）
                    "description": f"摄像头{self.camera_id}检测到吸烟行为"
                }
                
                # 发送 POST 请求给 Java
                response = requests.post(java_alarm_url, json=payload, timeout=3)
                
                if response.status_code == 200:
                    logger.info(f"🔥 [Alarm] Java 响应成功: 报警记录已由 Java 存库")
                else:
                    logger.error(f"❌ [Alarm] Java 响应异常: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ [Alarm] 无法连接到 Java 报警接口: {e}")

        # 放入后台线程，不阻塞识别主循环
        threading.Thread(target=notify_java_to_save_db, daemon=True).start()

    def _draw_ui(self, frame, detections):
        for det in detections:
            x1, y1, x2, y2 = det['box']
            if det['label'] == 'person':
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(frame, f"ID:{det['id']}", (x1, y1-10), 1, 1.2, (255,0,0), 2)
            elif det['label'] == 'cigarette':
                color = (0, 0, 255) if det.get('is_alarm') else (0, 255, 255)
                text = "SMOKING!" if det.get('is_alarm') else "cig"
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, text, (x1, y1-10), 1, 1.2, color, 2)
                if det.get('is_alarm'):
                    h, w = frame.shape[:2]
                    cv2.rectangle(frame, (0,0), (w,h), (0,0,255), 4)
        return frame

    def _watchdog_thread(self):
        while self.running:
            if time.time() - self.last_read_time > 15.0:
                self._update_db_status(0)
                self.reconnect_requested = True
            time.sleep(5)

    def start(self):
        with self.start_lock:
            if self.running: return True
            self.running = True
            threading.Thread(target=self._reader_thread, daemon=True).start()
            threading.Thread(target=self._processor_thread, daemon=True).start()
            threading.Thread(target=self._watchdog_thread, daemon=True).start()
            return True

    def stop(self):
        self.running = False
        self._update_db_status(0)
        with self.lock:
            if self.cap: self.cap.release(); self.cap = None

    def get_latest_frame(self):
        with self.lock:
            f = self.output_frame if self.output_frame is not None else self.latest_frame
            return cv2.resize(f, (640, 360)) if f is not None else None

class StreamManager:
    def __init__(self):
        self.stream_loaders = {}
        self.lock = threading.Lock()
        self.global_ai_enabled = True

    # 🚀 补回这个缺失的方法，供 app/__init__.py 调用
    def init_app(self, app):
        self.app = app
        logger.info("📡 [Manager] 已成功关联 Flask 应用上下文")

    def add_camera(self, cid, url):
        with self.lock:
            if cid in self.stream_loaders: self.stream_loaders[cid].stop()
            l = StreamLoader(cid, url)
            l.set_ai_status(self.global_ai_enabled)
            if l.start():
                self.stream_loaders[cid] = l
                return True
            return False

    def update_active_streams(self, active_devices_dict):
        with self.lock:
            active_ids = set(active_devices_dict.keys())
            current_ids = set(self.stream_loaders.keys())
            for cid in (current_ids - active_ids):
                self.stream_loaders[cid].stop()
                del self.stream_loaders[cid]
            for cid in (active_ids - current_ids):
                self.add_camera(cid, active_devices_dict[cid])

    def get_latest_frame(self, cid):
        l = self.stream_loaders.get(cid)
        return l.get_latest_frame() if l else None

    def set_global_ai(self, enabled):
        self.global_ai_enabled = enabled
        for loader in self.stream_loaders.values(): loader.set_ai_status(enabled)

import builtins
stream_manager = StreamManager()
builtins.GLOBAL_STREAM_MANAGER = stream_manager
logger.info("🛠️ [Global] StreamManager 已注册到全局内置空间")