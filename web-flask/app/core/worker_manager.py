"""
实验性的多进程 Worker 管理器（当前启动链路未启用）。

当前生产入口 ``run.py`` 只运行全局 ``StreamManager``。本模块保留用于
后续完成动态设备分片、Worker 帧处理和主进程 API 路由后的架构演进，
不得与当前 ``StreamManager`` 同时启动，否则会产生重复拉流和报警。

启动时根据 GPU 和 camera 总量，将摄像头分片到多个 Worker 进程。

⚠️ Windows spawn 安全：
- _spawn_worker 必须为模块级函数（不可作为实例方法），否则 pickle 会失败。
- WorkerManager 初始化必须在 if __name__ == '__main__' 块内，绝不能放在
  create_app() 中，否则子进程会递归衍生孙子进程。
"""

import multiprocessing
import os
import threading
import logging
import time
from typing import List

logger = logging.getLogger(__name__)


def _spawn_worker(worker_id: int, camera_ids: list[int],
                  gpu_device: str, alarm_queue: multiprocessing.Queue):
    """
    模块级 Worker 启动函数（Windows spawn 兼容）。

    Windows 的 spawn 模式下，multiprocessing.Process 的目标函数必须是
    可 pickle 的模块级函数。实例方法因含 unpicklable 的 Process 引用
    会导致序列化崩溃。
    """
    os.environ["CUDA_VISIBLE_DEVICES"] = gpu_device
    from app.core.worker_main import worker_main
    worker_main(worker_id, camera_ids, gpu_device, alarm_queue)


class WorkerManager:
    def __init__(self, camera_count: int = 200,
                 workers_per_gpu: int = 4,
                 gpu_devices: List[str] = None):
        self.camera_count = camera_count
        self.workers_per_gpu = workers_per_gpu
        self.gpu_devices = gpu_devices or ["0"]
        self.workers: List[multiprocessing.Process] = []
        self.alarm_queue = multiprocessing.Queue(maxsize=1000)

    def start(self):
        total_workers = self.workers_per_gpu * len(self.gpu_devices)
        cams_per_worker = max(1, self.camera_count // total_workers)

        for wi in range(total_workers):
            gpu_idx = wi // self.workers_per_gpu
            gpu_dev = self.gpu_devices[gpu_idx]
            start_id = wi * cams_per_worker + 1
            end_id = min((wi + 1) * cams_per_worker + 1, self.camera_count + 1)
            assigned_ids = list(range(start_id, end_id))

            p = multiprocessing.Process(
                target=_spawn_worker,
                args=(wi, assigned_ids, gpu_dev, self.alarm_queue),
                daemon=True
            )
            p.start()
            self.workers.append(p)
            logger.info(f"Worker[{wi}] 已启动: GPU={gpu_dev}, cameras={len(assigned_ids)}路")

        self._start_alarm_consumer()

    def _start_alarm_consumer(self):
        def consumer():
            import requests
            while True:
                try:
                    alarm = self.alarm_queue.get(timeout=1)
                    requests.post(
                        "http://localhost:8080/api/alerts/report",
                        json=alarm,
                        timeout=3
                    )
                except Exception:
                    pass
        t = threading.Thread(target=consumer, daemon=True)
        t.start()

    def stop(self):
        for p in self.workers:
            if p.is_alive():
                p.terminate()
                p.join(timeout=5)
        logger.info("所有 Worker 已终止")
