from agentdojo.default_suites.v1.shopping.task_suite import ShoppingEnvironment, TOOLS
from agentdojo.functions_runtime import make_function
from agentdojo.task_suite.task_suite import TaskSuite

task_suite = TaskSuite[ShoppingEnvironment](
    name="headphones",
    environment_type=ShoppingEnvironment,
    tools=[make_function(tool) for tool in TOOLS],
)

__all__ = ["ShoppingEnvironment", "task_suite"]
