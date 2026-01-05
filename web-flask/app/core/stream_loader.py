import cv2
import time
import threading
import os
import logging
import math
import numpy as np
from collections import defaultdict
from ultralytics import YOLO
from app.core.detector_cls import SmokingClassifier

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PersonState:
    def __init__(self):
        self.smoking_score = 0
        self.last_seen_time = time.time()
        self.is_alarming = False
        self.cooldown = 0

class StreamLoader:
    def __init__(self, camera_id: int, rtsp_url: str):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.lock = threading.Lock()
        
        self.pose_model = YOLO('yolov8n-pose.pt') 
        self.classifier = SmokingClassifier() 
        
        self.running = False
        self.cap = None
        self.latest_frame = None  
        self.output_frame = None  
        
        self.persons = defaultdict(PersonState)
        
        # 🔴 阈值设置
        self.trigger_threshold = 3.5    # 累计分阈值
        self.conf_strict = 0.88         # 分类器严格度
        self.skip_frames = 2            

    def start(self) -> bool:
        try:
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|buffer_size;1024"
            self.cap = cv2.VideoCapture(self.rtsp_url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not self.cap.isOpened(): return False
            self.running = True
            threading.Thread(target=self._reader_thread, daemon=True).start()
            threading.Thread(target=self._processor_thread, daemon=True).start()
            return True
        except: return False

    def stop(self):
        self.running = False
        if self.cap: self.cap.release()

    def _reader_thread(self):
        logger.info(f"Cam {self.camera_id} Reader Started")
        while self.running:
            try:
                if not self.cap or not self.cap.isOpened():
                    self._reconnect()
                    continue
                if not self.cap.grab():
                    time.sleep(0.01)
                    continue
                ret, frame = self.cap.retrieve()
                if ret:
                    with self.lock:
                        self.latest_frame = frame
            except: self._reconnect()

    def _processor_thread(self):
        logger.info(f"Cam {self.camera_id} Processor Started")
        frame_counter = 0
        while self.running:
            frame_to_process = None
            with self.lock:
                if self.latest_frame is not None:
                    frame_to_process = self.latest_frame.copy()
            
            if frame_to_process is None:
                time.sleep(0.1)
                continue

            small_frame = cv2.resize(frame_to_process, (640, 360))
            frame_counter += 1

            if frame_counter % self.skip_frames == 0:
                self._run_ai_logic(small_frame)
            
            final_view = self._draw_ui(small_frame)
            self.output_frame = final_view
            time.sleep(0.01)

    def _run_ai_logic(self, frame):
        try:
            # 追踪
            results = self.pose_model.track(frame, persist=True, verbose=False, imgsz=320)
            if not results or not results[0].boxes or results[0].boxes.id is None:
                return

            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().tolist()
            keypoints = results[0].keypoints.data.cpu().numpy()
            current_time = time.time()

            for box, track_id, kps in zip(boxes, track_ids, keypoints):
                person = self.persons[track_id]
                person.last_seen_time = current_time

                # 1. 姿态几何初筛 (带角度校验)
                is_suspicious, nose, wrist, debug_info = self._check_pose(kps, box)
                
                # 将调试信息存入 person 对象，方便在 UI 画出来
                person.debug_pose = debug_info 

                if is_suspicious:
                    # 2. 二级分类
                    is_real, conf, _ = self.classifier.classify(frame, nose, wrist)
                    
                    if is_real and conf > self.conf_strict:
                        person.smoking_score += 0.8
                        # logger.info(f"ID:{track_id} 积分增加: {person.smoking_score:.1f}")
                    else:
                        person.smoking_score = max(0, person.smoking_score - 0.2)
                else:
                    person.smoking_score = max(0, person.smoking_score - 0.5)

                if person.smoking_score >= self.trigger_threshold:
                    person.is_alarming = True
                    person.cooldown = 40
                    person.smoking_score = self.trigger_threshold
                    logger.warning(f"🔥 ALARM: Person {track_id}")
                
                if person.cooldown > 0:
                    person.is_alarming = True
                    person.cooldown -= 1
                else:
                    person.is_alarming = False
                    
            for pid in list(self.persons.keys()):
                if current_time - self.persons[pid].last_seen_time > 5.0:
                    del self.persons[pid]

        except Exception as e:
            logger.error(f"AI Error: {e}")

    # =========================================================
    # 📐 核心修复：恢复角度计算逻辑
    # =========================================================
    def _calculate_angle(self, a, b, c):
        """计算三点角度 (肩-肘-腕)"""
        ba = np.array([a[0] - b[0], a[1] - b[1]])
        bc = np.array([c[0] - b[0], c[1] - b[1]])
        norm_ba = np.linalg.norm(ba)
        norm_bc = np.linalg.norm(bc)
        if norm_ba < 1e-6 or norm_bc < 1e-6: return 180.0
        
        cosine_angle = np.dot(ba, bc) / (norm_ba * norm_bc)
        angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
        return np.degrees(angle)

    def _check_pose(self, kps, box):
        """
        严格姿态检查：
        1. 距离近
        2. 置信度高
        3. 必须在防线之上
        4. 必须有弯曲角度 (排除衣领误检)
        """
        nose = kps[0]
        # 肩膀(5,6), 肘部(7,8), 手腕(9,10)
        shoulder_l, shoulder_r = kps[5], kps[6]
        elbow_l, elbow_r = kps[7], kps[8]
        wrist_l, wrist_r = kps[9], kps[10]
        
        box_h = box[3] - box[1]
        
        thresh_dist = box_h * 0.35 
        thresh_height = nose[1] + (box_h * 0.20)
        conf_min = 0.60 

        # 调试信息 [左腕, 右腕, 防线Y]
        debug_info = [None, None, thresh_height]

        # 检查左手
        if wrist_l[2] > conf_min:
            debug_info[0] = wrist_l # 记录以便画图
            if wrist_l[1] < thresh_height:
                dist = np.linalg.norm(wrist_l[:2] - nose[:2])
                if dist < thresh_dist:
                    # 🔴 增加角度校验
                    angle = 180
                    if elbow_l[2] > 0.3 and shoulder_l[2] > 0.3:
                        angle = self._calculate_angle(shoulder_l[:2], elbow_l[:2], wrist_l[:2])
                    
                    # 只有角度小于 140 (弯曲) 才算，排除直臂和误检点
                    if angle < 140:
                        return True, nose[:2], wrist_l[:2], debug_info

        # 检查右手
        if wrist_r[2] > conf_min:
            debug_info[1] = wrist_r
            if wrist_r[1] < thresh_height:
                dist = np.linalg.norm(wrist_r[:2] - nose[:2])
                if dist < thresh_dist:
                    angle = 180
                    if elbow_r[2] > 0.3 and shoulder_r[2] > 0.3:
                        angle = self._calculate_angle(shoulder_r[:2], elbow_r[:2], wrist_r[:2])
                    
                    if angle < 140:
                        return True, nose[:2], wrist_r[:2], debug_info
        
        return False, None, None, debug_info

    def _draw_ui(self, frame):
        current_time = time.time()
        for track_id, person in self.persons.items():
            if current_time - person.last_seen_time > 2.0: continue

            # 1. 绘制调试骨架 (让你看到 AI 看到了什么)
            if hasattr(person, 'debug_pose') and person.debug_pose:
                wl, wr, limit_y = person.debug_pose
                # 画防线 (黄色)
                if limit_y:
                    cv2.line(frame, (0, int(limit_y)), (640, int(limit_y)), (0, 255, 255), 1)
                # 画手腕 (粉色)
                if wl is not None:
                    cv2.circle(frame, (int(wl[0]), int(wl[1])), 5, (255, 0, 255), -1)
                if wr is not None:
                    cv2.circle(frame, (int(wr[0]), int(wr[1])), 5, (255, 0, 255), -1)

            # 2. 绘制报警状态
            if person.is_alarming:
                h, w = frame.shape[:2]
                cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 255), 10)
                cv2.putText(frame, f"SMOKING: {track_id}", (50, 80), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            elif person.smoking_score > 0.5:
                # 只有分数大于0.5才显示，避免满屏文字
                score = min(person.smoking_score, self.trigger_threshold)
                cv2.putText(frame, f"ID:{track_id} Sus:{score:.1f}", (20, 40 + track_id*30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        return frame

    def _reconnect(self):
        if self.cap: self.cap.release()
        time.sleep(2)
        try:
            self.cap = cv2.VideoCapture(self.rtsp_url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except: pass

    def get_latest_frame(self):
        if self.output_frame is not None:
            return self.output_frame
        if self.latest_frame is not None:
            return cv2.resize(self.latest_frame, (640, 360))
        return None

class StreamManager:
    def __init__(self, buffer_size=60):
        self.stream_loaders = {}
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