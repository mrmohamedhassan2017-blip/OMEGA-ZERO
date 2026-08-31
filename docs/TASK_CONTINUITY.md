# Task Continuity

`omega.task_continuity` is the single provider-neutral durable-task engine used
by the Supervisor lifecycle. It does not replace the Supervisor, AgentBackend,
Host Verification, Wake Plane, ZFBR, PREB, or Capability Fabric.

## Runtime contract

The lifecycle is:

`TASK_ACCEPTED → BACKEND_ROUTED → SESSION_STARTED → CHECKPOINT_CREATED →`
`SESSION_LOST → BLOCKER_CLASSIFIED → SESSION_REHYDRATED → TASK_RESUMED →`
`HOST_VERIFIED → TASK_COMPLETED`.

Heartbeat fields expose the current durable task, active session, last
checkpoint, blocker, and recovery state from already-loaded continuity state.
Heartbeat never invokes Git, a provider, tests, or another subprocess.

The store uses hash-sealed JSON records, unique temporary files, flush + fsync +
atomic replacement, OS-released cross-process locks, compare-and-set task
revisions, and a single mutating session per task. Truncated or hash-mismatched
records fail closed.

## Frozen retry policy

- Session restarts: at most 2.
- Backend switches: at most 1.
- Same-provider retries: at most 1, and only after a material resource change.
- A parked task cannot start a new session without a material wake or route
  change.

`AUTH_REQUIRED`, `USAGE_QUOTA_LIMIT`, `AUTHORITY_BLOCKED`, and
`FINANCIAL_UNCERTAIN` remain distinct. Consumed, expired, or revoked authority
is never replayed.

## Rehydration gates

Before a replacement session can resume, the host compares repository root,
commit, dirty-state hash, workspace hash, authority envelope, and authority
state with the last checkpoint. Any mismatch enters
`RECONCILIATION_REQUIRED`; no file is overwritten.

Claude uses `BACKEND=CLAUDE_CODE_BACKEND` and `TRANSPORT=DIRECT_CLI` in the
current verified path. The schema keeps backend, transport, and upstream
provider separate so an optional OmniRoute transport can be classified without
mislabeling a transport outage as model failure.

## Read-only status and bounded proof

```powershell
python -m omega.cli task-continuity-status
python -m omega.cli task-continuity-live-chaos
```

The live chaos command is gated by the existing Claude authentication, shadow,
and controlled-canary evidence. It works only in an isolated temporary Git
repository, has no external-write or financial authority, terminates only the
owned Claude process, and requires Host Verification before completion.
# Work-session rehydration packets

`RehydrationPacket` extends the same Task Continuity store with an atomic, hash-sealed rollover record. It preserves the mission, phase, completed/current/next work, verified and failed evidence, artifacts and hashes, authority and resource boundaries, do-not-repeat rules, open questions, and success criteria. Identical freezes are idempotent and completed tasks cannot be represented as active.

The scientific bootstrap exposes its bounded packet through:

```text
python -m omega.cli scientific-learning-rehydration
```
