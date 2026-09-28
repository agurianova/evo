#!/usr/bin/env python3
"""Localhost HTTP CONNECT proxy for Codex / HTTPS_PROXY clients.

Binds 127.0.0.1 only. Forwards CONNECT (HTTPS) and ordinary HTTP through an
optional upstream HTTP proxy taken from --upstream or HTTPS_PROXY. Credentials
stay in that URL; this process never prints or writes them.

This host is rejected by OpenAI with 403 unsupported_country_region_territory.
Clients should point HTTP_PROXY/HTTPS_PROXY at this listener so they do not
embed the upstream credential themselves.
"""

from __future__ import annotations

import argparse
import base64
import os
import select
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, urlunsplit

BUFFER = 65536
DEFAULT_BIND = "127.0.0.1"
DEFAULT_PORT = 18080


def _split_proxy_url(url: str) -> tuple[str, int, str | None]:
    raw = (url or "").strip()
    if not raw:
        raise ValueError("empty upstream proxy URL")
    parsed = urlsplit(raw if "://" in raw else f"http://{raw}")
    host = parsed.hostname
    if not host:
        raise ValueError("upstream proxy URL has no host")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    auth = None
    if parsed.username is not None:
        user = parsed.username
        password = parsed.password or ""
        token = base64.b64encode(f"{user}:{password}".encode()).decode("ascii")
        auth = f"Basic {token}"
    return host, int(port), auth


def _redact(url: str) -> str:
    parsed = urlsplit(url if "://" in url else f"http://{url}")
    if parsed.username is None:
        return url
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{host}{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def _pipe(src: socket.socket, dst: socket.socket) -> None:
    try:
        while True:
            data = src.recv(BUFFER)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def _tunnel(a: socket.socket, b: socket.socket) -> None:
    t = threading.Thread(target=_pipe, args=(b, a), daemon=True)
    t.start()
    _pipe(a, b)
    t.join(timeout=1)


def _connect_upstream(host: str, port: int, timeout: float) -> socket.socket:
    sock = socket.create_connection((host, port), timeout=timeout)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return sock


def _connect_via_upstream(
    upstream_host: str,
    upstream_port: int,
    auth: str | None,
    target_host: str,
    target_port: int,
    timeout: float,
) -> socket.socket:
    sock = _connect_upstream(upstream_host, upstream_port, timeout)
    req = [
        f"CONNECT {target_host}:{target_port} HTTP/1.1",
        f"Host: {target_host}:{target_port}",
        "Proxy-Connection: Keep-Alive",
    ]
    if auth:
        req.append(f"Proxy-Authorization: {auth}")
    sock.sendall(("\r\n".join(req) + "\r\n\r\n").encode("ascii"))
    buf = b""
    sock.settimeout(timeout)
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(BUFFER)
        if not chunk:
            sock.close()
            raise OSError("upstream closed during CONNECT")
        buf += chunk
        if len(buf) > 65536:
            sock.close()
            raise OSError("oversized CONNECT response from upstream")
    header, _, rest = buf.partition(b"\r\n\r\n")
    status = header.split(b"\r\n", 1)[0].decode("latin-1", "replace")
    parts = status.split()
    code = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else 0
    if code != 200:
        sock.close()
        raise OSError(f"upstream CONNECT failed: {status}")
    if rest:
        raise OSError("unexpected payload after CONNECT 200")
    sock.settimeout(None)
    return sock


class ProxyHandler(BaseHTTPRequestHandler):
    timeout = 60
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _upstream(self) -> tuple[str, int, str | None] | None:
        return getattr(self.server, "upstream", None)

    def _timeout(self) -> float:
        return float(getattr(self.server, "connect_timeout", 30.0))

    def do_CONNECT(self) -> None:  # noqa: N802
        host_port = self.path.split("@")[-1]
        if ":" not in host_port:
            self.send_error(400, "CONNECT host:port required")
            return
        host, _, port_s = host_port.rpartition(":")
        host = host.strip("[]")
        try:
            port = int(port_s)
        except ValueError:
            self.send_error(400, "invalid CONNECT port")
            return
        try:
            upstream = self._upstream()
            if upstream is None:
                remote = _connect_upstream(host, port, self._timeout())
            else:
                remote = _connect_via_upstream(
                    upstream[0], upstream[1], upstream[2], host, port, self._timeout()
                )
        except OSError as exc:
            self.send_error(502, str(exc))
            return
        self.send_response(200, "Connection Established")
        self.send_header("Proxy-Agent", "pmhctcr-local-proxy")
        self.end_headers()
        self.close_connection = True
        try:
            _tunnel(self.connection, remote)
        finally:
            try:
                remote.close()
            except OSError:
                pass

    def _forward_http(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.scheme not in {"http", ""} or not parsed.netloc:
            self.send_error(400, "absolute http:// URL required")
            return
        host = parsed.hostname
        if not host:
            self.send_error(400, "target host required")
            return
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        body = b""
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length:
            body = self.rfile.read(length)
        hop = {
            "connection",
            "proxy-connection",
            "keep-alive",
            "transfer-encoding",
            "te",
            "trailer",
            "upgrade",
            "proxy-authorization",
        }
        headers = [
            f"{name}: {value}"
            for name, value in self.headers.items()
            if name.lower() not in hop
        ]
        upstream = self._upstream()
        if upstream is None:
            request_line = f"{self.command} {path} HTTP/1.1"
        else:
            request_line = f"{self.command} {self.path} HTTP/1.1"
            if upstream[2]:
                headers.append(f"Proxy-Authorization: {upstream[2]}")
        request = (request_line + "\r\n" + "\r\n".join(headers) + "\r\n\r\n").encode(
            "latin-1"
        ) + body
        try:
            if upstream is None:
                remote = _connect_upstream(host, port, self._timeout())
            else:
                remote = _connect_upstream(upstream[0], upstream[1], self._timeout())
            remote.sendall(request)
        except OSError as exc:
            self.send_error(502, str(exc))
            return
        self.close_connection = True
        try:
            _tunnel(self.connection, remote)
        finally:
            try:
                remote.close()
            except OSError:
                pass

    def do_GET(self) -> None:  # noqa: N802
        self._forward_http()

    def do_POST(self) -> None:  # noqa: N802
        self._forward_http()

    def do_HEAD(self) -> None:  # noqa: N802
        self._forward_http()

    def do_PUT(self) -> None:  # noqa: N802
        self._forward_http()

    def do_DELETE(self) -> None:  # noqa: N802
        self._forward_http()

    def do_PATCH(self) -> None:  # noqa: N802
        self._forward_http()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._forward_http()


class LocalProxy(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        bind: str,
        port: int,
        upstream_url: str | None,
        connect_timeout: float,
    ):
        super().__init__((bind, port), ProxyHandler)
        self.upstream = _split_proxy_url(upstream_url) if upstream_url else None
        self.connect_timeout = connect_timeout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default=DEFAULT_BIND)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--upstream",
        default=os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or "",
        help="Upstream HTTP proxy URL. Defaults to HTTPS_PROXY.",
    )
    parser.add_argument("--connect-timeout", type=float, default=30.0)
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Do not use an upstream proxy (direct connect).",
    )
    args = parser.parse_args()
    if args.bind not in {"127.0.0.1", "localhost", "::1"}:
        print("refusing to bind outside loopback", file=sys.stderr)
        return 2
    upstream = "" if args.direct else (args.upstream or "").strip()
    server = LocalProxy(args.bind, args.port, upstream or None, args.connect_timeout)
    if upstream:
        print(
            f"local proxy http://{args.bind}:{args.port} -> {_redact(upstream)}",
            flush=True,
        )
    else:
        print(f"local proxy http://{args.bind}:{args.port} (direct)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("stopped", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
