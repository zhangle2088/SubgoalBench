from collections import defaultdict

import agentdojo.default_suites.v1_1  # Register new tasks
import agentdojo.default_suites.v1_1_1  # Register new tasks
import agentdojo.default_suites.v1_2  # Register new tasks
import agentdojo.default_suites.v1_2_1  # Register new tasks
import agentdojo.default_suites.v1_2_2  # noqa: F401 # Register new tasks
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


# headphones suite 自注册（放在 register_suite 定义之后，避免循环导入时函数未定义）
import agentdojo.default_suites.v1.headphones  # noqa: F401
import agentdojo.default_suites.v1.headphones_review  # noqa: F401
import agentdojo.default_suites.v1.headphones_emails  # noqa: F401
import agentdojo.default_suites.v1.travel_hotel  # noqa: F401
import agentdojo.default_suites.v1.travel_hotel_link  # noqa: F401
import agentdojo.default_suites.v1.travel_hotel_link_v2  # noqa: F401
import agentdojo.default_suites.v1.travel_hotel_form  # noqa: F401
import agentdojo.default_suites.v1.travel_hotel_download  # noqa: F401
import agentdojo.default_suites.v1.travel_hotel_email  # noqa: F401
import agentdojo.default_suites.v1.travel_hotel_link_delta  # noqa: F401
import agentdojo.default_suites.v1.travel_recommend_restaurant  # noqa: F401
import agentdojo.default_suites.v1.shopping_delta  # noqa: F401
import agentdojo.default_suites.v1.dailylife_check_mailbox
import agentdojo.default_suites.v1.banking_delta  # noqa: F401
import agentdojo.default_suites.v1.banking_bridge_resistance  # noqa: F401
import agentdojo.default_suites.v1.shopping_send_command_control  # noqa: F401
import agentdojo.default_suites.v1.workspace_suggest_activities  # noqa: F401
import agentdojo.default_suites.v1.workspace_schedule_lunch  # noqa: F401
import agentdojo.default_suites.v1.dailylife_homework_delta  # noqa: F401
import agentdojo.default_suites.v1.dailylife_reserve_table
import agentdojo.default_suites.v1.shopping_otp  # noqa: F401  # noqa: F401
