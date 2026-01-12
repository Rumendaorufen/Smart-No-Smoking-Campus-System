from flask import Blueprint, jsonify, Response, request, stream_with_context
import cv2
import time
# 1. 直接导入全局 db 对象和模型
from app.models import db, Devices 
from app import stream_manager 

monitor_bp = Blueprint('monitor', __name__)

# ==========================================
# 1. 设备管理接口 (修复 500 错误)
# ==========================================

@monitor_bp.route('/devices', methods=['GET'])
def get_devices():
    """获取设备列表"""
    try:
        # ✅ 修正：使用 Flask-SQLAlchemy 标准查询写法
        devices = Devices.query.all()
        
        # 转为字典
        data = [d.to_dict() for d in devices]
        
        return jsonify({'code': 200, 'msg': 'success', 'data': data})
    except Exception as e:
        print(f"❌ 查询设备失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)})

@monitor_bp.route('/devices', methods=['POST'])
def add_device():
    """添加新设备"""
    try:
        data = request.json
        # ✅ 修正：直接使用全局 db.session
        new_device = Devices(
            name=data.get('name', '未命名设备'), 
            rtsp_url=data.get('rtsp', data.get('rtsp_url'))
        )
        db.session.add(new_device)
        db.session.commit()
        return jsonify({'code': 200, 'msg': '添加成功', 'data': {'id': new_device.id}})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': f"添加失败: {str(e)}"})

@monitor_bp.route('/devices/<int:device_id>', methods=['DELETE'])
def delete_device(device_id):
    """删除设备"""
    try:
        device = Devices.query.get(device_id)
        if not device:
            return jsonify({'code': 404, 'msg': '设备不存在'}), 404
        
        stream_manager.remove_camera(device_id)
        
        db.session.delete(device)
        db.session.commit()
        return jsonify({'code': 200, 'msg': '删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)})

# ==========================================
# 2. 视频流逻辑
# ==========================================

def generate_frames(device_id):
    """视频流生成器"""
    while True:
        frame = stream_manager.get_latest_frame(device_id)
        if frame is None:
            time.sleep(0.1)
            continue
        
        try:
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            ret, buffer = cv2.imencode('.jpg', frame, encode_param)
            if not ret: continue
            
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.04)
        except Exception as e:
            print(f"Stream generation error: {e}")
            break

@monitor_bp.route('/video_feed/<int:device_id>')
@monitor_bp.route('/stream/<int:device_id>') 
def video_feed(device_id):
    # ✅ 修正：查询单条数据
    device = Devices.query.get(device_id)
    
    if not device:
        return "Device not found in DB", 404
        
    stream_manager.add_camera(device_id, device.rtsp_url)
    
    return Response(
        stream_with_context(generate_frames(device_id)),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )