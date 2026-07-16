import agentdojo.task_suite  # 确保 task_suite 包先加载，避免循环导入
from agentdojo.default_suites.v1.headphones.task_suite import task_suite as headphones_task_suite
from agentdojo.default_suites.v1.headphones import injection_tasks  # noqa: F401 - Register tasks
from agentdojo.default_suites.v1.headphones import user_tasks  # noqa: F401 - Register tasks

# 自注册到全局 suite 注册表
from agentdojo.task_suite.load_suites import register_suite
register_suite(headphones_task_suite, "v1.2.2")

__all__ = ["headphones_task_suite"]
