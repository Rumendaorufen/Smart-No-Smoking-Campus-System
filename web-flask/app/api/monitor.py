from flask import Blueprint, jsonify, Response, request, stream_with_context
import cv2
import time
from app.models import db, Devices
from app.models.user import User  # ✅ 必须导入 User 模型用于权限检查
from app import stream_manager 
from flask_jwt_extended import jwt_required, get_jwt_identity

monitor_bp = Blueprint('monitor', __name__)

# ==========================================
# 辅助函数：权限检查
# ==========================================
def check_admin_permission():
    """检查当前用户是否为管理员"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != 'admin':
        return False
    return True

# ==========================================
# 1. 设备管理接口 (CRUD)
# ==========================================

@monitor_bp.route('/devices', methods=['GET'])
@jwt_required()
def get_devices():
    """获取设备列表 (所有登录用户可用)"""
    try:
        # 按 ID 倒序排列，新添加的在前面
        devices = Devices.query.order_by(Devices.id.desc()).all()
        data = [d.to_dict() for d in devices]
        return jsonify({'code': 200, 'msg': 'success', 'data': data})
    except Exception as e:
        print(f"❌ 查询设备失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)})

@monitor_bp.route('/devices', methods=['POST'])
@jwt_required()  # ✅ 加上认证
def add_device():
    """添加新设备 (仅管理员)"""
    if not check_admin_permission():
        return jsonify({'code': 403, 'msg': '权限不足，仅管理员可操作'}), 403

    try:
        data = request.json
        name = data.get('name')
        rtsp_url = data.get('rtsp', data.get('rtsp_url'))

        if not name or not rtsp_url:
            return jsonify({'code': 400, 'msg': '设备名称和RTSP地址不能为空'})

        # 检查重名
        if Devices.query.filter_by(name=name).first():
            return jsonify({'code': 400, 'msg': '设备名称已存在'})

        new_device = Devices(
            name=name, 
            rtsp_url=rtsp_url,
            status=0 # 默认为离线
        )
        db.session.add(new_device)
        db.session.commit()
        return jsonify({'code': 200, 'msg': '添加成功', 'data': {'id': new_device.id}})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': f"添加失败: {str(e)}"})
    
@monitor_bp.route('/devices/<int:device_id>', methods=['PUT'])
@jwt_required()  # ✅ 加上认证
def update_device(device_id):
    """编辑/更新设备信息 (仅管理员)"""
    if not check_admin_permission():
        return jsonify({'code': 403, 'msg': '权限不足'}), 403

    try:
        device = Devices.query.get(device_id)
        if not device:
            return jsonify({'code': 404, 'msg': '设备不存在'}), 404
        
        data = request.json
        old_rtsp_url = device.rtsp_url
        new_rtsp_url = data.get('rtsp_url') or data.get('rtsp')

        if 'name' in data:
            device.name = data['name']
        
        if new_rtsp_url and new_rtsp_url != old_rtsp_url:
            device.rtsp_url = new_rtsp_url
            # 🛑 重启流逻辑
            print(f"🔄 检测到 RTSP 地址变更，正在重启流: Cam {device_id}")
            stream_manager.remove_camera(device_id)
            # 可以在这里主动设为离线，等待下次连接
            device.status = 0 

        db.session.commit()
        return jsonify({'code': 200, 'msg': '更新成功'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': f"更新失败: {str(e)}"})

@monitor_bp.route('/devices/<int:device_id>', methods=['DELETE'])
@jwt_required()  # ✅ 加上认证
def delete_device(device_id):
    """删除设备 (仅管理员)"""
    if not check_admin_permission():
        return jsonify({'code': 403, 'msg': '权限不足'}), 403

    try:
        device = Devices.query.get(device_id)
        if not device:
            return jsonify({'code': 404, 'msg': '设备不存在'}), 404
        
        # 1. 停止推流
        stream_manager.remove_camera(device_id)
        
        # 2. 删除数据库记录
        db.session.delete(device)
        db.session.commit()
        return jsonify({'code': 200, 'msg': '删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)})

# ==========================================
# 2. 视频流逻辑 (无需 Strict JWT，因为 img src 无法带 Header)
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

@monitor_bp.route('/stream/<int:device_id>') 
def video_feed(device_id):
    device = Devices.query.get(device_id)
    if not device:
        return "Device not found", 404
        
    # 添加到流管理器（如果已存在会自动忽略）
    stream_manager.add_camera(device_id, device.rtsp_url)
    
    return Response(
        stream_with_context(generate_frames(device_id)),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

# 新增：流状态检测接口 (用于前端"测试连接"按钮)
@monitor_bp.route('/stream/status/<int:device_id>', methods=['GET'])
@jwt_required()
def check_stream_status(device_id):
    try:
        # 这里简单判断：如果 stream_manager 这一刻能取到帧，就认为在线
        # 或者你可以尝试用 cv2.VideoCapture 打开一下 rtsp
        device = Devices.query.get(device_id)
        if not device: return jsonify({'code': 404})
        
        
        # 尝试短暂连接
        cap = cv2.VideoCapture(device.rtsp_url)
        if cap.isOpened():
            ret, _ = cap.read()
            cap.release()
            if ret:
                device.status = 1
                db.session.commit()
                return jsonify({'code': 200, 'data': {'status': 1}, 'msg': '连接成功'})
        
        device.status = 0
        db.session.commit()
        return jsonify({'code': 200, 'data': {'status': 0}, 'msg': '连接失败'})
    except:
        return jsonify({'code': 500, 'msg': '检测异常'})