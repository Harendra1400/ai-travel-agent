"""Small dependency-free Prometheus metrics registry."""

from collections import defaultdict
from threading import Lock


class HTTPMetrics:
    """Track low-cardinality request counts and duration totals."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._count: defaultdict[tuple[str, int], int] = defaultdict(int)
        self._duration: defaultdict[tuple[str, int], float] = defaultdict(float)

    def observe(self, method: str, status: int, duration_seconds: float) -> None:
        """Record one completed request."""
        key = (method, status)
        with self._lock:
            self._count[key] += 1
            self._duration[key] += duration_seconds

    def render(self) -> str:
        """Render the current process registry in Prometheus text format."""
        lines = [
            "# HELP travel_agent_http_requests_total Completed HTTP requests.",
            "# TYPE travel_agent_http_requests_total counter",
        ]
        with self._lock:
            for (method, status), count in sorted(self._count.items()):
                labels = f'method="{method}",status="{status}"'
                lines.append(f"travel_agent_http_requests_total{{{labels}}} {count}")
            lines.extend(
                [
                    "# HELP travel_agent_http_request_duration_seconds_sum "
                    "Total request duration.",
                    "# TYPE travel_agent_http_request_duration_seconds_sum counter",
                ]
            )
            for (method, status), duration in sorted(self._duration.items()):
                labels = f'method="{method}",status="{status}"'
                lines.append(
                    "travel_agent_http_request_duration_seconds_sum"
                    f"{{{labels}}} {duration:.6f}"
                )
        return "\n".join(lines) + "\n"


http_metrics = HTTPMetrics()
