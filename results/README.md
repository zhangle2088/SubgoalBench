# Results

The public release stores machine-readable records under `runs/` or an archived results bundle. Each record should include the artifact commit, benchmark version, model identifier, suite, user-task ID, injection-task ID, condition, tool calls, validator outputs, Utility, Security, and status.

Coordinate records use payload-level keys for $\Phi_t$ and injection-task-level keys for $\Delta_t$. An `index.json` maps injection tasks to their shared payload coordinate. API responses may be omitted when provider terms require it; in that case, retain the validator labels and aggregate inputs used for the paper.
