import agentdojo.task_suite  # 确保 task_suite 包先加载，避免循环导入
from agentdojo.default_suites.v1.travel_hotel.task_suite import task_suite as travel_hotel_task_suite
from agentdojo.default_suites.v1.travel_hotel import injection_tasks  # noqa: F401 - Register tasks
from agentdojo.default_suites.v1.travel_hotel import user_tasks  # noqa: F401 - Register tasks

# 自注册到全局 suite 注册表
from agentdojo.task_suite.load_suites import register_suite
register_suite(travel_hotel_task_suite, "v1.2.2")

__all__ = ["travel_hotel_task_suite"]
