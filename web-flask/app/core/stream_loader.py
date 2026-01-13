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
        self.recorder = EvidenceRecorder(save_dir="app/static/evidence", fps=25, pre_record_sec=2)
        
        self.running = False
        self.cap = None
        self.latest_frame = None  
        self.output_frame = None  
        
        self.smoke_events = defaultdict(SmokeEvent)
        self.alarm_threshold_frames = 15
        self.lost_timeout = 2.0
        
        self.last_read_time = time.time()
        
        # 冷却记录 { id: time }
        self.smoker_records = {} 
        self.alarm_cooldown = 300.0 

        # 🛑 新增：重连信号旗
        # Watchdog 只能改这个值，不能动 self.cap
        self.reconnect_requested = False

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
        """只在 _reader_thread 内部调用，确保线程安全"""
        try:
            if self.cap: 
                self.cap.release()
            
            # 🛑 核心修改：优化 FFmpeg 参数
            # rtsp_transport;tcp  -> 强制使用 TCP (解决花屏、丢包、绿屏的关键)
            # stimeout;20000000   -> 设置 socket 超时时间为 20秒 (单位微秒)，防止连不上时卡死
            # buffer_size;10240   -> 增加内部缓冲区到 10MB，防止高清帧太大被截断
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;20000000|buffer_size;10240"
            
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            
            if self.cap.isOpened():
                # 禁用内部多线程 (防止崩溃)
                self.cap.set(cv2.CAP_PROP_N_THREADS, 1)
                
                # 🛑 修改：不要把 Buffer 设为 1 了，稍微给一点余量
                # 在网络波动时，设为 1 容易导致直接丢帧报错
                # 设为 3 可以在 "极低延迟" 和 "画面完整性" 之间找个平衡
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
                
                logger.info(f"✅ Cam {self.camera_id} Connected (TCP Mode).")
                return True
        except Exception as e:
            logger.error(f"Connection error: {e}")
        return False

    def _reader_thread(self):
        """唯一的读取线程，也是唯一的连接管理者"""
        logger.info(f"Cam {self.camera_id} Reader Started")
        
        # 第一次连接
        if not self._connect():
            logger.warning(f"Cam {self.camera_id} init failed.")

        while self.running:
            try:
                # 🛑 检查是否收到看门狗的重连指令
                if self.reconnect_requested:
                    logger.warning(f"🔄 Cam {self.camera_id} Reconnecting by request...")
                    self._connect()
                    self.reconnect_requested = False # 复位信号
                    self.last_read_time = time.time() # 重置时间防止死循环

                if not self.cap or not self.cap.isOpened():
                    time.sleep(1)
                    # 尝试自动重连
                    self._connect()
                    continue
                
                # 读取帧
                grabbed = self.cap.grab()
                if grabbed:
                    ret, frame = self.cap.retrieve()
                    if ret:
                        with self.lock:
                            self.latest_frame = frame
                            self.last_read_time = time.time() # 喂狗
                    else:
                        time.sleep(0.01)
                else:
                    # 没抓到帧，休息一下
                    time.sleep(0.01)
            
            except Exception as e:
                logger.error(f"Reader error: {e}")
                time.sleep(1)

    def _watchdog_thread(self):
        """看门狗：只负责发信号，不动手"""
        while self.running:
            # 如果超时 (比如 10秒)
            if time.time() - self.last_read_time > 10.0:
                logger.warning(f"🚨 Cam {self.camera_id} Frozen! Signaling restart...")
                
                # 🛑 关键修改：只举旗，不重连
                # 让 reader 线程在下一轮循环自己去连，避免线程冲突
                self.reconnect_requested = True
                
                # 临时更新时间，防止看门狗一秒钟发一次信号，给 reader 一点时间去处理
                self.last_read_time = time.time() 
            
            time.sleep(2)

    # ... ( _processor_thread, _match_person_id, _run_ai_logic, _save_alarm_to_db, _draw_ui, get_latest_frame 保持不变 )
    # 为节省篇幅，这里省略中间未修改的代码，请保留你上一次修改的逻辑
    
    def _processor_thread(self):
        # ... (保持原样) ...
        while self.running:
            frame_to_process = None
            with self.lock:
                if self.latest_frame is not None:
                    frame_to_process = self.latest_frame.copy()
            
            if frame_to_process is None:
                time.sleep(0.1)
                continue

            #process_frame = cv2.resize(frame_to_process, (640, 360))
            # 🛑 关键修改：不要在这里 resize 到 640x360！
            # process_frame = cv2.resize(frame_to_process, (640, 360)) <--- 删掉这行
            # 直接使用原图 (例如 1920x1080)
            process_frame = frame_to_process
            
            self.recorder.add_frame(process_frame)
            self.recorder.process_recording(process_frame)

            detections = self._run_ai_logic(process_frame)
            # 画完框后再缩放 (为了前端传输流畅，展示时可以小一点，但检测时必须大)
            final_view = self._draw_ui(process_frame, detections)
            # 这里的 output_frame 可以缩放，节省网络带宽
            self.output_frame = cv2.resize(final_view, (1280, 720)) 
            
            time.sleep(0.03)

    def _match_person_id(self, cigarette_box, person_detections):
        c_x1, c_y1, c_x2, c_y2 = cigarette_box
        c_center_x = (c_x1 + c_x2) / 2
        c_center_y = (c_y1 + c_y2) / 2
        
        # 寻找距离最近的人，而不仅仅是包含关系
        min_dist = float('inf')
        best_match_id = None
        
        for p in person_detections:
            p_box = p['box']
            p_id = p['id']
            
            # 计算人的中心点
            p_center_x = (p_box[0] + p_box[2]) / 2
            p_center_y = (p_box[1] + p_box[3]) / 2
            
            # 计算人框的宽度（用来动态调整搜索半径）
            p_width = p_box[2] - p_box[0]
            
            # 搜索半径：在这个人宽度的 2倍 范围内都算他的
            # 远处的烟头可能看起来离人很远，其实像素距离很近
            search_radius = max(p_width * 2.0, 100.0) 

            # 计算欧几里得距离
            dist = math.sqrt((c_center_x - p_center_x)**2 + (c_center_y - p_center_y)**2)
            
            if dist < search_radius:
                if dist < min_dist:
                    min_dist = dist
                    best_match_id = p_id
        
        return best_match_id

    def _run_ai_logic(self, frame):
        h, w = frame.shape[:2] # <--- 获取真实尺寸
        # ... (保持原样，含冷却逻辑) ...
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
                    cooldown_key = owner_id if owner_id is not None else "unknown_smoker"
                    last_time = self.smoker_records.get(cooldown_key, 0)
                    
                    if current_time - last_time > self.alarm_cooldown:
                        self.smoker_records[cooldown_key] = current_time
                        event.is_confirmed = True
                        
                        log_msg = f"🔥 ALARM: Person {owner_id}" if owner_id else "🔥 ALARM: Unknown Owner"
                        logger.warning(f"{log_msg} (Cig {cid})")
                        
                        file_prefix = f"alarm_p{owner_id}" if owner_id else "alarm_unknown"
                        filename = f"{file_prefix}_{int(time.time())}.mp4"
                        video_path = self.recorder.start_recording(
                            filename, 
                            post_record_sec=5, 
                            width=w,  # <--- 传真实宽
                            height=h  # <--- 传真实高
                        )
                        img_name = f"{file_prefix}_{int(time.time())}.jpg"
                        roi_path = self.recorder.save_snapshot(frame, img_name)
                        threading.Thread(target=self._save_alarm_to_db, args=(conf, video_path, roi_path)).start()
                    else:
                        event.is_confirmed = True
                        logger.info(f"❄️ Cooldown: {cooldown_key} ignored.")
            else:
                cig['is_alarm'] = False

        expired_ids = [tid for tid, evt in self.smoke_events.items() if current_time - evt.last_seen_time > self.lost_timeout]
        for tid in expired_ids: del self.smoke_events[tid]
        return detections

    def _save_alarm_to_db(self, confidence, video_full_path, roi_rel_path):
        # ... (保持原样) ...
        try:
            if not self.app: return
            if video_full_path:
                video_rel_path = "static/evidence/" + os.path.basename(video_full_path)
            else:
                video_rel_path = ""
            with self.app.app_context():
                new_alarm = Alarms(camera_id=self.camera_id, type='SMOKING', confidence=confidence, video_url=video_rel_path, roi_url=roi_rel_path)
                db.session.add(new_alarm)
                db.session.commit()
                logger.info(f"✅ Alarm saved to DB: ID {new_alarm.id}")
        except Exception as e:
            logger.error(f"❌ DB Save Error: {e}")

    def _draw_ui(self, frame, detections):
        # ... (保持原样) ...
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

# (StreamManager 类保持不变)
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