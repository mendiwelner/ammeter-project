import math
from socket import socket, AF_INET, SOCK_STREAM


class AmmeterClientError(RuntimeError):
    """Raised when an ammeter cannot return a valid measurement."""


def request_current_from_ammeter(port: int, command: bytes, timeout: float = 5.0) -> float:
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("port must be an integer between 1 and 65535")
    if not isinstance(command, bytes) or not command.strip():
        raise ValueError("command must be a non-empty bytes value")
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    try:
        with socket(AF_INET, SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(('localhost', port))
            s.sendall(command)
            data = s.recv(1024)
    except TimeoutError as exc:
        raise AmmeterClientError(f"Timed out while reading ammeter on port {port}") from exc
    except OSError as exc:
        raise AmmeterClientError(f"Could not communicate with ammeter on port {port}: {exc}") from exc

    if not data:
        raise AmmeterClientError(f"No measurement received from ammeter on port {port}")

    try:
        measurement = float(data.decode('utf-8').strip())
    except (UnicodeDecodeError, ValueError) as exc:
        raise AmmeterClientError(
            f"Invalid measurement received from port {port}: {data!r}"
        ) from exc
    if not math.isfinite(measurement):
        raise AmmeterClientError(f"Non-finite measurement received from port {port}: {data!r}")
    return measurement

