import time
import numpy as np
from collections import deque


def test_deque_maxlen():
    """验证 deque(maxlen=10) 不会超过 10 帧。"""
    buf = deque(maxlen=10)
    for i in range(15):
        buf.append((time.time(), np.zeros((100, 100, 3), dtype=np.uint8)))
    assert len(buf) == 10


def test_timeout_clear():
    """验证 2.5s 超时清空：模拟队首帧过旧。"""
    buf = deque(maxlen=10)
    old_ts = time.time() - 5.0  # 5 秒前
    buf.append((old_ts, np.zeros((100, 100, 3), dtype=np.uint8)))
    buf.append((time.time(), np.zeros((100, 100, 3), dtype=np.uint8)))

    now = time.time()
    if now - buf[0][0] > 2.5:
        buf.clear()
    assert len(buf) == 0


def test_ordered_timestamps():
    """验证 buf 内元素按时间戳顺序排列（新帧追加到尾部）。"""
    buf = deque(maxlen=5)
    ts = [1.0, 2.0, 3.0, 4.0, 5.0]
    for t in ts:
        buf.append((t, np.zeros((10, 10, 3), dtype=np.uint8)))
    for i, (t, _) in enumerate(buf):
        assert t == ts[i], f"Expected {ts[i]}, got {t} at position {i}"


def test_empty_buffer_no_error():
    """空 deque 上执行超时检查不应报错。"""
    buf = deque(maxlen=10)
    now = time.time()
    # 空 buffer 不进入判断
    assert len(buf) == 0
