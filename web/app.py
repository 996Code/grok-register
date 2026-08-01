"""Grok Register Web Control Panel — Flask backend.

Provides REST API + SSE for the Vue frontend.
Controls registration batches, reads/writes config, proxies grok2api admin API.
"""
import glob
import json
import os
import queue
import threading
import time
from datetime import datetime
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

# ── Path setup: make registration modules importable ──
_APP_DIR = Path(__file__).resolve().parent
_REPO_DIR = _APP_DIR.parent
os.chdir(_REPO_DIR)
import sys
sys.path.insert(0, str(_REPO_DIR))

app = Flask(__name__, static_folder=str(_APP_DIR / "static"), static_url_path="")

# ── Global state ──
_register_lock = threading.Lock()
_register_thread = None
_cancel_event = threading.Event()
_event_queues: list[queue.Queue] = []  # SSE subscriber queues
_last_stats = {"success": 0, "fail": 0, "pending": 0, "warnings": 0, "processed": 0, "total": 0, "running": False}


def _broadcast(event_type, data=None):
    """Push an event to all SSE subscribers."""
    msg = {"type": event_type, "data": data or {}}
    for q in _event_queues:
        try:
            q.put_nowait(msg)
        except queue.Full:
            pass


def _make_log_callback():
    def log(msg):
        _broadcast("log", {"line": msg, "time": datetime.now().strftime("%H:%M:%S")})
    return log


def _make_cancel_callback():
    return lambda: _cancel_event.is_set()


def _make_observer():
    def observer(batch, account, output):
        stats = {
            "success": batch.success_count,
            "fail": batch.fail_count,
            "pending": batch.registered_unsaved_count,
            "warnings": batch.postprocess_warning_count,
            "processed": batch.processed_count,
            "total": _last_stats.get("total", 0),
        }
        _last_stats.update(stats)
        if account and account.ok:
            _broadcast("account", {
                "email": account.email,
                "password": account.password,
                "sso": account.sso[:20] + "..." if account.sso else "",
                "saved": output.saved if output else False,
            })
        _broadcast("stats", stats)
    return observer


def _run_registration_task(count):
    """Runs in a background thread."""
    global _register_thread
    try:
        # Import registration modules (heavy imports deferred)
        from grok_register_ttk import run_registration_common
        from app_config import load_config, save_config, validate_run_requirements

        load_config()
        from app_config import config
        try:
            validated = validate_run_requirements(config)
            config.clear()
            config.update(validated)
            save_config()
        except Exception as exc:
            _broadcast("log", {"line": f"[!] 配置校验失败: {exc}", "time": datetime.now().strftime("%H:%M:%S")})
            _broadcast("error", {"message": str(exc)})
            return

        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        accounts_file = str(_REPO_DIR / f"accounts_{now}.txt")

        log_cb = _make_log_callback()
        cancel_cb = _make_cancel_callback()
        observer = _make_observer()

        log_cb(f"[*] Web 控制台启动注册，目标: {count} 个账号")
        log_cb(f"[*] 账号保存到: {accounts_file}")

        run_registration_common(
            count=count,
            log_callback=log_cb,
            cancel_callback=cancel_cb,
            accounts_output_file=accounts_file,
            observer=observer,
        )
        log_cb("[*] 注册任务完成")
        _broadcast("done", {"success": _last_stats["success"], "fail": _last_stats["fail"]})
    except Exception as exc:
        _broadcast("log", {"line": f"[!] 注册任务异常: {exc}", "time": datetime.now().strftime("%H:%M:%S")})
        _broadcast("error", {"message": str(exc)})
    finally:
        _last_stats["running"] = False
        _register_thread = None


# ════════════════════════════════════════════════
# API Routes
# ════════════════════════════════════════════════

@app.route("/api/register/start", methods=["POST"])
def register_start():
    global _register_thread
    if _register_thread and _register_thread.is_alive():
        return jsonify({"error": "已有注册任务在运行"}), 409

    data = request.get_json(silent=True) or {}
    count = int(data.get("count", 1))
    count = max(1, min(2500, count))

    _cancel_event.clear()
    _last_stats.update({"success": 0, "fail": 0, "pending": 0, "warnings": 0, "processed": 0, "total": count, "running": True})

    _register_thread = threading.Thread(target=_run_registration_task, args=(count,), daemon=True)
    _register_thread.start()

    return jsonify({"status": "started", "count": count})


@app.route("/api/register/stop", methods=["POST"])
def register_stop():
    _cancel_event.set()
    _broadcast("log", {"line": "[!] 用户请求停止注册...", "time": datetime.now().strftime("%H:%M:%S")})
    return jsonify({"status": "stopping"})


@app.route("/api/register/status")
def register_status():
    return jsonify(_last_stats)


@app.route("/api/register/stream")
def register_stream():
    """SSE endpoint for real-time log + stats."""
    q: queue.Queue = queue.Queue(maxsize=2000)
    _event_queues.append(q)

    def generate():
        try:
            # Send current state immediately
            yield f"data: {json.dumps({'type': 'stats', 'data': _last_stats})}\n\n"
            while True:
                try:
                    msg = q.get(timeout=15)
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            pass
        finally:
            if q in _event_queues:
                _event_queues.remove(q)

    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    })


@app.route("/api/config", methods=["GET"])
def get_config():
    try:
        from app_config import load_config, config
        load_config()
        return jsonify(dict(config))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/config", methods=["PUT"])
def put_config():
    try:
        from app_config import config, save_config, validate_config_structure
        data = request.get_json(silent=True) or {}
        validated = validate_config_structure(data)
        config.clear()
        config.update(validated)
        save_config()
        return jsonify({"status": "saved"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/accounts", methods=["GET"])
def list_accounts():
    """List all registered accounts from accounts_*.txt files."""
    results = []
    for f in sorted(glob.glob(str(_REPO_DIR / "accounts_*.txt")), reverse=True):
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    parts = line.strip().split("----", 2)
                    if len(parts) == 3:
                        email, password, sso = parts
                        results.append({
                            "email": email,
                            "password": password,
                            "sso": sso[:20] + "..." if len(sso) > 20 else sso,
                            "file": os.path.basename(f),
                        })
        except Exception:
            pass
    return jsonify({"accounts": results, "total": len(results)})


@app.route("/api/accounts/download", methods=["GET"])
def download_accounts():
    """Download the latest accounts file."""
    files = sorted(glob.glob(str(_REPO_DIR / "accounts_*.txt")), reverse=True)
    if not files:
        return jsonify({"error": "没有账号文件"}), 404
    return send_from_directory(_REPO_DIR, os.path.basename(files[0]), as_attachment=True)


@app.route("/api/pending", methods=["GET"])
def list_pending():
    """List pending files and their counts."""
    results = []
    for f in sorted(glob.glob(str(_REPO_DIR / "*.pending.jsonl")), reverse=True):
        count = 0
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                for _ in fh:
                    count += 1
        except Exception:
            pass
        results.append({"file": os.path.basename(f), "count": count})
    return jsonify({"pending": results})


@app.route("/api/pending/retry", methods=["POST"])
def retry_pending():
    """Retry a pending file."""
    data = request.get_json(silent=True) or {}
    pending_file = data.get("file", "")
    if not pending_file:
        return jsonify({"error": "缺少 file 参数"}), 400
    pending_path = str(_REPO_DIR / pending_file)
    if not os.path.isfile(pending_path):
        return jsonify({"error": f"文件不存在: {pending_file}"}), 404
    try:
        from account_outputs import retry_pending_file
        retry_pending_file(pending_path)
        return jsonify({"status": "ok"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ── grok2api proxy ──

@app.route("/api/grok2api/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy_grok2api(path):
    """Proxy requests to grok2api admin API."""
    import requests as req
    from app_config import config

    base = str(config.get("grok2api_remote_base", "") or "http://grok2api:8000").strip().rstrip("/")
    # Normalize base URL
    for suffix in ("/api/admin/v1", "/admin/api", "/admin"):
        if base.lower().endswith(suffix):
            base = base[:-len(suffix)].rstrip("/")
            break

    url = f"{base}/api/admin/v1/{path}"

    # Forward request
    headers = {k: v for k, v in request.headers if k.lower() not in ("host", "content-length")}
    try:
        resp = req.request(
            method=request.method,
            url=url,
            headers=headers,
            json=request.get_json(silent=True) if request.is_json else None,
            data=request.get_data() if not request.is_json else None,
            params=request.args,
            timeout=30,
            proxies={},
        )
        # Forward response
        excluded = {"content-encoding", "transfer-encoding", "connection"}
        response_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded]
        return Response(resp.content, status=resp.status_code, headers=response_headers)
    except Exception as exc:
        return jsonify({"error": f"代理请求失败: {exc}"}), 502


# ── SPA fallback ──

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path):
    static_dir = _APP_DIR / "static"
    if path and (static_dir / path).exists():
        return send_from_directory(static_dir, path)
    index = static_dir / "index.html"
    if index.exists():
        return send_from_directory(static_dir, "index.html")
    return jsonify({"status": "ok", "message": "Grok Register Web API. Frontend not built yet."})


if __name__ == "__main__":
    port = int(os.environ.get("WEB_PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
