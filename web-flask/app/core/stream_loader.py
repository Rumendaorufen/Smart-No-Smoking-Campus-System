#web-flask\app\core\stream_loader.py
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
        self.detector = get_detector() # 👈 直接用 detector.py 里提供的工厂函数
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
        #self.smoker_records = {} 
        # ✅ 新增：记录最近的报警事件 [(x, y, timestamp), ...]
        # self.recent_alarm_locations = [] 
        # ❌ 删除旧的: self.recent_alarm_locations = [] 
        # ✅ 新增: 动态冷却状态字典
        # 结构: { key: {'pos': (cx, cy), 'time': timestamp, 'type': 'dynamic'/'static'} }
        self.active_cooldowns = {}
        self.alarm_cooldown = 300.0
        self.alarm_radius = 200 # 像素距离，在这个范围内认为是同一个人

        # 信号量
        self.reconnect_requested = False
        
        # 🛑 新增：连续错误计数器
        self.consecutive_errors = 0

        self.start_lock = threading.Lock() # ✅ 新增启动锁


    def start(self) -> bool:
        with self.start_lock: # ✅ 确保不会被重复启动
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

   # ✅ 修改 1：增强版 stop 方法
    def stop(self):
        logger.info(f"🛑 [StreamLoader] 收到停止指令: Cam {self.camera_id}")
        self.running = False  # 1. 关掉总开关
        
        # 更新数据库状态
        self._update_db_status(0)

        # 2. ⚡️ 暴力释放资源，打断阻塞
        with self.lock:
            if self.cap:
                try:
                    # 这里的 release 通常会让正在进行的 grab/retrieve 抛出异常或返回 False
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
                    # logger.info(f"📡 Cam {self.camera_id} Status -> {status}")
        except Exception as e:
            logger.error(f"❌ DB Update Error: {e}")

    def _connect(self):
        try:
            if self.cap: self.cap.release()
            
            # 🛑 核心修复 1：缩短超时时间
            # stimeout;5000000 -> 5秒超时 (之前是20秒，太久了)
            # max_delay;500000 -> 限制最大延迟 0.5秒
            # buffer_size;1024 -> 极小的缓冲区，迫使 ffmpeg 丢弃旧帧
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000|max_delay;500000|buffer_size;1024"
            
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
            # 🛑 每次循环开始都检查一下是否被 stop 了
            if not self.running:
                break

            try:
                # 响应看门狗
                if self.reconnect_requested:
                    self._update_db_status(0)
                    self._connect()
                    self.reconnect_requested = False
                    self.last_read_time = time.time()

                # 如果 cap 被 stop() 置空了，直接退出
                if not self.cap or not self.cap.isOpened():
                    if not self.running: break # 双重检查
                    time.sleep(2)
                    self._connect()
                    continue
                
                # 读取帧
                try:
                    grabbed = self.cap.grab() # 这里可能会短暂阻塞
                except Exception:
                    # 如果 stop() 强行 release 了，这里会报错，正好退出
                    break

                if not self.running: break # grab 完再查一次

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
                
                # 主动熔断机制 (保持不变)
                if self.consecutive_errors > 30:
                    logger.warning(f"⚡ Cam {self.camera_id} stream corruption detected! Force reconnecting...")
                    self.reconnect_requested = True
                    self.consecutive_errors = 0
                    time.sleep(0.5)

            except Exception as e:
                # 如果是我们要它停止的，就不报错
                if self.running:
                    logger.error(f"Reader loop error: {e}")
                time.sleep(1)
        
        logger.info(f"👋 Reader Thread Exited: Cam {self.camera_id}")

    def _watchdog_thread(self):
        """看门狗：监控 Reader 是否卡死 (最后的防线)"""
        while self.running:
            # 🛑 修改：从 6.0 改为 15.0
            # 给 AI 处理和报警录像留足时间，防止误杀
            if time.time() - self.last_read_time > 15.0:
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
        
        # 1. AI 推理
        detections = self.detector.detect(frame)
        persons = [d for d in detections if d['label'] == 'person']
        cigarettes = [d for d in detections if d['label'] == 'cigarette']
        
        # =========================================================
        # 2. 🟢 维护阶段：更新冷却圈位置 (让冷却圈跟着人走)
        # =========================================================
        # 构建当前帧人物 ID 映射表 {pid: box}
        current_pids = {p['id']: p['box'] for p in persons}
        
        keys_to_remove = []
        for key, record in self.active_cooldowns.items():
            # A. 检查时间是否过期
            if current_time - record['time'] > self.alarm_cooldown:
                keys_to_remove.append(key)
                continue
            
            # B. 如果是动态冷却 (绑定了 Person ID)，且这个人还在画面里 -> 更新坐标
            # key 就是 person_id (int 类型)
            if isinstance(key, int):
                if key in current_pids:
                    # 人还在，更新坐标到人的中心点
                    box = current_pids[key]
                    cx, cy = (box[0] + box[2])/2, (box[1] + box[3])/2
                    record['pos'] = (cx, cy)
                    record['last_seen'] = current_time # 刷新最后可见时间
                else:
                    # 人跟丢了，保持最后已知位置 (退化为静态冷却)
                    # 可选：如果跟丢太久，是否提前移除？这里暂时保持静态保护直到超时
                    pass

        # 清理过期记录
        for k in keys_to_remove: 
            del self.active_cooldowns[k]

        # =========================================================
        # 3. 🔴 判定阶段：检测烟头是否触发报警
        # =========================================================
        for cig in cigarettes:
            cid = cig['id']
            conf = cig['conf']
            cbox = cig['box']
            
            event = self.smoke_events[cid]
            event.last_seen_time = current_time
            event.frame_count += 1
            
            if event.frame_count >= self.alarm_threshold_frames:
                cig['is_alarm'] = True
                
                # 如果这个事件还没确认过，才进行冷却检查
                if not event.is_confirmed:
                    # 获取烟头中心坐标
                    c_cx = (cbox[0] + cbox[2]) / 2
                    c_cy = (cbox[1] + cbox[3]) / 2
                    
                    is_cooling_down = False
                    
                    # 检查是否落在任何一个“冷却圈”内
                    for record in self.active_cooldowns.values():
                        rx, ry = record['pos']
                        # 计算欧氏距离
                        dist = math.sqrt((c_cx - rx)**2 + (c_cy - ry)**2)
                        if dist < self.alarm_radius:
                            is_cooling_down = True
                            break # 命中冷却，跳过
                    
                    if not is_cooling_down:
                        # 🔥 触发新报警！
                        event.is_confirmed = True
                        
                        # 尝试找到烟头的主人
                        owner_id = self._match_person_id(cbox, persons)
                        
                        logger.warning(f"🔥 ALARM TRIGGERED: Cam {self.camera_id}")
                        self._trigger_alarm_save(frame, owner_id, conf, w, h)
                        
                        # ⭐ 核心：创建新的冷却记录
                        if owner_id is not None:
                            # 绑定到人 (动态冷却)
                            # key 使用 owner_id (int)，方便后续更新
                            self.active_cooldowns[owner_id] = {
                                'pos': (c_cx, c_cy), # 初始位置
                                'time': current_time,
                                'type': 'dynamic'
                            }
                        else:
                            # 没匹配到人 (静态冷却)
                            # key 使用随机字符串，这就不会被上面的 isinstance(key, int) 更新逻辑捕获
                            static_key = f"static_{time.time()}_{cid}"
                            self.active_cooldowns[static_key] = {
                                'pos': (c_cx, c_cy),
                                'time': current_time,
                                'type': 'static'
                            }
            else:
                cig['is_alarm'] = False

        # 清理过期的烟头追踪记录 (不是冷却记录，是 YOLO 烟头 ID 缓存)
        expired = [tid for tid, evt in self.smoke_events.items() if current_time - evt.last_seen_time > self.lost_timeout]
        for tid in expired: del self.smoke_events[tid]
        
        return detections

    def _trigger_alarm_save(self, frame, owner_id, conf, w, h):
        prefix = f"alarm_p{owner_id}" if owner_id else "alarm_unknown"
        ts = int(time.time())
        video_name = f"{prefix}_{ts}.mp4"
        
        # 开始录制视频
        video_path = self.recorder.start_recording(video_name, post_record_sec=5, width=w, height=h)
        
        # 保存截图
        img_name = f"{prefix}_{ts}.jpg"
        roi_path = self.recorder.save_snapshot(frame, img_name)
        
        # 🛑 关键修改：传递真实的 app 对象给子线程
        # 这里的 self.app 是在 __init__ 里传进来的 Flask app 实例
        if self.app:
            threading.Thread(
                target=self._save_alarm_to_db, 
                args=(self.app, conf, video_path, roi_path) # 👈 把 app 传过去
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

    # 🛑 关键修改：接收 app 参数，并手动推送上下文
    def _save_alarm_to_db(self, app, confidence, video_path, roi_path):
        try:
            # 必须使用 with app.app_context(): 才能在线程里操作 DB
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
            # 在上下文里回滚
            with app.app_context():
                db.session.rollback()
            logger.error(f"❌ DB Save Error: {e}")

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

# web-flask/app/core/stream_loader.py 底部

class StreamManager:
    def __init__(self):
        self.stream_loaders = {}
        self.app = None 
        self.lock = threading.Lock() # ✅ 新增锁，防止并发添加导致覆盖

    def init_app(self, app):
        self.app = app

    def add_camera(self, cid, url):
        with self.lock: # ✅ 加锁，防止多线程同时操作字典
            # 1. 检查是否存在旧实例
            if cid in self.stream_loaders:
                existing_loader = self.stream_loaders[cid]
                
                # 如果 URL 没变且正在运行，直接返回，别折腾
                if existing_loader.rtsp_url == url and existing_loader.running:
                    return True
                
                # 🛑 关键点：如果 URL 变了，或者实例是旧的，必须先杀掉旧线程！
                # 否则这个旧线程就会变成僵尸，一直拉流且无法被删除
                logger.info(f"🔄 [Manager] 替换旧实例: Cam {cid}")
                existing_loader.stop()
                del self.stream_loaders[cid] # 确保从字典移除
            
            # 2. 创建新实例
            l = StreamLoader(cid, url, self.app)
            if l.start(): 
                self.stream_loaders[cid] = l
                return True
            return False

    def get_latest_frame(self, cid):
        # 简单读取不需要锁，字典读取是原子的
        l = self.stream_loaders.get(cid)
        return l.get_latest_frame() if l else None

    def remove_camera(self, cid):
        with self.lock: # ✅ 加锁
            if cid in self.stream_loaders:
                logger.info(f"🗑️ [Manager] Removing Camera ID: {cid}")
                loader = self.stream_loaders[cid]
                loader.stop() # 杀线程
                del self.stream_loaders[cid] # 删引用
            else:
                logger.warning(f"⚠️ [Manager] 试图删除不存在的设备: {cid} (可能是僵尸线程)")

stream_manager = StreamManager()