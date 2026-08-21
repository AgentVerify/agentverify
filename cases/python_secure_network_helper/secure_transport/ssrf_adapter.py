import socket

from .safe_path import _is_escape_hatch_enabled, is_blocked_ip


def _assert_safe_peer(sock: socket.socket) -> None:
    if is_blocked_ip(sock.getpeername()[0]):
        raise ValueError("private peer")


def create_validated_connection(host: str, port: int) -> socket.socket:
    if _is_escape_hatch_enabled():
        return socket.create_connection((host, port))
    addresses = socket.getaddrinfo(host, port)
    for address in addresses:
        if is_blocked_ip(address[4][0]):
            raise ValueError("private address")
    sock = socket.create_connection((host, port))
    _assert_safe_peer(sock)
    return sock


def _open_validated_socket(connection: object) -> socket.socket:
    return create_validated_connection(connection.host, connection.port)


class _SafeHTTPConnection:
    def _new_conn(self) -> socket.socket:
        return _open_validated_socket(self)


class _SafeHTTPSConnection:
    def _new_conn(self) -> socket.socket:
        return _open_validated_socket(self)


class _SafeHTTPConnectionPool:
    ConnectionCls = _SafeHTTPConnection


class _SafeHTTPSConnectionPool:
    ConnectionCls = _SafeHTTPSConnection


_SAFE_POOL_CLASSES = {
    "http": _SafeHTTPConnectionPool,
    "https": _SafeHTTPSConnectionPool,
}


class _SafePoolManager:
    def __init__(self) -> None:
        self.pool_classes_by_scheme = _SAFE_POOL_CLASSES


class SSRFProtectedAdapter:
    def init_poolmanager(self) -> None:
        self.poolmanager = _SafePoolManager()

    def proxy_manager_for(self, proxy: str) -> object:
        if not _is_escape_hatch_enabled():
            raise ValueError("proxies disabled")
        return proxy
