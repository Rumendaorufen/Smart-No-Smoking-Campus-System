# web-flask/app/core/recorder.py

import cv2
import os
import time
import threading  # ✅ 必须导入这个
import subprocess # ✅ 用于调用 FFmpeg

class EvidenceRecorder:
    def __init__(self, save_dir="static/evidence", fps=25, pre_record_sec=2):
        self.save_dir = save_dir
        self.fps = fps
        self.pre_record_sec = pre_record_sec
        
        # 确保目录存在
        os.makedirs(save_dir, exist_ok=True)
        # 专门创建截图目录
        os.makedirs(os.path.join(save_dir, "snapshots"), exist_ok=True)
        
        # 环形缓冲区 (Pre-record)
        self.buffer = [] 
        self.max_buffer_size = fps * pre_record_sec
        
        # 录制状态
        self.is_recording = False
        self.writer = None
        self.current_video_path = None
        self.record_start_time = 0
        self.post_record_sec = 0
        
        # ✅✅✅ 关键修复：初始化锁
        self.lock = threading.Lock() 

    def add_frame(self, frame):
        """持续接收帧，用于预录制缓冲"""
        with self.lock:
            self.buffer.append(frame)
            if len(self.buffer) > self.max_buffer_size:
                self.buffer.pop(0)
            
            # 如果正在录制，直接写入文件
            if self.is_recording and self.writer:
                self.writer.write(frame)

    def start_recording(self, filename, post_record_sec=5, width=1280, height=720):
        """开始触发录像"""
        with self.lock:
            if self.is_recording:
                return self.current_video_path

            self.is_recording = True
            self.post_record_sec = post_record_sec
            self.record_start_time = time.time()
            
            # 完整路径
            self.current_video_path = os.path.join(self.save_dir, filename)
            
            # 初始化写入器
            # 注意：这里先用 mp4v 录制，结束后再转码，防止 OpenCV 兼容性问题
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.writer = cv2.VideoWriter(
                self.current_video_path, fourcc, self.fps, (width, height)
            )
            
            # 写入预录制的缓冲帧
            for f in self.buffer:
                self.writer.write(f)
                
            print(f"🎥 开始录制: {filename}")
            return self.current_video_path

    def process_recording(self, frame):
        """在主循环中调用，判断是否需要停止录制"""
        # 注意：这里不要加锁，因为 add_frame 已经处理了写入
        if self.is_recording:
            if time.time() - self.record_start_time > self.post_record_sec:
                self.stop_recording()

    def stop_recording(self):
        """停止录制并转码"""
        with self.lock:
            if not self.is_recording:
                return

            if self.writer:
                self.writer.release()
                self.writer = None
                
            self.is_recording = False
            temp_path = self.current_video_path
            print(f"🛑 录制结束: {temp_path}")

            # 🔥 FFmpeg 转码逻辑 (让浏览器能播放)
            # 浏览器通常只支持 H.264 (avc1) 编码，OpenCV 默认生成的可能无法播放
            try:
                # 构造输出文件名 (临时改名策略)
                path_no_ext = os.path.splitext(temp_path)[0]
                final_path = f"{path_no_ext}_h264.mp4"
                
                # ffmpeg 命令: 转为 h264 + aac
                cmd = f'ffmpeg -y -i "{temp_path}" -vcodec libx264 -acodec aac "{final_path}"'
                
                # 执行命令 (静默模式)
                subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # 如果转码成功，替换原文件
                if os.path.exists(final_path):
                    os.remove(temp_path) # 删掉旧的
                    os.rename(final_path, temp_path) # 把新的改名回来
                    print("✅ [FFmpeg] 视频转码成功，浏览器可播放")
                
            except Exception as e:
                print(f"⚠️ [FFmpeg] 转码失败 (可能未安装 ffmpeg)，视频可能黑屏: {e}")

            return self.current_video_path

    def save_snapshot(self, frame, filename):
        """保存特写截图到 snapshots 子目录"""
        # 图片存入子文件夹，避免和视频混在一起
        snapshot_dir = os.path.join(self.save_dir, "snapshots")
        save_path = os.path.join(snapshot_dir, filename)
        cv2.imwrite(save_path, frame)
        return save_path