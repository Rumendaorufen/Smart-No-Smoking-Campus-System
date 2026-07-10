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

        # 🚀 多路并发录像：filename -> RecordingState
        self.recordings: dict[str, dict] = {}

        # 🚀 初始锚点
        self.target_w = 640
        self.target_h = 480

        self.lock = threading.Lock()

    def _write_to_active_recordings(self, frame_resized):
        """写入所有进行中的录像，检查超时自动闭合。"""
        expired = []
        for name, rec in self.recordings.items():
            try:
                rec['writer'].write(frame_resized)
            except Exception as e:
                logger.error(f"写入 {name} 失败: {e}")
                expired.append(name)
                continue
            if time.time() - rec['start_time'] > rec['post_sec']:
                expired.append(name)
        for name in expired:
            self._finalize_recording(name)

    def add_frame(self, frame):
        if frame is None: return
        with self.lock:
            frame_resized = cv2.resize(frame, (self.target_w, self.target_h))
            now = time.time()
            if self.buffer and (now - self.buffer[0][0]) > EvidenceRecorder.BUFFER_FLUSH_TIMEOUT:
                self.buffer.clear()
                logger.warning("🧹 Buffer 超时清空：防止时空错乱")
            self.buffer.append((now, frame_resized.copy()))
            self._write_to_active_recordings(frame_resized)

    def add_frame_no_detect(self, frame):
        if frame is None: return
        with self.lock:
            frame_resized = cv2.resize(frame, (self.target_w, self.target_h))
            now = time.time()
            if self.buffer and (now - self.buffer[0][0]) > EvidenceRecorder.BUFFER_FLUSH_TIMEOUT:
                self.buffer.clear()
            self.buffer.append((now, frame_resized.copy()))
            self._write_to_active_recordings(frame_resized)

    def start_recording(self, filename, post_record_sec=5, width=640, height=480):
        with self.lock:
            if filename in self.recordings:
                return self.recordings[filename]['path']

            video_path = os.path.join(self.ram_disk_dir, filename)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(video_path, fourcc, self.fps, (self.target_w, self.target_h))

            # 写入缓冲历史帧
            for ts, f in self.buffer:
                if f.shape[1] != self.target_w or f.shape[0] != self.target_h:
                    f = cv2.resize(f, (self.target_w, self.target_h))
                writer.write(f)

            self.recordings[filename] = {
                'writer': writer,
                'path': video_path,
                'start_time': time.time(),
                'post_sec': post_record_sec,
            }
            logger.info(f"🎥 录像启动: {filename} ({len(self.recordings)} 路并发)")
            return video_path

    def _finalize_recording(self, filename):
        """关闭录像文件，迁移到 SSD，重编码为 H264。"""
        rec = self.recordings.pop(filename, None)
        if not rec:
            return
        source_path = rec['path']
        try:
            rec['writer'].release()
        except Exception as e:
            logger.error(f"释放录像 {filename} 异常: {e}")
            return

        # RAM 盘模式先迁移到 SSD；SSD 回退模式直接使用原文件。
        final_path = source_path
        if (source_path and self.ram_disk_dir != self.save_dir
                and os.path.exists(source_path)):
            final_path = self.move_to_persistent(source_path)

        if not final_path or not os.path.exists(final_path):
            logger.error(f"录像文件不存在，无法转码: {final_path}")
            return

        # 两种存储模式都统一转为浏览器兼容的 H264。
        h264_path = final_path.replace('.mp4', '_h264.mp4')
        cmd = [
            'ffmpeg', '-y', '-i', final_path,
            '-c:v', 'libx264', '-preset', 'superfast',
            '-pix_fmt', 'yuv420p',
            '-an', h264_path
        ]
        try:
            result = subprocess.run(cmd, timeout=30, capture_output=True)
            if result.returncode == 0 and os.path.exists(h264_path):
                os.replace(h264_path, final_path)
                logger.info(f"🎥 录像完成 (H264): {os.path.basename(final_path)}")
            else:
                if os.path.exists(h264_path):
                    os.remove(h264_path)
                logger.warning(f"H264 编码失败，保留原文件: {final_path}")
        except Exception as e:
            if os.path.exists(h264_path):
                os.remove(h264_path)
            logger.error(f"FFmpeg 重编码异常，保留原文件: {e}")

    def process_recording(self, frame=None):
        """由 Processor 线程定期调用，检查超时。"""
        with self.lock:
            expired = [name for name, rec in self.recordings.items()
                       if time.time() - rec['start_time'] > rec['post_sec']]
        for name in expired:
            self._finalize_recording(name)

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
