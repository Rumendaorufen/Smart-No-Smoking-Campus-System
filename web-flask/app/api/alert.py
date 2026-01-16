# web-flask/app/api/alert.py

import os
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import desc

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
    try:
        current_user_id = get_jwt_identity()
        # 获取当前用户名（因为你的数据库 alarms.auditor 是存名字的字符串）
        user = User.query.get(current_user_id)
        username = user.username if user else "Unknown"

        data = request.json
        new_status = data.get('status')
        # remark = data.get('remark') # ❌ 数据库没这字段，存不了

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
        
        # ✅ 修正：使用 audit_status
        query = Alarms.query.filter(Alarms.audit_status != 0)

        if device_id:
            query = query.filter(Alarms.camera_id == device_id)
        if status:
            query = query.filter(Alarms.audit_status == status)

        # ✅ 修正：使用 create_time
        query = query.order_by(desc(Alarms.create_time))
        
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        data = [item.to_dict() for item in pagination.items]

        return jsonify({'code': 200, 'data': {'list': data, 'total': pagination.total, 'pages': pagination.pages}})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e)})

# 删除接口保持不变，只要引用对字段即可