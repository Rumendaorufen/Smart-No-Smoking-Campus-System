from app import create_app

app = create_app()

if __name__ == '__main__':
    # threaded=True 允许多个浏览器同时看视频流
    print("🚀 服务启动: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)