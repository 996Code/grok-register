"""提供共享的 HTTP 请求、代理处理和 Chromium 启动参数。"""
import os
import urllib.parse

from DrissionPage import ChromiumOptions
from curl_cffi import requests
from cpa_xai.proxyutil import (
    LocalAuthProxyBridge,
    prepare_chromium_proxy,
    proxy_for_chromium,
)

_config = {}
_extension_path = ""


def configure_runtime(config_ref, extension_path=""):
    global _config, _extension_path
    _config = config_ref
    _extension_path = str(extension_path or "")


def get_configured_proxy():
    return str(_config.get("proxy", "") or "").strip()


def get_proxies():
    proxy = get_configured_proxy()
    return {"http": proxy, "https": proxy} if proxy else {}


def _parse_proxy_url(proxy):
    raw = str(proxy or "").strip()
    if not raw:
        return None
    if "://" not in raw:
        raw = "http://" + raw
    try:
        return urllib.parse.urlsplit(raw)
    except Exception:
        return None


def _safe_proxy_port(parsed):
    try:
        return parsed.port
    except Exception:
        return None


def _proxy_has_auth(proxy):
    parsed = _parse_proxy_url(proxy)
    return bool(parsed and parsed.hostname and (parsed.username is not None or parsed.password is not None))


def _strip_proxy_auth(proxy):
    raw = str(proxy or "").strip()
    parsed = _parse_proxy_url(raw)
    if not parsed or not parsed.hostname:
        return raw
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = "[%s]" % host
    port = _safe_proxy_port(parsed)
    netloc = "%s:%s" % (host, port) if port else host
    stripped = urllib.parse.urlunsplit((parsed.scheme or "http", netloc, parsed.path, parsed.query, parsed.fragment))
    return stripped.split("://", 1)[1] if "://" not in raw else stripped


def _proxy_endpoint_terms(proxy=None):
    parsed = _parse_proxy_url(proxy or get_configured_proxy())
    if not parsed or not parsed.hostname:
        return []
    terms = [parsed.hostname]
    port = _safe_proxy_port(parsed)
    if port:
        terms.extend(["%s:%s" % (parsed.hostname, port), "port %s" % port])
    return [item.lower() for item in terms if item]


def is_proxy_connection_error(exc):
    if not get_configured_proxy():
        return False
    err = str(exc or "").lower()
    if not err:
        return False
    if any(item in err for item in ("proxy", "tunnel", "socks")):
        return True
    # curl_cffi 的 TLS 错误通过代理时出现，直连通常正常，应触发直连回退
    if any(item in err for item in ("tls connect error", "tls error", "ssl error", "invalid library")):
        return True
    # curl_cffi 通过代理时的连接超时，直连可能正常（如 DuckMail 直连可达）
    if "curl:" in err and "timed out" in err:
        return True
    markers = (
        "could not connect", "failed to connect", "connection refused",
        "connection reset", "connect error", "timed out", "timeout",
    )
    if any(item in err for item in markers):
        terms = _proxy_endpoint_terms()
        return not terms or any(term in err for term in terms)
    return False


def page_has_proxy_error(page_obj):
    try:
        url = str(getattr(page_obj, "url", "") or "")
        title = str(page_obj.run_js("return document.title || ''") or "")
        body = str(page_obj.run_js("return document.body ? document.body.innerText.slice(0, 2000) : ''") or "")
    except Exception:
        return False
    text = "%s\n%s\n%s" % (url, title, body)
    text = text.lower()
    return any(marker in text for marker in (
        "err_proxy", "proxy connection failed", "proxy server",
        "proxy authentication", "tunnel connection failed",
        "无法连接到代理服务器", "代理服务器",
    ))


def prepare_browser_proxy(use_proxy=True, log_callback=None):
    proxy = get_configured_proxy()
    if not use_proxy or not proxy:
        return "", None
    parsed = _parse_proxy_url(proxy)
    if _proxy_has_auth(proxy) and parsed and (parsed.scheme or "http").lower() not in ("http", "https"):
        stripped = _strip_proxy_auth(proxy)
        if log_callback:
            log_callback("[!] Chromium 暂不直接支持该认证代理协议，已使用去认证代理地址，失败将回退直连")
        return stripped, None
    logger = None
    if log_callback:
        logger = lambda message: log_callback("[*] 已为 Chromium启动本地认证代理桥: %s" % message.split(": ", 1)[-1]) if "started authenticated proxy bridge" in message else log_callback(message)
    return prepare_chromium_proxy(proxy, log=logger)


def apply_browser_proxy_option(options, proxy):
    if not proxy:
        return
    if hasattr(options, "set_proxy"):
        try:
            options.set_proxy(proxy)
            return
        except Exception:
            pass
    if not hasattr(options, "set_argument"):
        raise AttributeError("当前 DrissionPage ChromiumOptions 不支持设置浏览器代理")
    try:
        options.set_argument("--proxy-server=%s" % proxy)
    except TypeError:
        options.set_argument("--proxy-server", proxy)


def _is_docker_env():
    """检测是否运行在 Docker 容器中。"""
    if os.path.isfile("/.dockerenv"):
        return True
    try:
        with open("/proc/1/cgroup", "r") as f:
            return "docker" in f.read() or "containerd" in f.read()
    except Exception:
        return False


def _detect_chromium_path():
    """在 Linux 环境下自动检测 Chromium/Chrome 可执行路径。"""
    if os.name != "posix":
        return ""
    for candidate in (
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium-wrapper",
    ):
        if os.path.isfile(candidate):
            return candidate
    return ""


def create_browser_options(browser_proxy="", extension_path=None):
    options = ChromiumOptions()
    options.auto_port()
    options.set_timeouts(base=1)
    apply_browser_proxy_option(options, browser_proxy)
    effective_extension = _extension_path if extension_path is None else str(extension_path or "")
    if effective_extension and os.path.exists(effective_extension):
        options.add_extension(effective_extension)
    # Docker / Linux 服务器环境自动适配
    in_docker = _is_docker_env()
    if in_docker or os.environ.get("GROK_DOCKER"):
        for flag in (
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--mute-audio",
            "--no-first-run",
            "--disable-background-networking",
            "--window-size=1280,900",
        ):
            try:
                options.set_argument(flag)
            except Exception:
                pass
    # Linux 环境下自动检测 Chromium 路径
    chrome_path = _detect_chromium_path()
    if chrome_path:
        try:
            options.set_browser_path(chrome_path)
        except Exception:
            pass
    return options


def _build_request_kwargs(**kwargs):
    request_kwargs = dict(kwargs)
    proxies = request_kwargs.pop("proxies", None)
    if proxies is None:
        proxies = get_proxies()
    if proxies:
        request_kwargs["proxies"] = proxies
    request_kwargs.setdefault("timeout", 15)
    return request_kwargs


def http_get(url, **kwargs):
    request_kwargs = _build_request_kwargs(**kwargs)
    try:
        return requests.get(url, **request_kwargs)
    except Exception as exc:
        if is_proxy_connection_error(exc):
            direct = dict(request_kwargs)
            direct.pop("proxies", None)
            return requests.get(url, **direct)
        raise


def http_post(url, **kwargs):
    request_kwargs = _build_request_kwargs(**kwargs)
    try:
        return requests.post(url, **request_kwargs)
    except Exception as exc:
        if is_proxy_connection_error(exc):
            direct = dict(request_kwargs)
            direct.pop("proxies", None)
            return requests.post(url, **direct)
        raise
