import agentdojo.task_suite  # noqa: F401, I001
from agentdojo.default_suites.v1.dailylife_homework_delta import injection_tasks  # noqa: F401
from agentdojo.default_suites.v1.dailylife_homework_delta import user_tasks  # noqa: F401
from agentdojo.default_suites.v1.dailylife_homework_delta.task_suite import (
    task_suite as dailylife_homework_delta_task_suite,
)
from agentdojo.task_suite.load_suites import register_suite

register_suite(dailylife_homework_delta_task_suite, "v1.2.2")

__all__ = ["dailylife_homework_delta_task_suite"]
