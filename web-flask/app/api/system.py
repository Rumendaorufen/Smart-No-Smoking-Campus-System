# app/api/system.py
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User, Devices
from app.core.stream_loader import stream_manager
import psutil

system_bp = Blueprint('system', __name__)

@system_bp.route('/status', methods=['GET'])
@jwt_required()
def get_system_status():
    """获取服务器运行状态及所有设备状态"""
    cpu_usage = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    
    devices = Devices.query.all()
    device_list = []
    
    for d in devices:
        # 获取内存中的流加载器
        loader = stream_manager.stream_loaders.get(d.id)
        is_running = loader is not None and loader.running
        
        device_list.append({
            'id': d.id,
            'name': d.name,
            'rtsp_url': d.rtsp_url,
            'enabled': d.enabled, # ✅ 返回数据库里的启用状态
            'is_running': is_running
        })

    return jsonify({
        'code': 200,
        'data': {
            'cpu': cpu_usage,
            'ram_percent': memory.percent,
            'ram_used': round(memory.used / 1024 / 1024 / 1024, 2),
            'total_streams': len(stream_manager.stream_loaders),
            'global_ai': stream_manager.global_ai_enabled, # ✅ 返回全局 AI 状态
            'devices': device_list
        }
    })

@system_bp.route('/control/device', methods=['POST'])
@jwt_required()
def control_device():
    """控制设备启用/停用 (Persistent)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != 'admin':
        return jsonify({'code': 403, 'msg': '无权操作'})

    data = request.json
    device_id = data.get('id')
    enable = data.get('enable') # True/False

    success = stream_manager.toggle_device_enable(device_id, enable)
    
    if success:
        action_str = "启用" if enable else "停用"
        return jsonify({'code': 200, 'msg': f'设备已{action_str}'})
    else:
        return jsonify({'code': 500, 'msg': '操作失败'})

@system_bp.route('/control/global_ai', methods=['POST'])
@jwt_required()
def control_global_ai():
    """控制全局 AI 开关"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != 'admin':
        return jsonify({'code': 403, 'msg': '无权操作'})

    data = request.json
    enabled = data.get('enabled') # True/False

    stream_manager.set_global_ai(enabled)
    return jsonify({'code': 200, 'msg': f'全局 AI 已{"开启" if enabled else "关闭"}'})