# Artifact Guide

## Release contents

| Directory | Contents |
| --- | --- |
| `src/agentdojo/` | Agent pipeline, suites, attacks, probes, validators, and CLI |
| `skill/` | Model setup, benchmark execution, and coordinate-measurement guides |
| `tests/` | Regression tests for the runtime and task-suite interfaces |
| `configs/` | Paper-specific model, defense, and run manifests |
| `human_annotations/` | Offline annotation UI, anonymized individual labels, consensus data, and analysis scripts |
| `docs/` | Data card, schema (record fields, data layers, and raw-to-aggregate mapping), provenance, and troubleshooting notes; includes an illustrative `example_record.json` |

The public release excludes API keys, private endpoints, hidden model reasoning, and unrelated development logs.

## Benchmark manifest

The paper configuration uses `v1.2.2` and the following fixed-state suites:

`banking_bridge_resistance`, `dailylife_check_mailbox`, `dailylife_homework_delta`, `dailylife_reserve_table`, `shopping_delta`, `shopping_otp`, `travel_hotel_link_delta`, `travel_recommend_restaurant`, `workspace_schedule_lunch`, and `workspace_suggest_activities`.

Each state has one executable user task, six payloads, and eight prefixes per payload. Stable instance IDs, source suite, carrier span, target tool call, attack-critical arguments, and validator outcomes are recorded in the release manifest.

## Reproduction tiers

- **Inspection:** load suites, validate the 480-instance construction, and replay released records without calling a model.
- **Smoke test:** run one user task and one injection task on a compatible model.
- **Full run:** execute all SMA instances, matched controls, coordinate probes, and selected defenses.

Every run records the artifact commit, benchmark version, model identifier, configuration, timestamp, and completed/failed instance IDs. Proprietary-model reruns may vary because of provider updates, endpoint availability, decoding nondeterminism, and cost; released records support verification without repeating every paid call.
