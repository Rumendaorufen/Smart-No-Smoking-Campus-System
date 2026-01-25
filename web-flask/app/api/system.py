from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User, Devices, Alarms 
from app.core.stream_loader import stream_manager
import psutil
import os
import time
import datetime
import threading # 👈 引入多线程

# 尝试导入显卡库
try:
    import pynvml
    pynvml.nvmlInit()
    HAS_GPU = True
except:
    HAS_GPU = False

system_bp = Blueprint('system', __name__)

# ==========================================
# 🔄 全局缓存 & 后台监控线程 (核心优化)
# ==========================================
# 用于存放最新的系统状态，API 直接读这个变量，不用每次都算
SYSTEM_CACHE = {
    'cpu': 0,
    'memory': {'percent': 0, 'used': 0},
    'gpu': {'used': 0, 'total': 0, 'percent': 0, 'mem_percent': 0, 'name': 'N/A'},
    'disk': {'total': 0, 'used': 0, 'free': 0, 'percent': 0}
}

def monitor_task():
    """后台线程：持续循环更新系统状态"""
    print("🚀 [System] 硬件监控线程已启动 (Interval=1s)...")
    while True:
        try:
            # 1. CPU: 采样 1 秒 (这行代码会阻塞线程1秒，正好符合任务管理器的刷新率)
            cpu = psutil.cpu_percent(interval=1)
            
            # 2. 内存
            mem = psutil.virtual_memory()
            
            # 3. GPU
            gpu_data = {'used': 0, 'total': 0, 'percent': 0, 'name': 'N/A', 'mem_percent': 0}
            if HAS_GPU:
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    name = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(name, bytes): name = name.decode('utf-8')
                    
                    gpu_data = {
                        'used': round(mem_info.used / 1024**3, 2),
                        'total': round(mem_info.total / 1024**3, 2),
                        'percent': util.gpu, # 这是真实的 AI 算力使用率
                        'mem_percent': round((mem_info.used / mem_info.total) * 100, 1),
                        'name': name
                    }
                except:
                    pass

            # 4. 磁盘
            disk_data = {'percent': 0, 'free': 0}
            try:
                usage = psutil.disk_usage(os.getcwd())
                disk_data = {
                    'total': round(usage.total / 1024**3, 2),
                    'used': round(usage.used / 1024**3, 2),
                    'free': round(usage.free / 1024**3, 2),
                    'percent': usage.percent
                }
            except:
                pass

            # ⚡️ 原子更新缓存
            SYSTEM_CACHE['cpu'] = cpu
            SYSTEM_CACHE['memory'] = {'percent': mem.percent, 'used': round(mem.used / 1024**3, 2)}
            SYSTEM_CACHE['gpu'] = gpu_data
            SYSTEM_CACHE['disk'] = disk_data

        except Exception as e:
            print(f"⚠️ 监控线程出错: {e}")
            time.sleep(1) 

# 启动后台线程 (Daemon模式，随主程序退出)
# 注意：Flask 的热重载 (Debug模式) 可能会导致线程启动两次，生产环境不会
if not os.environ.get('WERKZEUG_RUN_MAIN') == 'true': 
    # 简单的防止重载启动两次的判断，但在 socketio.run 下通常没事
    t = threading.Thread(target=monitor_task, daemon=True)
    t.start()
else:
    # 兼容 Flask 调试模式的重载机制
    t = threading.Thread(target=monitor_task, daemon=True)
    t.start()


# ==========================================
# API 接口 (现在只读缓存，速度极快)
# ==========================================

@system_bp.route('/status', methods=['GET'])
@jwt_required()
def get_system_status():
    # 1. 直接读取缓存 (CPU数据现在是平滑的1秒平均值)
    cpu_usage = SYSTEM_CACHE['cpu']
    ram_data = SYSTEM_CACHE['memory']
    gpu_info = SYSTEM_CACHE['gpu']
    disk_info = SYSTEM_CACHE['disk']
    
    # 2. 业务数据 (必须实时查)
    today = datetime.date.today()
    today_alarms = Alarms.query.filter(db.func.date(Alarms.created_at) == today).count()
    pending_audit = Alarms.query.filter_by(audit_status=0).count()
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")

    # 3. 设备列表
    devices = Devices.query.all()
    device_list = []
    for d in devices:
        loader = stream_manager.stream_loaders.get(d.id)
        is_running = loader is not None and loader.running
        device_list.append({
            'id': d.id,
            'name': d.name,
            'rtsp_url': d.rtsp_url,
            'enabled': d.enabled,
            'is_running': is_running
        })

    return jsonify({
        'code': 200,
        'data': {
            'cpu': cpu_usage,
            'ram_percent': ram_data['percent'],
            'ram_used': ram_data['used'],
            'gpu': gpu_info,
            'disk': disk_info,
            'business': {
                'today_alarms': today_alarms,
                'pending_audit': pending_audit,
                'boot_time': boot_time
            },
            'total_streams': len(stream_manager.stream_loaders),
            'global_ai': stream_manager.global_ai_enabled,
            'devices': device_list
        }
    })

# 下面是控制接口 (保持不变)
@system_bp.route('/control/device', methods=['POST'])
@jwt_required()
def control_device():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != 'admin':
        return jsonify({'code': 403, 'msg': '无权操作'})

    data = request.json
    device_id = data.get('id')
    enable = data.get('enable')

    success = stream_manager.toggle_device_enable(device_id, enable)
    
    if success:
        action_str = "启用" if enable else "停用"
        return jsonify({'code': 200, 'msg': f'设备已{action_str}'})
    else:
        return jsonify({'code': 500, 'msg': '操作失败'})

@system_bp.route('/control/global_ai', methods=['POST'])
@jwt_required()
def control_global_ai():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != 'admin':
        return jsonify({'code': 403, 'msg': '无权操作'})

    data = request.json
    enabled = data.get('enabled')

    stream_manager.set_global_ai(enabled)
    return jsonify({'code': 200, 'msg': f'全局 AI 已{"开启" if enabled else "关闭"}'})