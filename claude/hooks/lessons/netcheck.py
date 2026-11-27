"""网络：把 [network] 代理注入无头子进程，并在调用前预检连通性，避免把网络故障误判为模型输出错误。"""
from __future__ import annotations

import urllib.error
import urllib.request
from urllib.parse import urlparse

PROXY_KEYS = ("https_proxy", "http_proxy", "all_proxy", "no_proxy")


def child_env(network: dict, env) -> dict:
    out = dict(env)
    for k in PROXY_KEYS:
        v = network.get(k) or ""
        if v:
            out[k] = v
            out[k.upper()] = v
    # 防递归：无头会话内的 AI314 hook 看到该变量即退出
    out["AI314_HEADLESS"] = "1"
    return out


def _get(env, key: str) -> str:
    return env.get(key) or env.get(key.upper()) or ""


def _bypass(host: str, no_proxy: str) -> bool:
    for item in (x.strip().lstrip(".") for x in no_proxy.split(",")):
        if item and (item == "*" or host == item or host.endswith("." + item)):
            return True
    return False


def proxies(url: str, env) -> dict:
    host = urlparse(url).hostname or ""
    if _bypass(host, _get(env, "no_proxy")):
        return {}
    p = _get(env, "https_proxy" if url.startswith("https") else "http_proxy") or _get(env, "all_proxy")
    return {"https": p, "http": p} if p else {}


def probe(url: str, env, timeout: float = 5) -> bool:
    """能建立连接即视为可达；HTTP 层错误码（401/404）不代表网络不通。"""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies(url, env)))
    try:
        opener.open(urllib.request.Request(url, method="HEAD"), timeout=timeout).close()
        return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, OSError, ValueError):
        return False
