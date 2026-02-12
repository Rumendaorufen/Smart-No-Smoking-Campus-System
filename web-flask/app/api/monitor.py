from flask import Blueprint, Response, request, jsonify
import requests
import time
import cv2
import builtins
import logging
import threading

logger = logging.getLogger(__name__)
monitor_bp = Blueprint('monitor', __name__)
device_config_cache = {}

def get_sm():
    return getattr(builtins, 'GLOBAL_STREAM_MANAGER', None)

def local_frame_generator(device_id):
    sm = get_sm()
    while True:
        loader = sm.stream_loaders.get(device_id) if sm else None
        if not loader or not loader.running: break
        frame = loader.get_latest_frame()
        if frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        else: time.sleep(0.1)
        time.sleep(0.04)

@monitor_bp.route('/sync', methods=['POST'])
def sync_devices():
    sm = get_sm()
    global device_config_cache
    if not sm: return jsonify({"code": 500}), 500
    try:
        resp = requests.get("http://localhost:8080/api/monitor/devices", timeout=5)
        if resp.status_code == 200:
            devices, active_devices = resp.json().get('data', []), {}
            for dev in devices:
                d_id = int(dev['id'])
                is_enabled = dev.get('enabled') in [True, 1, "true", "True"]
                url = dev.get('rtspUrl') or dev.get('rtsp_url')
                device_config_cache[d_id] = {"enabled": is_enabled, "url": url}
                if is_enabled: active_devices[d_id] = url
                elif d_id in sm.stream_loaders: sm.stream_loaders[d_id].stop()
            sm.update_active_streams(active_devices)
            return jsonify({"code": 200})
    except: return jsonify({"code": 500}), 500

@monitor_bp.route('/stream/<int:device_id>') 
def video_feed(device_id):
    sm = get_sm()
    config = device_config_cache.get(device_id)
    if not config or not config.get('enabled'):
        sync_devices()
        config = device_config_cache.get(device_id)

    if not config or not config.get('enabled'): return "Disabled", 403

    loader = sm.stream_loaders.get(device_id)
    # 🚀 判定逻辑：如果没在跑，或者还没有拿到像素帧
    if not loader or not loader.running or loader.latest_frame is None:
        logger.info(f"🔥 [点火确认] ID:{device_id}")
        # 🚀 必须异步拉起，防止阻塞 Flask 响应
        threading.Thread(target=sm.add_camera, args=(device_id, config['url']), daemon=True).start()
        
        # 🚀 自旋等待：最多等 5 秒，直到后台线程成功 read() 到像素
        start_wait = time.time()
        while time.time() - start_wait < 5.0:
            loader = sm.stream_loaders.get(device_id)
            if loader and loader.latest_frame is not None:
                logger.info(f"✨ [就绪] ID:{device_id} 耗时 {round(time.time()-start_wait, 2)}s")
                break
            time.sleep(0.3)

    loader = sm.stream_loaders.get(device_id)
    if loader and loader.latest_frame is not None:
        return Response(local_frame_generator(device_id), mimetype='multipart/x-mixed-replace; boundary=frame')
    
    return "Stream Pending", 404