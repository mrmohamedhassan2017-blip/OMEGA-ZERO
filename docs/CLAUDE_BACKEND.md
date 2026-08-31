# Claude Code Backend (Bounded Capability)

This document describes the `CLAUDE_CODE_BACKEND` adapter implemented in
`omega/claude_backend.py` and configured in `.omega/config.toml`
(`[backends.claude_code]`).

The adapter is a **bounded execution provider**. It is not a control plane, not
an authority, and not a verifier. Provider claims are deliberately kept separate
from Host Verification.

## Status

- `enabled = true`, `mode = "shadow"` in `.omega/config.toml`.
- `production_routing = false`; the bounded `controlled_canary` gate is now
  `true` after its Host-verified pass.
- The production default backend is unchanged (`CODEX_BACKEND`); the deterministic
  host executor remains first.
- This document does **not** claim production activation. No measured superiority
  over any other backend is claimed or implied.

## Bounded task envelope

Every execution is governed by a `TaskEnvelope` (`omega/claude_backend.py`).
Key fields and enforced constraints:

| Field | Meaning / enforcement |
| --- | --- |
| `task_id`, `objective` | Required, non-empty. |
| `task_class` | Must be one of: `CODE_REPAIR`, `BUG_DIAGNOSIS`, `REFACTOR`, `TEST_GENERATION`, `DOCUMENTATION_UPDATE`, `STATIC_REVIEW`, `CODE_REVIEW`, `ARCHITECTURAL_ANALYSIS`. |
| `allowed_paths` | Repository-relative allowlist. Any write task (`expected_change_class != "NONE"`) must supply an explicit allowlist. Absolute paths and `..` segments are rejected. |
| `forbidden_paths` | Defaults deny `.git/**`, `.omega/**`, `**/*credential*`, `**/*secret*`, `**/*token*`. |
| `expected_change_class` | `"NONE"` for read-only tasks; anything else requires `allowed_paths`. |
| `max_duration` | Validated within 1–3600 seconds. Enforced by a host-side deadline; the process is cancelled/killed on timeout. |
| `resource_budget.max_backend_attempts` | Must be exactly `1`. One adapter execution equals one backend attempt. |
| `resource_budget.max_output_bytes` | Validated within 1 KiB–1 MiB; only the trailing bytes of stdout/stderr are retained (default 65536). |
| `authority_class` | Informational label (e.g. `INTERNAL_READ_ONLY`, `INTERNAL_BOUNDED_CANARY`). |
| `network_policy` | Must be `PROVIDER_API_ONLY`. |
| `external_write_policy` | Must be `DENIED`. |
| `financial_policy` | Must be `DENIED`. |
| `allow_deletions` | Default `false`; deletions otherwise count as scope violations. |
| `allow_binary_changes` | Default `false`; binary edits otherwise count as scope violations. |

`TaskEnvelope.validate()` raises before any process starts if these constraints
are not met, producing failure class `INVALID_TASK_ENVELOPE`.

### Scope enforcement

Before and after the run, the adapter takes a SHA-256 snapshot of the repository
tree (excluding `.git`, `.omega`, caches, virtualenvs, `node_modules`). Post-run
it computes changed and deleted files and records `scope_violations` for:

- `forbidden:<path>` — matched a forbidden pattern.
- `outside-allowlist:<path>` — not covered by `allowed_paths`.
- `path-escape:<path>` — resolved outside the canonical root.
- `binary:<path>` — binary change without `allow_binary_changes`.
- `deleted:<path>` — deletion without `allow_deletions`.

Any violation forces `failure_class = "TASK_SCOPE_VIOLATION"` and
`claimed_success = false`. A read-only envelope that nonetheless changes files is
also a scope violation.

## Tools allowed

From `ClaudeCodeBackend.capabilities()` and `_command()`:

- Allowed tools: **`Read`, `Edit`, `Write`, `Glob`, `Grep`**.
- Write tasks run with tools `Read,Edit,Write,Glob,Grep` and permission mode
  `acceptEdits`.
- Read-only tasks run with **no** edit tools and permission mode `plan`.
- `Bash`, `WebFetch`, `WebSearch`, and MCP tools are **not** allowlisted.
  The CLI is invoked with `--safe-mode`, `--strict-mcp-config`,
  `--no-session-persistence`, and permission-bypass modes are disallowed.
- The subprocess runs with a minimal environment (a small allowlist of Windows
  path/temp variables plus `NO_COLOR` / `PYTHONUTF8`), with `cwd` pinned to the
  backend's validated canonical root.
- Secrets are redacted from captured stdout/stderr (`Bearer` tokens and common
  `api_key` / `token` / `password` / `cookie` style key-value pairs).

## Host Verification authority

- The host is the sole verifier. The adapter never self-verifies:
  `capabilities()` reports `host_tests: false` and `self_verification: false`.
- A successful provider exit yields result state
  `COMPLETED_PENDING_HOST_VERIFICATION` with `claimed_success = true` and
  `verified_success = false`.
- `compatible_dict()` always sets `host_verification_required: true`.
- `verified_success` is only ever set by host-side verification, never by this
  adapter. Any recorded `failure_class` forces `result_state = "FAILED"` and
  `verified_success = false`.
- The rollback plan for a failed verification is to discard only
  backend-owned changes.

## SHADOW-only routing

- `.omega/config.toml` sets `mode = "shadow"`, `production_routing = false`,
  and records that the bounded controlled canary passed. This does not activate
  production routing.
- `backend_status()` reports `router_mode: "SHADOW"`,
  `production_default: "CODEX_BACKEND"`, `deterministic_host_first: true`, and
  lists `CLAUDE_CODE_BACKEND` with `routing: "SHADOW_ONLY"`.
- `CODEX_BACKEND` routing is `CURRENT_DEFAULT_UNCHANGED`; `dual_agent_default`
  is `false`.
- The compatibility entry point `execute()` builds a read-only
  (`expected_change_class = "NONE"`) envelope, so plain prompts cannot silently
  gain repository-write authority. Production routing remains disabled.
- Only allowlisted evidence keys may be persisted via
  `record_backend_evidence()` (e.g. `shadow_result`, `shadow_metrics`,
  `canary_result`, `router_shadow_result`, `last_verified_at`). Provider output
  and credentials are never persisted.

## Provider-managed credentials

- Authentication is entirely provider/CLI-managed. The adapter only *observes*
  state via `claude auth status --json`, reporting `authentication_state` as
  `AUTHENTICATED`, `NOT_AUTHENTICATED`, `AUTH_EXPIRED`, or `AUTH_UNKNOWN`, plus
  optional `auth_method` (`claude.ai` / `apiKey`) and `api_provider`.
- No credentials, API keys, or tokens are read, stored, injected, or logged by
  the adapter. The minimal subprocess environment does not forward credential
  variables.
- `provider_account_rotation = false` / `DISALLOWED` and
  `quota_bypass = false` / `DISALLOWED`.

## Unknown quota and cost

- `discover()` / `availability()` report `quota_visibility: "UNKNOWN"`.
- `usage()` reports `quota_visibility: "UNKNOWN"` and
  `billing_accounting: "NOT_AVAILABLE"`; it only counts local history rows and
  verified successes.
- Provider-side quota exhaustion or billing state is surfaced only reactively as
  failure classes `USAGE_QUOTA_LIMIT` or `RATE_LIMIT` when detected in provider
  output. The adapter cannot measure or predict cost.

## Zero external-write and financial authority

- `capabilities()` reports `external_write_authority: "NONE"` and
  `financial_authority: "NONE"`.
- `backend_status()` repeats `external_write_authority: "NONE"` and
  `financial_authority: "NONE"` for every backend entry.
- `.omega/config.toml` sets `external_write_authority = "none"` and
  `financial_authority = "none"`.
- `TaskEnvelope.validate()` rejects any envelope whose `external_write_policy` or
  `financial_policy` is not `DENIED`, and any `network_policy` other than
  `PROVIDER_API_ONLY`.
- The adapter performs no network calls itself beyond the provider CLI, makes no
  external writes, changes no accounts, and spends no money.

## Failure classes

`execute_envelope()` may return one of: `BACKEND_NOT_FOUND`, `AUTH_FAILURE`,
`PROVIDER_UNAVAILABLE`, `USAGE_QUOTA_LIMIT`, `RATE_LIMIT`, `NETWORK_FAILURE`,
`TIMEOUT`, `PROCESS_CRASH`, `INVALID_OUTPUT`, `NO_CHANGES`, `TASK_REFUSED`,
`TOOL_FAILURE`, `PERMISSION_FAILURE`, `VERIFICATION_FAILURE`,
`UNKNOWN_PROVIDER_FAILURE`, `TASK_SCOPE_VIOLATION`, `INVALID_TASK_ENVELOPE`,
`CANCELLED`. Unrecognized values are normalized to `UNKNOWN_PROVIDER_FAILURE`.
