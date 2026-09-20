#!/usr/bin/env python3
"""Loopback QA fixture server with exact-origin, dynamic-port, nonce identity isolation.

The reviewed harness for exercising a built artifact or a narrow source fixture
without the weaknesses of the app-local sweeps: those compare request URLs with a
string prefix and a fixed port. This harness instead

* binds loopback on an operating-system-allocated port (never a fixed one);
* accepts a request only when its *parsed* origin equals the served origin exactly;
* proves server identity with a random nonce served from the intended narrow
  fixture, so a different listener on the same host cannot be mistaken for it;
* serves only a dedicated, narrow fixture directory (never the system temp root,
  a repository root, a working directory, or anything holding Git history);
* scans that fixture for the same excluded content the build refuses; and
* reaps the listener and removes the fixture on teardown.
"""

from __future__ import annotations

import json
import secrets
import shutil
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from layout import forbidden_content_reason  # noqa: E402

IDENTITY_PATH = "/__qa_identity__"
MAX_FIXTURE_FILES = 64


def canonical_origin(url: str) -> str:
    """Return ``scheme://host:port`` for an absolute http(s) URL, exactly parsed."""
    parts = urlsplit(url)
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        raise ValueError(f"not an absolute http(s) origin: {url!r}")
    if parts.username is not None or parts.password is not None:
        raise ValueError(f"origin must not embed credentials: {url!r}")
    try:
        port = parts.port
    except ValueError as error:  # malformed or out-of-range port
        raise ValueError(f"origin has an invalid port: {url!r}") from error
    scheme = parts.scheme.lower()
    if port is None:
        port = 443 if scheme == "https" else 80
    return f"{scheme}://{parts.hostname.lower()}:{port}"


def origin_allows(request_url: str, allowed_origin: str) -> bool:
    """True only when the request's exact parsed origin equals the allowed origin.

    A string prefix such as ``http://127.0.0.1:1234`` would also match
    ``http://127.0.0.1:12345/``, ``http://127.0.0.1:1234.evil.example/`` or
    ``http://127.0.0.1:1234@evil.example/``; an exact origin comparison does not.
    """
    try:
        return canonical_origin(request_url) == allowed_origin
    except ValueError:
        return False


def _validate_fixture(fixture: Path) -> Path:
    candidate = Path(fixture)
    if candidate.is_symlink():
        raise ValueError("QA fixture must not be a symlink")
    resolved = candidate.resolve()
    if not resolved.is_dir():
        raise ValueError(f"QA fixture must be an existing directory: {candidate}")
    if resolved.parent == resolved:
        raise ValueError("QA fixture must not be a filesystem root")
    if resolved == Path(tempfile.gettempdir()).resolve():
        raise ValueError("QA fixture must be a dedicated directory, not the system temp root")
    for root in (REPOSITORY_ROOT.resolve(), Path.cwd().resolve()):
        if resolved == root or root.is_relative_to(resolved):
            raise ValueError(f"QA fixture must not serve a workspace root: {resolved}")
    if (resolved / ".git").exists():
        raise ValueError("QA fixture must not serve Git history")
    return resolved


def _scan_fixture(fixture: Path) -> None:
    count = 0
    for path in sorted(fixture.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"QA fixture must not contain symlinks: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"QA fixture contains an unsupported entry: {path}")
        count += 1
        if count > MAX_FIXTURE_FILES:
            raise ValueError("QA fixture exceeds its file-count budget")
        relative = path.relative_to(fixture).as_posix()
        reason = forbidden_content_reason(relative, path.read_bytes())
        if reason is not None:
            raise ValueError(f"QA fixture contains {reason}: {relative}")


class _Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args: object) -> None:  # keep test output quiet
        return

    def do_GET(self) -> None:  # noqa: N802 - stdlib interface
        if urlsplit(self.path).path == IDENTITY_PATH:
            body = json.dumps({"nonce": getattr(self.server, "qa_nonce", "")}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


class QAFixtureServer:
    """Serve one narrow fixture on a dynamic loopback port with nonce identity."""

    def __init__(self, fixture: Path, *, repository_root: Path = REPOSITORY_ROOT) -> None:
        self.fixture = _validate_fixture(fixture)
        if Path(repository_root).resolve() == self.fixture:
            raise ValueError("QA fixture must not be the repository root")
        _scan_fixture(self.fixture)
        self._nonce = secrets.token_hex(32)
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def nonce(self) -> str:
        return self._nonce

    @property
    def port(self) -> int:
        if self._server is None:
            raise RuntimeError("QA fixture server is not started")
        return int(self._server.server_address[1])

    @property
    def origin(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> "QAFixtureServer":
        if self._server is not None:
            return self
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Handler, directory=str(self.fixture)))
        server.daemon_threads = True
        server.qa_nonce = self._nonce  # type: ignore[attr-defined]
        self._server = server
        self._thread = threading.Thread(target=server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def allows(self, request_url: str) -> bool:
        return origin_allows(request_url, self.origin)

    def fetch(self, path: str) -> bytes:
        with urlopen(self.origin + path, timeout=5) as response:
            return response.read()

    def verify_identity(self, expected_nonce: str | None = None) -> bool:
        expected = self._nonce if expected_nonce is None else expected_nonce
        with urlopen(self.origin + IDENTITY_PATH, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload.get("nonce") == expected

    def stop(self) -> None:
        server, self._server = self._server, None
        if server is not None:
            server.shutdown()
            server.server_close()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=5)
        if self.fixture.exists():
            shutil.rmtree(self.fixture)

    def __enter__(self) -> "QAFixtureServer":
        return self.start()

    def __exit__(self, *exc_info: object) -> bool:
        self.stop()
        return False
