"""
全局 I/O 限流管理器。

限制并发写盘操作数，防止多路同时录像挤死 SSD。
"""

import threading
import subprocess
import logging
import shutil

logger = logging.getLogger(__name__)

# 🚀 启动时检测 FFmpeg 是否可用
_FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None
if not _FFMPEG_AVAILABLE:
    logger.error("❌ FFmpeg 未安装！视频录制无法工作。")
    logger.error("   下载: https://ffmpeg.org/download.html")
    logger.error("   或管理员 PowerShell: winget install ffmpeg")


class IOThrottle:
    """
    写盘限流令牌桶。
    - max_concurrent: 最大并发写盘数（默认 2）
    - 提供 run_ffmpeg 包装方法自动管理
    """

    _semaphore = threading.Semaphore(2)
    _active_pids: set[int] = set()
    _lock = threading.Lock()

    @classmethod
    def acquire(cls) -> bool:
        """获取写盘令牌。阻塞直到有可用槽位。"""
        acquired = cls._semaphore.acquire(blocking=True, timeout=30)
        if acquired:
            logger.debug(f"IO 令牌获取成功 (活跃: {cls.active_count()})")
        else:
            logger.error("IO 令牌等待超时 (30s)")
        return acquired

    @classmethod
    def release(cls):
        """归还写盘令牌。"""
        cls._semaphore.release()

    @classmethod
    def active_count(cls) -> int:
        with cls._lock:
            return len(cls._active_pids)

    @classmethod
    def run_ffmpeg(cls, cmd: list, timeout: int = 30) -> bool:
        """
        带限流和超时的 FFmpeg 执行包装。

        1. 检查 FFmpeg 是否可用
        2. 获取写盘令牌
        3. 设置 Windows Below Normal 优先级
        4. 启动进程并在超时后强制终止
        """
        if not _FFMPEG_AVAILABLE:
            logger.error("FFmpeg 未安装，跳过录像")
            return False
        if not cls.acquire():
            return False

        process = None
        try:
            CREATE_BELOW_NORMAL = 0x00004000
            process = subprocess.Popen(
                cmd,
                creationflags=CREATE_BELOW_NORMAL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            with cls._lock:
                cls._active_pids.add(process.pid)

            process.wait(timeout=timeout)
            if process.returncode != 0:
                err = process.stderr.read().decode('utf-8', errors='replace') if process.stderr else ''
                logger.error(f"FFmpeg 失败 (rc={process.returncode}): {err[:2000]}")
            return process.returncode == 0

        except subprocess.TimeoutExpired:
            logger.warning(f"FFmpeg 超时 ({timeout}s)，强制终止 PID={process.pid}")
            if process:
                try:
                    subprocess.run(
                        ['taskkill', '/F', '/T', '/PID', str(process.pid)],
                        capture_output=True
                    )
                except Exception as e:
                    logger.error(f"终止失败: {e}")
            return False

        except Exception as e:
            logger.error(f"FFmpeg 异常: {e}")
            return False

        finally:
            if process:
                with cls._lock:
                    cls._active_pids.discard(process.pid)
            cls.release()
