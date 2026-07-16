# Run the benchmark

Install dependencies and inspect available options:

```bash
uv sync --dev
uv run python -m agentdojo.scripts.benchmark --help
```

Run one instance first, then a complete suite:

```bash
uv run python -m agentdojo.scripts.benchmark \
  -s shopping_delta --model <model> --benchmark-version v1.2.2 \
  -ut user_task_0 -it injection_task_0 --attack focused

uv run python -m agentdojo.scripts.benchmark \
  -s shopping_delta --model <model> --benchmark-version v1.2.2 \
  --attack focused --use-probe-template -f
```

Use `--defense <name>` for a defense condition and `--logdir <path>` to keep runs separate. Results are written below `runs/<model>/<suite>/`; preserve the run manifest and model revision with every result. The full study uses the ten documented suites, six payloads per state, and eight prefixes per payload.
