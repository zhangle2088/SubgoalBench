from pathlib import Path

from agentdojo.default_suites.v1.shopping.task_suite import TOOLS, ShoppingEnvironment
from agentdojo.functions_runtime import make_function
from agentdojo.task_suite.task_suite import TaskSuite

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "suites" / "shopping_delta"

task_suite = TaskSuite[ShoppingEnvironment](
    name="shopping_delta",
    environment_type=ShoppingEnvironment,
    tools=[make_function(tool) for tool in TOOLS],
    data_path=DATA_PATH,
)

__all__ = ["ShoppingEnvironment", "task_suite"]
