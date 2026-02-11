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
from app.core.detector import get_detector

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
        self.detector = get_detector()
        self.recorder = EvidenceRecorder(save_dir="app/static/evidence", fps=25, pre_record_sec=2)
        
        # 运行状态
        self.running = False
        self.cap = None
        self.latest_frame = None   
        self.output_frame = None   
        
        # ✅ 新增：AI 功能开关，默认开启
        self.ai_enabled = True 

        # AI 逻辑状态
        self.smoke_events = defaultdict(SmokeEvent)
        self.alarm_threshold_frames = 15
        self.lost_timeout = 2.0
        self.last_read_time = time.time()
        
        # 动态冷却状态字典
        self.active_cooldowns = {}
        self.alarm_cooldown = 300.0
        self.alarm_radius = 200 

        # 信号量
        self.reconnect_requested = False
        
        # 连续错误计数器
        self.consecutive_errors = 0

        self.start_lock = threading.Lock() 

    # ✅ 新增方法：动态开关 AI 检测
    def set_ai_status(self, enabled: bool):
        self.ai_enabled = enabled
        logger.info(f"🤖 Cam {self.camera_id} AI Status -> {enabled}")

    def start(self) -> bool:
        with self.start_lock:
            if self.running:
                logger.warning(f"⚠️ Cam {self.camera_id} 已经在运行中，跳过启动")
                return True
                
            self.running = True
            logger.info(f"🚀 Cam {self.camera_id} 启动线程...")
            
            # 启动各个线程
            threading.Thread(target=self._reader_thread, daemon=True).start()
            threading.Thread(target=self._processor_thread, daemon=True).start()
            threading.Thread(target=self._watchdog_thread, daemon=True).start()
            return True

    def stop(self):
        logger.info(f"🛑 [StreamLoader] 收到停止指令: Cam {self.camera_id}")
        self.running = False  # 1. 关掉总开关
        
        # 更新数据库状态
        self._update_db_status(0)

        # 2. ⚡️ 暴力释放资源，打断阻塞
        with self.lock:
            if self.cap:
                try:
                    self.cap.release()
                except Exception as e:
                    logger.error(f"⚠️ Release error: {e}")
                finally:
                    self.cap = None # 彻底置空
        
        logger.info(f"💀 [StreamLoader] 资源已释放: Cam {self.camera_id}")

    def _update_db_status(self, status):
        if not self.app: return
        try:
            with self.app.app_context():
                device = Devices.query.get(self.camera_id)
                if device and device.status != status:
                    device.status = status
                    db.session.commit()
        except Exception as e:
            logger.error(f"❌ DB Update Error: {e}")

    def _connect(self):
        try:
            if self.cap: self.cap.release()
            
            # 🚀 核心修复 1: 强制使用 TCP (rtsp_transport;tcp)
            # TCP 保证数据包按顺序到达，绝不会出现花屏和 h264 error
            # 增大 stimeout (超时时间) 到 5秒 (5000000微秒)，防止网络波动误判断流
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000|max_delay;500000"
            
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            
            if self.cap.isOpened():
                # 🚀 核心修复 2: 禁用 OpenCV 内部缓冲区，避免延时累积
                # BUFFERSIZE=0 意味着一旦读慢了，旧帧直接丢弃，永远只拿最新帧
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 0) 
                
                logger.info(f"✅ Cam {self.camera_id} Connected (TCP Mode).")
                self._update_db_status(1)
                self.consecutive_errors = 0 
                return True
            else:
                logger.warning(f"❌ Cam {self.camera_id} Failed to open RTSP stream.")
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
            if not self.running: break

            try:
                # 响应看门狗
                if self.reconnect_requested:
                    self._update_db_status(0)
                    self._connect()
                    self.reconnect_requested = False
                    self.last_read_time = time.time()

                if not self.cap or not self.cap.isOpened():
                    if not self.running: break
                    time.sleep(2)
                    self._connect()
                    continue
                
                try:
                    grabbed = self.cap.grab()
                except Exception:
                    break

                if not self.running: break

                if grabbed:
                    ret, frame = self.cap.retrieve()
                    if ret and frame is not None and frame.size > 0:
                        with self.lock:
                            self.latest_frame = frame
                            self.last_read_time = time.time()
                            self.consecutive_errors = 0 
                    else:
                        self.consecutive_errors += 1
                else:
                    self.consecutive_errors += 1
                
                if self.consecutive_errors > 30:
                    logger.warning(f"⚡ Cam {self.camera_id} stream corruption detected! Force reconnecting...")
                    self.reconnect_requested = True
                    self.consecutive_errors = 0
                    time.sleep(0.5)

            except Exception as e:
                if self.running:
                    logger.error(f"Reader loop error: {e}")
                time.sleep(1)
        
        logger.info(f"👋 Reader Thread Exited: Cam {self.camera_id}")

    def _watchdog_thread(self):
        """看门狗：监控 Reader 是否卡死"""
        while self.running:
            if time.time() - self.last_read_time > 15.0:
                if not self.reconnect_requested:
                    logger.warning(f"🚨 Cam {self.camera_id} Timeout/Frozen! Requesting restart...")
                    self.reconnect_requested = True
                    self._update_db_status(0)
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

            self.recorder.add_frame(frame_to_process)
            self.recorder.process_recording(frame_to_process)

            # ✅ 修改：根据开关决定是否运行 AI 检测
            detections = []
            if self.ai_enabled:
                detections = self._run_ai_logic(frame_to_process)
            
            # 绘图 (如果没有 AI，就只画原图，不画框)
            final_view = self._draw_ui(frame_to_process, detections)
            
            self.output_frame = cv2.resize(final_view, (1280, 720))
            time.sleep(0.03)

    def _run_ai_logic(self, frame):
        h, w = frame.shape[:2]
        current_time = time.time()
        
        # 1. AI 推理
        detections = self.detector.detect(frame)
        persons = [d for d in detections if d['label'] == 'person']
        cigarettes = [d for d in detections if d['label'] == 'cigarette']
        
        # 2. 🟢 维护阶段：更新冷却圈位置
        current_pids = {p['id']: p['box'] for p in persons}
        
        keys_to_remove = []
        for key, record in self.active_cooldowns.items():
            if current_time - record['time'] > self.alarm_cooldown:
                keys_to_remove.append(key)
                continue
            
            if isinstance(key, int):
                if key in current_pids:
                    box = current_pids[key]
                    cx, cy = (box[0] + box[2])/2, (box[1] + box[3])/2
                    record['pos'] = (cx, cy)
                    record['last_seen'] = current_time 
                else:
                    pass

        for k in keys_to_remove: 
            del self.active_cooldowns[k]

        # 3. 🔴 判定阶段
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
                    c_cx = (cbox[0] + cbox[2]) / 2
                    c_cy = (cbox[1] + cbox[3]) / 2
                    
                    is_cooling_down = False
                    
                    for record in self.active_cooldowns.values():
                        rx, ry = record['pos']
                        dist = math.sqrt((c_cx - rx)**2 + (c_cy - ry)**2)
                        if dist < self.alarm_radius:
                            is_cooling_down = True
                            break 
                    
                    if not is_cooling_down:
                        event.is_confirmed = True
                        owner_id = self._match_person_id(cbox, persons)
                        logger.warning(f"🔥 ALARM TRIGGERED: Cam {self.camera_id}")
                        self._trigger_alarm_save(frame, owner_id, conf, w, h)
                        
                        if owner_id is not None:
                            self.active_cooldowns[owner_id] = {
                                'pos': (c_cx, c_cy), 
                                'time': current_time,
                                'type': 'dynamic'
                            }
                        else:
                            static_key = f"static_{time.time()}_{cid}"
                            self.active_cooldowns[static_key] = {
                                'pos': (c_cx, c_cy),
                                'time': current_time,
                                'type': 'static'
                            }
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
        
        if self.app:
            threading.Thread(
                target=self._save_alarm_to_db, 
                args=(self.app, conf, video_path, roi_path)
            ).start()
        else:
            logger.error("❌ App context is missing, cannot save alarm to DB")

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

    def _save_alarm_to_db(self, app, confidence, video_path, roi_path):
        try:
            with app.app_context():
                video_rel = "static/evidence/" + os.path.basename(video_path) if video_path else ""
                roi_rel = "static/evidence/snapshots/" + os.path.basename(roi_path) if roi_path else ""
                    
                alarm = Alarms(
                    camera_id=self.camera_id, 
                    type='SMOKING', 
                    confidence=confidence, 
                    video_url=video_rel, 
                    roi_url=roi_rel,
                    audit_status=0 
                )
                db.session.add(alarm)
                db.session.commit()
                logger.info(f"💾 [DB] 报警记录已保存: ID {alarm.id}")
        except Exception as e:
            with app.app_context():
                db.session.rollback()
            logger.error(f"❌ DB Save Error: {e}")

    def _draw_ui(self, frame, detections):
        for det in detections:
            x1, y1, x2, y2 = det['box']
            label = det['label']
            if label == 'person':
                color = (255, 0, 0)
                # 加上摄像头ID前缀
                text = f"Cam{self.camera_id}-ID:{det['id']}"
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

# ==========================================
# StreamManager: 管理所有摄像头
# ==========================================
class StreamManager:
    def __init__(self):
        self.stream_loaders = {}
        self.app = None 
        self.lock = threading.Lock() 
        
        # ✅ 新增：全局 AI 开关 (默认开启)
        self.global_ai_enabled = True

    def init_app(self, app):
        self.app = app

    def add_camera(self, cid, url):
        with self.lock: 
            if cid in self.stream_loaders:
                existing = self.stream_loaders[cid]
                if existing.rtsp_url == url and existing.running:
                    # 即使已经在运行，也要同步一下当前的全局 AI 状态
                    existing.set_ai_status(self.global_ai_enabled)
                    return True
                logger.info(f"🔄 [Manager] 替换旧实例: Cam {cid}")
                existing.stop()
                del self.stream_loaders[cid] 
            
            l = StreamLoader(cid, url, self.app)
            
            # ✅ 启动时应用全局 AI 状态
            l.set_ai_status(self.global_ai_enabled)
            
            if l.start(): 
                self.stream_loaders[cid] = l
                return True
            return False

    def get_latest_frame(self, cid):
        l = self.stream_loaders.get(cid)
        return l.get_latest_frame() if l else None

    def remove_camera(self, cid):
        with self.lock: 
            if cid in self.stream_loaders:
                logger.info(f"🗑️ [Manager] Removing Camera ID: {cid}")
                loader = self.stream_loaders[cid]
                loader.stop() 
                del self.stream_loaders[cid] 
            else:
                logger.warning(f"⚠️ [Manager] 试图删除不存在的设备: {cid}")

    # ✅ 修改：启动前检查 enabled 字段
    def start_camera_task(self, device_id):
        from app.models.devices import Devices 
        if not self.app: return False
        
        with self.app.app_context():
            device = Devices.query.get(device_id)
            if not device: return False
            
            # 🛑 核心拦截：如果设备被禁用了，拒绝启动
            if device.enabled == False: # 显式检查 False
                logger.warning(f"🚫 [Manager] Cam {device_id} 已被停用，拒绝启动")
                return False

            if device.rtsp_url:
                return self.add_camera(device.id, device.rtsp_url)
        return False

    # ✅ 新增：切换设备的“启用/停用”状态 (写入数据库)
    def toggle_device_enable(self, device_id, enable):
        from app.models.devices import Devices
        if not self.app: return False
        
        with self.app.app_context():
            device = Devices.query.get(device_id)
            if device:
                device.enabled = enable
                db.session.commit()
                
                if enable:
                    # 如果启用，尝试启动流
                    return self.start_camera_task(device_id)
                else:
                    # 如果停用，强制停止流
                    self.remove_camera(device_id)
                    # 强制更新状态为离线
                    device.status = 0
                    db.session.commit()
                    return True
        return False

    # ✅ 新增：设置全局 AI 开关
    def set_global_ai(self, enabled):
        self.global_ai_enabled = enabled
        logger.info(f"🌍 [System] 全局 AI 设定为: {enabled}")
        
        # 遍历所有正在运行的加载器，实时更新它们的状态
        with self.lock:
            for loader in self.stream_loaders.values():
                loader.set_ai_status(enabled)
        return True

stream_manager = StreamManager()