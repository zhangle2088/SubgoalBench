from pathlib import Path

from agentdojo.default_suites.v1.dailylife.task_suite import TOOLS
from agentdojo.default_suites.v1.dailylife.task_suite import DailyLifeEnvironment as BaseDailyLifeEnvironment
from agentdojo.functions_runtime import make_function
from agentdojo.task_suite.task_suite import TaskSuite


class DailyLifeEnvironment(BaseDailyLifeEnvironment):
    pass


DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "suites" / "dailylife_homework_delta"


task_suite = TaskSuite[DailyLifeEnvironment](
    "dailylife_homework_delta",
    DailyLifeEnvironment,
    [make_function(tool) for tool in TOOLS],
    data_path=DATA_PATH,
)

__all__ = ["DailyLifeEnvironment", "task_suite"]
