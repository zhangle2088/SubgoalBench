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

## Released data layers

The table above describes the **published aggregate layer**: one self-describing record per instance that joins the coordinate measurement with the run outcome. The benchmark writes a richer **raw layer** under `runs/`; the aggregate layer is derived from it. The mapping from each aggregate field to its raw source is:

| Aggregate field | Raw source under `runs/<model>/<suite>/` |
| --- | --- |
| `instance_id` | `<suite>/<user_task_id>/<condition>/<injection_task_id>` reconstructed from the run path |
| `suite` | ASR record `suite_name` |
| `benchmark_version` | ASR record `benchmark_version` |
| `user_task_id`, `injection_task_id` | ASR record fields of the same name |
| `condition` | run-path segment (`focused`, `traditional_ipi`, `payload_only`, `none`) |
| `payload_key` | `phi_resistance/` record `payload_key` |
| `prefix_label` | prefix-gradient label resolved from the `delta/` record `prefix_text` against the per-payload eight-level prefix set |
| `target_action` | `phi_resistance/` or `delta/` record `target_action` |
| `phi_t` | `phi_resistance/` record `phi_resistance` (equals `resistance_score`; payload-level) |
| `delta_t` | `delta/` record `delta_mechanism` (equals `test_score`; injection-task-level) |
| `utility`, `security` | ASR record `utility`, `security` |
| `tool_calls` | assistant tool calls and simulated responses extracted from the ASR record `messages` |
| `metadata` | ASR record `evaluation_timestamp`, `agentdojo_package_version`, `pipeline_name`, plus the artifact commit |

Raw probe outputs (`raw_logprobs`, `probe_messages`, `test_label_probs`) are retained in the raw layer and intentionally omitted from the aggregate layer. `phi_t` is read from `phi_resistance/` (one value per `payload_key`); `delta_t` is read from `delta/` (one value per injection task).

## Storage and completeness

Machine-readable records are stored under `runs/<model>/<suite>/`. Each run record carries the artifact commit, benchmark version, model identifier, suite, user-task ID, injection-task ID, condition, tool calls, validator outputs, utility, security, and status. An `index.json` in each `phi_resistance/` directory maps injection tasks to their shared payload-level $\Phi_t$ coordinate. Provider API responses may be omitted when terms require it; in that case the validator labels and aggregate inputs used for the paper are retained.

See `example_record.json` in this directory for an illustrative instance of the aggregate layer (`metadata.status = illustrative_schema_record`; values are schematic, not from a real run).
