# web-flask/app/api/system.py
from flask import Blueprint, jsonify, request
from app.core.stream_loader import stream_manager

# 定义蓝图，确保这里的逻辑能对接到全局单例 stream_manager
system_bp = Blueprint('system', __name__)

# 🚀 对应路径: http://localhost:5000/api/v1/system/global_ai
# 增加 'GET' 到 methods 列表中
@system_bp.route('/global_ai', methods=['GET', 'POST', 'OPTIONS'])
def toggle_global_ai():
    # 1. 处理跨域预检请求
    if request.method == 'OPTIONS':
        return jsonify({"msg": "ok"}), 200

    # 2. 处理 GET 请求：返回当前 AI 引擎的真实运行状态
    if request.method == 'GET':
        # 假设你的 stream_manager 有 global_ai_enabled 属性
        current_status = getattr(stream_manager, 'global_ai_enabled', True)
        return jsonify({
            "code": 200,
            "msg": "获取成功",
            "data": current_status # 必须返回这个，否则前端开关位置会错乱
        })

    # 3. 处理 POST 请求：切换开关逻辑
    data = request.json
    if not data or 'enabled' not in data:
        return jsonify({"code": 400, "msg": "Missing 'enabled' parameter"}), 400
    
    enabled = data.get('enabled')
    
    try:
        # 调用 stream_manager 控制所有正在运行的 AI 引擎
        stream_manager.set_global_ai(enabled)
        status_text = "开启" if enabled else "关闭"
        print(f"🌍 [System] 全局 AI 设定为: {status_text}")
        
        return jsonify({
            "code": 200, 
            "msg": f"全局 AI 引擎已{status_text}",
            "data": enabled
        })
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500