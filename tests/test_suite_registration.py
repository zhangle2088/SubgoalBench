from agentdojo.task_suite.load_suites import get_suites

PAPER_SUITES = (
    "banking_bridge_resistance",
    "dailylife_check_mailbox",
    "dailylife_homework_delta",
    "dailylife_reserve_table",
    "shopping_delta",
    "shopping_otp",
    "travel_hotel_link_delta",
    "travel_recommend_restaurant",
    "workspace_schedule_lunch",
    "workspace_suggest_activities",
)


def test_paper_suites_are_registered_with_expected_tasks() -> None:
    suites = get_suites("v1.2.2")

    for suite_name in PAPER_SUITES:
        suite = suites[suite_name]
        assert len(suite.user_tasks) == 1
        assert len(suite.injection_tasks) == 48
