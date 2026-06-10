"""Health check and metrics endpoints for the alert engine."""
import psutil
from flask import Blueprint, jsonify

health_bp = Blueprint('health', __name__)


@health_bp.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "service": "web-flask",
        "uptime_seconds": _uptime()
    })


@health_bp.route('/metrics')
def metrics():
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return jsonify({
        "cpu": {
            "percent": psutil.cpu_percent(interval=0.1)
        },
        "memory": {
            "total_gb": round(mem.total / 1024**3, 1),
            "used_gb": round(mem.used / 1024**3, 1),
            "percent": mem.percent
        },
        "disk": {
            "total_gb": round(disk.total / 1024**3, 1),
            "used_gb": round(disk.used / 1024**3, 1),
            "percent": disk.percent
        }
    })


def _uptime():
    """Return process uptime in seconds."""
    try:
        import time
        p = psutil.Process()
        return round(time.time() - p.create_time())
    except Exception:
        return -1
