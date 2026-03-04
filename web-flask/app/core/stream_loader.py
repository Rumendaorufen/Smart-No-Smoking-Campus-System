import cv2
import time
import threading
import os
import requests
import logging
import math
from collections import defaultdict
from app.core.detector import get_detector
from app.core.recorder import EvidenceRecorder

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
        self.alarm_threshold_frames = 15 
        self.lost_timeout = 2.0         
        self.active_cooldowns = {}      
        self.alarm_cooldown = 300.0     
        self.alarm_radius = 200         

        self.reconnect_requested = False
        self.start_lock = threading.Lock() 

    def set_ai_status(self, enabled: bool):
        with self.lock:
            self.ai_enabled = enabled
        logger.info(f"🤖 Cam {self.camera_id} AI 状态切换 -> {enabled}")

    def _update_db_status(self, status):
        """同步状态至 Java 后端 (增加严谨的超时和异常捕获)"""
        try:
            java_sync_url = "http://localhost:8080/api/monitor/devices/sync-status"
            # 🚀 必须设置 timeout，且捕获所有异常
            requests.post(
                java_sync_url, 
                json={"id": self.camera_id, "status": status}, 
                timeout=1.0  # 给 1 秒足够了
            )
        except Exception as e: 
            # 仅仅记录，不要抛出，防止崩掉调用它的线程
            logger.debug(f"通知 Java 失败(正常现象): {e}")

    def _connect(self):
        """🚀 增强稳定性连接配置"""
        try:
            if self.cap: 
                self.cap.release()
            
            # 🚀 关键修复：禁用 FFmpeg 内部线程，由 Python 线程全权负责
            # 添加 threads=1 解决 pthread_frame.c 断言失败问题
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;3000000|threads;1"
            
            logger.info(f"🛰️ 正在点火: {self.rtsp_url.split('@')[-1]}")
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            
            # 这里的设置也很重要
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
            logger.error(f"💥 连接异常: {e}")
            return False

    def _reader_thread(self):
        while self.running:
            # 🚀 增加判断：如果已经被外部 stop 了，直接退出
            if not self.running: break
            
            if not self.cap or not self.cap.isOpened() or self.reconnect_requested:
                if self._connect(): 
                    self.reconnect_requested = False
                else:
                    self._update_db_status(0)
                    time.sleep(2); continue

            try:
                # 再次确认
                if self.cap and self.cap.isOpened():
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        with self.lock:
                            self.latest_frame = frame
                            self.last_read_time = time.time()
                    else:
                        if self.running: # 只有在预期运行中丢失信号才报警
                            logger.warning(f"⚠️ Cam {self.camera_id} 信号丢失")
                            self._update_db_status(0)
                            self.reconnect_requested = True
                        time.sleep(1)
            except Exception as e:
                logger.debug(f"读取线程退出捕获: {e}")
                break

    def _processor_thread(self):
        """AI 处理线程 (已修正顺序以支持带框录像)"""
        while self.running:
            frame_to_process = None
            ai_on = True
            with self.lock:
                if self.latest_frame is not None:
                    frame_to_process = self.latest_frame.copy()
                ai_on = self.ai_enabled
            
            if frame_to_process is None:
                time.sleep(0.1); continue

            detections = []
            
            # 1. 跑推理逻辑
            if ai_on:
                try:
                    detections = self.detector.detect(frame_to_process)
                    detections = self._handle_alarm_logic(frame_to_process, detections)
                except Exception as e:
                    logger.error(f"AI Error: {e}")

            # 2. 渲染画面：把框画在图上
            frame_to_process = self._draw_ui(frame_to_process, detections)

            # 3. 🚀 将带框的帧存入录像机缓冲区
            self.recorder.add_frame(frame_to_process)

            # 4. 更新输出预览
            with self.lock:
                self.output_frame = frame_to_process
            
            self.recorder.process_recording()
            time.sleep(0.01)

    def _handle_alarm_logic(self, frame, detections):
        current_time = time.time()
        persons = [d for d in detections if d['label'] == 'person']
        cigarettes = [d for d in detections if d['label'] == 'cigarette']
        self._update_cooldowns(current_time, persons)
        for cig in cigarettes:
            cid, cbox = cig.get('id', 0), cig['box']
            event = self.smoke_events[cid]
            event.last_seen_time = current_time
            event.frame_count += 1
            if event.frame_count >= self.alarm_threshold_frames:
                cig['is_alarm'] = True
                if not event.is_confirmed:
                    c_cx, c_cy = (cbox[0]+cbox[2])/2, (cbox[1]+cbox[3])/2
                    if not self._is_in_cooldown(c_cx, c_cy):
                        event.is_confirmed = True
                        owner_id = self._match_person_id(cbox, persons)
                        
                        # 🚀 录像带框的关键点：在保存快照前，先画个带框的图
                        evidence_frame = self._draw_ui(frame.copy(), detections)
                        self._trigger_alarm_save(evidence_frame, owner_id, cig['conf'])
                        
                        self._add_cooldown(owner_id, c_cx, c_cy, current_time)
            else: cig['is_alarm'] = False
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

    def _trigger_alarm_save(self, frame, owner_id, conf):
        ts = int(time.time())
        img_name = f"alarm_cam{self.camera_id}__p{owner_id or 'unk'}_{ts}.jpg"
        self.recorder.save_snapshot(frame, img_name)
        video_name = img_name.replace('.jpg', '.mp4')
        h, w = frame.shape[:2]
        self.recorder.start_recording(video_name, post_record_sec=5, width=w, height=h)
        def notify_java():
            try:
                requests.post("http://localhost:8080/api/alerts/report", json={
                    "deviceId": self.camera_id, "type": "SMOKING", "confidence": round(float(conf), 2),
                    "snapshotUrl": f"static/evidence/snapshots/{img_name}", "videoUrl": f"static/evidence/{video_name}",
                    "personId": owner_id, "description": f"人员{owner_id or '未知'}吸烟"
                }, timeout=3)
            except: pass
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
            if time.time() - self.last_read_time > 5.0:
                if not self.reconnect_requested:
                    logger.warning(f"🚨 Cam {self.camera_id} 超时卡死，标记离线")
                    self._update_db_status(0)
                    self.reconnect_requested = True
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
        
        # 2. 立即异步通知 Java（不阻塞主进程）
        threading.Thread(target=self._update_db_status, args=(0,), daemon=True).start()
        
        # 3. 🚀 给 FFmpeg 解码器一点缓冲时间（0.2秒），让它先停下来
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
            f = self.output_frame if self.output_frame is not None else self.latest_frame
            return cv2.resize(f, (1280, 720)) if f is not None else None

class StreamManager:
    def __init__(self):
        self.stream_loaders = {}
        self.lock = threading.Lock()
        self.global_ai_enabled = True
        self.app = None 

    def init_app(self, app):
        self.app = app
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
            if l._connect():
                self.stream_loaders[cid] = l
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