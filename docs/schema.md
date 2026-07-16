# Artifact Schema

The public artifact uses one record per evaluated instance. JSON keys below are stable across model runs; provider-specific fields may be added under `metadata`.

| Field | Type | Description |
| --- | --- | --- |
| `instance_id` | string | Stable identifier for the suite, user task, injection task, and condition |
| `suite` | string | Registered suite name, for example `shopping_delta` |
| `benchmark_version` | string | Task-suite version, currently `v1.2.2` |
| `user_task_id` | string | User task identifier |
| `injection_task_id` | string | Injection task identifier |
| `condition` | string | `focused`, `traditional_ipi`, or `payload_only` |
| `payload_key` | string | Payload-level key shared by prefix variants |
| `prefix_label` | string or null | Prefix gradient label; null for controls without a prefix |
| `target_action` | object | Target tool name and attack-critical arguments |
| `phi_t` | number or null | Payload-level execution-friction coordinate in $[0,1]$ |
| `delta_t` | number or null | Prefix--payload bridging coordinate in $[0,1]$ |
| `utility` | number | User-task validator outcome, normally 0 or 1 |
| `security` | number or null | Security validator outcome; attack success is recorded as `0` |
| `tool_calls` | array | Serialized assistant tool calls and simulated tool responses |
| `metadata` | object | Model revision, configuration, commit, timestamp, and status |

`phi_t` is computed once per unique payload and reused by all prefix variants. `delta_t` is measured per prefix--payload instance. Aggregation scripts must preserve these granularities and must not average duplicated payload coordinates as independent samples.
