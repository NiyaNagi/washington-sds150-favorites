"""Minimal request routing for the stdlib-only web UI server.

No framework: a list of (method, path-template, handler) tuples where a
path template like ``/api/v1/profile/{slug}`` becomes a regex with a named
group. Handlers receive a :class:`RequestContext` and return a
:class:`Response`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs


@dataclass
class RequestContext:
    method: str
    path: str
    params: Dict[str, str]
    query: Dict[str, List[str]]
    body: bytes
    headers: Any

    def json_body(self) -> Any:
        import json

        if not self.body:
            return None
        return json.loads(self.body.decode("utf-8"))


@dataclass
class Response:
    status: int
    body: bytes = b""
    content_type: str = "application/json"
    headers: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def json(cls, status: int, data: Any) -> "Response":
        import json

        payload = json.dumps(data, indent=2, sort_keys=True, default=str).encode("utf-8")
        return cls(status=status, body=payload, content_type="application/json")


Handler = Callable[[RequestContext], Response]

_PARAM_RE = re.compile(r"\{(\w+)\}")


class Router:
    def __init__(self) -> None:
        self._routes: List[Tuple[str, "re.Pattern[str]", Handler]] = []

    def add(self, method: str, path_template: str, handler: Handler) -> None:
        pattern = "^" + _PARAM_RE.sub(r"(?P<\1>[^/]+)", path_template) + "$"
        self._routes.append((method.upper(), re.compile(pattern), handler))

    def resolve(self, method: str, path: str) -> Optional[Tuple[Handler, Dict[str, str]]]:
        for route_method, regex, handler in self._routes:
            if route_method != method.upper():
                continue
            match = regex.match(path)
            if match:
                return handler, match.groupdict()
        return None

    @staticmethod
    def parse_query(raw_query: str) -> Dict[str, List[str]]:
        return parse_qs(raw_query)
