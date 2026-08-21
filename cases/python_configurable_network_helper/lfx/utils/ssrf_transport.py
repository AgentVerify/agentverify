class AsyncConnectionPool:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class ConnectionPool(AsyncConnectionPool):
    pass


class AsyncClient(AsyncConnectionPool):
    pass


class Client(AsyncConnectionPool):
    pass


class DNSPinningNetworkBackend:
    async def connect(self, pinned_ip):
        return await self.backend.connect_tcp(host=pinned_ip)


class DNSPinningSyncNetworkBackend:
    def connect(self, pinned_ip):
        return self.backend.connect_tcp(host=pinned_ip)


class SSRFProtectedTransport:
    def __init__(self, proxy=None):
        network_backend = DNSPinningNetworkBackend()
        self.pool = AsyncConnectionPool(network_backend=network_backend)
        if proxy is not None:
            raise NotImplementedError()


class SSRFProtectedSyncTransport:
    def __init__(self, proxy=None):
        network_backend = DNSPinningSyncNetworkBackend()
        self.pool = ConnectionPool(network_backend=network_backend)
        if proxy is not None:
            raise NotImplementedError()


def create_ssrf_protected_client(hostname, validated_ips):
    transport = SSRFProtectedTransport()
    return AsyncClient(transport=transport)


def create_ssrf_protected_sync_client(hostname, validated_ips):
    transport = SSRFProtectedSyncTransport()
    return Client(transport=transport)
