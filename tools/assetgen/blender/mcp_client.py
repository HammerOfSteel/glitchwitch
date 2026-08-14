"""Client for the blender-mcp addon's raw execute socket.

Dev-iteration convenience only (see spec's "Dev iteration loop" section) — the
reproducible build path never uses this, it always shells out to headless
`blender --background --python`. This lets a script be sent to a *running*
Blender instance (with the blender-mcp addon's server active on
127.0.0.1:9876) so changes are visible live in that Blender window.
"""
from __future__ import annotations

import json
import socket


class BlenderMCPError(RuntimeError):
    pass


def run(code: str, host: str = "127.0.0.1", port: int = 9876, timeout: float = 30) -> dict:
    """Execute `code` inside the running Blender process and return its result dict.

    `code` must set a `result = {...}` (JSON-serializable) variable, matching the
    blender-mcp addon's execute-request contract.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        request = {"type": "execute", "code": code, "strict_json": True}
        sock.sendall((json.dumps(request) + "\0").encode("utf-8"))
        buf = b""
        while b"\0" not in buf:
            chunk = sock.recv(1 << 20)
            if not chunk:
                break
            buf += chunk
    except OSError as exc:
        raise BlenderMCPError(
            "could not reach blender-mcp at "
            f"{host}:{port} — is Blender running with the addon enabled?"
        ) from exc
    finally:
        sock.close()

    text = buf.split(b"\0", 1)[0].decode("utf-8", errors="replace")
    response = json.loads(text)
    if response.get("status") != "ok":
        raise BlenderMCPError(response.get("message", str(response)))
    return response.get("result", {})
