# from flask import Blueprint, request, jsonify
# from app.models import db
# from app.models.user import User
# from datetime import datetime
# # 引入 JWT
# from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

# auth_bp = Blueprint('auth', __name__)

# def get_real_ip():
#     """获取真实IP地址"""
#     # 1. 优先获取反向代理传过来的 X-Forwarded-For
#     x_forwarded_for = request.headers.get('X-Forwarded-For')
#     if x_forwarded_for:
#         return x_forwarded_for.split(',')[0].strip()
    
#     # 2. 其次获取 X-Real-IP
#     x_real_ip = request.headers.get('X-Real-IP')
#     if x_real_ip:
#         return x_real_ip
        
#     # 3. 最后获取直连 IP
#     return request.remote_addr

# @auth_bp.route('/login', methods=['POST'])
# def login():
#     try:
#         data = request.json
#         username = data.get('username')
#         password = data.get('password')

#         if not username or not password:
#             return jsonify({'code': 400, 'msg': '请输入账号和密码'})

#         user = User.query.filter_by(username=username).first()

#         if not user:
#             return jsonify({'code': 401, 'msg': '账号不存在'})

#         if not user.verify_password(password):
#             return jsonify({'code': 401, 'msg': '密码错误'})
            
#         if user.status != 1:
#             return jsonify({'code': 403, 'msg': '该账号已被禁用'})

#         # ✅ 核心修复：获取并更新 IP
#         client_ip = get_real_ip()
        
#         # 💡 调试打印：在终端看看获取到了什么
#         print(f"🔍 正在记录登录 IP: {client_ip}")

#         user.last_login_time = datetime.now()
#         user.last_login_ip = client_ip  # 赋值给数据库模型
        
#         # 提交到数据库
#         db.session.commit()

#         # 生成 Token
#         access_token = create_access_token(
#             identity=str(user.id), 
#             additional_claims={"username": user.username, "role": user.role}
#         )

#         return jsonify({
#             'code': 200,
#             'msg': '登录成功',
#             'data': {
#                 'token': access_token,
#                 'userInfo': user.to_dict()
#             }
#         })

#     except Exception as e:
#         db.session.rollback()
#         print(f"❌ 登录异常: {str(e)}")
#         return jsonify({'code': 500, 'msg': '服务器内部错误'})

# @auth_bp.route('/logout', methods=['POST'])
# @jwt_required()
# def logout():
#     return jsonify({'code': 200, 'msg': '退出成功'})

# @auth_bp.route('/me', methods=['GET'])
# @jwt_required()
# def get_current_user_info():
#     current_user_id = get_jwt_identity()
#     user = User.query.get(current_user_id)
#     if not user:
#         return jsonify({'code': 401, 'msg': '用户不存在'})
#     return jsonify({'code': 200, 'data': user.to_dict()})