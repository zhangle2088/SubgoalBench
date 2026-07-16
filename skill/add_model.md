# Add a model

## Hosted provider

1. Add the model identifier to `src/agentdojo/models.py` (`ModelsEnum`, provider mapping, and display name).
2. Add or reuse the provider client in `src/agentdojo/agent_pipeline/agent_pipeline.py`.
3. Export the provider's API key and run a smoke test:

```bash
uv run python -m agentdojo.scripts.benchmark \
  -s shopping_delta --model <registered-model> \
  -ut user_task_0 -it injection_task_0 --attack focused
```

## OpenAI-compatible local model

Serve the model with a stable name, then use that same name as `--model-id`:

```bash
uv run python -m agentdojo.scripts.benchmark \
  -s shopping_delta --model vllm_parsed --model-id <served-model-name> \
  --local-llm-base-url http://127.0.0.1:<port>/v1 \
  -ut user_task_0 -it injection_task_0 --attack focused
```

Keep the model revision, endpoint configuration, tool-call parser, and hardware in the run manifest. Do not regenerate fixed probe templates merely because the target model changes.
