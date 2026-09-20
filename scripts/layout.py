#!/usr/bin/env python3
"""Verified Git object loading and bounded artifact-tree primitives."""

from __future__ import annotations

import hashlib
import json
import os
import re
import selectors
import stat
import subprocess
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

NORMALIZED_MTIME = 946684800  # 2000-01-01T00:00:00Z
APP_DESTINATIONS = {"public": PurePosixPath("."), "form": PurePosixPath("form"), "hub": PurePosixPath("hub")}
MAX_FILES = 120
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_FILE_BYTES = 1024 * 1024
MAX_PATH_DEPTH = 12
MAX_PATH_BYTES = 240
MAX_TRAVERSAL_WORK = 256
MAX_OBJECT_BYTES = 2 * 1024 * 1024
MAX_GIT_STDERR = 128 * 1024
GIT_TIMEOUT_SECONDS = 60

EXPECTED_APPLICATION_PATHS = frozenset(
    {
        "apps/form/.gitignore",
        "apps/form/.nojekyll",
        "apps/form/4ws-report.html",
        "apps/form/5ws-report.html",
        "apps/form/README.md",
        "apps/form/cards.html",
        "apps/form/contact.html",
        "apps/form/icons/apple-touch-icon.png",
        "apps/form/icons/icon-192.png",
        "apps/form/icons/icon-512.png",
        "apps/form/icons/maskable-512.png",
        "apps/form/index.html",
        "apps/form/manifest.webmanifest",
        "apps/form/phq9.html",
        "apps/form/pwa.js",
        "apps/form/referral.html",
        "apps/form/selfreport.html",
        "apps/form/sw.js",
        "apps/form/tools/i18n-check.py",
        "apps/form/tools/i18n-pages.txt",
        "apps/form/tools/precache.sha",
        "apps/form/tools/qr-build.py",
        "apps/form/tools/qr-check.py",
        "apps/form/tools/site.conf",
        "apps/form/tools/sw-precache-check.py",
        "apps/form/tools/text-setting-check.py",
        "apps/hub/.gitignore",
        "apps/hub/.nojekyll",
        "apps/hub/README.md",
        "apps/hub/access.html",
        "apps/hub/assets/app.css",
        "apps/hub/assets/brand.css",
        "apps/hub/assets/brand.js",
        "apps/hub/assets/codes.js",
        "apps/hub/assets/design.css",
        "apps/hub/assets/fb-config.js",
        "apps/hub/assets/fb.js",
        "apps/hub/assets/form.css",
        "apps/hub/assets/hub.css",
        "apps/hub/assets/hub.js",
        "apps/hub/assets/i18n-strings.js",
        "apps/hub/assets/i18n.js",
        "apps/hub/assets/icons.js",
        "apps/hub/assets/l1.js",
        "apps/hub/assets/mark.js",
        "apps/hub/assets/qr.js",
        "apps/hub/assets/store.js",
        "apps/hub/coverage.html",
        "apps/hub/data/README.md",
        "apps/hub/data/demo.js",
        "apps/hub/data/demo.json",
        "apps/hub/docs/DATA_MODEL.md",
        "apps/hub/forms.html",
        "apps/hub/gen.js",
        "apps/hub/inbox.html",
        "apps/hub/index.html",
        "apps/hub/tools/contrast-check.py",
        "apps/hub/tools/contrast-sweep.py",
        "apps/hub/tools/i18n-check.py",
        "apps/hub/tools/i18n-pages.txt",
        "apps/hub/tools/justify-sweep.py",
        "apps/hub/tools/key-chrome.py",
        "apps/hub/tools/key-prose.py",
        "apps/hub/tools/rail.py",
        "apps/hub/tools/site.conf",
        "apps/hub/tools/text-setting-check.py",
        "apps/public/.gitignore",
        "apps/public/.nojekyll",
        "apps/public/README.md",
        "apps/public/access-explained.html",
        "apps/public/architecture.html",
        "apps/public/assets/app.css",
        "apps/public/assets/brand.css",
        "apps/public/assets/brand.js",
        "apps/public/assets/codes.js",
        "apps/public/assets/design.css",
        "apps/public/assets/fb-config.js",
        "apps/public/assets/i18n-strings.js",
        "apps/public/assets/i18n.js",
        "apps/public/assets/icons.js",
        "apps/public/assets/mark.js",
        "apps/public/assets/page.css",
        "apps/public/assets/public-read.js",
        "apps/public/assets/referral-facilities.js",
        "apps/public/assets/referral-find.js",
        "apps/public/assets/referral-geo.js",
        "apps/public/assets/referral-map.js",
        "apps/public/assets/site.css",
        "apps/public/assets/vendor/leaflet/LICENSE.txt",
        "apps/public/assets/vendor/leaflet/leaflet.css",
        "apps/public/assets/vendor/leaflet/leaflet.js",
        "apps/public/assets/workforce-view.js",
        "apps/public/assets/workforce.js",
        "apps/public/bps.html",
        "apps/public/contact-us.html",
        "apps/public/coordination/admin.html",
        "apps/public/coordination/inbox.html",
        "apps/public/coordination/index.html",
        "apps/public/dashboard/index.html",
        "apps/public/flood-response.html",
        "apps/public/iec.html",
        "apps/public/index.html",
        "apps/public/layer3.html",
        "apps/public/method.html",
        "apps/public/referral-directory.html",
        "apps/public/resources.html",
        "apps/public/tools/contrast-check.py",
        "apps/public/tools/contrast-sweep.py",
        "apps/public/tools/i18n-check.py",
        "apps/public/tools/i18n-pages.txt",
        "apps/public/tools/justify-sweep.py",
        "apps/public/tools/key-chrome.py",
        "apps/public/tools/key-prose.py",
        "apps/public/tools/map-build.py",
        "apps/public/tools/nav.py",
        "apps/public/tools/roster-fig.py",
        "apps/public/tools/site.conf",
        "apps/public/tools/text-setting-check.py",
        "apps/public/tools/workforce-build.py",
        "apps/public/videos.html",
    }
)
if len(EXPECTED_APPLICATION_PATHS) != MAX_FILES:
    raise RuntimeError("the application allowlist must contain exactly 120 files")

_FORBIDDEN_SUFFIXES = {
    ".bak",
    ".csv",
    ".db",
    ".dump",
    ".key",
    ".ods",
    ".p12",
    ".pem",
    ".psv",
    ".sql",
    ".sqlite",
    ".sqlite3",
    ".tsv",
    ".xls",
    ".xlsm",
    ".xlsx",
}
_FORBIDDEN_ARTIFACT_WORDS = {"backup", "backups", "export", "exports", "snapshot", "snapshots"}
# The complete legacy set: the DOS device names, the console aliases, CLOCK$, and
# the superscript COM/LPT variants that Windows also resolves as devices. Names
# are compared after stripping trailing dots/spaces from the pre-extension stem.
_WINDOWS_RESERVED_BASE = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "CLOCK$",
    "CONIN$",
    "CONOUT$",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
    "COM\u00b9",
    "COM\u00b2",
    "COM\u00b3",
    "LPT\u00b9",
    "LPT\u00b2",
    "LPT\u00b3",
}
_WINDOWS_RESERVED = {name.rstrip(". ") for name in _WINDOWS_RESERVED_BASE}
# Suffix-independent secret detection: key/value assignment shapes for secrets,
# tokens, passwords, and private/API keys. Applied to every bounded blob.
_SECRET_ASSIGNMENT = re.compile(
    rb"(?im)^[ \t]*(?:export[ \t]+)?[\"']?([A-Za-z0-9_.$@-]*"
    rb"(?:secret|token|password|passwd|passphrase|api[_-]?key|private[_-]?key"
    rb"|access[_-]?key|client[_-]?secret|auth[_-]?token)"
    rb"[A-Za-z0-9_.$@-]*)[\"']?[ \t]*[:=]"
)
# Narrow, explicit, path-and-content-scoped exceptions for known-public
# configuration only. Each entry records the allowed assignment keys and the
# reason the material is knowingly public. Nothing else may bypass the scan.
_PUBLIC_CONFIG_EXCEPTIONS: dict[str, tuple[frozenset[str], str]] = {
    "apps/hub/assets/fb-config.js": (
        frozenset({"apikey"}),
        "Firebase web configuration is a public identifier published in the page source; "
        "authorization is the (unverified) server-side Firestore Rules, not this key.",
    ),
    "apps/public/assets/fb-config.js": (
        frozenset({"apikey"}),
        "Firebase web configuration is a public identifier published in the page source; "
        "authorization is the (unverified) server-side Firestore Rules, not this key.",
    ),
}
_HEX_OBJECT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_AWS_ACCESS_KEY = re.compile(rb"AKIA[0-9A-Z]{16}")
_GITHUB_TOKEN = re.compile(rb"(?i)\bgh[pousr]_[A-Za-z0-9]{30,}")
_BEARER_TOKEN = re.compile(rb"(?i)\bbearer[ \t]+[A-Za-z0-9._\-]{20,}")
_SYNTHETIC_DEMOS = {"apps/hub/data/demo.json", "apps/hub/data/demo.js"}


@dataclass(frozen=True)
class SourceEntry:
    git_path: str
    destination: PurePosixPath
    oid: str
    data: bytes


@dataclass(frozen=True)
class SourceLayout:
    repository: Path
    git_dir: Path
    root: Path
    commit: str
    entries: tuple[SourceEntry, ...]


@dataclass(frozen=True)
class OutputFile:
    path: str
    data: bytes
    mode: int
    mtime_ns: int


@dataclass(frozen=True)
class OutputDirectory:
    path: str
    mode: int
    mtime_ns: int


def _absolute_lexical(path: Path) -> Path:
    return path if path.is_absolute() else Path.cwd() / path


def _path_parts(path: Path) -> tuple[str, ...]:
    return tuple(part for part in _absolute_lexical(path).parts[1:] if part != ".")


def canonical_path_key(path: str) -> str:
    """One canonical comparison key: NFC-normalized, case-folded.

    Colliding names must be rejected under a single combined key so that a pair
    differing only by case folding, only by Unicode normalization, or only by the
    interaction of both cannot reach two destinations that one filesystem would
    merge (or that two filesystems would treat differently).
    """
    return unicodedata.normalize("NFC", path).casefold()


def validate_path_component(component: str, *, label: str) -> None:
    """Reject names with unsafe or cross-platform ambiguous spelling."""
    if not component or component in {".", ".."}:
        raise ValueError(f"unsafe {label} component: {component!r}")
    if any(unicodedata.category(character).startswith("C") for character in component):
        raise ValueError(f"unsafe control or format character in {label}: {component!r}")
    if component.endswith((".", " ")):
        raise ValueError(f"unsafe trailing dot or space in {label}: {component!r}")
    if canonical_path_key(component) == ".git":
        raise ValueError(f"forbidden .git path component in {label}: {component!r}")
    windows_stem = component.split(".", 1)[0].upper().rstrip(". ")
    if windows_stem in _WINDOWS_RESERVED:
        raise ValueError(f"unsafe Windows-reserved name in {label}: {component!r}")


def _validate_user_path(path: Path, label: str) -> Path:
    absolute = _absolute_lexical(path)
    parts = _path_parts(path)
    for component in parts:
        validate_path_component(component, label=label)
    return Path(os.path.abspath(os.fspath(absolute)))


def _open_directory(path: Path, label: str) -> int:
    """Open an existing directory without following any path-component link."""
    absolute = _absolute_lexical(path)
    if not absolute.is_absolute():
        raise ValueError(f"{label} must be absolute")
    descriptor = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for component in absolute.parts[1:]:
            if component in {"", ".", ".."}:
                if component == "..":
                    raise ValueError(f"unsafe parent reference in {label}: {path}")
                continue
            next_descriptor = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read_small_regular(path: Path, limit: int, label: str) -> bytes:
    parent_descriptor = _open_directory(path.parent, f"{label} parent")
    try:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=parent_descriptor)
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
                raise ValueError(f"invalid {label}: {path}")
            data = os.read(descriptor, limit + 1)
            if len(data) > limit:
                raise ValueError(f"invalid {label}: {path}")
            return data
        finally:
            os.close(descriptor)
    finally:
        os.close(parent_descriptor)


def _discover_repository(source_root: Path) -> tuple[Path, Path, Path]:
    source_path = _validate_user_path(source_root, "source root")
    if source_path.name != "apps":
        raise ValueError(f"source root must be the repository apps directory: {source_path}")
    source_descriptor = _open_directory(source_path, "source root")
    os.close(source_descriptor)
    repository = source_path.parent
    repository_descriptor = _open_directory(repository, "repository")
    os.close(repository_descriptor)

    dot_git = repository / ".git"
    metadata = os.lstat(dot_git)
    if stat.S_ISDIR(metadata.st_mode):
        git_dir = dot_git
    elif stat.S_ISREG(metadata.st_mode):
        raw = _read_small_regular(dot_git, 4096, "Git worktree metadata")
        try:
            text = raw.decode("utf-8", "strict").strip()
        except UnicodeDecodeError as error:
            raise ValueError("invalid Git worktree metadata") from error
        if not text.startswith("gitdir: ") or "\n" in text:
            raise ValueError("invalid Git worktree metadata")
        candidate = Path(text[8:])
        git_dir = candidate if candidate.is_absolute() else repository / candidate
        git_dir = Path(os.path.abspath(os.fspath(git_dir)))
    else:
        raise ValueError(f"repository metadata is not a real file or directory: {dot_git}")
    git_descriptor = _open_directory(git_dir, "Git directory")
    os.close(git_descriptor)
    if not (git_dir / "HEAD").is_file():
        raise ValueError(f"verified Git directory has no HEAD: {git_dir}")
    return repository, git_dir, source_path


def _git_environment() -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment["GIT_NO_LAZY_FETCH"] = "1"
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return environment


def _bounded_process(
    command: list[str],
    *,
    input_bytes: bytes | None = None,
    stdout_limit: int,
    stderr_limit: int = MAX_GIT_STDERR,
    timeout: int = GIT_TIMEOUT_SECONDS,
) -> tuple[int, bytes, bytes]:
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_git_environment(),
    )
    if input_bytes is not None:
        assert process.stdin is not None
        process.stdin.write(input_bytes)
        process.stdin.close()
    assert process.stdout is not None and process.stderr is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, ("stdout", stdout_limit))
    selector.register(process.stderr, selectors.EVENT_READ, ("stderr", stderr_limit))
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    deadline = time.monotonic() + timeout
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                process.kill()
                raise ValueError("Git command exceeded its time limit")
            events = selector.select(min(remaining, 1.0))
            if not events and process.poll() is not None:
                events = [(key, selectors.EVENT_READ) for key in list(selector.get_map().values())]
            for key, _ in events:
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                stream, limit = key.data
                buffers[stream].extend(chunk)
                if len(buffers[stream]) > limit:
                    process.kill()
                    raise ValueError(f"Git {stream} exceeded its resource limit")
        return_code = process.wait(timeout=max(1, int(deadline - time.monotonic())))
        return return_code, bytes(buffers["stdout"]), bytes(buffers["stderr"])
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
            process.wait()
        for pipe in (process.stdin, process.stdout, process.stderr):
            if pipe is not None and not pipe.closed:
                pipe.close()


def _git(
    repository: Path,
    git_dir: Path,
    *arguments: str,
    input_bytes: bytes | None = None,
    stdout_limit: int = MAX_OBJECT_BYTES + 4096,
    timeout: int = GIT_TIMEOUT_SECONDS,
) -> bytes:
    command = [
        "git",
        "--no-replace-objects",
        f"--git-dir={git_dir}",
        f"--work-tree={repository}",
        *arguments,
    ]
    return_code, stdout, stderr = _bounded_process(
        command,
        input_bytes=input_bytes,
        stdout_limit=stdout_limit,
        timeout=timeout,
    )
    if return_code:
        diagnostic = stderr.decode("utf-8", "replace").strip()
        raise ValueError(f"Git object verification failed: {diagnostic or 'unknown Git error'}")
    return stdout


def _object_digest(object_type: str, content: bytes, oid: str) -> str:
    algorithm = "sha1" if len(oid) == 40 else "sha256"
    header = f"{object_type} {len(content)}\0".encode("ascii")
    return hashlib.new(algorithm, header + content).hexdigest()


def _read_object(repository: Path, git_dir: Path, oid: str, expected_type: str) -> bytes:
    if not _HEX_OBJECT.fullmatch(oid):
        raise ValueError(f"invalid Git object id: {oid!r}")
    raw = _git(
        repository,
        git_dir,
        "cat-file",
        "--batch",
        input_bytes=(oid + "\n").encode("ascii"),
    )
    header_end = raw.find(b"\n")
    if header_end < 0:
        raise ValueError("Git object lookup returned a truncated header")
    try:
        returned_oid, object_type, size_text = raw[:header_end].decode("ascii", "strict").split()
        size = int(size_text)
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError("Git object lookup returned an invalid header") from error
    if returned_oid != oid or object_type != expected_type or size < 0 or size > MAX_OBJECT_BYTES:
        raise ValueError(f"Git object lookup returned an invalid {expected_type} object")
    content = raw[header_end + 1 :]
    if len(content) != size + 1 or not content.endswith(b"\n"):
        raise ValueError("Git object lookup returned truncated or trailing data")
    content = content[:-1]
    if _object_digest(object_type, content, oid) != oid:
        raise ValueError(f"Git {object_type} failed object-id verification: {oid}")
    return content


def _parse_commit_tree(commit: bytes, oid_length: int) -> str:
    first_line = commit.split(b"\n", 1)[0]
    prefix = b"tree "
    if not first_line.startswith(prefix):
        raise ValueError("verified Git commit has no leading tree header")
    try:
        tree_oid = first_line[len(prefix) :].decode("ascii", "strict")
    except UnicodeDecodeError as error:
        raise ValueError("verified Git commit has an invalid tree id") from error
    if len(tree_oid) != oid_length or not _HEX_OBJECT.fullmatch(tree_oid):
        raise ValueError("verified Git commit has an invalid tree id")
    return tree_oid


def _parse_tree(data: bytes, oid_bytes: int) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    offset = 0
    while offset < len(data):
        space = data.find(b" ", offset)
        nul = data.find(b"\0", space + 1) if space >= 0 else -1
        if space < 0 or nul < 0 or nul + 1 + oid_bytes > len(data):
            raise ValueError("verified Git tree has a truncated entry")
        try:
            mode = data[offset:space].decode("ascii", "strict")
            name = data[space + 1 : nul].decode("utf-8", "strict")
        except UnicodeDecodeError as error:
            raise ValueError("verified Git tree has a non-UTF-8 entry") from error
        oid = data[nul + 1 : nul + 1 + oid_bytes].hex()
        entries.append((mode, name, oid))
        offset = nul + 1 + oid_bytes
    return entries


class _PathRegistry:
    """Reject any two classified paths that share one canonical comparison key."""

    def __init__(self) -> None:
        self.by_key: dict[str, str] = {}

    def add(self, path: str, *, kind: str = "path") -> None:
        key = canonical_path_key(path)
        previous = self.by_key.get(key)
        if previous is not None and previous != path:
            raise ValueError(
                f"canonical collision between {kind}s under one key: {previous!r} and {path!r}"
            )
        self.by_key[key] = path


def _validate_git_path(path: str) -> tuple[str, ...]:
    try:
        encoded_length = len(path.encode("utf-8", "strict"))
    except UnicodeEncodeError as error:
        raise ValueError(f"unsafe committed source path: {path!r}") from error
    parts = tuple(path.split("/"))
    if path.startswith("/") or any(not part for part in parts):
        raise ValueError(f"unsafe committed source path: {path!r}")
    if len(parts) > MAX_PATH_DEPTH:
        raise ValueError(f"committed path depth limit exceeded: {path!r}")
    if encoded_length > MAX_PATH_BYTES:
        raise ValueError(f"committed path length limit exceeded: {path!r}")
    for component in parts:
        validate_path_component(component, label="committed source path")
    return parts


def _forbidden_path(path: str) -> bool:
    parts = tuple(part.casefold() for part in path.split("/"))
    name = parts[-1]
    suffix = PurePosixPath(name).suffix
    stem = name[: -len(suffix)] if suffix else name
    synthetic_demo = path in _SYNTHETIC_DEMOS
    return (
        name.startswith(".env")
        or suffix == ".json" and not synthetic_demo
        or suffix in _FORBIDDEN_SUFFIXES
        or any((part[: -len(PurePosixPath(part).suffix)] if PurePosixPath(part).suffix else part) in _FORBIDDEN_ARTIFACT_WORDS for part in parts)
        or stem in {"secret", "secrets", "token", "tokens", "password", "passwords"}
        or "service_account" in name
        or "service-account" in name
        or "serviceaccount" in name
        or name.startswith("firebase-adminsdk")
    )


def _secret_assignment(data: bytes, path: str) -> "re.Match[bytes] | None":
    """Return the first secret-shaped assignment, honoring narrow exceptions.

    The assignment scan is deliberately independent of the file suffix: an
    allowlisted ``.html``, ``.js``, ``.css``, or binary blob is scanned in full
    exactly like a configuration file.
    """
    for match in _SECRET_ASSIGNMENT.finditer(data):
        key = match.group(1).decode("utf-8", "replace").casefold()
        exception = _PUBLIC_CONFIG_EXCEPTIONS.get(path)
        if exception is not None and key in exception[0]:
            continue
        return match
    return None


def forbidden_content_reason(path: str, data: bytes) -> "str | None":
    """Classify one bounded blob for excluded content, suffix-independently."""
    upper = data.upper()
    if b"-----BEGIN " in upper and b"PRIVATE KEY-----" in upper:
        return "private-key material"
    lowered = data.lower()
    if re.search(rb'"type"\s*:\s*"service_account"', lowered) or (
        b'"private_key_id"' in lowered and b'"client_email"' in lowered
    ):
        return "service-account material"
    for label, pattern in (
        ("AWS access-key id", _AWS_ACCESS_KEY),
        ("GitHub token", _GITHUB_TOKEN),
        ("bearer token", _BEARER_TOKEN),
    ):
        if pattern.search(data):
            return label
    if _secret_assignment(data, path) is not None:
        return "secret/token/password assignment"
    return None


class _DuplicateKey(ValueError):
    """Raised when strict JSON parsing meets a duplicate object key."""


def _reject_duplicate_pairs(pairs: "list[tuple[str, object]]") -> dict[str, object]:
    seen: set[str] = set()
    for key, _ in pairs:
        if key in seen:
            raise _DuplicateKey(key)
        seen.add(key)
    return dict(pairs)


def _reject_non_finite(token: str) -> object:
    raise ValueError(f"non-finite JSON value: {token}")


def parse_structured_data(path: str, data: bytes) -> object | None:
    """Strictly parse a classified JSON or web-manifest blob before any output.

    Returns the parsed value, or ``None`` when the path is not structured data.
    Malformed, duplicate-keyed, or non-finite content raises ``ValueError`` so the
    whole build fails closed instead of copying ambiguous structured content.
    """
    lowered = path.casefold()
    if not lowered.endswith((".json", ".webmanifest")):
        return None
    try:
        text = data.decode("utf-8", "strict")
    except UnicodeDecodeError as error:
        raise ValueError(f"structured data is not valid UTF-8: {path}") from error
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_non_finite,
        )
    except _DuplicateKey as error:
        raise ValueError(f"structured data has a duplicate key: {path} ({error})") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"structured data is malformed JSON: {path} ({error})") from error
    except (ValueError, TypeError) as error:
        raise ValueError(f"structured data is invalid: {path} ({error})") from error


def _destination_for(git_path: str) -> PurePosixPath:
    _, app, *remainder = git_path.split("/")
    destination = APP_DESTINATIONS[app]
    for component in remainder:
        destination /= component
    return destination


def inspect_source(source_root: Path, revision: str = "HEAD") -> SourceLayout:
    """Resolve and independently verify one exact committed application tree."""
    repository, git_dir, source_path = _discover_repository(source_root)
    resolved = _git(
        repository,
        git_dir,
        "rev-parse",
        "--verify",
        "--end-of-options",
        f"{revision}^{{commit}}",
        stdout_limit=256,
    ).decode("ascii", "strict").strip()
    if not _HEX_OBJECT.fullmatch(resolved):
        raise ValueError("Git did not resolve exactly one commit object")
    _git(
        repository,
        git_dir,
        "fsck",
        "--strict",
        "--full",
        "--no-reflogs",
        "--no-progress",
        "--no-dangling",
        resolved,
        stdout_limit=1024 * 1024,
        timeout=GIT_TIMEOUT_SECONDS,
    )

    oid_bytes = len(resolved) // 2
    commit_data = _read_object(repository, git_dir, resolved, "commit")
    root_tree_oid = _parse_commit_tree(commit_data, len(resolved))
    root_tree = _parse_tree(_read_object(repository, git_dir, root_tree_oid, "tree"), oid_bytes)

    registry = _PathRegistry()
    traversal_work = 0
    for _, name, _ in root_tree:
        traversal_work += 1
        if traversal_work > MAX_TRAVERSAL_WORK:
            raise ValueError("committed tree traversal work limit exceeded")
        _validate_git_path(name)
        registry.add(name)

    apps_matches = [(mode, oid) for mode, name, oid in root_tree if name == "apps"]
    if len(apps_matches) != 1 or apps_matches[0][0] != "40000":
        raise ValueError("verified commit must contain exactly one apps tree")

    file_count = 0
    total_bytes = 0
    found: dict[str, SourceEntry] = {}

    def walk_tree(tree_oid: str, prefix: str) -> None:
        nonlocal traversal_work, file_count, total_bytes
        tree_data = _read_object(repository, git_dir, tree_oid, "tree")
        for mode, name, oid in _parse_tree(tree_data, oid_bytes):
            traversal_work += 1
            if traversal_work > MAX_TRAVERSAL_WORK:
                raise ValueError("committed tree traversal work limit exceeded")
            path = f"{prefix}/{name}"
            _validate_git_path(path)
            entry_kind = "directory" if mode == "40000" else "file"
            registry.add(path, kind=entry_kind)
            if mode == "40000":
                walk_tree(oid, path)
                continue
            if mode not in {"100644", "100755"}:
                raise ValueError(f"unsupported committed source entry: {path} ({mode})")
            file_count += 1
            data = _read_object(repository, git_dir, oid, "blob")
            size = len(data)
            if size > MAX_FILE_BYTES:
                raise ValueError(f"per-file byte limit exceeded: {path}")
            total_bytes += size
            if total_bytes > MAX_TOTAL_BYTES:
                raise ValueError("total byte limit exceeded for committed application files")
            if _forbidden_path(path):
                raise ValueError(f"forbidden committed source path: {path}")
            forbidden_reason = forbidden_content_reason(path, data)
            if forbidden_reason is not None:
                raise ValueError(f"forbidden committed source contains {forbidden_reason}: {path}")
            found[path] = SourceEntry(path, _destination_for(path), oid, data)

    apps_tree = _parse_tree(_read_object(repository, git_dir, apps_matches[0][1], "tree"), oid_bytes)
    app_roots: dict[str, str] = {}
    for mode, name, oid in apps_tree:
        traversal_work += 1
        if traversal_work > MAX_TRAVERSAL_WORK:
            raise ValueError("committed tree traversal work limit exceeded")
        path = f"apps/{name}"
        _validate_git_path(path)
        registry.add(path)
        if name not in APP_DESTINATIONS or mode != "40000":
            raise ValueError(f"unclassified application root: {path}")
        app_roots[name] = oid
    if set(app_roots) != set(APP_DESTINATIONS):
        raise ValueError("verified commit is missing an expected application root")
    for app in sorted(app_roots):
        walk_tree(app_roots[app], f"apps/{app}")

    extra = sorted(set(found) - EXPECTED_APPLICATION_PATHS)
    if extra:
        if len(extra) == 1:
            raise ValueError(f"unclassified application path: {extra[0]}")
        raise ValueError(
            f"total file limit exceeded: expected exactly {MAX_FILES} classified application files"
        )
    missing = sorted(EXPECTED_APPLICATION_PATHS - set(found))
    if missing:
        raise ValueError(f"missing expected application path: {missing[0]}")
    if file_count != MAX_FILES:
        raise ValueError(f"total file limit requires exactly {MAX_FILES} files, found {file_count}")

    # Strict structured-data parsing, AFTER every resource/allowlist budget has
    # been enforced and BEFORE any output bytes are materialized: malformed or
    # ambiguous JSON / web-manifest content fails the whole build closed.
    for path in sorted(found):
        parse_structured_data(path, found[path].data)

    documentation = found["apps/hub/data/README.md"].data.decode("utf-8", "replace").casefold()
    if "synthetic" not in documentation or not all(PurePosixPath(path).name.casefold() in documentation for path in _SYNTHETIC_DEMOS):
        raise ValueError("synthetic demo allowlist is not documented in apps/hub/data/README.md")

    destinations: dict[str, str] = {}
    for path, entry in found.items():
        destination = entry.destination.as_posix()
        prior = destinations.get(destination)
        if prior is not None:
            raise ValueError(f"ambiguous output destination: {prior} and {path}")
        destinations[destination] = path
    return SourceLayout(
        repository=repository,
        git_dir=git_dir,
        root=source_path,
        commit=resolved,
        entries=tuple(found[path] for path in sorted(found)),
    )


def _read_exact_file(descriptor: int, size: int, label: str) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = os.read(descriptor, min(65536, remaining))
        if not chunk:
            raise ValueError(f"file changed while reading {label}")
        chunks.append(chunk)
        remaining -= len(chunk)
    if os.read(descriptor, 1):
        raise ValueError(f"file changed while reading {label}")
    return b"".join(chunks)


def read_output_tree(
    root: Path,
) -> tuple[Path, tuple[OutputFile, ...], tuple[OutputDirectory, ...]]:
    """Read one bounded, link-free output tree through verified descriptors."""
    root_path = _validate_user_path(root, "output root")
    root_descriptor = _open_directory(root_path, "output root")
    files: list[OutputFile] = []
    directories: list[OutputDirectory] = []
    total_bytes = 0
    work = 0

    def visit(directory_descriptor: int, prefix: PurePosixPath) -> None:
        nonlocal total_bytes, work
        with os.scandir(directory_descriptor) as iterator:
            names = sorted(entry.name for entry in iterator)
        for name in names:
            validate_path_component(name, label="output path")
            relative = prefix / name if prefix != PurePosixPath(".") else PurePosixPath(name)
            relative_text = relative.as_posix()
            _validate_git_path(f"apps/{relative_text}")
            work += 1
            if work > MAX_TRAVERSAL_WORK:
                raise ValueError("output traversal work limit exceeded")
            before = os.stat(name, dir_fd=directory_descriptor, follow_symlinks=False)
            if stat.S_ISLNK(before.st_mode):
                raise ValueError(f"symlink in output: {relative_text}")
            if stat.S_ISDIR(before.st_mode):
                child = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                    dir_fd=directory_descriptor,
                )
                try:
                    after = os.fstat(child)
                    if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                        raise ValueError(f"output directory identity changed: {relative_text}")
                    visit(child, relative)
                    final = os.fstat(child)
                    directories.append(
                        OutputDirectory(
                            path=relative_text,
                            mode=stat.S_IMODE(final.st_mode),
                            mtime_ns=final.st_mtime_ns,
                        )
                    )
                finally:
                    os.close(child)
            elif stat.S_ISREG(before.st_mode):
                if len(files) >= MAX_FILES:
                    raise ValueError("output total file limit exceeded")
                if before.st_size > MAX_FILE_BYTES:
                    raise ValueError(f"output per-file byte limit exceeded: {relative_text}")
                total_bytes += before.st_size
                if total_bytes > MAX_TOTAL_BYTES:
                    raise ValueError("output total byte limit exceeded")
                descriptor = os.open(
                    name,
                    os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                    dir_fd=directory_descriptor,
                )
                try:
                    after = os.fstat(descriptor)
                    if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                        raise ValueError(f"output file identity changed: {relative_text}")
                    data = _read_exact_file(descriptor, after.st_size, relative_text)
                    files.append(
                        OutputFile(
                            path=relative_text,
                            data=data,
                            mode=stat.S_IMODE(after.st_mode),
                            mtime_ns=after.st_mtime_ns,
                        )
                    )
                finally:
                    os.close(descriptor)
            else:
                raise ValueError(f"unsupported path in output: {relative_text}")

    try:
        visit(root_descriptor, PurePosixPath("."))
        root_metadata = os.fstat(root_descriptor)
        directories.append(
            OutputDirectory(
                path=".",
                mode=stat.S_IMODE(root_metadata.st_mode),
                mtime_ns=root_metadata.st_mtime_ns,
            )
        )
    finally:
        os.close(root_descriptor)
    return (
        root_path,
        tuple(sorted(files, key=lambda item: item.path)),
        tuple(sorted(directories, key=lambda item: item.path)),
    )


def json_manifest(root: Path) -> str:
    """Deterministic JSON manifest covering files AND directories.

    Directories are recorded so the artifact's structure is unambiguous, and both
    file and directory paths are run through the same canonical collision
    registry used for source classification, so a cross-platform path collision
    can never be represented silently.
    """
    _, files, directories = read_output_tree(root)
    registry = _PathRegistry()
    for item in directories:
        registry.add(item.path, kind="directory")
    for item in files:
        registry.add(item.path, kind="file")

    directory_records = [
        {"mode": f"{item.mode:04o}", "mtime_ns": item.mtime_ns, "path": item.path}
        for item in directories
    ]
    file_records = [
        {
            "mode": f"{item.mode:04o}",
            "mtime_ns": item.mtime_ns,
            "path": item.path,
            "sha256": hashlib.sha256(item.data).hexdigest(),
            "size": len(item.data),
        }
        for item in files
    ]
    value = {
        "directories": directory_records,
        "files": file_records,
        "schema": 2,
        "total_bytes": sum(record["size"] for record in file_records),
        "total_directories": len(directory_records),
        "total_files": len(file_records),
    }
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
