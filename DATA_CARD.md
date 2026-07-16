# SubgoalBench Data Card

## Motivation and composition

SubgoalBench measures whether adversarial context can make an unauthorized action appear to be a task-relevant local step while the agent continues pursuing the user's global request. The paper release contains 10 fixed workflow states, 60 payloads, and 480 prefix--payload instances, plus matched traditional-IPI and payload-only controls.

## Data generation and validation

Each instance starts from a benign simulated trajectory. The attacker-controlled span in one tool response is replaced while the preceding context, user task, tool interface, and validator remain fixed. Payloads cover actions such as visiting a webpage, downloading a file, sending money, changing a password, deleting a file, and sending an email. Task-specific validators identify Utility and Security outcomes from tool calls and simulated state changes.

## Provenance and licensing

The execution framework and adapted environments retain applicable AgentDojo and AgentDyn notices. Newly authored payloads, prefixes, probes, and analysis scripts will be separately identified and licensed in the public release. The release manifest will record provenance and modifications for every inherited component.

## Ethics and limitations

All accounts, URLs, credentials, messages, and records are fictional. The benchmark never contacts real services and is intended for defensive evaluation. It does not estimate risk over all dynamic trajectories, deployed tool policies, or attack distributions. Coordinates are operational proxies, not model-internal states or causal ground truth. Live results for proprietary models may change as providers update their systems.
