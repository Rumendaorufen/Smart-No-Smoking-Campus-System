from flask import Flask, jsonify, request, Response, stream_with_context
import re
from agent_service import AgentService
from config import get_settings

settings = get_settings()
agent_service = AgentService(settings)
app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(
        {
            "code": 200,
            "msg": "ok",
            "data": {
                "service": "web-agent",
                "model": settings.openai_model,
                "includeTables": settings.include_tables,
            },
        }
    )

# 🚀 新增：流式对话接口
@app.post("/api/agent/chat/stream")
def chat_stream():
    body = request.get_json(silent=True) or {}
    message = str(body.get("message", "")).strip()
    conversation_id = str(body.get("conversationId", "")).strip()

    if not message or not conversation_id:
        return jsonify({"code": 400, "msg": "参数缺失"}), 400

    try:
        def generate_sse():
            generator = agent_service.ask_stream(message, conversation_id)
            for chunk in generator:
                # 🚀 物理拦截残留 SQL
                clean = re.sub(r'SELECT.*?(LIMIT\s+\d+|;)', '', chunk, flags=re.IGNORECASE | re.DOTALL)
                if not clean.strip() and chunk.strip(): continue
                
                # 把空格伪装成 <<sp>>，完美躲过任何网络层的自动裁剪
                safe_chunk = clean.replace('\n', '<<br>>').replace(' ', '<<sp>>')
                yield f"data: {safe_chunk}\n\n"
        
        return Response(stream_with_context(generate_sse()), mimetype='text/event-stream')
    except Exception as exc:
        return jsonify({"code": 500, "msg": str(exc)}), 500
    
@app.post("/api/agent/chat")
def chat():
    body = request.get_json(silent=True) or {}
    message = str(body.get("message", "")).strip()
    # 获取 conversationId
    conversation_id = str(body.get("conversationId", "")).strip()

    # 🚀 1. 严格校验：消息和会话ID都不能缺
    if not message:
        return jsonify({"code": 400, "msg": "message is required", "data": None}), 400
    
    if not conversation_id:
        return jsonify({"code": 400, "msg": "conversationId is required", "data": None}), 400

    try:
        # 🚀 2. 正确调用：传入 conversation_id
        result = agent_service.ask(message, conversation_id)
        
        return jsonify(
            {
                "code": 200,
                "msg": "success",
                "data": {
                    "conversationId": conversation_id,
                    "answer": result["answer"],
                },
            }
        )
    except Exception as exc:
        # 打印一下具体的错误栈到控制台，方便后续排查
        import traceback
        traceback.print_exc()
        return jsonify({"code": 500, "msg": str(exc), "data": None}), 500


if __name__ == "__main__":
    app.run(host=settings.host, port=settings.port, debug=settings.debug)