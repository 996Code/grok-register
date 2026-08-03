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

# Use writable data directory for config (avoid volume mount issues)
_DATA_DIR = _REPO_DIR / "data"
_DATA_DIR.mkdir(exist_ok=True)
_CONFIG_FILE = _DATA_DIR / "config.json"

# If config.json exists in repo root but not in data dir, copy it
if (_REPO_DIR / "config.json").exists() and not _CONFIG_FILE.exists():
    import shutil
    shutil.copy2(_REPO_DIR / "config.json", _CONFIG_FILE)

os.chdir(_REPO_DIR)
import sys
sys.path.insert(0, str(_REPO_DIR))

# Patch app_config to use data dir for config file
import app_config
app_config.CONFIG_FILE = str(_CONFIG_FILE)

app = Flask(__name__, static_folder=str(_APP_DIR / "static"), static_url_path="")

# ── Global state ──
_register_lock = threading.Lock()
_register_thread = None
_cancel_event = threading.Event()
_event_queues: list[queue.Queue] = []
_event_queues_lock = threading.Lock()
_last_stats = {
    "success": 0, "fail": 0, "pending": 0, "warnings": 0,
    "processed": 0, "total": 0, "running": False,
}

# Load config once at startup so proxy_grok2api has correct base URL
try:
    from app_config import load_config
    load_config()
except Exception:
    pass

# Cache for client key full secrets (grok2api only returns prefix on list)
_KEY_CACHE_FILE = _REPO_DIR / "data" / ".key_cache.json"


def _load_key_cache():
    try:
        with open(_KEY_CACHE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_key_cache(cache):
    try:
        with open(_KEY_CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass


def _broadcast(event_type, data=None):
    """Push an event to all SSE subscribers (thread-safe)."""
    msg = {"type": event_type, "data": data or {}}
    with _event_queues_lock:
        subscribers = list(_event_queues)
    for q in subscribers:
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


def _run_registration_task(total_count, batch_size=100, interval_sec=0):
    """Runs in a background thread. Registers in batches with optional interval."""
    global _register_thread
    try:
        from grok_register_ttk import run_registration_common
        from app_config import load_config, save_config, validate_run_requirements, config

        load_config()
        try:
            validated = validate_run_requirements(config)
            config.clear()
            config.update(validated)
            save_config()
        except Exception as exc:
            _broadcast("log", {"line": f"[!] 配置校验失败: {exc}", "time": datetime.now().strftime("%H:%M:%S")})
            _broadcast("error", {"message": str(exc)})
            return

        log_cb = _make_log_callback()
        cancel_cb = _make_cancel_callback()
        observer = _make_observer()

        remaining = total_count
        batch_num = 0
        total_success = 0
        total_fail = 0

        while remaining > 0:
            if _cancel_event.is_set():
                log_cb("[!] 用户停止，结束注册")
                break

            batch_num += 1
            this_batch = min(batch_size, remaining)
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            accounts_file = str(_REPO_DIR / f"accounts_{now}.txt")

            log_cb(f"[*] ═══ 第 {batch_num} 批，本轮 {this_batch} 个 (总计目标 {total_count}) ═══")

            # Reset per-batch counters in stats
            _last_stats["processed"] = 0
            _last_stats["total"] = this_batch
            _broadcast("stats", dict(_last_stats))

            run_registration_common(
                count=this_batch,
                log_callback=log_cb,
                cancel_callback=cancel_cb,
                accounts_output_file=accounts_file,
                observer=observer,
            )

            total_success += _last_stats.get("success", 0)
            total_fail += _last_stats.get("fail", 0)
            remaining -= this_batch

            log_cb(f"[*] 第 {batch_num} 批完成。累计: 成功 {total_success} / 失败 {total_fail} / 剩余 {remaining}")

            # Interval between batches
            if remaining > 0 and interval_sec > 0 and not _cancel_event.is_set():
                log_cb(f"[*] 等待 {interval_sec} 秒后继续下一批...")
                _last_stats["waiting"] = True
                _last_stats["next_batch_in"] = interval_sec
                _broadcast("stats", dict(_last_stats))

                for i in range(interval_sec):
                    if _cancel_event.is_set():
                        break
                    time.sleep(1)
                    _last_stats["next_batch_in"] = interval_sec - i - 1
                    if i % 10 == 0 or i == interval_sec - 1:
                        _broadcast("stats", dict(_last_stats))

                _last_stats["waiting"] = False
                if not _cancel_event.is_set():
                    log_cb(f"[*] 间隔结束，继续注册")

        _last_stats["success"] = total_success
        _last_stats["fail"] = total_fail
        _last_stats["total"] = total_count
        _last_stats["processed"] = total_success + total_fail
        log_cb(f"[*] 全部注册任务完成！总计: 成功 {total_success} / 失败 {total_fail}")
        _broadcast("done", {"success": total_success, "fail": total_fail})
    except Exception as exc:
        _broadcast("log", {"line": f"[!] 注册任务异常: {exc}", "time": datetime.now().strftime("%H:%M:%S")})
        _broadcast("error", {"message": str(exc)})
    finally:
        _last_stats["running"] = False
        _last_stats["waiting"] = False
        _register_thread = None


# ════════════════════════════════════════════════
# Registration Control API
# ════════════════════════════════════════════════

@app.route("/api/register/start", methods=["POST"])
def register_start():
    global _register_thread
    if _register_thread and _register_thread.is_alive():
        return jsonify({"error": "已有注册任务在运行"}), 409

    data = request.get_json(silent=True) or {}
    try:
        count = int(data.get("count", 1))
    except (ValueError, TypeError):
        return jsonify({"error": "count 必须是整数"}), 400
    count = max(1, min(2500, count))

    try:
        batch_size = int(data.get("batch_size", 100))
    except (ValueError, TypeError):
        batch_size = 100
    batch_size = max(1, min(500, batch_size))

    try:
        interval = int(data.get("interval", 0))
    except (ValueError, TypeError):
        interval = 0
    interval = max(0, min(86400, interval))

    _cancel_event.clear()
    _last_stats.update({
        "success": 0, "fail": 0, "pending": 0, "warnings": 0,
        "processed": 0, "total": count, "running": True,
        "waiting": False, "next_batch_in": 0,
    })

    _register_thread = threading.Thread(
        target=_run_registration_task,
        args=(count, batch_size, interval),
        daemon=True,
    )
    _register_thread.start()

    return jsonify({"status": "started", "count": count, "batch_size": batch_size, "interval": interval})

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
    with _event_queues_lock:
        _event_queues.append(q)

    def generate():
        try:
            yield f"data: {json.dumps({'type': 'stats', 'data': _last_stats}, ensure_ascii=False)}\n\n"
            while True:
                try:
                    msg = q.get(timeout=15)
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            pass
        finally:
            with _event_queues_lock:
                if q in _event_queues:
                    _event_queues.remove(q)

    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    })


# ════════════════════════════════════════════════
# Config API
# ════════════════════════════════════════════════

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


# ════════════════════════════════════════════════
# Accounts API
# ════════════════════════════════════════════════

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
                            "sso_full": sso,
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


@app.route("/api/accounts/<int:idx>/check", methods=["POST"])
def check_account_alive(idx):
    """Check if an account's SSO token is still alive by calling grok2api.
    idx is the index in the accounts list."""
    accounts = []
    for f in sorted(glob.glob(str(_REPO_DIR / "accounts_*.txt")), reverse=True):
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    parts = line.strip().split("----", 2)
                    if len(parts) == 3:
                        accounts.append({"email": parts[0], "sso": parts[2]})
        except Exception:
            pass

    if idx >= len(accounts):
        return jsonify({"error": "账号不存在"}), 404

    account = accounts[idx]
    sso = account["sso"]

    # Check via grok2api: import and see if sync succeeds
    import requests as req
    try:
        from app_config import config
        load_config()
        base = str(config.get("grok2api_remote_base", "") or "http://grok2api:8000").strip().rstrip("/")
        for suffix in ("/api/admin/v1", "/admin/api", "/admin"):
            if base.lower().endswith(suffix):
                base = base[:-len(suffix)].rstrip("/")
                break
        api_base = base + "/api/admin/v1"

        username = str(config.get("grok2api_remote_admin_username", "")).strip()
        password = str(config.get("grok2api_remote_admin_password", "")).strip()

        if not username or not password:
            return jsonify({"error": "未配置 grok2api 管理员账号"}), 400

        # Login
        login_resp = req.post(
            f"{api_base}/auth/login",
            json={"username": username, "password": password},
            timeout=15, proxies={},
        )
        token = login_resp.json().get("data", {}).get("tokens", {}).get("accessToken", "")

        # Import SSO and check sync result
        from curl_cffi import CurlMime
        multipart = CurlMime()
        multipart.addpart(
            name="file", filename="check-sso.txt",
            content_type="text/plain; charset=utf-8",
            data=(sso + "\n").encode("utf-8"),
        )
        resp = req.post(
            f"{api_base}/accounts/web/import",
            headers={"Authorization": f"Bearer {token}", "Accept": "text/event-stream"},
            multipart=multipart, timeout=60, proxies={},
        )
        multipart.close()

        # Parse SSE for complete event
        synced = 0
        sync_failed = 0
        created = 0
        for line in resp.text.split("\n"):
            if line.startswith("data:") and "complete" in line:
                try:
                    data = json.loads(line[5:].strip())
                    synced = data.get("synced", 0)
                    sync_failed = data.get("syncFailed", 0)
                    created = data.get("created", 0)
                except Exception:
                    pass

        alive = synced > 0 and sync_failed == 0
        return jsonify({
            "email": account["email"],
            "alive": alive,
            "synced": synced,
            "syncFailed": sync_failed,
            "created": created,
            "message": "SSO 有效" if alive else "SSO 失效或同步失败",
        })
    except Exception as exc:
        return jsonify({"error": f"检测失败: {exc}"}), 500


# ════════════════════════════════════════════════
# Pending API
# ════════════════════════════════════════════════

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
    """Retry a pending file. Returns restored/remaining counts."""
    data = request.get_json(silent=True) or {}
    pending_file = data.get("file", "")
    if not pending_file:
        return jsonify({"error": "缺少 file 参数"}), 400
    pending_path = str(_REPO_DIR / pending_file)
    if not os.path.isfile(pending_path):
        return jsonify({"error": f"文件不存在: {pending_file}"}), 404
    try:
        from account_outputs import retry_pending_file
        result = retry_pending_file(pending_path)
        return jsonify({
            "status": "ok",
            "restored": result.get("restored", 0) if isinstance(result, dict) else 0,
            "remaining": result.get("remaining", 0) if isinstance(result, dict) else 0,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ════════════════════════════════════════════════
# Token Pool API — manual push to local/remote pools
# ════════════════════════════════════════════════

@app.route("/api/tokens/add", methods=["POST"])
def add_token_to_pools():
    """Manually push an SSO token to grok2api pools (local and/or remote)."""
    data = request.get_json(silent=True) or {}
    sso = str(data.get("sso", "")).strip()
    email = str(data.get("email", "")).strip()
    if not sso:
        return jsonify({"error": "缺少 sso 参数"}), 400
    try:
        from app_config import load_config, config
        load_config()
        # Sync config into account_outputs module
        import account_outputs
        account_outputs.config.clear()
        account_outputs.config.update(config)
        # Provide required helpers if not yet bound
        if not getattr(account_outputs, "_web_runtime_bound", False):
            from browser_runtime import http_get, http_post
            account_outputs.log_exception = lambda ctx, exc, cb=None: str(exc)
            account_outputs.http_get = http_get
            account_outputs.http_post = http_post
            account_outputs._web_runtime_bound = True
        result = account_outputs.add_token_to_grok2api_pools(sso, email=email, log_callback=lambda m: None)
        return jsonify({"status": "ok", "result": result})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/tokens/local-file", methods=["GET"])
def get_local_token_file():
    """Return the resolved local token file path."""
    try:
        from app_config import load_config, config
        load_config()
        from account_outputs import resolve_grok2api_local_token_file
        path = resolve_grok2api_local_token_file()
        exists = os.path.isfile(path)
        size = os.path.getsize(path) if exists else 0
        return jsonify({"path": path, "exists": exists, "size": size})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ════════════════════════════════════════════════
# Config Validation API
# ════════════════════════════════════════════════

@app.route("/api/config/validate", methods=["POST"])
def validate_config():
    """Pre-flight validate config without saving. Returns errors or OK."""
    try:
        from app_config import validate_run_requirements
        data = request.get_json(silent=True) or {}
        validated = validate_run_requirements(data)
        return jsonify({"status": "ok"})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400


# ════════════════════════════════════════════════
# Mail Test API — test email provider connection
# ════════════════════════════════════════════════

@app.route("/api/mail/domains", methods=["GET"])
def mail_domains():
    """List available domains for the current email provider."""
    try:
        from app_config import load_config, config
        load_config()
        provider = str(config.get("email_provider", "duckmail"))
        if provider == "duckmail":
            from mail_service import get_domains, _get_duckmail_api_base, _duckmail_direct_kwargs
            api_key = config.get("duckmail_api_key", "")
            domains = get_domains(api_key=api_key if api_key else None)
            return jsonify({"provider": provider, "domains": [d.get("domain", "") for d in domains]})
        elif provider == "cloudflare":
            from mail_service import cloudflare_get_domains
            api_base = config.get("cloudflare_api_base", "")
            api_key = config.get("cloudflare_api_key", "")
            domains = cloudflare_get_domains(api_base, api_key=api_key if api_key else None)
            return jsonify({"provider": provider, "domains": domains if isinstance(domains, list) else []})
        elif provider == "yyds":
            from mail_service import yyds_get_domains
            api_key = config.get("yyds_api_key", "")
            jwt = config.get("yyds_jwt", "")
            domains = yyds_get_domains(api_key=api_key if api_key else None, jwt=jwt if jwt else None)
            return jsonify({"provider": provider, "domains": domains if isinstance(domains, list) else []})
        else:
            return jsonify({"provider": provider, "domains": str(config.get("cloudmail_domains", "")).split(",")})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/mail/test", methods=["POST"])
def mail_test():
    """Test email provider by creating a temp mailbox."""
    try:
        from app_config import load_config, config
        load_config()
        # Bind mail service runtime
        import grok_register_ttk
        grok_register_ttk._bind_mail_service()
        from mail_service import get_email_and_token
        api_key = config.get("duckmail_api_key", "")
        address, token = get_email_and_token(api_key=api_key if api_key else None)
        if address:
            return jsonify({"status": "ok", "address": address, "message": "邮箱创建成功"})
        else:
            return jsonify({"status": "error", "message": "创建邮箱失败"}), 400
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


# ════════════════════════════════════════════════
# CPA Credential API
# ════════════════════════════════════════════════

@app.route("/api/cpa/credentials", methods=["GET"])
def cpa_credentials():
    """List CPA xAI credential files with email/expiry."""
    try:
        from app_config import load_config, config
        load_config()
        auth_dir = str(config.get("cpa_auth_dir", "./cpa_auths"))
        if not os.path.isabs(auth_dir):
            auth_dir = str(_REPO_DIR / auth_dir)
        results = []
        for f in sorted(glob.glob(os.path.join(auth_dir, "xai-*.json"))):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                results.append({
                    "file": os.path.basename(f),
                    "email": data.get("email", ""),
                    "expired": data.get("expired", ""),
                    "base_url": data.get("base_url", ""),
                })
            except Exception:
                pass
        return jsonify({"credentials": results, "total": len(results)})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/cpa/failures", methods=["GET"])
def cpa_failures():
    """List CPA mint failure records."""
    try:
        from app_config import load_config, config
        load_config()
        auth_dir = str(config.get("cpa_auth_dir", "./cpa_auths"))
        if not os.path.isabs(auth_dir):
            auth_dir = str(_REPO_DIR / auth_dir)
        fail_file = os.path.join(auth_dir, "cpa_auth_failed.txt")
        results = []
        if os.path.isfile(fail_file):
            with open(fail_file, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    parts = line.strip().split("----", 2)
                    if len(parts) >= 2:
                        results.append({"email": parts[0], "error": parts[1] if len(parts) > 1 else ""})
        return jsonify({"failures": results, "total": len(results)})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ════════════════════════════════════════════════
# grok2api Proxy (auto-login, no manual auth needed)
# ════════════════════════════════════════════════

_grok2api_token_cache = {"token": "", "expires": 0}


def _get_grok2api_token():
    """Auto-login to grok2api using config credentials, cache the token."""
    import time
    import requests as req
    from app_config import config, load_config
    load_config()

    # Return cached token if still valid
    if _grok2api_token_cache["token"] and _grok2api_token_cache["expires"] > time.time() + 60:
        return _grok2api_token_cache["token"]

    username = str(config.get("grok2api_remote_admin_username", "")).strip()
    password = str(config.get("grok2api_remote_admin_password", "")).strip()
    if not username or not password:
        return None

    base = str(config.get("grok2api_remote_base", "") or "http://grok2api:8000").strip().rstrip("/")
    for suffix in ("/api/admin/v1", "/admin/api", "/admin"):
        if base.lower().endswith(suffix):
            base = base[:-len(suffix)].rstrip("/")
            break
    api_base = base + "/api/admin/v1"

    try:
        resp = req.post(f"{api_base}/auth/login", json={"username": username, "password": password}, timeout=15, proxies={})
        token = resp.json().get("data", {}).get("tokens", {}).get("accessToken", "")
        if token:
            _grok2api_token_cache["token"] = token
            _grok2api_token_cache["expires"] = time.time() + 840  # 14 min
            return token
    except Exception:
        pass
    return None


@app.route("/api/grok2api/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy_grok2api(path):
    """Proxy requests to grok2api admin API with auto-login."""
    import requests as req
    from app_config import config, load_config
    load_config()

    token = _get_grok2api_token()
    if not token and not path.startswith("auth/"):
        return jsonify({"error": "无法自动登录 grok2api，请检查配置中的管理员账号密码"}), 401

    base = str(config.get("grok2api_remote_base", "") or "http://grok2api:8000").strip().rstrip("/")
    for suffix in ("/api/admin/v1", "/admin/api", "/admin"):
        if base.lower().endswith(suffix):
            base = base[:-len(suffix)].rstrip("/")
            break

    url = f"{base}/api/admin/v1/{path}"

    # Auto-inject auth token (unless it's a login request)
    headers = {}
    if not path.startswith("auth/"):
        headers["Authorization"] = f"Bearer {token}"
    # Also forward client-provided headers
    for k, v in request.headers:
        if k.lower() not in ("host", "content-length", "authorization"):
            headers[k] = v
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

        # Intercept client-keys responses to cache/inject full secrets
        if "client-keys" in path and resp.status_code == 200:
            try:
                body = resp.json()
                # Cache secret on create
                if request.method == "POST" and "secret" in body.get("data", {}):
                    secret = body["data"]["secret"]
                    prefix = body["data"].get("key", {}).get("prefix", "")
                    cache = _load_key_cache()
                    cache[prefix] = secret
                    _save_key_cache(cache)
                # Inject cached secrets on list
                elif request.method == "GET" and "items" in body.get("data", {}):
                    cache = _load_key_cache()
                    for item in body["data"]["items"]:
                        prefix = item.get("prefix", "")
                        if prefix in cache:
                            item["fullSecret"] = cache[prefix]
                    return jsonify(body)
            except Exception:
                pass

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
