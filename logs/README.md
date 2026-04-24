# logs

Execution traces and audit logs.

## Structure
- `logs/{username}/`   — per-user agent interactions and tool calls
- `logs/system/`       — system-wide pipeline and error logs

## What to log
- Every agent invocation (user, timestamp, input, output)
- Every tool call (name, parameters, result, duration)
- Errors and exceptions with stack traces
