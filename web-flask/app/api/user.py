# from flask import Blueprint, request, jsonify
# from flask_jwt_extended import jwt_required, get_jwt_identity
# from app.models import db
# from app.models.user import User

# user_bp = Blueprint('user', __name__)

# @user_bp.route('/', methods=['GET'])
# @jwt_required()
# def get_user_list():
#     """获取用户列表"""
#     current_user_id = get_jwt_identity()
#     current_user = User.query.get(current_user_id)
    
#     if not current_user or current_user.role != 'admin':
#         return jsonify({'code': 403, 'msg': '权限不足'})
        
#     # 按创建时间倒序排列
#     users = User.query.order_by(User.created_at.desc()).all()
#     return jsonify({
#         'code': 200,
#         'data': [u.to_dict() for u in users]
#     })

# @user_bp.route('/', methods=['POST'])
# @jwt_required()
# def add_user():
#     """添加用户"""
#     # ... (原有添加逻辑保持不变，但建议加上 status 的处理) ...
#     current_user_id = get_jwt_identity()
#     current_user = User.query.get(current_user_id)
    
#     if not current_user or current_user.role != 'admin':
#         return jsonify({'code': 403, 'msg': '权限不足'})
        
#     data = request.json
#     if not data.get('username') or not data.get('password'):
#         return jsonify({'code': 400, 'msg': '账号密码不能为空'})

#     if User.query.filter_by(username=data['username']).first():
#         return jsonify({'code': 400, 'msg': '账号已存在'})
        
#     new_user = User()
#     new_user.username = data['username']
#     new_user.password = data['password'] 
#     new_user.role = data.get('role', 'user')
#     new_user.status = data.get('status', 1) # 默认启用
    
#     try:
#         db.session.add(new_user)
#         db.session.commit()
#         return jsonify({'code': 200, 'msg': '用户创建成功'})
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'code': 500, 'msg': str(e)})

# # ✅ 新增：更新用户信息接口
# @user_bp.route('/<int:user_id>', methods=['PUT'])
# @jwt_required()
# def update_user(user_id):
#     """更新用户信息 (修改角色、状态、密码)"""
#     current_user_id = get_jwt_identity()
#     current_user = User.query.get(current_user_id)
    
#     if not current_user or current_user.role != 'admin':
#         return jsonify({'code': 403, 'msg': '权限不足'})

#     user = User.query.get(user_id)
#     if not user:
#         return jsonify({'code': 404, 'msg': '用户不存在'})

#     data = request.json
    
#     # 更新普通字段
#     if 'role' in data:
#         user.role = data['role']
#     if 'status' in data:
#         user.status = int(data['status'])
    
#     # 只有当密码字段不为空时，才更新密码
#     if 'password' in data and data['password']:
#         if len(data['password']) < 5:
#             return jsonify({'code': 400, 'msg': '密码长度不能少于5位'})
#         user.password = data['password'] # setter 自动加密

#     try:
#         db.session.commit()
#         return jsonify({'code': 200, 'msg': '更新成功'})
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'code': 500, 'msg': str(e)})

# @user_bp.route('/<int:user_id>', methods=['DELETE'])
# @jwt_required()
# def delete_user(user_id):
#     # ... (保持原有的删除逻辑不变) ...
#     current_user_id = get_jwt_identity()
#     current_user = User.query.get(current_user_id)
    
#     if not current_user or current_user.role != 'admin':
#         return jsonify({'code': 403, 'msg': '权限不足'})
        
#     if str(user_id) == str(current_user_id):
#         return jsonify({'code': 400, 'msg': '无法删除当前登录账号'})
        
#     user_to_delete = User.query.get(user_id)
#     if user_to_delete:
#         db.session.delete(user_to_delete)
#         db.session.commit()
#         return jsonify({'code': 200, 'msg': '删除成功'})
    
#     return jsonify({'code': 404, 'msg': '用户不存在'})