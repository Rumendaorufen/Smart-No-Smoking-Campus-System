import cv2
import threading
import time
import os
import logging
from app.core.detector_pose import PoseDetector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StreamLoader:
    def __init__(self, camera_id: int, rtsp_url: str):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        
        self.raw_frame = None
        self.final_frame = None
        self.latest_detections = []
        
        self.last_alarm_time = 0 
        self.alarm_duration = 3.0 
        
        self.running = False
        self.lock = threading.Lock()
        self.detector = PoseDetector()
        
        # 🔴 优化1: AI 冷却时间设为 1.0 秒 (即每秒只检测 1 次)
        self.last_ai_time = 0
        self.ai_interval = 1.0 

    def start(self) -> bool:
        try:
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|buffer_size;1024"
            self.cap = cv2.VideoCapture(self.rtsp_url)
            # 尝试降低分辨率输入
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            if not self.cap.isOpened(): return False
            self.running = True
            threading.Thread(target=self._worker_reader, daemon=True).start()
            threading.Thread(target=self._worker_processor, daemon=True).start()
            return True
        except: return False

    def stop(self):
        self.running = False
        time.sleep(0.5)
        if self.cap: self.cap.release()

    def _worker_reader(self):
        """线程A: 采集"""
        while self.running:
            if not self.cap or not self.cap.isOpened():
                time.sleep(2)
                self._reconnect()
                continue
            
            # 🔴 优化2: 强制休眠。即使是读取线程，也睡 0.03 秒
            # 这会把 RTSP 读取限制在 30帧以下，防止抢占 CPU
            time.sleep(0.03) 
            
            self.cap.grab() # 清空缓存
            ret, frame = self.cap.retrieve() # 拿一帧
            
            if not ret:
                time.sleep(1)
                continue
            
            with self.lock:
                self.raw_frame = frame

    def _worker_processor(self):
        """线程B: 处理"""
        while self.running:
            frame_to_process = None
            with self.lock:
                if self.raw_frame is not None:
                    frame_to_process = self.raw_frame.copy()
            
            if frame_to_process is None:
                time.sleep(0.1)
                continue
            
            # 🔴 优化3: 处理前强制缩小到 480x270 (非常小，显示够用)
            small_frame = cv2.resize(frame_to_process, (480, 270))
            
            current_time = time.time()
            
            # AI 门控：每 1 秒跑一次
            if current_time - self.last_ai_time > self.ai_interval:
                try:
                    # AI 传入的已经是小图了，速度会很快
                    detections = self.detector.predict_data(small_frame)
                    self.latest_detections = detections
                    self.last_ai_time = current_time
                    
                    for d in detections:
                        if d['is_smoking']:
                            self.last_alarm_time = time.time()
                            print("🔥 报警")
                            break
                except: pass
            
            # 合成画面
            is_in_alarm = (time.time() - self.last_alarm_time) < self.alarm_duration
            
            annotated_frame = self.detector.draw_on_frame(
                small_frame, 
                self.latest_detections, 
                force_alarm=is_in_alarm
            )
            
            self.final_frame = annotated_frame
            
            # 🔴 优化4: 这里的 sleep 决定了最终视频流的 FPS
            # sleep(0.06) ≈ 15 FPS。对于监控来说，15帧完全足够且流畅。
            time.sleep(0.06)

    def _reconnect(self):
        if self.cap: self.cap.release()
        try: self.cap = cv2.VideoCapture(self.rtsp_url)
        except: pass

    def get_latest_frame(self):
        if self.final_frame is not None:
            return self.final_frame
        return None
        
class StreamManager:
    # ... (保持不变) ...
    def __init__(self, buffer_size=60):
        self.streams = {}
    def add_camera(self, camera_id, rtsp_url):
        if camera_id in self.streams: return True
        loader = StreamLoader(camera_id, rtsp_url)
        if loader.start():
            self.streams[camera_id] = loader
            return True
        return False
    def remove_camera(self, camera_id):
        if camera_id in self.streams:
            self.streams[camera_id].stop()
            del self.streams[camera_id]
    def get_latest_frame(self, camera_id):
        if camera_id in self.streams:
            return self.streams[camera_id].get_latest_frame()
        return None