from __future__ import annotations

import json
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

DEFAULT_ROUTER = "http://127.0.0.1:8080"
LAUNCHD_LABEL = "com.llama.testbed"


def normalize_router_base(raw: str | None) -> str:
    base = (raw or "").strip().rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3].rstrip("/")
    return base or DEFAULT_ROUTER


def _host_port(base: str) -> tuple[str, int]:
    parsed = urlparse(base)
    host = parsed.hostname or "127.0.0.1"
    if parsed.port is not None:
        return host, parsed.port
    return host, 443 if parsed.scheme == "https" else 8080


def router_up(base: str, timeout_s: float = 0.5) -> bool:
    host, port = _host_port(base)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout_s)
        try:
            return sock.connect_ex((host, port)) == 0
        except OSError:
            return False


def get_json(url: str, timeout_s: float = 5.0) -> object:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read())


def post_json(url: str, payload: dict, timeout_s: float = 60.0) -> object:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


@dataclass(frozen=True)
class ModelStatus:
    id: str
    loaded: bool


def list_models(base: str) -> list[ModelStatus]:
    data = get_json(f"{base}/models")
    rows = data.get("data") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return []
    out: list[ModelStatus] = []
    for entry in rows:
        if not isinstance(entry, dict):
            continue
        ids = {str(entry.get("id") or "")}
        ids.update(str(alias) for alias in (entry.get("aliases") or []))
        loaded = (entry.get("status") or {}).get("value") == "loaded"
        for model_id in ids:
            if model_id:
                out.append(ModelStatus(id=model_id, loaded=bool(loaded)))
    return out


def model_loaded(base: str, model_id: str) -> bool:
    return any(row.id == model_id and row.loaded for row in list_models(base))


def start_launchd(uid: int | None = None) -> None:
    user = (
        uid
        if uid is not None
        else subprocess.check_output(["id", "-u"], text=True).strip()
    )
    subprocess.run(
        ["/bin/launchctl", "kickstart", f"gui/{user}/{LAUNCHD_LABEL}"],
        check=True,
    )


def wait_for_router(base: str, timeout_s: float = 30.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if router_up(base):
            try:
                get_json(f"{base}/health", timeout_s=2.0)
                return
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
                pass
        time.sleep(0.4)
    raise TimeoutError(f"llama.cpp router did not become healthy at {base}")


def load_model(base: str, model_id: str, timeout_s: float = 300.0) -> None:
    if model_loaded(base, model_id):
        return
    try:
        post_json(f"{base}/models/load", {"model": model_id}, timeout_s=timeout_s)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"POST /models/load failed: {exc.code} {body}") from exc
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if model_loaded(base, model_id):
            return
        time.sleep(1.0)
    raise TimeoutError(f"model {model_id} did not reach loaded status")
