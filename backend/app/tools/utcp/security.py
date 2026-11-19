import ipaddress
import socket
from urllib.parse import urlparse

import structlog

from app.tools.errors import ToolAuthorizationError

logger = structlog.get_logger(__name__)

# Private, loopback, link-local and cloud metadata CIDRs
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback IPv4
    ipaddress.ip_network("10.0.0.0/8"),  # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),  # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),  # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / AWS / GCP / Azure metadata
    ipaddress.ip_network("0.0.0.0/8"),  # Current network
    ipaddress.ip_network("::1/128"),  # Loopback IPv6
    ipaddress.ip_network("fc00::/7"),  # Unique local address IPv6
    ipaddress.ip_network("fe80::/10"),  # Link-local IPv6
]


class SSRFGuard:
    """Enforces network egress boundaries to prevent SSRF against internal resources."""

    @staticmethod
    def validate_url(url: str, allow_local_dev: bool = False) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ToolAuthorizationError(
                f"Invalid URL scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted."
            )

        hostname = parsed.hostname
        if not hostname:
            raise ToolAuthorizationError("URL is missing a valid hostname.")

        # In standard test environments, allow localhost only if explicitly enabled
        if allow_local_dev and hostname in ("localhost", "127.0.0.1", "::1"):
            return url

        # Resolve hostname to IP addresses
        try:
            addr_info = socket.getaddrinfo(
                hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
            )
        except socket.gaierror as e:
            raise ToolAuthorizationError(f"Failed to resolve hostname '{hostname}': {e}") from e

        for entry in addr_info:
            ip_str = entry[4][0]
            ip_obj = ipaddress.ip_address(ip_str)

            for blocked_net in BLOCKED_NETWORKS:
                if ip_obj in blocked_net:
                    logger.error(
                        "ssrf.blocked_request",
                        hostname=hostname,
                        ip=ip_str,
                        network=str(blocked_net),
                    )
                    raise ToolAuthorizationError(
                        f"SSRF violation: Hostname '{hostname}' resolves to restricted network '{blocked_net}'."
                    )

        return url
