from flask import Blueprint, jsonify, Response, request, stream_with_context
import cv2
import time
from app.models import Devices, get_db
# 🛑 关键修改 1: 从 app 包导入全局唯一的 stream_manager 实例
# 不要在这里 StreamManager()，否则会创建两个独立的管理器，导致画面不通
from app import stream_manager 

monitor_bp = Blueprint('monitor', __name__)

# ==========================================
# 1. 设备管理接口 (数据库 CRUD)
# ==========================================

@monitor_bp.route('/devices', methods=['GET'])
def get_devices():
    """获取设备列表"""
    try:
        db = next(get_db())
        devices = db.query(Devices).all()
        # 将 SQLAlchemy 对象转为字典
        data = []
        for d in devices:
            data.append({
                'id': d.id,
                'name': d.name,
                'rtsp': d.rtsp_url, # 前端字段可能叫 rtsp 或 rtsp_url，根据你前端调整
                'location': getattr(d, 'location', '未知位置'), # 防报错
                'status': 'Online' # 这里暂时写死，以后可以从 stream_manager 获取真实状态
            })
        return jsonify({'code': 200, 'msg': 'success', 'data': data})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e)})

@monitor_bp.route('/devices', methods=['POST'])
def add_device():
    """添加新设备"""
    try:
        data = request.json
        db = next(get_db())
        # 注意：确保你的前端传来的字段名和这里一致
        new_device = Devices(
            name=data.get('name', '未命名设备'), 
            rtsp_url=data.get('rtsp', data.get('rtsp_url'))
        )
        db.add(new_device)
        db.commit()
        return jsonify({'code': 200, 'msg': '添加成功', 'data': {'id': new_device.id}})
    except Exception as e:
        db.rollback()
        return jsonify({'code': 500, 'msg': f"添加失败: {str(e)}"})

@monitor_bp.route('/devices/<int:device_id>', methods=['DELETE'])
def delete_device(device_id):
    """删除设备"""
    try:
        db = next(get_db())
        device = db.query(Devices).filter(Devices.id == device_id).first()
        if not device:
            return jsonify({'code': 404, 'msg': '设备不存在'}), 404
        
        # 1. 先停止拉流任务
        stream_manager.remove_camera(device_id)
        
        # 2. 再删数据库
        db.delete(device)
        db.commit()
        return jsonify({'code': 200, 'msg': '删除成功'})
    except Exception as e:
        db.rollback()
        return jsonify({'code': 500, 'msg': str(e)})

@monitor_bp.route('/devices/<int:device_id>', methods=['PUT'])
def update_device(device_id):
    """更新设备信息"""
    try:
        db = next(get_db())
        device = db.query(Devices).filter(Devices.id == device_id).first()
        if not device:
            return jsonify({'code': 404, 'msg': '设备不存在'}), 404
        
        data = request.json
        
        # 更新设备信息
        if 'name' in data:
            device.name = data['name']
        if 'rtsp_url' in data or 'rtsp' in data:
            # 兼容两种字段名
            new_rtsp = data.get('rtsp_url') or data.get('rtsp')
            # 如果 RTSP 地址改变，重新启动拉流
            if new_rtsp and new_rtsp != device.rtsp_url:
                device.rtsp_url = new_rtsp
                # 停止旧流，重新拉流
                stream_manager.remove_camera(device_id)
                stream_manager.add_camera(device_id, new_rtsp)
        
        db.commit()
        return jsonify({'code': 200, 'msg': '更新成功'})
    except Exception as e:
        db.rollback()
        return jsonify({'code': 500, 'msg': f'更新失败: {str(e)}'})

# ==========================================
# 2. 视频流逻辑 (融合 AI 处理)
# ==========================================

def generate_frames(device_id):
    """视频流生成器"""
    while True:
        # 从全局管理器获取最新 AI 处理帧
        frame = stream_manager.get_latest_frame(device_id)
        
        if frame is None:
            # 没画面时(连接中或断开)，稍微等待，防止 CPU 空转
            time.sleep(0.1)
            continue
        
        try:
            # 🛑 优化: 降低 JPEG 质量到 70 (保留你的优化逻辑，非常棒)
            # 这能显著降低网络带宽占用，且肉眼几乎看不出区别
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            ret, buffer = cv2.imencode('.jpg', frame, encode_param)
            
            if not ret: continue
            
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # 发送端限制频率 (约 25fps)，减轻浏览器渲染压力
            time.sleep(0.04)
            
        except Exception as e:
            print(f"Stream generation error: {e}")
            break

# 兼容两种路由写法，防止前端找不到
@monitor_bp.route('/video_feed/<int:device_id>')
@monitor_bp.route('/stream/<int:device_id>') 
def video_feed(device_id):
    """视频流入口"""
    # 1. 查库获取 RTSP 地址
    db = next(get_db())
    device = db.query(Devices).filter(Devices.id == device_id).first()
    
    if not device:
        # 如果数据库没这个设备，无法拉流
        return "Device not found in DB", 404
        
    # 2. 告诉全局管理器开始干活 (懒加载：有人看才开始拉流)
    # 你的模型 Devices 里的字段名是 rtsp_url
    stream_manager.add_camera(device_id, device.rtsp_url)
    
    # 3. 返回流
    return Response(
        stream_with_context(generate_frames(device_id)),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )