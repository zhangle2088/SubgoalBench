import agentdojo.task_suite  # noqa: F401, I001
from agentdojo.default_suites.v1.banking_bridge_resistance.task_suite import task_suite as banking_bridge_resistance_task_suite
from agentdojo.default_suites.v1.banking_bridge_resistance import injection_tasks  # noqa: F401
from agentdojo.default_suites.v1.banking_bridge_resistance import user_tasks  # noqa: F401

from agentdojo.task_suite.load_suites import register_suite
register_suite(banking_bridge_resistance_task_suite, "v1.2.2")

__all__ = ["banking_bridge_resistance_task_suite"]
