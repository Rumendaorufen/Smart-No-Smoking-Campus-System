# D:\engineering\Smart No-Smoking Campus System\web-flask\app\api\monitor.py
from flask import Blueprint, jsonify, Response, request
import cv2
import time
from app.models import Devices, get_db
from app.core.stream_loader import StreamManager
from config import Config

monitor_bp = Blueprint('monitor', __name__)

# 全局管理器
stream_manager = StreamManager(buffer_size=Config.BUFFER_SIZE)

@monitor_bp.route('/devices', methods=['GET'])
def get_devices():
    db = next(get_db())
    devices = db.query(Devices).all()
    return jsonify({'code': 200, 'data': [d.to_dict() for d in devices]})

@monitor_bp.route('/devices', methods=['POST'])
def add_device():
    data = request.json
    db = next(get_db())
    new_device = Devices(name=data['name'], rtsp_url=data['rtsp_url'])
    db.add(new_device)
    db.commit()
    return jsonify({'code': 200, 'msg': '添加成功'})

@monitor_bp.route('/devices/<int:device_id>', methods=['DELETE'])
def delete_device(device_id):
    db = next(get_db())
    device = db.query(Devices).filter(Devices.id == device_id).first()
    if not device:
        return jsonify({'code': 404, 'msg': '设备不存在'}), 404
    
    stream_manager.remove_camera(device_id)
    db.delete(device)
    db.commit()
    return jsonify({'code': 200, 'msg': '删除成功'})

@monitor_bp.route('/stream/<int:device_id>')
def video_feed(device_id):
    db = next(get_db())
    device = db.query(Devices).filter(Devices.id == device_id).first()
    
    if not device:
        return "Device not found", 404
        
    # 懒加载启动流
    stream_manager.add_camera(device_id, device.rtsp_url)
    
    def generate():
        while True:
            # 获取的是已经 Resize 过的 640x360 图片
            frame = stream_manager.get_latest_frame(device_id)
            if frame is None:
                # 没画面时稍微睡一下，防止死循环空转
                time.sleep(0.1)
                continue
            
            # 优化: 降低 JPEG 质量到 70 (肉眼看不出区别，带宽减半)
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            ret, buffer = cv2.imencode('.jpg', frame, encode_param)
            
            if not ret:
                continue
                
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # 发送端限制频率 (约 20fps)，让浏览器喘口气
            time.sleep(0.05) 
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')