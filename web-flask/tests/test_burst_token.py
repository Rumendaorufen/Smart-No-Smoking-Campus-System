import time
from app.core.burst_token import BurstTokenManager


def test_acquire_release():
    """测试令牌获取和归还。"""
    # 清理状态
    BurstTokenManager._active_bursts.clear()

    now = time.time()
    assert BurstTokenManager.acquire(1, now) is True
    assert BurstTokenManager.is_in_burst(1) is True
    assert BurstTokenManager.active_count() == 1

    BurstTokenManager.release(1)
    assert BurstTokenManager.is_in_burst(1) is False
    assert BurstTokenManager.active_count() == 0


def test_max_bursts():
    """测试超过 MAX_BURSTS 时返回 False（进入降级模式）。"""
    BurstTokenManager._active_bursts.clear()

    now = time.time()
    assert BurstTokenManager.acquire(1, now) is True
    assert BurstTokenManager.acquire(2, now) is True
    assert BurstTokenManager.acquire(3, now) is True
    # 第 4 路应被拒绝
    assert BurstTokenManager.acquire(4, now) is False
    # 弹性降级配置应正确返回
    config = BurstTokenManager.get_degraded_config()
    assert config['threshold'] == 0.85

    BurstTokenManager.release(1)
    BurstTokenManager.release(2)
    BurstTokenManager.release(3)


def test_timeout_reclaim():
    """测试超时后自动回收。"""
    BurstTokenManager._active_bursts.clear()

    # 模拟过去的时间（now + 9s 使 8s 超时触发）
    past = time.time() - 9
    BurstTokenManager.acquire(1, past)

    # 新时间戳应触发过期清理
    now = time.time()
    assert BurstTokenManager.acquire(2, now) is True
    # 第 1 路应该已被清理
    assert BurstTokenManager.is_in_burst(1) is False
    BurstTokenManager.release(2)


def test_degraded_config():
    """弹性降级配置。"""
    config = BurstTokenManager.get_degraded_config()
    assert config['fps'] == 5
    assert config['threshold'] == 0.85


def test_release_nonexistent():
    """释放不存在的令牌不应报错。"""
    BurstTokenManager._active_bursts.clear()
    # 不应抛出异常
    BurstTokenManager.release(999)
    assert BurstTokenManager.active_count() == 0
