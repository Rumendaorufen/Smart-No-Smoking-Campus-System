from flask import Flask, jsonify, request

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


@app.post("/api/agent/chat")
def chat():
    body = request.get_json(silent=True) or {}
    message = str(body.get("message", "")).strip()
    conversation_id = str(body.get("conversationId", "")).strip() or None

    if not message:
        return jsonify({"code": 400, "msg": "message is required", "data": None}), 400

    try:
        result = agent_service.ask(message)
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
        return jsonify({"code": 500, "msg": str(exc), "data": None}), 500


if __name__ == "__main__":
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
