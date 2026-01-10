import cv2
import time
import threading
import os
import logging
from collections import defaultdict
from app.core.detector import SmokingDetector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SmokeEvent:
    def __init__(self):
        self.start_time = time.time()
        self.last_seen_time = time.time()
        self.frame_count = 0     
        self.is_confirmed = False 

class StreamLoader:
    def __init__(self, camera_id: int, rtsp_url: str):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.lock = threading.Lock()
        self.detector = SmokingDetector()
        
        self.running = False
        self.cap = None
        self.latest_frame = None  
        self.output_frame = None  
        
        self.smoke_events = defaultdict(SmokeEvent)
        self.alarm_threshold_frames = 5
        self.lost_timeout = 2.0
        
        # 🐶 看门狗时间戳
        self.last_read_time = time.time()

    def start(self) -> bool:
        self.running = True
        # 启动线程
        threading.Thread(target=self._reader_thread, daemon=True).start()
        threading.Thread(target=self._processor_thread, daemon=True).start()
        # 启动看门狗线程
        threading.Thread(target=self._watchdog_thread, daemon=True).start()
        return True

    def stop(self):
        self.running = False
        if self.cap: self.cap.release()

    def _connect(self):
        """建立连接的独立方法"""
        try:
            if self.cap: self.cap.release()
            # 强制使用 TCP 传输，比 UDP 更稳定，不易花屏
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|buffer_size;1024"
            self.cap = cv2.VideoCapture(self.rtsp_url)
            if self.cap.isOpened():
                logger.info(f"✅ Cam {self.camera_id} Connected.")
                return True
        except Exception as e:
            logger.error(f"Connection error: {e}")
        return False

    def _reader_thread(self):
        """读取线程：只负责把最新帧读进来，越快越好"""
        logger.info(f"Cam {self.camera_id} Reader Started")
        
        # 初次连接
        if not self._connect():
            logger.warning(f"Cam {self.camera_id} init failed, watchdog will handle it.")

        while self.running:
            try:
                if not self.cap or not self.cap.isOpened():
                    time.sleep(1) # 等待重连
                    continue
                
                # grab() 是非阻塞的，比 retrieve() 快
                if self.cap.grab():
                    ret, frame = self.cap.retrieve()
                    if ret:
                        with self.lock:
                            self.latest_frame = frame
                            self.last_read_time = time.time() # 喂狗
                    else:
                        time.sleep(0.01)
                else:
                    # 如果抓不到帧，稍微休眠防止 CPU 100%
                    time.sleep(0.01)
            except Exception as e:
                logger.error(f"Reader error: {e}")
                time.sleep(1)

    def _watchdog_thread(self):
        """🐶 看门狗：监控读取流是否卡死"""
        logger.info(f"Cam {self.camera_id} Watchdog Started")
        while self.running:
            # 如果超过 5 秒没有新帧，说明卡死了
            if time.time() - self.last_read_time > 5.0:
                logger.warning(f"🚨 Cam {self.camera_id} Frozen! Restarting connection...")
                self._connect() # 强制重连
                self.last_read_time = time.time() # 重置时间
            time.sleep(2)

    def _processor_thread(self):
        """处理线程：AI 推理"""
        while self.running:
            frame_to_process = None
            with self.lock:
                if self.latest_frame is not None:
                    frame_to_process = self.latest_frame.copy()
            
            # 如果没有画面，就不推理，省资源
            if frame_to_process is None:
                time.sleep(0.1)
                continue

            # 缩小尺寸加速
            process_frame = cv2.resize(frame_to_process, (640, 360))
            detections = self._run_ai_logic(process_frame)
            final_view = self._draw_ui(process_frame, detections)
            
            self.output_frame = final_view
            time.sleep(0.03) # 限制推理帧率，防止积压

    def _run_ai_logic(self, frame):
        current_time = time.time()
        detections = self.detector.detect(frame)
        
        for det in detections:
            if det['label'] == 'person': continue
            tid = det['id']
            event = self.smoke_events[tid]
            event.last_seen_time = current_time
            event.frame_count += 1
            
            if event.frame_count >= self.alarm_threshold_frames:
                if not event.is_confirmed:
                    logger.warning(f"🔥 ALARM: Cigarette ID {tid}")
                    event.is_confirmed = True
                det['is_alarm'] = True
            else:
                det['is_alarm'] = False

        expired_ids = [tid for tid, evt in self.smoke_events.items() 
                      if current_time - evt.last_seen_time > self.lost_timeout]
        for tid in expired_ids:
            del self.smoke_events[tid]
            
        return detections

    def _draw_ui(self, frame, detections):
        h, w = frame.shape[:2]
        is_global_alarm = False
        
        for det in detections:
            box = det['box']
            conf = det['conf']
            label = det['label']
            
            if label == 'person':
                color = (255, 0, 0) 
                thickness = 2
                text = f"Person {conf:.2f}"
            elif det.get('is_alarm', False):
                color = (0, 0, 255)
                thickness = 3
                text = f"SMOKING! {conf:.2f}"
                is_global_alarm = True
            else:
                color = (0, 255, 255)
                thickness = 2
                text = f"Smoke {conf:.2f}"
            
            cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, thickness)
            cv2.putText(frame, text, (box[0], box[1]-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        if is_global_alarm:
            cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 255), 8)
            cv2.putText(frame, "SMOKING DETECTED", (20, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
            
        return frame

    def get_latest_frame(self):
        if self.output_frame is not None:
            return self.output_frame
        if self.latest_frame is not None:
            return cv2.resize(self.latest_frame, (640, 360))
        return None

class StreamManager:
    def __init__(self, buffer_size=60):
        self.stream_loaders = {}
        self.buffer_size = buffer_size

    def add_camera(self, cid, url):
        if cid in self.stream_loaders: return True
        l = StreamLoader(cid, url)
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