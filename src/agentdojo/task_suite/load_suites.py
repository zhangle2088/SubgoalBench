# ruff: noqa: I001

from collections import defaultdict

import agentdojo.default_suites.v1_1  # Register new tasks
import agentdojo.default_suites.v1_1_1  # Register new tasks
import agentdojo.default_suites.v1_2  # Register new tasks
import agentdojo.default_suites.v1_2_1  # Register new tasks
import agentdojo.default_suites.v1_2_2  # Register new tasks
from agentdojo.default_suites.v1.banking import banking_task_suite
from agentdojo.default_suites.v1.slack import slack_task_suite
from agentdojo.default_suites.v1.travel import travel_task_suite
from agentdojo.default_suites.v1.workspace import workspace_task_suite
from agentdojo.default_suites.v1.shopping import shopping_task_suite
from agentdojo.default_suites.v1.github import github_task_suite
from agentdojo.default_suites.v1.dailylife import dailylife_task_suite
from agentdojo.task_suite.task_suite import TaskSuite

_V1_SUITES: dict[str, TaskSuite] = {
    "workspace": workspace_task_suite,
    "travel": travel_task_suite,
    "banking": banking_task_suite,
    "slack": slack_task_suite,
    "shopping": shopping_task_suite,
    "github": github_task_suite,
    "dailylife": dailylife_task_suite,
}

_V1_1_SUITES: dict[str, TaskSuite] = {
    "workspace": workspace_task_suite,
    "travel": travel_task_suite.get_new_version((1, 1, 0)),
    "banking": banking_task_suite,
    "slack": slack_task_suite,
    "shopping": shopping_task_suite,
    "github": github_task_suite,
    "dailylife": dailylife_task_suite,
}

_V1_1_1_SUITES: dict[str, TaskSuite] = {
    "workspace": workspace_task_suite.get_new_version((1, 1, 1)),
    "travel": travel_task_suite.get_new_version((1, 1, 1)),
    "banking": banking_task_suite.get_new_version((1, 1, 1)),
    "slack": slack_task_suite.get_new_version((1, 1, 1)),
    "shopping": shopping_task_suite,
    "github": github_task_suite,
    "dailylife": dailylife_task_suite,
}

_V1_1_2_SUITES: dict[str, TaskSuite] = {
    "workspace": workspace_task_suite.get_new_version((1, 1, 2)),
    "travel": travel_task_suite.get_new_version((1, 1, 2)),
    "banking": banking_task_suite.get_new_version((1, 1, 1)),
    "slack": slack_task_suite.get_new_version((1, 1, 1)),
    "shopping": shopping_task_suite,
    "github": github_task_suite,
    "dailylife": dailylife_task_suite,
}

_V1_2_SUITES: dict[str, TaskSuite] = {
    "workspace": workspace_task_suite.get_new_version((1, 2, 0)),
    "travel": travel_task_suite.get_new_version((1, 2, 0)),
    "banking": banking_task_suite.get_new_version((1, 2, 0)),
    "slack": slack_task_suite.get_new_version((1, 2, 0)),
    "shopping": shopping_task_suite,
    "github": github_task_suite,
    "dailylife": dailylife_task_suite,
}

_V1_2_1_SUITES: dict[str, TaskSuite] = {
    "workspace": workspace_task_suite.get_new_version((1, 2, 1)),
    "travel": travel_task_suite.get_new_version((1, 2, 0)),
    "banking": banking_task_suite.get_new_version((1, 2, 0)),
    "slack": slack_task_suite.get_new_version((1, 2, 0)),
    "shopping": shopping_task_suite,
    "github": github_task_suite,
    "dailylife": dailylife_task_suite,
}

_V1_2_2_SUITES: dict[str, TaskSuite] = {
    "workspace": workspace_task_suite.get_new_version((1, 2, 2)),
    "travel": travel_task_suite.get_new_version((1, 2, 0)),
    "banking": banking_task_suite.get_new_version((1, 2, 2)),
    "slack": slack_task_suite.get_new_version((1, 2, 0)),
    "shopping": shopping_task_suite,
    "github": github_task_suite,
    "dailylife": dailylife_task_suite,
}

_SUITES: defaultdict[str, dict[str, TaskSuite]] = defaultdict(
    dict,
    {
        "v1": _V1_SUITES,
        "v1.1": _V1_1_SUITES,
        "v1.1.1": _V1_1_1_SUITES,
        "v1.1.2": _V1_1_2_SUITES,
        "v1.2": _V1_2_SUITES,
        "v1.2.1": _V1_2_1_SUITES,
        "v1.2.2": _V1_2_2_SUITES,
    },
)


def register_suite(suite: TaskSuite, version: str) -> None:
    _SUITES[version][suite.name] = suite


def get_suites(benchmark_version: str) -> dict[str, TaskSuite]:
    return _SUITES[benchmark_version]


def get_suite(benchmark_version: str, suite_name: str) -> TaskSuite:
    return _SUITES[benchmark_version][suite_name]


# Standalone suites self-register after register_suite is defined. Import order
# is significant because the base suites contain circular registration imports.
# Keep the list explicit so a source distribution cannot import development-only
# suites that are absent from the released artifact.
import agentdojo.default_suites.v1.headphones
import agentdojo.default_suites.v1.travel_hotel
import agentdojo.default_suites.v1.travel_hotel_link_delta
import agentdojo.default_suites.v1.travel_recommend_restaurant
import agentdojo.default_suites.v1.shopping_delta
import agentdojo.default_suites.v1.dailylife_check_mailbox
import agentdojo.default_suites.v1.banking_bridge_resistance
import agentdojo.default_suites.v1.workspace_suggest_activities
import agentdojo.default_suites.v1.workspace_schedule_lunch
import agentdojo.default_suites.v1.dailylife_homework_delta
import agentdojo.default_suites.v1.dailylife_reserve_table
import agentdojo.default_suites.v1.shopping_otp  # noqa: F401
