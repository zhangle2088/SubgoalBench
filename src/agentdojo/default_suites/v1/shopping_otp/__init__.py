import agentdojo.task_suite  # noqa: F401, I001
from agentdojo.default_suites.v1.shopping_otp.task_suite import task_suite as shopping_otp_task_suite
from agentdojo.default_suites.v1.shopping_otp import injection_tasks  # noqa: F401
from agentdojo.default_suites.v1.shopping_otp import user_tasks  # noqa: F401

from agentdojo.task_suite.load_suites import register_suite
register_suite(shopping_otp_task_suite, "v1.2.2")

__all__ = ["shopping_otp_task_suite"]
