import agentdojo.task_suite  # noqa: F401, I001
from agentdojo.default_suites.v1.workspace_suggest_activities.task_suite import (
    task_suite as workspace_suggest_activities_task_suite,
)
from agentdojo.default_suites.v1.workspace_suggest_activities import injection_tasks  # noqa: F401
from agentdojo.default_suites.v1.workspace_suggest_activities import user_tasks  # noqa: F401

from agentdojo.task_suite.load_suites import register_suite

register_suite(workspace_suggest_activities_task_suite, "v1.2.2")

__all__ = ["workspace_suggest_activities_task_suite"]
