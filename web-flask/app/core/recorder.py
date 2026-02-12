import cv2
import os
import time
import threading
import subprocess
import logging

logger = logging.getLogger(__name__)

class EvidenceRecorder:
    def __init__(self, save_dir="app/static/evidence", fps=25, pre_record_sec=2):
        self.save_dir = os.path.abspath(save_dir)
        self.fps = fps
        self.pre_record_sec = pre_record_sec
        
        os.makedirs(self.save_dir, exist_ok=True)
        os.makedirs(os.path.join(self.save_dir, "snapshots"), exist_ok=True)
        
        self.buffer = [] 
        self.max_buffer_size = fps * pre_record_sec
        
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
            # 1. 先进行物理对齐，确保存入缓冲区和写入文件的尺寸一致
            # 🚀 关键：如果 VideoWriter 是 640x480，每一帧都必须 resize 过去
            frame_resized = cv2.resize(frame, (self.target_w, self.target_h))
            
            self.buffer.append(frame_resized.copy())
            if len(self.buffer) > self.max_buffer_size:
                self.buffer.pop(0)
            
            # 2. 写入文件
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
            
            self.current_video_path = os.path.join(self.save_dir, filename)
            
            # 使用 mp4v 写入（它是 OpenCV 兼容性最好的本地写入器）
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.writer = cv2.VideoWriter(
                self.current_video_path, fourcc, self.fps, (self.target_w, self.target_h)
            )
            
            # 将缓冲区内的历史帧写入
            for f in self.buffer:
                # 再次确认尺寸一致性
                if f.shape[1] != self.target_w or f.shape[0] != self.target_h:
                    f = cv2.resize(f, (self.target_w, self.target_h))
                self.writer.write(f)
                
            logger.info(f"🎥 录制物理启动: {filename} ({width}x{height})")
            return self.current_video_path

    def process_recording(self, frame=None):
        """在 StreamLoader 的循环中被调用"""
        if self.is_recording:
            # 录制时长到了（当前时间 > 开始时间 + 持续时间）
            if time.time() - self.record_start_time > self.post_record_sec:
                logger.info("⏰ 录制时长已到，执行同步闭合...")
                self.stop_recording() # 🚀 改为同步调用，确保 release 先执行

    def stop_recording(self):
        """同步闭合文件并触发修复"""
        with self.lock:
            if not self.is_recording or self.writer is None:
                return
            
            # 1. 物理闭合（这一步最重要）
            self.writer.release()
            self.writer = None
            self.is_recording = False
            
        temp_path = self.current_video_path
        logger.info(f"🛑 [Physical Release] 文件已闭合: {os.path.basename(temp_path)}")

        # 2. 只有闭合成功了，才去启动转码（转码可以异步）
        if temp_path and os.path.exists(temp_path):
            t = threading.Thread(target=self._convert_to_h264, args=(temp_path,))
            t.daemon = True
            t.start()

    def _convert_to_h264(self, video_path):
        """
        使用 FFmpeg 强制重构 MP4 容器并修复索引
        -movflags +faststart 是解决“文件大小正常但打不开”的万能药
        """
        path_no_ext = os.path.splitext(video_path)[0]
        final_path = f"{path_no_ext}_ready.mp4"
        
        # 🚀 -pix_fmt yuv420p 是保证浏览器/Windows播放器能播放的关键
        cmd = [
            'ffmpeg', '-y', '-i', video_path,
            '-c:v', 'libx264', 
            '-pix_fmt', 'yuv420p', 
            '-movflags', '+faststart',
            '-preset', 'ultrafast',
            final_path
        ]
        
        try:
            # 增加 stderr=subprocess.STDOUT 来捕捉错误
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"FFmpeg 报错: {result.stdout}")
                return

            if os.path.exists(final_path):
                time.sleep(0.5)
                os.replace(final_path, video_path) 
                logger.info(f"✨ 视频转码与头修复完成")
        except Exception as e:
            logger.error(f"⚠️ 转码异常: {e}")

    def save_snapshot(self, frame, filename):
        if frame is None: return
        snapshot_dir = os.path.join(self.save_dir, "snapshots")
        save_path = os.path.join(snapshot_dir, filename)
        cv2.imwrite(save_path, frame)
        return save_path