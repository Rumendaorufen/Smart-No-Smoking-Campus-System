from flask import Blueprint, Response, request, jsonify
import requests
import time
import cv2
import builtins
import logging
import threading

logger = logging.getLogger(__name__)
monitor_bp = Blueprint('monitor', __name__)

# 内存缓存设备配置
device_config_cache = {}

def get_sm():
    return getattr(builtins, 'GLOBAL_STREAM_MANAGER', None)

# 🚀 1. 核心同步逻辑：改为请求 Java 的 internal 白名单接口
def _do_sync():
    sm = get_sm()
    global device_config_cache
    if not sm:
        logger.error("❌ Manager 尚未准备就绪")
        return False
    
    try:
        # 🚀 指向 Java 新开辟的 internal 接口，无需 Token
        logger.info("📡 正在向 Java 侧同步设备列表 (Internal Channel)...")
        resp = requests.get(
            "http://localhost:8080/api/internal/devices", 
            timeout=5
        )
        
        if resp.status_code == 200:
            devices = resp.json().get('data', [])
            active_devices = {}
            temp_cache = {}
            
            for dev in devices:
                try:
                    d_id = int(dev['id'])
                    # 兼容布尔判定
                    is_enabled = str(dev.get('enabled')).lower() in ['true', '1', 'yes']
                    url = dev.get('rtspUrl') or dev.get('rtsp_url')
                    
                    if not url: continue

                    temp_cache[d_id] = {"enabled": is_enabled, "url": url}
                    
                    if is_enabled:
                        active_devices[d_id] = url
                    elif d_id in sm.stream_loaders:
                        sm.stream_loaders[d_id].stop()
                except Exception as e:
                    logger.error(f"❌ 解析设备项失败: {dev}, {e}")
            
            # 原子更新缓存
            device_config_cache = temp_cache
            sm.update_active_streams(active_devices)
            logger.info(f"✅ 同步成功！当前缓存设备 ID: {list(device_config_cache.keys())}")
            return True
        else:
            # 如果这里还报 401，说明 Java 的 WebMvcConfig 排除路径没写对
            logger.error(f"❌ Java 同步失败，状态码: {resp.status_code}")
    except Exception as e:
        logger.error(f"💥 同步异常: {str(e)}")
    
    return False

def local_frame_generator(device_id):
    sm = get_sm()
    while True:
        loader = sm.stream_loaders.get(device_id) if sm else None
        if not loader or not loader.running:
            break
        frame = loader.get_latest_frame()
        if frame is not None:
            # 限制 JPEG 质量以节省带宽
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        else:
            time.sleep(0.1)
        time.sleep(0.04)

# 2. 同步 API 路由
@monitor_bp.route('/sync', methods=['POST'])
def sync_devices_api():
    if _do_sync():
        return jsonify({"code": 200, "msg": "Sync Success"})
    return jsonify({"code": 500, "msg": "Sync Failed"}), 500

# 3. 主视频流路由
@monitor_bp.route('/stream/<int:device_id>') 
def video_feed(device_id):
    sm = get_sm()
    if not sm: return "Manager Offline", 503

    # 检查缓存是否存在，不存在则同步
    if device_id not in device_config_cache:
        logger.warning(f"🔍 缓存未命中 ID:{device_id}，执行内部同步...")
        _do_sync()

    config = device_config_cache.get(device_id)

    if not config:
        return "Device Not Found", 404

    if not config.get('enabled'):
        return "Disabled", 403

    loader = sm.stream_loaders.get(device_id)
    
    # 点火逻辑
    if not loader or not loader.running or loader.latest_frame is None:
        logger.info(f"🔥 [准备点火] ID:{device_id}")
        threading.Thread(target=sm.add_camera, args=(device_id, config['url']), daemon=True).start()
        
        # 返回 404 触发前端 Monitor.vue 的 3 秒防抖重试逻辑
        return "Waiting for frames", 404

    # 正常推流
    return Response(
        local_frame_generator(device_id), 
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )