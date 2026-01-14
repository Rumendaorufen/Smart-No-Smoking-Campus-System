import cv2
import time
import threading
import os
import logging
import math
from collections import defaultdict
from app.core.detector import SmokingDetector
from app.core.recorder import EvidenceRecorder
from app.models import db, Alarms, Devices

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 🔇 屏蔽 OpenCV/FFmpeg 底层疯狂报错的噪音
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["OPENCV_FFMPEG_LOG_LEVEL"] = "quiet"

# ==========================================
# 辅助类
# ==========================================
class SmokeEvent:
    def __init__(self):
        self.start_time = time.time()
        self.last_seen_time = time.time()
        self.frame_count = 0     
        self.is_confirmed = False 

# ==========================================
# StreamLoader: 单个摄像头的管理单元
# ==========================================
class StreamLoader:
    def __init__(self, camera_id: int, rtsp_url: str, app=None):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.app = app 
        self.lock = threading.Lock()
        
        # AI & 录像组件
        self.detector = SmokingDetector()
        self.recorder = EvidenceRecorder(save_dir="app/static/evidence", fps=25, pre_record_sec=2)
        
        # 运行状态
        self.running = False
        self.cap = None
        self.latest_frame = None   
        self.output_frame = None   
        
        # AI 逻辑状态
        self.smoke_events = defaultdict(SmokeEvent)
        self.alarm_threshold_frames = 15
        self.lost_timeout = 2.0
        self.last_read_time = time.time()
        self.smoker_records = {} 
        self.alarm_cooldown = 300.0 

        # 信号量
        self.reconnect_requested = False
        
        # 🛑 新增：连续错误计数器
        self.consecutive_errors = 0

    def start(self) -> bool:
        self.running = True
        threading.Thread(target=self._reader_thread, daemon=True).start()
        threading.Thread(target=self._processor_thread, daemon=True).start()
        threading.Thread(target=self._watchdog_thread, daemon=True).start()
        return True

    def stop(self):
        self.running = False
        self._update_db_status(0)
        if self.cap: 
            self.cap.release()
            logger.info(f"🛑 Cam {self.camera_id} Stopped.")

    def _update_db_status(self, status):
        if not self.app: return
        try:
            with self.app.app_context():
                device = Devices.query.get(self.camera_id)
                if device and device.status != status:
                    device.status = status
                    db.session.commit()
                    # logger.info(f"📡 Cam {self.camera_id} Status -> {status}")
        except Exception as e:
            logger.error(f"❌ DB Update Error: {e}")

    def _connect(self):
        try:
            if self.cap: self.cap.release()
            
            # 🛑 核心修复 1：缩短超时时间
            # stimeout;5000000 -> 5秒超时 (之前是20秒，太久了)
            # max_delay;500000 -> 限制最大延迟 0.5秒
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000|max_delay;500000|buffer_size;10240"
            
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_N_THREADS, 1)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # 恢复为1，为了低延迟，因为我们有错误计数器兜底
                
                logger.info(f"✅ Cam {self.camera_id} Connected.")
                self._update_db_status(1)
                self.consecutive_errors = 0 # 重置错误计数
                return True
            else:
                self._update_db_status(0)
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self._update_db_status(0)
        return False

    def _reader_thread(self):
        logger.info(f"Cam {self.camera_id} Reader Started")
        if not self._connect():
            logger.warning(f"Cam {self.camera_id} init failed.")

        while self.running:
            try:
                # 响应看门狗
                if self.reconnect_requested:
                    self._update_db_status(0)
                    self._connect()
                    self.reconnect_requested = False
                    self.last_read_time = time.time()

                if not self.cap or not self.cap.isOpened():
                    time.sleep(2)
                    self._connect()
                    continue
                
                # 读取帧
                grabbed = self.cap.grab()
                
                if grabbed:
                    ret, frame = self.cap.retrieve()
                    if ret and frame is not None and frame.size > 0:
                        with self.lock:
                            self.latest_frame = frame
                            self.last_read_time = time.time() # 成功喂狗
                            self.consecutive_errors = 0 # ✅ 成功读取，清零错误
                    else:
                        # 虽然 grab 成功，但解码失败 (那些 H264 error 就会走这里)
                        self.consecutive_errors += 1
                else:
                    # grab 直接失败
                    self.consecutive_errors += 1
                
                # 🛑 核心修复 2：主动熔断机制
                # 如果连续 30 帧 (约1秒) 出现解码错误，不要等 Watchdog，直接自杀重启
                if self.consecutive_errors > 30:
                    logger.warning(f"⚡ Cam {self.camera_id} stream corruption detected! Force reconnecting...")
                    self.reconnect_requested = True
                    self.consecutive_errors = 0
                    time.sleep(0.5)

            except Exception as e:
                logger.error(f"Reader loop error: {e}")
                time.sleep(1)

    def _watchdog_thread(self):
        """看门狗：监控 Reader 是否卡死 (最后的防线)"""
        while self.running:
            # 如果超过 6 秒 (之前是15秒) 没有读取到新帧
            # 缩短这里的时间，以便在完全没数据时更快反应
            if time.time() - self.last_read_time > 6.0:
                if not self.reconnect_requested:
                    logger.warning(f"🚨 Cam {self.camera_id} Timeout/Frozen! Requesting restart...")
                    self.reconnect_requested = True
                    self._update_db_status(0)
            
            time.sleep(2)

    # ------------------------------------------------------------------
    # _processor_thread 及其他 AI 逻辑保持不变 (直接粘贴你之前的逻辑即可)
    # ------------------------------------------------------------------
    def _processor_thread(self):
        while self.running:
            frame_to_process = None
            with self.lock:
                if self.latest_frame is not None:
                    frame_to_process = self.latest_frame.copy()
            
            if frame_to_process is None:
                time.sleep(0.1)
                continue

            self.recorder.add_frame(frame_to_process)
            self.recorder.process_recording(frame_to_process)

            detections = self._run_ai_logic(frame_to_process)
            final_view = self._draw_ui(frame_to_process, detections)
            
            self.output_frame = cv2.resize(final_view, (1280, 720))
            time.sleep(0.03)

    def _run_ai_logic(self, frame):
        h, w = frame.shape[:2]
        current_time = time.time()
        detections = self.detector.detect(frame)
        persons = [d for d in detections if d['label'] == 'person']
        cigarettes = [d for d in detections if d['label'] == 'cigarette']
        
        for cig in cigarettes:
            cid = cig['id']
            conf = cig['conf']
            cbox = cig['box']
            event = self.smoke_events[cid]
            event.last_seen_time = current_time
            event.frame_count += 1
            
            if event.frame_count >= self.alarm_threshold_frames:
                cig['is_alarm'] = True
                if not event.is_confirmed:
                    owner_id = self._match_person_id(cbox, persons)
                    cooldown_key = owner_id if owner_id is not None else "unknown"
                    last_time = self.smoker_records.get(cooldown_key, 0)
                    if current_time - last_time > self.alarm_cooldown:
                        self.smoker_records[cooldown_key] = current_time
                        event.is_confirmed = True
                        logger.warning(f"🔥 ALARM TRIGGERED: Cam {self.camera_id}")
                        self._trigger_alarm_save(frame, owner_id, conf, w, h)
            else:
                cig['is_alarm'] = False

        expired = [tid for tid, evt in self.smoke_events.items() if current_time - evt.last_seen_time > self.lost_timeout]
        for tid in expired: del self.smoke_events[tid]
        return detections

    def _trigger_alarm_save(self, frame, owner_id, conf, w, h):
        prefix = f"alarm_p{owner_id}" if owner_id else "alarm_unknown"
        ts = int(time.time())
        video_name = f"{prefix}_{ts}.mp4"
        video_path = self.recorder.start_recording(video_name, post_record_sec=5, width=w, height=h)
        img_name = f"{prefix}_{ts}.jpg"
        roi_path = self.recorder.save_snapshot(frame, img_name)
        threading.Thread(target=self._save_alarm_to_db, args=(conf, video_path, roi_path)).start()

    def _match_person_id(self, c_box, persons):
        c_cx, c_cy = (c_box[0]+c_box[2])/2, (c_box[1]+c_box[3])/2
        min_dist = float('inf')
        best_id = None
        for p in persons:
            p_box = p['box']
            p_cx, p_cy = (p_box[0]+p_box[2])/2, (p_box[1]+p_box[3])/2
            p_w = p_box[2] - p_box[0]
            search_radius = max(p_w * 2.0, 100.0)
            dist = math.sqrt((c_cx - p_cx)**2 + (c_cy - p_cy)**2)
            if dist < search_radius and dist < min_dist:
                min_dist = dist
                best_id = p['id']
        return best_id

    def _save_alarm_to_db(self, confidence, video_path, roi_path):
        if not self.app: return
        try:
            video_rel = "static/evidence/" + os.path.basename(video_path) if video_path else ""
            with self.app.app_context():
                alarm = Alarms(camera_id=self.camera_id, type='SMOKING', confidence=confidence, video_url=video_rel, roi_url=roi_path)
                db.session.add(alarm)
                db.session.commit()
        except Exception as e:
            logger.error(f"DB Save Error: {e}")

    def _draw_ui(self, frame, detections):
        for det in detections:
            x1, y1, x2, y2 = det['box']
            label = det['label']
            if label == 'person':
                color = (255, 0, 0)
                text = f"ID:{det['id']}"
            else:
                if det.get('is_alarm'):
                    color = (0, 0, 255)
                    text = "SMOKING!"
                    h, w = frame.shape[:2]
                    cv2.rectangle(frame, (0,0), (w,h), (0,0,255), 5)
                else:
                    color = (0, 255, 255)
                    text = "cig"
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        return frame

    def get_latest_frame(self):
        if self.output_frame is not None: 
            return cv2.resize(self.output_frame, (640, 360))
        if self.latest_frame is not None:
            return cv2.resize(self.latest_frame, (640, 360))
        return None

# StreamManager 保持不变
class StreamManager:
    def __init__(self):
        self.stream_loaders = {}
        self.app = None 

    def init_app(self, app):
        self.app = app

    def add_camera(self, cid, url):
        if cid in self.stream_loaders and self.stream_loaders[cid].running:
            return True
        l = StreamLoader(cid, url, self.app)
        if l.start(): 
            self.stream_loaders[cid] = l
            return True
        return False

    def get_latest_frame(self, cid):
        l = self.stream_loaders.get(cid)
        return l.get_latest_frame() if l else None

    def remove_camera(self, cid):
        if cid in self.stream_loaders:
            self.stream_loaders[cid].stop()
            del self.stream_loaders[cid]

stream_manager = StreamManager()