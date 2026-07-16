# Measure $\Phi_t$ and $\Delta_t$

Use one fixed `probe_template.json` per suite and keep it unchanged across probe and target models. The main study uses Kimi K2.6 as the coordinate model; substitute another model only when explicitly recording a recalibration.

## Execution friction ($\Phi_t$)

Measure each unique payload once; instances sharing a payload reuse its score:

```bash
uv run python -m agentdojo.scripts.benchmark \
  -s shopping_delta --model kimi-k2.6 --benchmark-version v1.2.2 \
  --attack focused --measure-phi-resistance \
  --measure-delta monte_carlo --probe-samples 30 -f
```

## Bridging strength ($\Delta_t$)

Measure the prefix-to-payload bridge for every injection task:

```bash
uv run python -m agentdojo.scripts.benchmark \
  -s shopping_delta --model kimi-k2.6 --benchmark-version v1.2.2 \
  --attack focused --delta-mechanism-probe \
  --measure-delta monte_carlo --probe-samples 30 -f
```

The result directories contain payload-level $\Phi_t$, injection-task-level $\Delta_t$, and index files mapping the two granularities. Use the same fixed contexts when subsequently measuring ASR with `--use-probe-template`.
