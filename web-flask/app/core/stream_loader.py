import cv2
import time
import threading
import os
import logging
import math
from collections import defaultdict
from app.core.detector import SmokingDetector
from app.core.recorder import EvidenceRecorder
from app.models import db, Alarms

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SmokeEvent:
    def __init__(self):
        self.start_time = time.time()
        self.last_seen_time = time.time()
        self.frame_count = 0     
        self.is_confirmed = False 

class StreamLoader:
    def __init__(self, camera_id: int, rtsp_url: str, app=None):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.app = app 
        self.lock = threading.Lock()
        self.detector = SmokingDetector()
        
        # 初始化录制器
        self.recorder = EvidenceRecorder(save_dir="app/static/evidence", fps=25, pre_record_sec=2)
        
        self.running = False
        self.cap = None
        self.latest_frame = None  
        self.output_frame = None  
        
        self.smoke_events = defaultdict(SmokeEvent)
        self.alarm_threshold_frames = 15 # 建议调高到 15 帧防抖
        self.lost_timeout = 2.0
        
        self.last_read_time = time.time()
        
        # 记录 "Person ID" 的最后报警时间
        # 格式: { person_id_or_unknown_key: last_alarm_time }
        self.smoker_records = {} 
        
        self.alarm_cooldown = 300.0  # 冷却时间 5分钟

    def start(self) -> bool:
        self.running = True
        threading.Thread(target=self._reader_thread, daemon=True).start()
        threading.Thread(target=self._processor_thread, daemon=True).start()
        threading.Thread(target=self._watchdog_thread, daemon=True).start()
        return True

    def stop(self):
        self.running = False
        if self.cap: self.cap.release()

    def _connect(self):
        try:
            if self.cap: self.cap.release()
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|buffer_size;1024"
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_N_THREADS, 1)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                logger.info(f"✅ Cam {self.camera_id} Connected.")
                return True
        except Exception as e:
            logger.error(f"Connection error: {e}")
        return False

    def _reader_thread(self):
        logger.info(f"Cam {self.camera_id} Reader Started")
        if not self._connect():
            logger.warning(f"Cam {self.camera_id} init failed.")

        while self.running:
            try:
                if not self.cap or not self.cap.isOpened():
                    time.sleep(1)
                    continue
                if self.cap.grab():
                    ret, frame = self.cap.retrieve()
                    if ret:
                        with self.lock:
                            self.latest_frame = frame
                            self.last_read_time = time.time()
                    else:
                        time.sleep(0.01)
                else:
                    time.sleep(0.01)
            except Exception as e:
                logger.error(f"Reader error: {e}")
                time.sleep(1)

    def _watchdog_thread(self):
        while self.running:
            if time.time() - self.last_read_time > 10.0: # 放宽一点到 10秒
                logger.warning(f"🚨 Cam {self.camera_id} Frozen! Restarting...")
                self._connect()
                self.last_read_time = time.time()
            time.sleep(2)

    def _processor_thread(self):
        while self.running:
            frame_to_process = None
            with self.lock:
                if self.latest_frame is not None:
                    frame_to_process = self.latest_frame.copy()
            
            if frame_to_process is None:
                time.sleep(0.1)
                continue

            process_frame = cv2.resize(frame_to_process, (640, 360))
            
            self.recorder.add_frame(process_frame)
            self.recorder.process_recording(process_frame)

            detections = self._run_ai_logic(process_frame)
            final_view = self._draw_ui(process_frame, detections)
            
            self.output_frame = final_view
            time.sleep(0.03)

    # 🛑 修复：将匹配函数放回类内部，并增加距离阈值判断
    def _match_person_id(self, cigarette_box, person_detections):
        c_x1, c_y1, c_x2, c_y2 = cigarette_box
        c_center_x = (c_x1 + c_x2) / 2
        c_center_y = (c_y1 + c_y2) / 2
        
        best_match_id = None
        min_dist = float('inf')

        for p in person_detections:
            p_box = p['box']
            p_id = p['id']
            
            # 宽松判定：扩展框
            padding = 50
            if (p_box[0] - padding < c_center_x < p_box[2] + padding) and \
               (p_box[1] - padding < c_center_y < p_box[3] + padding):
                return p_id
        
        return None

    def _run_ai_logic(self, frame):
        current_time = time.time()
        detections = self.detector.detect(frame)
        
        persons = [d for d in detections if d['label'] == 'person']
        cigarettes = [d for d in detections if d['label'] == 'cigarette'] # 假设你的标签是 cigarette
        
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
                    # 1. 找主人
                    owner_id = self._match_person_id(cbox, persons)
                    
                    # 2. 确定冷却键 (如果有主人用ID，没主人用 "unknown")
                    # 这样可以防止 "Unknown Owner" 疯狂重复报警
                    cooldown_key = owner_id if owner_id is not None else "unknown_smoker"
                    
                    # 3. 检查冷却
                    last_time = self.smoker_records.get(cooldown_key, 0)
                    
                    if current_time - last_time > self.alarm_cooldown:
                        # 🔥 触发报警
                        self.smoker_records[cooldown_key] = current_time # 更新冷却时间
                        event.is_confirmed = True
                        
                        log_msg = f"🔥 ALARM: Person {owner_id}" if owner_id else "🔥 ALARM: Unknown Owner"
                        logger.warning(f"{log_msg} (Cig {cid})")
                        
                        # 录制与入库
                        file_prefix = f"alarm_p{owner_id}" if owner_id else "alarm_unknown"
                        filename = f"{file_prefix}_{int(time.time())}.mp4"
                        video_path = self.recorder.start_recording(filename, post_record_sec=5)
                        
                        img_name = f"{file_prefix}_{int(time.time())}.jpg"
                        roi_path = self.recorder.save_snapshot(frame, img_name)
                        
                        threading.Thread(target=self._save_alarm_to_db, 
                                         args=(conf, video_path, roi_path)).start()
                    else:
                        # ❄️ 冷却中，忽略
                        event.is_confirmed = True # 标记为已处理，防止下一帧重复检查冷却
                        logger.info(f"❄️ Cooldown: {cooldown_key} ignored.")
            else:
                cig['is_alarm'] = False

        expired_ids = [tid for tid, evt in self.smoke_events.items() 
                      if current_time - evt.last_seen_time > self.lost_timeout]
        for tid in expired_ids:
            del self.smoke_events[tid]
            
        return detections

    def _save_alarm_to_db(self, confidence, video_full_path, roi_rel_path):
        try:
            if not self.app: return
            
            if video_full_path:
                video_rel_path = "static/evidence/" + os.path.basename(video_full_path)
            else:
                video_rel_path = ""

            with self.app.app_context():
                new_alarm = Alarms(
                    camera_id=self.camera_id,
                    type='SMOKING',
                    confidence=confidence,
                    video_url=video_rel_path,
                    roi_url=roi_rel_path
                )
                db.session.add(new_alarm)
                db.session.commit()
                logger.info(f"✅ Alarm saved to DB: ID {new_alarm.id}")
        except Exception as e:
            logger.error(f"❌ DB Save Error: {e}")

    def _draw_ui(self, frame, detections):
        h, w = frame.shape[:2]
        is_global_alarm = False
        persons = [d for d in detections if d['label'] == 'person']

        for det in detections:
            box = det['box']
            label = det['label']
            tid = det['id']
            
            if label == 'person':
                cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), (255, 0, 0), 2)
                cv2.putText(frame, f"ID:{tid}", (box[0], box[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
            else:
                if det.get('is_alarm', False):
                    owner_id = self._match_person_id(box, persons)
                    text = f"SMOKING! Owner:{owner_id}" if owner_id else "SMOKING! Unknown"
                    cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), (0, 0, 255), 3)
                    cv2.putText(frame, text, (box[0], box[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    is_global_alarm = True
                else:
                    cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), (0, 255, 255), 2)

        if is_global_alarm:
            cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 255), 8)
            
        return frame
        
    def get_latest_frame(self):
        if self.output_frame is not None: return self.output_frame
        if self.latest_frame is not None: return cv2.resize(self.latest_frame, (640, 360))
        return None

class StreamManager:
    def __init__(self, buffer_size=60):
        self.stream_loaders = {}
        self.app = None 

    def init_app(self, app):
        self.app = app

    def add_camera(self, cid, url):
        if cid in self.stream_loaders: return True
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