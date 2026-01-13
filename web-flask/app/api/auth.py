from flask import Blueprint, request, jsonify
from app.models import db
from app.models.user import User
from datetime import datetime
import time
# ✅ 引入 JWT 核心模块
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

auth_bp = Blueprint('auth', __name__)

def get_real_ip():
    """
    获取客户端真实公网 IP
    优先读取 X-Forwarded-For (反向代理透传)，其次读取 X-Real-IP，最后使用 remote_addr
    """
    # 1. 尝试获取 X-Forwarded-For (格式: client, proxy1, proxy2)
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        # 取第一个 IP，通常是真实客户端 IP
        return x_forwarded_for.split(',')[0].strip()
    
    # 2. 尝试获取 X-Real-IP (Nginx 常用)
    x_real_ip = request.headers.get('X-Real-IP')
    if x_real_ip:
        return x_real_ip
        
    # 3. 回退到直接连接 IP (开发环境/直连)
    return request.remote_addr

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录接口 (生成 JWT)"""
    try:
        data = request.json
        if not data:
            return jsonify({'code': 400, 'msg': '请求参数为空'})

        username = data.get('username')
        password = data.get('password')

        # 1. 基础校验
        if not username or not password:
            return jsonify({'code': 400, 'msg': '请输入账号和密码'})

        # 2. 查询用户
        user = User.query.filter_by(username=username).first()

        # 3. 验证账号是否存在
        if not user:
            return jsonify({'code': 401, 'msg': '账号不存在'})

        # 4. 验证密码 (verify_password 是 model 中定义的方法)
        if not user.verify_password(password):
            return jsonify({'code': 401, 'msg': '密码错误'})
            
        # 5. ✅ 检查账号状态 (关键逻辑)
        # 如果 status 不为 1 (例如 0 表示禁用)，则拒绝登录
        if user.status != 1:
            return jsonify({
                'code': 403, 
                'msg': '该账号已被禁用，请联系管理员'
            })

        # 6. 更新登录审计信息 (时间和IP)
        client_ip = get_real_ip()
        user.last_login_time = datetime.now()
        user.last_login_ip = client_ip
        
        # 提交事务
        db.session.commit()

        print(f"👤 用户 [{username}] 登录成功 | IP: {client_ip}")

        # 7. ✅ 生成 JWT Access Token
        # identity: 通常存用户主键 ID (必须是字符串)
        # additional_claims: 存一些前端常用的非敏感信息，如角色、用户名
        access_token = create_access_token(
            identity=str(user.id), 
            additional_claims={
                "username": user.username,
                "role": user.role
            }
        )

        return jsonify({
            'code': 200,
            'msg': '登录成功',
            'data': {
                'token': access_token,  # 前端拿到这个串后，存入 localStorage
                'userInfo': user.to_dict()
            }
        })

    except Exception as e:
        db.session.rollback()
        print(f"❌ 登录接口异常: {str(e)}")
        return jsonify({'code': 500, 'msg': '服务器内部错误'})

@auth_bp.route('/logout', methods=['POST'])
@jwt_required() # ✅ 只有登录过的用户带 Token 才能调用
def logout():
    """退出登录"""
    # 获取当前用户 ID (从 Token 解析出来的)
    current_user_id = get_jwt_identity()
    print(f"👋 用户 ID {current_user_id} 执行登出")
    
    # 简单的 JWT 登出只需前端丢弃 Token 即可
    # 如果需要严格登出（让 Token 即刻失效），需要配合 Redis 做 Token 黑名单（进阶功能）
    return jsonify({'code': 200, 'msg': '退出成功'})

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user_info():
    """获取当前登录用户信息 (用于页面刷新后重新校验 Token)"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'code': 401, 'msg': '用户不存在'})
            
        return jsonify({
            'code': 200, 
            'data': user.to_dict()
        })
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e)})