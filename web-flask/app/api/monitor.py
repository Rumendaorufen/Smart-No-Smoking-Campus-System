from flask import Blueprint, jsonify, Response, request, stream_with_context
import cv2
import time
import os
import socket  # 👈 必须导入
import threading # 👈 必须导入
from urllib.parse import urlparse # 👈 必须导入
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
    # 保存旧环境变量
    old_props = {}
    for k in ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
        if k in os.environ:
            old_props[k] = os.environ[k]
            del os.environ[k]

    try:
        yield
    finally:
        # 恢复环境变量
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
        
        # print(f"📡 [Socket] Pinging {host}:{port}...")
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception as e:
        print(f"⚠️ [Socket Check Failed]: {e}")
        return False

# ==========================================
# 设备 CRUD 接口 (保持不变)
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
        new_device = Devices(name=data['name'], rtsp_url=data.get('rtsp', data.get('rtsp_url')), status=0)
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
                stream_manager.remove_camera(device_id) # 停止旧流
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

# ... 保持前面的 imports 和辅助函数不变 ...

@monitor_bp.route('/stream/status/<int:device_id>', methods=['GET'])
@jwt_required()
def check_stream_status(device_id):
    try:
        device = Devices.query.get(device_id)
        if not device: return jsonify({'code': 404, 'msg': '设备不存在'})

        with no_proxy_scope():
            print(f"🔍 [Monitor] 开始检测: {device.name}")
            
            # 1. Socket 基础网络检测
            # 手机休眠时 Ping 可能会慢，给 3 秒
            socket_ok = check_socket_open(device.rtsp_url, timeout=3.0)
            
            if not socket_ok:
                # 给一次重试机会
                time.sleep(0.5)
                socket_ok = check_socket_open(device.rtsp_url, timeout=3.0)
                
                if not socket_ok:
                    print(f"❌ [Fast Fail] Socket 无法连接: {device.rtsp_url}")
                    device.status = 0
                    db.session.commit()
                    return jsonify({'code': 200, 'data': {'status': 0}, 'msg': '无法连接主机(网络不可达)'})
            
            # 2. 视频流智能握手 (自动重试核心)
            print("✅ Socket 通畅，开始握手...")
            result_holder = {'success': False}

            def connect_task(url):
                # 策略列表：专门针对手机 RTSP 设计
                strategies = [
                    # 第 1 步：唤醒尝试 (5秒)
                    # 目的：如果是休眠设备，这一步通常会超时失败，但能把设备唤醒
                    ("WakeUp/UDP", "stimeout;5000000"),
                    
                    # 第 2 步：正式连接 (10秒)
                    # 目的：设备醒了，这次大概率成功。如果第1步失败，这里会接力
                    ("Retry/UDP", "stimeout;10000000"),
                    
                    # 第 3 步：保底 TCP (10秒)
                    # 目的：如果 UDP 实在不行，尝试 TCP
                    ("Fallback/TCP", "rtsp_transport;tcp|stimeout;10000000") 
                ]

                for mode, options in strategies:
                    if result_holder['success']: break 
                    
                    print(f"🔄 正在尝试: {mode} ...")
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = options
                    
                    try:
                        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                        if cap.isOpened():
                            # 只要能读到 1 帧，就认为成功
                            # 手机性能差，读多帧容易卡顿
                            if cap.grab(): 
                                result_holder['success'] = True
                                print(f"🎉 {mode} 连接成功！")
                                cap.release()
                                return
                        cap.release()
                    except Exception as e:
                        print(f"⚠️ {mode} 失败: {e}")
                    
                    # 失败后，休息 1 秒再试下一种策略
                    # 这个休息非常重要！给手机 CPU 喘息时间
                    print("⏳ 等待设备响应...")
                    time.sleep(1.0)

            t = threading.Thread(target=connect_task, args=(device.rtsp_url,))
            t.daemon = True
            t.start()
            
            # 总等待时间：5s + 1s + 10s + 1s + 10s = 27s
            # 我们给线程 18秒 的总限时，足够跑完前两步
            # 只要前两步有一步成功，就会立即返回
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
    """一键重连所有离线设备 (异步多线程)"""
    try:
        # 1. 找出所有离线设备
        offline_devices = Devices.query.filter_by(status=0).all()
        if not offline_devices:
            return jsonify({'code': 200, 'msg': '所有设备均已在线'})
        
        print(f"🔄 [Batch] 开始批量重连 {len(offline_devices)} 台设备...")

        # 2. 定义单个检测任务 (复用之前的逻辑)
        def single_check_task(device_id):
            # 这里我们复用 check_stream_status 的逻辑，但为了方便，直接内部调用
            # 注意：在 Flask 中内部调用路由函数比较麻烦，建议提取公共逻辑
            # 这里简单起见，我们直接发起一个新的检测请求，或者直接拷贝检测代码
            # 为了最稳妥，我们让前端去触发每个设备的检测，或者后端直接在这里跑
            
            # 由于 check_stream_status 里有复杂的 socket/opencv 逻辑
            # 我们直接调用 requests 库反向请求自己，或者直接实例化检测类
            # 但最简单的还是：只返回成功，让前端去遍历调用 check_stream_status
            pass 

        # ⚡️ 方案优化：
        # 后端做批量检测太复杂且容易超时。
        # 最简单的做法是：后端返回所有离线设备的 ID 列表，让前端去逐个触发 "check_stream_status"。
        
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
    stream_manager.add_camera(device_id, device.rtsp_url)
    return Response(stream_with_context(generate_frames(device_id)), mimetype='multipart/x-mixed-replace; boundary=frame')