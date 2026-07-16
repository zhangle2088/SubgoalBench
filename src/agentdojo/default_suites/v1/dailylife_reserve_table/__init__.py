import agentdojo.task_suite  # noqa: F401, I001
from agentdojo.default_suites.v1.dailylife_reserve_table import injection_tasks  # noqa: F401
from agentdojo.default_suites.v1.dailylife_reserve_table import user_tasks  # noqa: F401
from agentdojo.default_suites.v1.dailylife_reserve_table.task_suite import (
    task_suite as dailylife_reserve_table_task_suite,
)
from agentdojo.task_suite.load_suites import register_suite

register_suite(dailylife_reserve_table_task_suite, "v1.2.2")

__all__ = ["dailylife_reserve_table_task_suite"]
