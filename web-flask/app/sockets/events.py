# # SocketIO事件处理
# from flask_socketio import emit, join_room, leave_room

# # 连接事件
# @socketio.on('connect')
# def handle_connect():
#     """
#     客户端连接事件
#     """
#     print('客户端已连接')
#     emit('connection_response', {'message': '连接成功'})

# # 断开连接事件
# @socketio.on('disconnect')
# def handle_disconnect():
#     """
#     客户端断开连接事件
#     """
#     print('客户端已断开连接')

# # 房间事件
# @socketio.on('join_room')
# def handle_join_room(data):
#     """
#     客户端加入房间
#     """
#     room = data.get('room')
#     join_room(room)
#     emit('joined_room', {'room': room, 'message': f'已加入房间 {room}'})

# @socketio.on('leave_room')
# def handle_leave_room(data):
#     """
#     客户端离开房间
#     """
#     room = data.get('room')
#     leave_room(room)
#     emit('left_room', {'room': room, 'message': f'已离开房间 {room}'})

# # 报警推送事件
# def push_alert(alert_data):
#     """
#     推送报警信息给客户端
    
#     Args:
#         alert_data: 报警数据
#     """
#     socketio.emit('server_push_alert', alert_data, broadcast=True)

# # 设备状态更新事件
# def update_device_status(device_id, status):
#     """
#     更新设备状态
    
#     Args:
#         device_id: 设备ID
#         status: 设备状态
#     """
#     socketio.emit('device_status_update', {
#         'device_id': device_id,
#         'status': status
#     }, broadcast=True)
