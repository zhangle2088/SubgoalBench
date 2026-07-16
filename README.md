# SubgoalBench

SubgoalBench is a reproducible benchmark for **context-induced subgoal misalignment** in tool-using LLM agents. It evaluates Subgoal Misalignment Attacks (SMA) at fixed workflow states and separates two external coordinates:

- **Execution friction ($\Phi_t$):** how difficult a target action is to support in the current workflow.
- **Bridging strength ($\Delta_t$):** how strongly an adversarial prefix makes that action appear to be a plausible next step.

The paper benchmark contains 10 fixed workflow states, 60 target-action payloads, and eight prefixes per payload (480 SMA instances), together with matched traditional-IPI and payload-only controls. All environments are synthetic and resettable; no real banking, shopping, email, travel, or filesystem service is contacted.

SubgoalBench is not a repackaging of AgentDojo. Its new value lies in fixed-state, action-matched, prefix-graded construction and the joint measurement of execution friction and bridging strength. AgentDojo provides the trusted execution framework and simulated tool interfaces; SubgoalBench adds the benchmark instances, contextual prefix gradients, coordinate probes, validators, and matched analyses used to study CISM/SMA.

## Installation

```bash
uv sync --dev
```

The Python package retains the `agentdojo` import namespace for compatibility with the underlying execution framework. The repository and artifact are named **SubgoalBench**.

## Quickstart

Set the API key required by the selected provider, then run one instance:

```bash
uv run python -m agentdojo.scripts.benchmark \
  -s shopping_delta --model <model> --benchmark-version v1.2.2 \
  -ut user_task_0 -it injection_task_0 --attack focused
```

Run a complete suite with a fixed probe template:

```bash
uv run python -m agentdojo.scripts.benchmark \
  -s shopping_delta --model <model> --benchmark-version v1.2.2 \
  --attack focused --use-probe-template -f
```

Results are written below `runs/<model>/<suite>/`. Use `--logdir` to select a clean output directory and preserve the model revision and configuration with the run.

## Reproducing the paper

1. Validate the suites and run the smoke test in `skill/run_benchmark.md`.
2. Reuse one fixed `probe_template.json` per suite.
3. Measure payload-level $\Phi_t$ and injection-task-level $\Delta_t$ using `skill/measure_coordinates.md`.
4. Run SMA with `--use-probe-template`, then run matched controls and defenses.

The `skill/` directory contains short guides for adding a model, running the benchmark, and measuring the coordinates. `ARTIFACT.md` specifies the release contents and staged reproduction protocol. `DATA_CARD.md`, `docs/schema.md`, and `docs/provenance.md` document provenance, instance fields, limitations, ethics, and licensing.

## Responsible use

The benchmark is intended for controlled evaluation and mitigation of indirect prompt-injection vulnerabilities. Payloads use fictional identifiers and simulated environments. Do not adapt the examples to target deployed systems or include real credentials in experiments.

## License and citation

Code retains the upstream AgentDojo MIT notice where applicable; newly authored benchmark material will carry the license stated in `DATA_CARD.md`. Citation metadata is provided in `CITATION.cff`.
