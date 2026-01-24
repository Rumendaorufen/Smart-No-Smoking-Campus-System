# web-flask/app/api/alert.py

import os
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import desc
from app.models.devices import Devices #  引入 Devices 模型

from app.models import db
from app.models.alarm import Alarms
from app.models.user import User

alert_bp = Blueprint('alert', __name__)

# 获取待审核列表
@alert_bp.route('/pending', methods=['GET'])
@jwt_required()
def get_pending_alerts():
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

       # ✅ 改为 audit_status 和 created_at
        query = Alarms.query.filter_by(audit_status=0).order_by(desc(Alarms.created_at))
        
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        data = [item.to_dict() for item in pagination.items]
        
        return jsonify({
            'code': 200,
            'data': {
                'list': data,
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e)})

# 提交审核结果
@alert_bp.route('/<int:alarm_id>/audit', methods=['POST'])
@jwt_required()
def audit_alarm(alarm_id):
    """
    提交人工判断结果
    Body: { "status": 1, "remark": "确实是吸烟" }
    status: 1=确认, 2=误报, 9=忽略
    """
    try:
        current_user_id = get_jwt_identity()
        # 获取当前用户名（因为你的数据库 alarms.auditor 是存名字的字符串）
        user = User.query.get(current_user_id)
        username = user.username if user else "Unknown"

        data = request.json
        new_status = data.get('status')
        remark = data.get('remark') 

        if new_status not in [1, 2, 9]:
            return jsonify({'code': 400, 'msg': '无效的状态码'})

        alarm = Alarms.query.get(alarm_id)
        if not alarm:
            return jsonify({'code': 404, 'msg': '记录不存在'})

        # ✅ 改为 audit_status 和 auditor_id (你截图里有 auditor_id)
        alarm.audit_status = new_status
        alarm.auditor_id = current_user_id  # 存 ID
        alarm.audit_time = datetime.now()
        alarm.audit_remark = remark
        
        db.session.commit()
        return jsonify({'code': 200, 'msg': '审核完成'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)})

# 历史档案查询
@alert_bp.route('/archive', methods=['GET'])
@jwt_required()
def get_archive():
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        device_id = request.args.get('device_id', type=int)
        status = request.args.get('status', type=int)

        #  获取审核人参数
        auditor_name = request.args.get('auditor_name')
        
        # 获取时间参数
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')

        # 获取前端传来的设备名称 (可能为空)
        device_name = request.args.get('device_name')
        
        # 1. 基础过滤
        query = Alarms.query.filter(Alarms.audit_status != 0)

        if device_id:
            query = query.filter(Alarms.camera_id == device_id)
        if status:
            query = query.filter(Alarms.audit_status == status)
            
        # ✅ 2. 补上时间过滤 (使用正确的 created_at)
        if start_time and end_time:
            query = query.filter(Alarms.created_at.between(start_time, end_time))

        # ✅新增：设备名称模糊查询 (联表查询)
        if device_name:
            # 逻辑：Alarms 表连接 Devices 表，查找 Devices.name 包含关键词的记录
            query = query.join(Devices).filter(Devices.name.like(f'%{device_name}%'))
        
           # 筛选审核人
        if auditor_name:
            # 联表查询：Alarm 连 User 表，查找 username 包含关键词的
            query = query.join(User, Alarms.auditor_id == User.id).filter(User.username.like(f'%{auditor_name}%'))


        # ✅ 3. 修复排序报错 (使用正确的 created_at)
        query = query.order_by(desc(Alarms.created_at))
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        data = [item.to_dict() for item in pagination.items]

     
        return jsonify({
            'code': 200, 
            'data': {
                'list': data, 
                'total': pagination.total, 
                'pages': pagination.pages
            }
        })
    except Exception as e:
        # 建议打印错误，方便你在控制台看到真实的报错
        print(f"❌ 档案查询报错: {e}")
        return jsonify({'code': 500, 'msg': str(e)})

# 删除接口保持不变，只要引用对字段即可
# ==========================================
# 4. 删除记录 (物理删除)
# ==========================================
@alert_bp.route('/<int:alarm_id>', methods=['DELETE'])
@jwt_required()
def delete_alarm(alarm_id):
    """管理员删除记录，同时删除物理文件"""
    try:
        # 鉴权：只有管理员能删
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.role != 'admin':
            return jsonify({'code': 403, 'msg': '无权操作'})

        alarm = Alarms.query.get(alarm_id)
        if not alarm:
            return jsonify({'code': 404, 'msg': '记录不存在'})

        # 1. 删除物理文件 (加 try-except 防止文件不存在报错)
        _delete_physical_file(alarm.roi_url)
        _delete_physical_file(alarm.video_url)

        # 2. 删除数据库记录
        db.session.delete(alarm)
        db.session.commit()

        return jsonify({'code': 200, 'msg': '删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)})

# --- 辅助函数：删除文件 ---
def _delete_physical_file(rel_path):
    if not rel_path: return
    try:
        # 假设 rel_path 是 "static/evidence/xxx.jpg"
        # 需要拼上 Flask 的根目录
        base_dir = current_app.root_path # app/
        # 注意：如果 rel_path 包含 app/static 前缀，需要处理一下路径拼接
        # 假设数据库存的是 "static/evidence/..." 相对路径
        # 而物理路径是 /your/project/web-flask/app/static/evidence/...
        
        # 简单处理：拼接绝对路径
        file_path = os.path.join(base_dir, rel_path.lstrip('/'))
        
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️ 已物理删除: {file_path}")
    except Exception as e:
        print(f"⚠️ 文件删除失败: {e}")