# web-flask/app/api/monitor.py

from flask import Blueprint, Response, request, jsonify
import requests
import time
import cv2
import builtins

monitor_bp = Blueprint('monitor', __name__)

def get_sm():
    # 强制从全局内置空间获取单例
    return getattr(builtins, 'GLOBAL_STREAM_MANAGER', None)

def local_frame_generator(device_id):
    sm = get_sm()
    print(f"📺 [Thread] 开始为 {device_id} 推流...")
    while True:
        frame = sm.get_latest_frame(device_id) if sm else None
        if frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        else:
            time.sleep(0.1)
        time.sleep(0.04)

@monitor_bp.route('/stream/<int:device_id>') 
def video_feed(device_id):
    sm = get_sm()
    
    # 1. 核心补救：如果内存里没这个设备，当场启动它！
    if sm and device_id not in sm.stream_loaders:
        print(f"🛠️ [Monitor] 内存为空，正在为 ID:{device_id} 执行紧急现场启动...")
        java_url = "http://localhost:8080/api/monitor/devices"
        try:
            resp = requests.get(java_url, timeout=3)
            if resp.status_code == 200:
                devices = resp.json().get('data', [])
                for dev in devices:
                    if dev['id'] == device_id:
                        url = dev.get('rtspUrl') or dev.get('rtsp_url')
                        if url:
                            print(f"🚀 [Monitor] 成功获取地址: {url}，正在拉起线程...")
                            sm.add_camera(device_id, url)
                            # 给线程一点点启动时间
                            time.sleep(1.5) 
                        break
        except Exception as e:
            print(f"❌ [Monitor] 现场启动失败: {e}")

    # 2. 检查启动结果
    loader = sm.stream_loaders.get(device_id) if sm else None
    
    if loader and loader.running:
        print(f"✅ [Monitor] 设备 {device_id} 准备就绪，开始输出流")
        return Response(local_frame_generator(device_id), 
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    
    return f"Device {device_id} Not Found or Offline", 404