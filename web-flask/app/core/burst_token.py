"""
全局爆发令牌桶（Global Burst Token Bucket）。

允许最多 MAX_BURSTS 路摄像头同时处于 25fps 全帧推理状态。
满员时后续触发者不排队，而是弹性降级（中帧率 + 高阈值）。
"""

import threading
import time
import logging

logger = logging.getLogger(__name__)


class BurstTokenManager:
    _lock = threading.Lock()
    MAX_BURSTS = 3                     # 最大并发爆发数
    HARD_TIMEOUT = 8.0                 # 每路爆发硬超时（秒）
    _active_bursts: dict[int, float] = {}  # camera_id -> start_time

    # 弹性降级配置
    DEGRADED_FPS = 5                    # 降级后的推理帧率目标
    DEGRADED_THRESHOLD = 0.85           # 降级后的报警阈值

    @classmethod
    def acquire(cls, camera_id: int, now: float) -> bool:
        """尝试获取爆发令牌。成功返回 True，失败表示进入弹性降级模式。"""
        with cls._lock:
            # 清理过期令牌
            expired = [
                cid for cid, start in cls._active_bursts.items()
                if now - start > cls.HARD_TIMEOUT
            ]
            for cid in expired:
                logger.info(f"⏰ 强制回收令牌 CID={cid}（超时）")
                del cls._active_bursts[cid]

            if len(cls._active_bursts) < cls.MAX_BURSTS:
                cls._active_bursts[camera_id] = now
                return True

            logger.warning(
                f"⚠️ 令牌桶已满 ({cls.MAX_BURSTS})，CID={camera_id} 进入弹性降级模式 "
                f"(阈值 {cls.DEGRADED_THRESHOLD})"
            )
            return False

    @classmethod
    def release(cls, camera_id: int):
        """主动归还爆发令牌。"""
        with cls._lock:
            if camera_id in cls._active_bursts:
                del cls._active_bursts[camera_id]
                logger.info(f"♻️ 令牌归还 CID={camera_id}，剩余爆发: {len(cls._active_bursts)}")

    @classmethod
    def is_in_burst(cls, camera_id: int) -> bool:
        """检查某路是否持有爆发令牌。"""
        with cls._lock:
            return camera_id in cls._active_bursts

    @classmethod
    def active_count(cls) -> int:
        """当前爆发路数。"""
        with cls._lock:
            return len(cls._active_bursts)

    @classmethod
    def get_degraded_config(cls) -> dict:
        """弹性降级配置（供 Processor 在无令牌时使用）。"""
        return {
            "fps": cls.DEGRADED_FPS,
            "threshold": cls.DEGRADED_THRESHOLD,
        }
