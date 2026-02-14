from flask import Blueprint, Response, request, jsonify
import requests
import time
import cv2
import builtins
import logging
import threading

# 配置日志
logger = logging.getLogger(__name__)
monitor_bp = Blueprint('monitor', __name__)

# 全局内存缓存
device_config_cache = {}
# 🚀 增加：点火状态追踪，防止高频重复拉起线程
igniting_devices = set()
ignite_lock = threading.Lock()

def get_sm():
    """获取全局流管理器"""
    return getattr(builtins, 'GLOBAL_STREAM_MANAGER', None)

# 🚀 1. 核心同步逻辑：通过 Java 侧的 Internal 白名单接口同步
def _do_sync():
    global device_config_cache
    sm = get_sm()
    if not sm:
        logger.error("❌ StreamManager 尚未初始化")
        return False
    
    try:
        # 注意：这里访问的是你刚在 Java 侧 Exclude 放行的 internal 接口
        logger.info("📡 正在向 Java 侧同步设备列表 (Internal Channel)...")
        resp = requests.get("http://localhost:8080/api/internal/devices", timeout=3.0)
        
        if resp.status_code == 200:
            data_json = resp.json()
            devices = data_json.get('data', [])
            
            temp_cache = {}
            active_devices = {}
            
            for dev in devices:
                try:
                    d_id = int(dev.get('id', 0))
                    if d_id == 0: continue

                    url = dev.get('rtspUrl') or dev.get('rtsp_url')
                    is_enabled = str(dev.get('enabled')).lower() in ['true', '1', 'yes']

                    if not url: continue

                    temp_cache[d_id] = {"enabled": is_enabled, "url": url}
                    if is_enabled:
                        active_devices[d_id] = url
                    elif d_id in sm.stream_loaders:
                        sm.stream_loaders[d_id].stop()
                            
                except Exception as e:
                    logger.error(f"❌ 解析项失败: {dev}, Error: {e}")

            device_config_cache = temp_cache
            sm.update_active_streams(active_devices)
            logger.info(f"✅ 同步成功！当前缓存 ID 列表: {list(device_config_cache.keys())}")
            return True
        else:
            logger.error(f"❌ Java 接口同步失败，状态码: {resp.status_code}")
    except Exception as e:
        logger.error(f"💥 同步过程异常: {e}")
    
    return False

def local_frame_generator(device_id):
    """视频流生成器"""
    sm = get_sm()
    while True:
        loader = sm.stream_loaders.get(device_id) if sm else None
        if not loader or not loader.running:
            logger.warning(f"🛑 [ID:{device_id}] 生成器退出")
            break
        
        frame = loader.get_latest_frame()
        if frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        else:
            time.sleep(0.1)
        time.sleep(0.04)

@monitor_bp.route('/sync', methods=['POST'])
def sync_api():
    if _do_sync():
        return jsonify({"code": 200, "msg": "Sync Success"})
    return jsonify({"code": 500, "msg": "Sync Failed"}), 500

@monitor_bp.route('/stream/<int:device_id>') 
def video_feed(device_id):
    sm = get_sm()
    if not sm: return "Stream Manager Offline", 503

    # 1. 自动同步
    if device_id not in device_config_cache:
        _do_sync()

    config = device_config_cache.get(device_id)
    if not config:
        return "Device Not Found", 404
    if not config.get('enabled'):
        return "Device Disabled", 403

    loader = sm.stream_loaders.get(device_id)
    
    # 🚀 2. 增强型点火判定：如果流没在跑，且没有正在尝试开启
    if not loader or not loader.running or loader.latest_frame is None:
        
        with ignite_lock:
            if device_id not in igniting_devices:
                igniting_devices.add(device_id)
                logger.info(f"🔥 [首次点火] ID:{device_id}，地址: {config['url']}")
                
                # 定义点火包装函数
                def wrapped_ignite(d_id, url):
                    try:
                        # 调用真实的 AI 加载逻辑
                        sm.add_camera(d_id, url)
                    finally:
                        # 无论成功失败，进入 10 秒冷却期，防止前端刷爆后端线程
                        def cooldown():
                            with ignite_lock:
                                igniting_devices.discard(d_id)
                                logger.info(f"❄️ [冷却结束] ID:{d_id} 允许重新尝试点火")
                        
                        threading.Timer(10, cooldown).start()

                threading.Thread(target=wrapped_ignite, args=(device_id, config['url']), daemon=True).start()
            else:
                # 记录但不重复开启线程
                logger.debug(f"⏳ ID:{device_id} 正在尝试连接中，跳过重复点火...")

        # 返回 404 触发前端 Monitor.vue 的 3 秒防抖重试
        return "Stream Loading", 404

    # 3. 正常输出流
    return Response(
        local_frame_generator(device_id), 
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )