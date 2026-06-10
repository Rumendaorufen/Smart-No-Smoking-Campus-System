import cv2
import os
import time
import threading
import subprocess
import logging
import shutil
from collections import deque

logger = logging.getLogger(__name__)

class EvidenceRecorder:
    # 🚀 缓冲超时：队首帧超过此阈值则清空，防止时空错乱
    BUFFER_FLUSH_TIMEOUT = 2.5

    def __init__(self, save_dir="app/static/evidence", fps=25, pre_record_sec=2,
                 ram_disk_dir="R:/evidence"):
        self.save_dir = os.path.abspath(save_dir)        # SSD 长期存储
        self.fps = fps
        self.pre_record_sec = pre_record_sec

        os.makedirs(self.save_dir, exist_ok=True)
        os.makedirs(os.path.join(self.save_dir, "snapshots"), exist_ok=True)

        # 🚀 检测 RAM 盘是否存在，不存在则回退到 SSD
        self.ram_disk_dir = ram_disk_dir
        if os.path.exists("R:\\"):
            os.makedirs(self.ram_disk_dir, exist_ok=True)
            os.makedirs(os.path.join(self.ram_disk_dir, "snapshots"), exist_ok=True)
            logger.info("💾 使用 ImDisk 内存盘: %s", self.ram_disk_dir)
        else:
            self.ram_disk_dir = self.save_dir
            logger.info("💾 内存盘不可用，回退到 SSD: %s", self.save_dir)

        # 🚀 改用 deque(maxlen=10)，每帧带时间戳
        self.buffer = deque(maxlen=10)  # type: deque[tuple[float, cv2.Mat]]

        self.is_recording = False
        self.writer = None
        self.current_video_path = None
        self.record_start_time = 0
        self.post_record_sec = 0
        
        # 🚀 初始锚点（必须与 VideoWriter 一致）
        self.target_w = 640
        self.target_h = 480
        
        self.lock = threading.Lock() 

    def add_frame(self, frame):
        if frame is None: return

        with self.lock:
            frame_resized = cv2.resize(frame, (self.target_w, self.target_h))
            now = time.time()

            # 🚀 2.5s 超时清空：如果队首帧时间戳太旧，说明发生了卡顿或断流
            if self.buffer and (now - self.buffer[0][0]) > EvidenceRecorder.BUFFER_FLUSH_TIMEOUT:
                self.buffer.clear()
                logger.warning("🧹 Buffer 超时清空：防止时空错乱")

            self.buffer.append((now, frame_resized.copy()))

            if self.is_recording and self.writer:
                try:
                    self.writer.write(frame_resized)
                except Exception as e:
                    logger.error(f"写入视频帧失败: {e}")

    def add_frame_no_detect(self, frame):
        """Processor 跳过推理时仍将帧写入 buffer（保证录像连贯性）"""
        if frame is None: return
        with self.lock:
            frame_resized = cv2.resize(frame, (self.target_w, self.target_h))
            now = time.time()
            if self.buffer and (now - self.buffer[0][0]) > EvidenceRecorder.BUFFER_FLUSH_TIMEOUT:
                self.buffer.clear()
            self.buffer.append((now, frame_resized.copy()))
            if self.is_recording and self.writer:
                try:
                    self.writer.write(frame_resized)
                except Exception as e:
                    logger.error(f"写入视频帧失败: {e}")

    def start_recording(self, filename, post_record_sec=5, width=640, height=480):
        with self.lock:
            if self.is_recording:
                return self.current_video_path

            # 🚀 记录本次录像的法定尺寸
            self.target_w = width
            self.target_h = height
            self.is_recording = True
            self.post_record_sec = post_record_sec
            self.record_start_time = time.time()
            
            # 🚀 路径指向内存盘
            self.current_video_path = os.path.join(self.ram_disk_dir, filename)
            
            # 使用 mp4v 写入（它是 OpenCV 兼容性最好的本地写入器）
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.writer = cv2.VideoWriter(
                self.current_video_path, fourcc, self.fps, (self.target_w, self.target_h)
            )
            
            # 🚀 从 deque 取出历史帧作为视频开头（证据拼接）
            for ts, f in self.buffer:
                if f.shape[1] != self.target_w or f.shape[0] != self.target_h:
                    f = cv2.resize(f, (self.target_w, self.target_h))
                self.writer.write(f)

            logger.info(f"🎥 录制物理启动: {filename} ({width}x{height}), 含 {len(self.buffer)} 帧历史")
            return self.current_video_path

    def process_recording(self, frame=None):
        """在 StreamLoader 的循环中被调用"""
        if self.is_recording:
            # 录制时长到了（当前时间 > 开始时间 + 持续时间）
            if time.time() - self.record_start_time > self.post_record_sec:
                logger.info("⏰ 录制时长已到，执行同步闭合...")
                self.stop_recording() # 🚀 改为同步调用，确保 release 先执行

    def stop_recording(self):
        with self.lock:
            if not self.is_recording or self.writer is None:
                return
            ram_path = self.current_video_path
            self.writer.release()
            self.writer = None
            self.is_recording = False
        if ram_path and self.ram_disk_dir != self.save_dir:
            ssd_path = self.move_to_persistent(ram_path)
            logger.info(f"🎥 录像完成: {os.path.basename(ssd_path)}")
        else:
            logger.info(f"🛑 录制闭合: {os.path.basename(ram_path)}")

    def save_snapshot(self, frame, filename):
        if frame is None: return
        snapshot_dir = os.path.join(self.ram_disk_dir, "snapshots")
        save_path = os.path.join(snapshot_dir, filename)
        cv2.imwrite(save_path, frame)
        return save_path

    def move_to_persistent(self, ram_path: str) -> str:
        """确诊报警后，将证据从内存盘 COPY 到 SSD（跨盘不能用 os.replace）。"""
        if not ram_path or not os.path.exists(ram_path):
            return ram_path
        rel_path = os.path.relpath(ram_path, self.ram_disk_dir)
        persistent_path = os.path.join(self.save_dir, rel_path)
        os.makedirs(os.path.dirname(persistent_path), exist_ok=True)
        # 🚀 shutil.copy2 支持跨磁盘复制
        shutil.copy2(ram_path, persistent_path)
        os.remove(ram_path)
        logger.info(f"📦 证据移至 SSD: {persistent_path}")
        return persistent_path