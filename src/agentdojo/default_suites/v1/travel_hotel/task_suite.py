from pathlib import Path

from agentdojo.default_suites.v1.travel.task_suite import TOOLS, TravelEnvironment
from agentdojo.functions_runtime import make_function
from agentdojo.task_suite.task_suite import TaskSuite

# 复用 travel 的数据目录
DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "suites" / "travel"

task_suite = TaskSuite[TravelEnvironment](
    name="travel_hotel",
    environment_type=TravelEnvironment,
    tools=[make_function(tool) for tool in TOOLS],
    data_path=DATA_PATH,
)

__all__ = ["TravelEnvironment", "task_suite"]
