"""
Worker 子进程入口。

每个 Worker 拥有独立的：
- StreamManager + SmokingDetector
- GPU 绑定 (CUDA_VISIBLE_DEVICES)
- camera_id 分片
"""

import os
import time
import multiprocessing
import builtins


def worker_main(worker_id: int, camera_ids: list[int],
                gpu_device: str, alarm_queue: multiprocessing.Queue):
    """
    Worker 子进程主函数。

    🚀 Worker 为纯推理进程，不发起任何 HTTP 网络请求。
    所有报警事件通过 alarm_queue 上报给 Master 统一转发。
    """
    os.environ["CUDA_VISIBLE_DEVICES"] = gpu_device

    # 延迟导入（确保 GPU 绑定后才初始化 PyTorch/YOLO）
    from app.core.stream_loader import StreamManager

    sm = StreamManager()
    builtins.GLOBAL_STREAM_MANAGER = sm

    # 通知 StreamLoader 使用 alarm_queue 而非直接 HTTP 上报
    sm.alarm_queue = alarm_queue

    # 持续运行
    while True:
        time.sleep(1)
