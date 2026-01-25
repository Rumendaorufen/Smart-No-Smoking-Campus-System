# web-flask\app\api\monitor.py
from flask import Blueprint, jsonify, Request, request, stream_with_context, Response, send_file, current_app
import cv2
import time
import re  
import os
import socket  
import threading 
from urllib.parse import urlparse 
from contextlib import contextmanager
from app.models import db, Devices
from app.models.user import User 
from app import stream_manager 
from flask_jwt_extended import jwt_required, get_jwt_identity

monitor_bp = Blueprint('monitor', __name__)

# ==========================================
# 辅助配置
# ==========================================

# 1. 上下文管理器：临时绕过系统代理
@contextmanager
def no_proxy_scope():
    old_props = {}
    for k in ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
        if k in os.environ:
            old_props[k] = os.environ[k]
            del os.environ[k]

    try:
        yield
    finally:
        for k, v in old_props.items():
            os.environ[k] = v

# 2. 辅助函数：权限检查
def check_admin_permission():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != 'admin':
        return False
    return True

# 3. 辅助函数：端口检测
def check_socket_open(rtsp_url, timeout=1.0):
    try:
        parsed = urlparse(rtsp_url)
        host = parsed.hostname
        port = parsed.port if parsed.port else 554 
        
        if not host: return False
        
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception as e:
        # print(f"⚠️ [Socket Check Failed]: {e}")
        return False

# ==========================================
# 设备 CRUD 接口
# ==========================================

@monitor_bp.route('/devices', methods=['GET'])
@jwt_required()
def get_devices():
    try:
        devices = Devices.query.order_by(Devices.id.desc()).all()
        data = [d.to_dict() for d in devices]
        return jsonify({'code': 200, 'msg': 'success', 'data': data})
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'code': 500, 'msg': str(e)})

@monitor_bp.route('/devices', methods=['POST'])
@jwt_required()
def add_device():
    if not check_admin_permission(): return jsonify({'code': 403, 'msg': '无权操作'})
    try:
        data = request.json
        if Devices.query.filter_by(name=data['name']).first():
            return jsonify({'code': 400, 'msg': '名称已存在'})
        # 默认启用 enabled=True
        new_device = Devices(name=data['name'], rtsp_url=data.get('rtsp', data.get('rtsp_url')), status=0, enabled=True)
        db.session.add(new_device)
        db.session.commit()
        return jsonify({'code': 200, 'msg': '添加成功', 'data': {'id': new_device.id}})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)})
    
@monitor_bp.route('/devices/<int:device_id>', methods=['PUT'])
@jwt_required()
def update_device(device_id):
    if not check_admin_permission(): return jsonify({'code': 403, 'msg': '无权操作'})
    try:
        device = Devices.query.get(device_id)
        if not device: return jsonify({'code': 404, 'msg': '设备不存在'})
        data = request.json
        if 'name' in data: device.name = data['name']
        if 'rtsp_url' in data or 'rtsp' in data:
            new_url = data.get('rtsp_url') or data.get('rtsp')
            if new_url != device.rtsp_url:
                device.rtsp_url = new_url
                stream_manager.remove_camera(device_id) 
                device.status = 0
        db.session.commit()
        return jsonify({'code': 200, 'msg': '更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)})

@monitor_bp.route('/devices/<int:device_id>', methods=['DELETE'])
@jwt_required()
def delete_device(device_id):
    if not check_admin_permission(): return jsonify({'code': 403, 'msg': '无权操作'})
    try:
        device = Devices.query.get(device_id)
        if not device: return jsonify({'code': 404})
        stream_manager.remove_camera(device_id)
        db.session.delete(device)
        db.session.commit()
        return jsonify({'code': 200, 'msg': '删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)})

# ==========================================
# 视频流与检测核心接口
# ==========================================

@monitor_bp.route('/stream/status/<int:device_id>', methods=['GET'])
@jwt_required()
def check_stream_status(device_id):
    try:
        device = Devices.query.get(device_id)
        if not device: return jsonify({'code': 404, 'msg': '设备不存在'})

        # 🔥🔥🔥 修改点 1：如果设备被停用，直接拒绝检测 🔥🔥🔥
        if device.enabled == False:
            print(f"🚫 [Monitor] {device.name} 已停用，拒绝连接")
            return jsonify({'code': 200, 'data': {'status': 0}, 'msg': '设备已停用，请联系管理员启用'})

        with no_proxy_scope():
            print(f"🔍 [Monitor] 开始检测: {device.name}")
            
            # 1. Socket 基础网络检测
            socket_ok = check_socket_open(device.rtsp_url, timeout=3.0)
            
            if not socket_ok:
                time.sleep(0.5)
                socket_ok = check_socket_open(device.rtsp_url, timeout=3.0)
                
                if not socket_ok:
                    print(f"❌ [Fast Fail] Socket 无法连接: {device.rtsp_url}")
                    device.status = 0
                    db.session.commit()
                    return jsonify({'code': 200, 'data': {'status': 0}, 'msg': '无法连接主机(网络不可达)'})
            
            # 2. 视频流智能握手
            print("✅ Socket 通畅，开始握手...")
            result_holder = {'success': False}

            def connect_task(url):
                strategies = [
                    ("WakeUp/UDP", "stimeout;5000000"),
                    ("Retry/UDP", "stimeout;10000000"),
                    ("Fallback/TCP", "rtsp_transport;tcp|stimeout;10000000") 
                ]

                for mode, options in strategies:
                    if result_holder['success']: break 
                    
                    print(f"🔄 正在尝试: {mode} ...")
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = options
                    
                    try:
                        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                        if cap.isOpened():
                            if cap.grab(): 
                                result_holder['success'] = True
                                print(f"🎉 {mode} 连接成功！")
                                cap.release()
                                return
                        cap.release()
                    except Exception as e:
                        print(f"⚠️ {mode} 失败: {e}")
                    
                    print("⏳ 等待设备响应...")
                    time.sleep(1.0)

            t = threading.Thread(target=connect_task, args=(device.rtsp_url,))
            t.daemon = True
            t.start()
            
            t.join(timeout=18.0)
            
            if result_holder['success']:
                device.status = 1
                db.session.commit()
                return jsonify({'code': 200, 'data': {'status': 1}, 'msg': '连接成功'})
            else:
                print("❌ 最终连接失败")
                device.status = 0
                db.session.commit()
                return jsonify({'code': 200, 'data': {'status': 0}, 'msg': '握手失败(设备未就绪)'})

    except Exception as e:
        print(f"❌ 系统异常: {e}")
        return jsonify({'code': 200, 'data': {'status': 0}, 'msg': '系统错误'})

@monitor_bp.route('/reconnect_all', methods=['POST'])
@jwt_required()
def reconnect_all():
    """一键重连所有离线设备"""
    try:
        # 只查找状态离线 且 已启用的设备
        offline_devices = Devices.query.filter_by(status=0, enabled=True).all()
        if not offline_devices:
            return jsonify({'code': 200, 'msg': '没有可重连的设备'})
        
        offline_ids = [d.id for d in offline_devices]
        return jsonify({
            'code': 200, 
            'msg': f'即将重连 {len(offline_ids)} 台设备', 
            'data': offline_ids 
        })

    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e)})

def generate_frames(device_id):
    while True:
        frame = stream_manager.get_latest_frame(device_id)
        if frame is None:
            time.sleep(0.1)
            continue
        try:
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            ret, buffer = cv2.imencode('.jpg', frame, encode_param)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.04)
        except: break

@monitor_bp.route('/stream/<int:device_id>') 
def video_feed(device_id):
    device = Devices.query.get(device_id)
    if not device: return "Device not found", 404

    # 🔥🔥🔥 修改点 2：如果设备被停用，拒绝推流 🔥🔥🔥
    # 这是防止前端 img 标签直接通过 URL 访问的关键
    if device.enabled == False:
        return "Device is disabled", 403

    # 如果没被停用，才允许添加到管理器
    stream_manager.add_camera(device_id, device.rtsp_url)
    return Response(stream_with_context(generate_frames(device_id)), mimetype='multipart/x-mixed-replace; boundary=frame')

@monitor_bp.route('/video/<path:filename>')
def stream_video_file(filename):
    base_dir = current_app.root_path 
    clean_filename = filename.replace('app/', '')
    file_path = os.path.join(current_app.root_path, clean_filename)
    
    if not os.path.exists(file_path):
        if clean_filename.startswith('static/'):
             file_path = os.path.join(current_app.root_path, clean_filename)
    
    if not os.path.exists(file_path):
        return Response("Video not found", status=404)

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get('Range', None)

    if not range_header:
        return send_file(file_path)

    match = re.search(r'(\d+)-(\d*)', range_header)
    groups = match.groups()

    first_byte = int(groups[0]) if groups[0] else 0
    last_byte = int(groups[1]) if groups[1] else file_size - 1

    if last_byte >= file_size:
        last_byte = file_size - 1

    length = last_byte - first_byte + 1

    with open(file_path, 'rb') as f:
        f.seek(first_byte)
        data = f.read(length)

    resp = Response(data, 206, mimetype='video/mp4', direct_passthrough=True)
    resp.headers.add('Content-Range', f'bytes {first_byte}-{last_byte}/{file_size}')
    resp.headers.add('Accept-Ranges', 'bytes')
    return resp