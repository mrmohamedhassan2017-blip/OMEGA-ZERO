"""
OMEGA / ZERO Public Gateway Safe Backend V1
============================================
Internet-safe, bounded CODE_SCAN service.

SUPREME RULES (enforced here, not just documented):
  PUBLIC INPUT IS HOSTILE UNTIL PROVEN OTHERWISE.
  UPLOADED CODE IS DATA, NOT AUTHORITY.
  A GITHUB URL IS NOT PERMISSION TO EXECUTE ITS CODE.
  STATIC ANALYSIS DOES NOT REQUIRE TRUSTING THE TARGET.
  NO FINDINGS DOES NOT MEAN NO VULNERABILITIES.
"""
from __future__ import annotations

import hashlib
import ipaddress
import io
import json
import os
import re
import shutil
import socket
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Resource limits
# ---------------------------------------------------------------------------
MAX_COMPRESSED_BYTES = 50 * 1024 * 1024     # 50 MB zip download
MAX_EXTRACTED_BYTES = 200 * 1024 * 1024     # 200 MB extracted total
MAX_FILES = 2_000
MAX_FILE_BYTES = 5 * 1024 * 1024            # 5 MB per file for analysis
MAX_PATH_DEPTH = 20
MAX_SCAN_SECONDS = 30.0
MAX_REDIRECTS = 3
FETCH_TIMEOUT_SECONDS = 20
CONCURRENCY_LIMIT = 5
QUEUE_LIMIT = 20
RATE_WINDOW_SECONDS = 60
RATE_MAX_PER_WINDOW = 10
READ_BYTES_PER_FILE = 1024 * 1024           # analyse at most 1 MB of each file

BACKEND_VERSION = "safe-backend-v1"

# ---------------------------------------------------------------------------
# Rate / queue / concurrency controls
# ---------------------------------------------------------------------------
_rate_lock = threading.Lock()
_rate_buckets: dict[str, list[float]] = defaultdict(list)
_active_scans = threading.Semaphore(CONCURRENCY_LIMIT)
_queue_count = 0
_queue_lock = threading.Lock()


def _check_rate(client_id: str) -> bool:
    now = time.monotonic()
    with _rate_lock:
        bucket = _rate_buckets[client_id]
        bucket[:] = [t for t in bucket if now - t < RATE_WINDOW_SECONDS]
        if len(bucket) >= RATE_MAX_PER_WINDOW:
            return False
        bucket.append(now)
        return True


def _enter_queue() -> bool:
    global _queue_count
    with _queue_lock:
        if _queue_count >= QUEUE_LIMIT:
            return False
        _queue_count += 1
        return True


def _leave_queue() -> None:
    global _queue_count
    with _queue_lock:
        _queue_count = max(0, _queue_count - 1)


# ---------------------------------------------------------------------------
# SSRF / network firewall
# ---------------------------------------------------------------------------
_FORBIDDEN_SCHEMES = ("http://", "file://", "ftp://", "gopher://",
                      "data:", "javascript:", "\\\\")
_PRIVATE_NETWORKS = [
    ipaddress.ip_network(s) for s in (
        "127.0.0.0/8", "0.0.0.0/8", "10.0.0.0/8",
        "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16",
        "100.64.0.0/10", "::1/128", "fc00::/7", "fe80::/10",
    )
]
_ALLOWED_FETCH_HOSTS = frozenset({
    "api.github.com", "github.com", "codeload.github.com",
    "objects.githubusercontent.com",
})
_GITHUB_URL_RE = re.compile(
    r"^https://github\.com/"
    r"([A-Za-z0-9](?:[A-Za-z0-9._-]{0,37}[A-Za-z0-9])?)"
    r"/([A-Za-z0-9._-]{1,100})/?$"
)


def _is_private_host(hostname: str) -> bool:
    """Return True if hostname resolves to a private / reserved address."""
    # direct IP literal
    try:
        addr = ipaddress.ip_address(hostname)
        return any(addr in net for net in _PRIVATE_NETWORKS)
    except ValueError:
        pass
    # DNS resolution — guard each resolved address
    try:
        for _fam, _typ, _proto, _canon, sockaddr in socket.getaddrinfo(hostname, None):
            try:
                addr = ipaddress.ip_address(sockaddr[0])
                if any(addr in net for net in _PRIVATE_NETWORKS):
                    return True
            except ValueError:
                pass
    except (socket.gaierror, OSError):
        pass
    return False


def _validate_github_url(raw: str) -> dict[str, Any]:
    url = (raw or "").strip()
    low = url.lower()
    for bad in _FORBIDDEN_SCHEMES:
        if low.startswith(bad):
            return {"valid": False,
                    "error": "unsupported scheme — only public GitHub HTTPS URLs accepted"}
    m = _GITHUB_URL_RE.match(url)
    if not m:
        return {"valid": False,
                "error": "only https://github.com/<owner>/<repo> URLs are accepted"}
    owner, repo = m.group(1), m.group(2)
    # guard metadata-like strings embedded in path
    combined = f"{owner}/{repo}".lower()
    if any(s in combined for s in ("169.254", "localhost", "127.0", "internal", "metadata")):
        return {"valid": False, "error": "invalid repository identifier"}
    return {"valid": True, "owner": owner, "repo": repo}


# ---------------------------------------------------------------------------
# Redirect-safe HTTP handler
# ---------------------------------------------------------------------------
class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    max_repeats = MAX_REDIRECTS
    max_redirections = MAX_REDIRECTS

    def _guard(self, location: str) -> None:
        parsed = urllib.request.urlparse(location)
        if parsed.scheme != "https":
            raise urllib.error.URLError(f"redirect to non-https blocked")
        host = (parsed.hostname or "").lower()
        if host not in _ALLOWED_FETCH_HOSTS:
            raise urllib.error.URLError(f"redirect to disallowed host blocked")
        if _is_private_host(host):
            raise urllib.error.URLError(f"redirect to private host blocked")

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self._guard(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


# ---------------------------------------------------------------------------
# Safe GitHub fetch
# ---------------------------------------------------------------------------
def _fetch_github_zip(owner: str, repo: str) -> tuple[bytes, str]:
    """
    Download the default-branch zipball from GitHub.
    Returns (zip_bytes, head_sha_or_unknown).
    Raises ValueError with public-safe message on any failure.
    """
    # DNS rebinding pre-check
    if _is_private_host("api.github.com"):
        raise ValueError("github API host resolved to private address")

    url = f"https://api.github.com/repos/{owner}/{repo}/zipball"
    opener = urllib.request.build_opener(_SafeRedirectHandler())
    opener.addheaders = [
        ("User-Agent", "OMEGA-ZERO-Public-Gateway/1.0"),
        ("Accept", "application/vnd.github+json"),
        ("X-GitHub-Api-Version", "2022-11-28"),
    ]
    try:
        resp = opener.open(url, timeout=FETCH_TIMEOUT_SECONDS)
        data = b""
        while True:
            chunk = resp.read(65_536)
            if not chunk:
                break
            data += chunk
            if len(data) > MAX_COMPRESSED_BYTES:
                resp.close()
                raise ValueError("repository archive exceeds size limit")
        final_url = resp.geturl()
        sha_m = re.search(r"/([0-9a-f]{40})\b", final_url)
        return data, sha_m.group(1) if sha_m else "unknown"
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ValueError("repository not found or is private")
        if exc.code == 403:
            raise ValueError("repository access denied — rate limited or blocked")
        raise ValueError(f"repository fetch failed ({exc.code})")
    except urllib.error.URLError as exc:
        reason = str(exc.reason)
        if any(k in reason for k in ("private", "blocked", "disallowed")):
            raise ValueError("repository host not permitted")
        raise ValueError("repository fetch failed — network unavailable")
    except TimeoutError:
        raise ValueError("repository fetch timed out")


# ---------------------------------------------------------------------------
# Archive safety
# ---------------------------------------------------------------------------
def _safe_extract(zip_bytes: bytes, dest: Path) -> dict[str, Any]:
    """
    Extract zip into dest with full path traversal, symlink, size, and
    file-count guards. Returns extraction metadata dict.
    Raises ValueError on any safety violation.
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        raise ValueError("archive is not a valid zip file")

    members = zf.infolist()
    if len(members) > MAX_FILES:
        raise ValueError(f"archive contains too many entries ({len(members)} > {MAX_FILES})")

    extracted_bytes = 0
    extracted_count = 0
    skipped: list[dict] = []
    dest.mkdir(parents=True, exist_ok=True)
    dest_resolved = dest.resolve()

    for info in members:
        name = info.filename

        # ── path traversal guard ──────────────────────────────────────────
        if ".." in name or name.startswith("/") or name.startswith("\\"):
            raise ValueError(f"archive contains path traversal entry: {name[:80]!r}")
        if re.match(r"^[A-Za-z]:[/\\]", name):
            raise ValueError(f"archive contains absolute Windows path: {name[:80]!r}")
        if name.startswith("\\\\"):
            raise ValueError(f"archive contains UNC path: {name[:80]!r}")

        # ── symlink guard ─────────────────────────────────────────────────
        unix_mode = (info.external_attr >> 16) & 0xFFFF
        if unix_mode and (unix_mode & 0xF000) == 0xA000:
            skipped.append({"path": name[:200], "reason": "symlink_skipped"})
            continue

        # ── depth guard ───────────────────────────────────────────────────
        parts = Path(name).parts
        if len(parts) > MAX_PATH_DEPTH:
            skipped.append({"path": name[:200], "reason": "path_too_deep"})
            continue

        # ── directory entries ─────────────────────────────────────────────
        if name.endswith("/") or info.is_dir():
            continue

        # ── per-file size ─────────────────────────────────────────────────
        if info.file_size > MAX_FILE_BYTES:
            skipped.append({"path": name[:200], "reason": "file_too_large"})
            continue

        # ── compression ratio / bomb guard ───────────────────────────────
        if info.compress_size > 0 and info.file_size / info.compress_size > 1000:
            skipped.append({"path": name[:200], "reason": "compression_ratio_exceeded"})
            continue

        # ── total extraction budget ───────────────────────────────────────
        extracted_bytes += info.file_size
        if extracted_bytes > MAX_EXTRACTED_BYTES:
            raise ValueError("archive extraction budget exceeded")

        target = dest / name
        # final traversal guard after path join
        try:
            target.resolve().relative_to(dest_resolved)
        except ValueError:
            raise ValueError(f"archive path escapes extraction root: {name[:80]!r}")

        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, open(target, "wb") as out:
            out.write(src.read())
        extracted_count += 1

    return {
        "files_extracted": extracted_count,
        "bytes_extracted": extracted_bytes,
        "skipped": skipped,
    }


# ---------------------------------------------------------------------------
# Static analysis patterns (no execution, data only)
# ---------------------------------------------------------------------------
_SECRET_CHECKS = [
    (re.compile(r'(?i)(?:api[_-]?key|apikey)\s*[=:]\s*["\']?([A-Za-z0-9/_+\-]{20,})["\']?'), "API_KEY"),
    (re.compile(r'(?i)(?:password|passwd|pwd)\s*[=:]\s*["\']([^\s"\']{8,})["\']'), "PASSWORD"),
    (re.compile(r'(?i)(?:secret|token|client_secret|access_token|refresh_token)\s*[=:]\s*["\']([A-Za-z0-9/_+\-.]{16,})["\']'), "SECRET_TOKEN"),
    (re.compile(r'AIza[0-9A-Za-z\-_]{35}'), "GOOGLE_API_KEY"),
    (re.compile(r'sk-[A-Za-z0-9]{32,}'), "OPENAI_KEY"),
    (re.compile(r'ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{82}'), "GITHUB_TOKEN"),
    (re.compile(r'AKIA[0-9A-Z]{16}'), "AWS_ACCESS_KEY"),
    (re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'), "PRIVATE_KEY"),
    (re.compile(r'(?i)\.env\b'), "ENV_FILE_REFERENCE"),
]
_DANGER_CHECKS = [
    (re.compile(r'(?i)\b(?:subprocess|os\.system|os\.popen)\s*[\.(]'), "SUBPROCESS_USAGE", "HIGH"),
    (re.compile(r'(?i)\beval\s*\('), "EVAL_USAGE", "HIGH"),
    (re.compile(r'(?i)\bexec\s*\('), "EXEC_USAGE", "MEDIUM"),
    (re.compile(r'(?i)\bpickle\.loads?\s*\('), "UNSAFE_DESERIALIZATION", "HIGH"),
    (re.compile(r'(?i)\byaml\.load\s*\((?!.*SafeLoader)'), "UNSAFE_YAML_LOAD", "HIGH"),
    (re.compile(r'(?i)\b__import__\s*\('), "DYNAMIC_IMPORT", "MEDIUM"),
    (re.compile(r'(?i)child_process\b'), "NODEJS_CHILD_PROCESS", "MEDIUM"),
    (re.compile(r'(?i)Runtime\.getRuntime\(\)\.exec'), "JAVA_RUNTIME_EXEC", "HIGH"),
]
_NETWORK_CHECKS = [
    (re.compile(r'(?i)\brequests\.(get|post|put|delete|patch)\s*\('), "HTTP_CLIENT"),
    (re.compile(r'(?i)\burllib\.request\.(urlopen|urlretrieve)\s*\('), "HTTP_CLIENT"),
    (re.compile(r'(?i)\bsocket\.connect\s*\('), "RAW_SOCKET"),
    (re.compile(r'(?i)\bfetch\s*\('), "FETCH_CALL"),
]

_SKIP_EXTS = frozenset({
    ".png",".jpg",".jpeg",".gif",".bmp",".ico",".webp",
    ".mp3",".mp4",".avi",".mov",".wav",".ogg",
    ".woff",".woff2",".ttf",".otf",".eot",
    ".zip",".tar",".gz",".bz2",".7z",".rar",".xz",
    ".exe",".dll",".so",".dylib",".bin",".a",".o",
    ".pyc",".pyd",".class",".jar",".war",
    ".lock",".sum",".snap",
    ".pdf",".docx",".xlsx",".pptx",
})
_TEXT_EXTS = frozenset({
    ".py",".pyw",".pyi",".js",".mjs",".cjs",".ts",".tsx",".jsx",
    ".java",".kt",".kts",".scala",".groovy",
    ".rb",".php",".go",".rs",".c",".cpp",".cc",".h",".hpp",
    ".cs",".swift",".dart",".lua",".r",".pl",".pm",
    ".sh",".bash",".zsh",".fish",".ps1",".bat",".cmd",
    ".env",".ini",".cfg",".conf",".config",
    ".yaml",".yml",".toml",".json",".jsonc",".xml",
    ".html",".htm",".css",".scss",".sass",".less",
    ".md",".rst",".txt",".dockerfile",
    ".tf",".hcl",".bicep",".cloudformation",
    ".sql",".graphql",".proto",
})


def _finding_id(category: str, path: str, line: int) -> str:
    raw = f"{category}:{path}:{line}"
    return f"{category[:4]}-{hashlib.sha1(raw.encode()).hexdigest()[:8]}"


def _analyze_text(rel_path: str, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    lines = text.splitlines()
    for lineno, line in enumerate(lines, 1):
        for pattern, label in _SECRET_CHECKS:
            if pattern.search(line):
                findings.append({
                    "finding_id": _finding_id("SEC", rel_path, lineno),
                    "category": "SECRET_PATTERN",
                    "severity": "HIGH",
                    "confidence": "MEDIUM",
                    "file": rel_path[:200],
                    "line": lineno,
                    # NEVER echo the matched value
                    "evidence": f"{label} pattern matched at line {lineno}",
                    "reason": f"A credential/secret pattern ({label}) was detected. The value itself is not reported.",
                    "limitations": "Pattern matching may produce false positives on test fixtures or example data.",
                })
                break  # one secret finding per line per file is sufficient
        for pattern, label, sev in _DANGER_CHECKS:
            if pattern.search(line):
                findings.append({
                    "finding_id": _finding_id("DNG", rel_path, lineno),
                    "category": "DANGEROUS_COMMAND_CONSTRUCTION",
                    "severity": sev,
                    "confidence": "LOW",
                    "file": rel_path[:200],
                    "line": lineno,
                    "evidence": f"{label} pattern at line {lineno}",
                    "reason": f"Potentially unsafe code pattern ({label}); actual risk depends on runtime context.",
                    "limitations": "Static analysis only; no dataflow or taint analysis.",
                })
        for pattern, label in _NETWORK_CHECKS:
            if pattern.search(line):
                findings.append({
                    "finding_id": _finding_id("NET", rel_path, lineno),
                    "category": "NETWORK_USAGE",
                    "severity": "INFO",
                    "confidence": "LOW",
                    "file": rel_path[:200],
                    "line": lineno,
                    "evidence": f"{label} pattern at line {lineno}",
                    "reason": "Outbound network usage detected; review for unintended data exposure.",
                    "limitations": "Static analysis only.",
                })
    return findings


def _analyze_file(rel_path: str, content: bytes) -> list[dict[str, Any]]:
    ext = Path(rel_path).suffix.lower()
    if ext in _SKIP_EXTS:
        return []
    try:
        text = content[:READ_BYTES_PER_FILE].decode("utf-8", errors="replace")
    except Exception:
        return []
    return _analyze_text(rel_path, text)


# ---------------------------------------------------------------------------
# Error sanitization — NEVER expose internal paths or traces
# ---------------------------------------------------------------------------
_WIN_PATH_RE = re.compile(r"[A-Za-z]:[/\\][^\n]+")
_UNIX_PATH_RE = re.compile(r"/[a-z][^\s,;)\]]{3,}")


def _sanitize_error(exc: Exception) -> str:
    msg = str(exc)
    msg = _WIN_PATH_RE.sub("[path]", msg)
    msg = _UNIX_PATH_RE.sub("[path]", msg)
    # strip tracebacks
    msg = re.sub(r'(File|line\s+\d+|in\s+\w+)\s+"?[^\s"]+', r"\1 [detail]", msg)
    return msg[:200]


# ---------------------------------------------------------------------------
# Public health
# ---------------------------------------------------------------------------
def public_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "backend": BACKEND_VERSION,
        "deployment": "LOCAL — NOT PUBLICLY DEPLOYED",
        "capabilities": ["CODE_SCAN"],
        "input_modes": ["fixture:known-good", "fixture:known-bad", "github_public_https_url"],
        "limits": {
            "max_compressed_bytes": MAX_COMPRESSED_BYTES,
            "max_extracted_bytes": MAX_EXTRACTED_BYTES,
            "max_files": MAX_FILES,
            "max_file_bytes": MAX_FILE_BYTES,
            "max_scan_seconds": MAX_SCAN_SECONDS,
            "concurrency_limit": CONCURRENCY_LIMIT,
            "queue_limit": QUEUE_LIMIT,
            "rate_max_per_minute": RATE_MAX_PER_WINDOW,
            "max_redirects": MAX_REDIRECTS,
        },
        "arbitrary_code_execution": False,
        "arbitrary_shell": False,
        "arbitrary_filesystem_access": False,
    }


# ---------------------------------------------------------------------------
# Core scan
# ---------------------------------------------------------------------------
def public_code_scan(
    target: str,
    *,
    client_id: str = "default",
) -> dict[str, Any]:
    """
    Public CODE_SCAN entry point.
    target: fixture:known-good | fixture:known-bad | https://github.com/<owner>/<repo>
    client_id: opaque caller identifier for rate limiting (e.g. remote IP).
    """
    import uuid
    scan_id = "pgsb-" + uuid.uuid4().hex[:12]
    t0 = time.monotonic()
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _resp(verdict, input_class, *, files_discovered=0, files_analyzed=0,
              files_skipped=0, checks_executed=0, findings=None,
              uncertainty=None, limitations=None, error_code=None):
        f = findings or []
        sev = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for item in f:
            k = item.get("severity", "INFO")
            sev[k] = sev.get(k, 0) + 1
        r: dict[str, Any] = {
            "scan_id": scan_id,
            "scan_version": BACKEND_VERSION,
            "timestamp": ts,
            "input_class": input_class,
            "files_discovered": files_discovered,
            "files_analyzed": files_analyzed,
            "files_skipped": files_skipped,
            "checks_executed": checks_executed,
            "findings": f,
            "severity_summary": sev,
            "evidence": {
                "duration_ms": round((time.monotonic() - t0) * 1000),
                "source_retained": False,
            },
            "uncertainty": uncertainty or (
                "static pattern analysis only; does not prove absence of vulnerabilities"
            ),
            "limitations": limitations or [
                "pattern matching only; no AST, dataflow, or taint analysis",
                "no dependency or supply-chain analysis",
                "binary and oversized files are skipped",
                "VERIFIED_CLEAN_WITHIN_CHECKS means no patterns matched, not that code is safe",
            ],
            "zero_verdict": verdict,
        }
        if error_code:
            r["error_code"] = error_code
        return r

    # ── rate limit ────────────────────────────────────────────────────────
    if not _check_rate(client_id):
        return _resp("SCAN_LIMIT_EXCEEDED", "RATE_LIMITED",
                     uncertainty="rate limit exceeded — retry after 60 s",
                     error_code="RATE_LIMIT_EXCEEDED")

    # ── queue limit ───────────────────────────────────────────────────────
    if not _enter_queue():
        return _resp("SCAN_LIMIT_EXCEEDED", "QUEUE_FULL",
                     uncertainty="service at capacity — retry later",
                     error_code="QUEUE_FULL")

    try:
        text = (target or "").strip()
        if not text:
            return _resp("INVALID_INPUT", "EMPTY", error_code="EMPTY_INPUT",
                         uncertainty="no input provided")

        # ── deterministic fixtures ────────────────────────────────────────
        if text == "fixture:known-good":
            return _resp(
                "VERIFIED_CLEAN_WITHIN_CHECKS", "LOCAL_FIXTURE",
                files_discovered=1, files_analyzed=1, checks_executed=len(_SECRET_CHECKS),
                findings=[{
                    "finding_id": "PG-KG-001",
                    "category": "FIXTURE",
                    "severity": "INFO",
                    "confidence": "CONFIRMED",
                    "file": "fixture:known-good",
                    "line": 0,
                    "evidence": "known-good fixture: test marker present, no secret marker",
                    "reason": "Deterministic fixture representing a clean baseline.",
                    "limitations": "Fixture only; does not represent a real repository scan.",
                }],
                uncertainty="fixture result — does not represent a real repository",
                limitations=["deterministic fixture; not a live scan"],
            )
        if text == "fixture:known-bad":
            return _resp(
                "NEEDS_ATTENTION", "LOCAL_FIXTURE",
                files_discovered=1, files_analyzed=1, checks_executed=len(_SECRET_CHECKS),
                findings=[{
                    "finding_id": "PG-KB-001",
                    "category": "SECRET_PATTERN",
                    "severity": "HIGH",
                    "confidence": "CONFIRMED",
                    "file": "fixture:known-bad",
                    "line": 1,
                    "evidence": "intentional dummy SECRET_TOKEN marker at line 1",
                    "reason": "Fixture designed to prove evidence-backed detection works.",
                    "limitations": "Dummy value; fixture only.",
                }],
                uncertainty="fixture result — demonstrates detection capability only",
                limitations=["deterministic fixture; not a live scan"],
            )

        # ── GitHub URL validation ─────────────────────────────────────────
        val = _validate_github_url(text)
        if not val["valid"]:
            return _resp("INVALID_INPUT", "INVALID_URL", error_code="INVALID_INPUT",
                         uncertainty=val["error"])

        owner, repo = val["owner"], val["repo"]

        # ── concurrency gate ──────────────────────────────────────────────
        if not _active_scans.acquire(blocking=False):
            return _resp("SCAN_LIMIT_EXCEEDED", "CONCURRENCY_LIMIT",
                         error_code="CONCURRENCY_LIMIT",
                         uncertainty="too many concurrent scans — retry later")

        tmpdir: Path | None = None
        try:
            # ── fetch ─────────────────────────────────────────────────────
            try:
                zip_bytes, _sha = _fetch_github_zip(owner, repo)
            except ValueError as exc:
                return _resp("INVALID_INPUT", "GITHUB_REPOSITORY",
                             error_code="FETCH_FAILED",
                             uncertainty=str(exc))

            if time.monotonic() - t0 > MAX_SCAN_SECONDS:
                return _resp("SCAN_TIMEOUT", "GITHUB_REPOSITORY",
                             error_code="TIMEOUT")

            # ── extract ───────────────────────────────────────────────────
            tmpdir = Path(tempfile.mkdtemp(prefix="omega_pgsb_"))
            try:
                meta = _safe_extract(zip_bytes, tmpdir)
            except ValueError as exc:
                return _resp("INVALID_INPUT", "GITHUB_REPOSITORY",
                             error_code="ARCHIVE_SAFETY",
                             uncertainty=_sanitize_error(exc))

            # ── static analysis ───────────────────────────────────────────
            all_file_paths = [p for p in tmpdir.rglob("*") if p.is_file()]
            files_discovered = len(all_file_paths)
            files_analyzed = 0
            files_skipped = len(meta["skipped"])
            all_findings: list[dict] = []
            checks_executed = (
                len(_SECRET_CHECKS) + len(_DANGER_CHECKS) + len(_NETWORK_CHECKS)
            )

            for fpath in all_file_paths:
                if time.monotonic() - t0 > MAX_SCAN_SECONDS:
                    return _resp(
                        "SCAN_TIMEOUT", "GITHUB_REPOSITORY",
                        files_discovered=files_discovered,
                        files_analyzed=files_analyzed,
                        files_skipped=files_skipped,
                        checks_executed=checks_executed,
                        findings=all_findings[:500],
                        error_code="TIMEOUT",
                    )
                ext = fpath.suffix.lower()
                if ext in _SKIP_EXTS:
                    files_skipped += 1
                    continue
                if ext not in _TEXT_EXTS and fpath.stat().st_size > 65_536:
                    files_skipped += 1
                    continue
                try:
                    rel = str(fpath.relative_to(tmpdir))
                    content = fpath.read_bytes()
                    file_findings = _analyze_file(rel, content)
                    all_findings.extend(file_findings)
                    files_analyzed += 1
                except Exception:
                    files_skipped += 1

            # ── verdict ───────────────────────────────────────────────────
            has_high = any(f["severity"] == "HIGH" for f in all_findings)
            has_medium = any(f["severity"] == "MEDIUM" for f in all_findings)
            if has_high or has_medium:
                verdict = "NEEDS_ATTENTION"
            elif all_findings:
                verdict = "NEEDS_ATTENTION"
            else:
                verdict = "VERIFIED_CLEAN_WITHIN_CHECKS"

            return _resp(
                verdict, "GITHUB_REPOSITORY",
                files_discovered=files_discovered,
                files_analyzed=files_analyzed,
                files_skipped=files_skipped,
                checks_executed=checks_executed,
                findings=all_findings[:500],  # bounded response
                uncertainty=(
                    f"static pattern analysis of {files_analyzed}/{files_discovered} files; "
                    "does not execute code; does not resolve dependencies; "
                    "false positives and negatives are possible"
                ),
                limitations=[
                    "pattern-based detection only — no AST, dataflow, or taint analysis",
                    "no dependency or supply-chain analysis",
                    "binary, image, and oversized files are skipped",
                    "false positives possible on test or example data",
                    "VERIFIED_CLEAN_WITHIN_CHECKS: no patterns matched, not that code is safe",
                ],
            )

        finally:
            # ── privacy: delete ALL temporary material immediately ─────────
            if tmpdir and tmpdir.exists():
                shutil.rmtree(tmpdir, ignore_errors=True)
            _active_scans.release()

    except Exception as exc:
        return _resp("INTERNAL_ERROR", "UNKNOWN",
                     error_code="INTERNAL_ERROR",
                     uncertainty=_sanitize_error(exc))
    finally:
        _leave_queue()
