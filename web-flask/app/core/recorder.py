# 证据视频合成  web-flask\app\core\recorder.py
import cv2
import os
import logging
from collections import deque

logger = logging.getLogger(__name__)

class EvidenceRecorder:
    def __init__(self, save_dir="../static/evidence", fps=25, pre_record_sec=2):
        self.save_dir = save_dir
        self.fps = fps
        self.buffer = deque(maxlen=fps * pre_record_sec) # 环形缓冲
        self.writer = None
        self.recording_frames_left = 0 # 剩余要录制的帧数
        self.current_file_path = None
        
        os.makedirs(save_dir, exist_ok=True)
        os.makedirs(os.path.join(save_dir, "snapshots"), exist_ok=True)

    def add_frame(self, frame):
        """每帧都调用：存入缓冲"""
        self.buffer.append(frame)

    def start_recording(self, filename, post_record_sec=3, width=640, height=360):
        """触发报警时调用"""
        if self.writer is not None:
            return None # 正在录制中，忽略

        full_path = os.path.join(self.save_dir, filename)
        self.current_file_path = full_path
        
        # 初始化写入器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(full_path, fourcc, self.fps, (width, height))
        
        # 1. 立即写入缓冲区里的“过去”画面
        for f in self.buffer:
            self.writer.write(f)
            
        # 2. 设置还要录多少帧（未来画面）
        self.recording_frames_left = self.fps * post_record_sec
        
        return full_path

    def process_recording(self, frame):
        """每帧调用：如果正在录制，就写入文件"""
        if self.writer and self.recording_frames_left > 0:
            self.writer.write(frame)
            self.recording_frames_left -= 1
            
            if self.recording_frames_left <= 0:
                self.stop_recording()
                return True # 表示录制刚刚完成
        return False

    def stop_recording(self):
        if self.writer:
            self.writer.release()
            self.writer = None
            logger.info(f"🎥 Video saved: {self.current_file_path}")

    def save_snapshot(self, frame, filename):
        path = os.path.join(self.save_dir, "snapshots", filename)
        cv2.imwrite(path, frame)
        # 返回用于存储数据库的路径 (相对路径)
        return f"static/evidence/snapshots/{filename}"
