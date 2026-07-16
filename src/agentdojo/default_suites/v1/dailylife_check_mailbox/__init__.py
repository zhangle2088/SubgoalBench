import agentdojo.task_suite  # noqa: F401, I001
from agentdojo.default_suites.v1.dailylife_check_mailbox import injection_tasks  # noqa: F401
from agentdojo.default_suites.v1.dailylife_check_mailbox import user_tasks  # noqa: F401
from agentdojo.default_suites.v1.dailylife_check_mailbox.task_suite import (
    task_suite as dailylife_check_mailbox_task_suite,
)
from agentdojo.task_suite.load_suites import register_suite

register_suite(dailylife_check_mailbox_task_suite, "v1.2.2")

__all__ = ["dailylife_check_mailbox_task_suite"]
