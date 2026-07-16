from pathlib import Path

from agentdojo.default_suites.v1.shopping.task_suite import TOOLS as SHOPPING_TOOLS
from agentdojo.default_suites.v1.shopping.task_suite import ShoppingEnvironment
from agentdojo.default_suites.v1.shopping_otp.tools import (
    checkout_selected_cart,
    update_shopping_account_password,
    verify_shopping_account,
)
from agentdojo.functions_runtime import make_function
from agentdojo.task_suite.task_suite import TaskSuite

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "suites" / "shopping_otp"
TOOL_OVERRIDES = {
    checkout_selected_cart.__name__: checkout_selected_cart,
    update_shopping_account_password.__name__: update_shopping_account_password,
    verify_shopping_account.__name__: verify_shopping_account,
}
TOOLS = [TOOL_OVERRIDES.get(tool.__name__, tool) for tool in SHOPPING_TOOLS]

task_suite = TaskSuite[ShoppingEnvironment](
    name="shopping_otp",
    environment_type=ShoppingEnvironment,
    tools=[make_function(tool) for tool in TOOLS],
    data_path=DATA_PATH,
)

__all__ = ["ShoppingEnvironment", "task_suite"]
