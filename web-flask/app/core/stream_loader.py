#web-flask\app\core\stream_loader.py
import cv2
import time
import threading
import os
import logging
import uuid
from collections import defaultdict
from app.core.detector import SmokingDetector
from app.core.recorder import EvidenceRecorder # 导入录制器
# 导入 app 创建函数以便获取 context，或者直接从 run import app (如果结构允许)
# 这里假设我们在 __init__.py 里已经初始化了 db，我们需要在线程里使用它
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
        self.app = app # 存起来
        self.lock = threading.Lock()
        self.detector = SmokingDetector()
        
        # ✅ 初始化录制器 (FPS=25, 预录2秒)
        self.recorder = EvidenceRecorder(save_dir="app/static/evidence", fps=25, pre_record_sec=2)
        
        self.running = False
        self.cap = None
        self.latest_frame = None  
        self.output_frame = None  
        
        self.smoke_events = defaultdict(SmokeEvent)
        self.alarm_threshold_frames = 5
        self.lost_timeout = 2.0
        
        self.last_read_time = time.time()

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
            # 使用 Headless 兼容模式
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_N_THREADS, 1) # 单线程稳定模式
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
            if time.time() - self.last_read_time > 5.0:
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
            
            # ✅ 1. 将帧送入录制器缓冲 (不管是否报警，都要存，为了预录制)
            self.recorder.add_frame(process_frame)
            
            # ✅ 2. 如果正在录制中，继续写入后续帧
            # 如果录制刚结束 (返回True)，则可以做些清理工作(可选)
            self.recorder.process_recording(process_frame)

            detections = self._run_ai_logic(process_frame)
            final_view = self._draw_ui(process_frame, detections)
            
            self.output_frame = final_view
            time.sleep(0.03)

    def _run_ai_logic(self, frame):
        current_time = time.time()
        detections = self.detector.detect(frame)
        
        for det in detections:
            if det['label'] == 'person': continue
            
            tid = det['id']
            conf = det['conf']
            event = self.smoke_events[tid]
            event.last_seen_time = current_time
            event.frame_count += 1
            
            # 🚨 触发报警逻辑
            if event.frame_count >= self.alarm_threshold_frames:
                if not event.is_confirmed:
                    logger.warning(f"🔥 ALARM TRIGGERED: Cigarette ID {tid}")
                    event.is_confirmed = True
                    
                    # ✅ 3. 开始录制 (文件名：alarm_时间戳.mp4)
                    filename = f"alarm_{int(time.time())}_{tid}.mp4"
                    # 录制后3秒，画面尺寸640x360
                    video_path = self.recorder.start_recording(filename, post_record_sec=3, width=640, height=360)
                    
                    # ✅ 4. 保存特写截图
                    img_name = f"alarm_{int(time.time())}_{tid}.jpg"
                    roi_path = self.recorder.save_snapshot(frame, img_name)
                    
                    # ✅ 5. 写入数据库 (异步执行，防卡顿)
                    threading.Thread(target=self._save_alarm_to_db, 
                                     args=(conf, video_path, roi_path)).start()

                det['is_alarm'] = True
            else:
                det['is_alarm'] = False

        expired_ids = [tid for tid, evt in self.smoke_events.items() 
                      if current_time - evt.last_seen_time > self.lost_timeout]
        for tid in expired_ids:
            del self.smoke_events[tid]
            
        return detections

    def _save_alarm_to_db(self, confidence, video_full_path, roi_rel_path):
        """将报警信息写入 MySQL"""
        try:
            # 这是一个在子线程里运行的函数，需要手动推 context
            from app import create_app
            app = create_app() # 这里会复用配置
            
            # 转换视频路径为相对路径 (static/evidence/...)
            if video_full_path:
                video_rel_path = "static/evidence/" + os.path.basename(video_full_path)
            else:
                video_rel_path = ""

            with app.app_context():
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
        # (保持你原有的 UI 绘制逻辑不变)
        h, w = frame.shape[:2]
        is_global_alarm = False
        for det in detections:
            box = det['box']
            conf = det['conf']
            label = det['label']
            if label == 'person':
                color = (255, 0, 0); thickness = 2; text = f"Person {conf:.2f}"
            elif det.get('is_alarm', False):
                color = (0, 0, 255); thickness = 3; text = f"SMOKING! {conf:.2f}"
                is_global_alarm = True
            else:
                color = (0, 255, 255); thickness = 2; text = f"Smoke {conf:.2f}"
            cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, thickness)
            cv2.putText(frame, text, (box[0], box[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        if is_global_alarm:
            cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 255), 8)
            cv2.putText(frame, "SMOKING DETECTED", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
        return frame
        
    # (保持 get_latest_frame 不变)
    def get_latest_frame(self):
        if self.output_frame is not None: return self.output_frame
        if self.latest_frame is not None: return cv2.resize(self.latest_frame, (640, 360))
        return None

# (StreamManager 类保持不变)
class StreamManager:
    def __init__(self, buffer_size=60):
        self.stream_loaders = {}
        self.buffer_size = buffer_size
        self.app = None # 新增：用来存 app 实例

    # 新增：接收 app 实例
    def init_app(self, app):
        self.app = app

    def add_camera(self, cid, url):
        if cid in self.stream_loaders: return True
        # 把 self.app 传给 StreamLoader
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