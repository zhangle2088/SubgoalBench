import agentdojo.task_suite  # noqa: F401, I001
from agentdojo.default_suites.v1.travel_recommend_restaurant import injection_tasks  # noqa: F401
from agentdojo.default_suites.v1.travel_recommend_restaurant import user_tasks  # noqa: F401
from agentdojo.default_suites.v1.travel_recommend_restaurant.task_suite import (
    task_suite as travel_recommend_restaurant_task_suite,
)
from agentdojo.task_suite.load_suites import register_suite

register_suite(travel_recommend_restaurant_task_suite, "v1.2.2")

__all__ = ["travel_recommend_restaurant_task_suite"]
