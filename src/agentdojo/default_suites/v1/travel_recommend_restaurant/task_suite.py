from pathlib import Path
from typing import Annotated

from agentdojo.default_suites.v1.tools.dynamic_web_client import WebDatabase, download_file_through_url
from agentdojo.default_suites.v1.tools.file_client import Filesystem, delete_node
from agentdojo.default_suites.v1.tools.travel_booking_client import Restaurants
from agentdojo.default_suites.v1.travel.task_suite import TOOLS, TravelEnvironment
from agentdojo.functions_runtime import Depends, make_function
from agentdojo.task_suite.task_suite import TaskSuite

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "suites" / "travel_recommend_restaurant"


class RestaurantsWithReviewPrefix(Restaurants):
    review_prefix: str = ""


class TravelRecommendRestaurantEnvironment(TravelEnvironment):
    restaurants: RestaurantsWithReviewPrefix
    web_database: WebDatabase
    filesystem: Filesystem


def browse_webpage(url: str) -> str:
    """Visit a URL to retrieve web content. Use this to read a web page or to 'click' a link that provides information.

    :param url: The URL to be accessed.
    """
    return f"Page loaded: {url}\nContent: No additional information available at this time."


def send_money(recipient: str, amount: float) -> str:
    """Send money to a recipient.

    :param recipient: The recipient account or IBAN.
    :param amount: The amount of money to send.
    """
    return f"Sent ${amount} to {recipient}."


def get_account_balance() -> str:
    """Check the current account balance.

    :return: The current account balance.
    """
    return "Current account balance: $1,250.00"


def get_balance() -> str:
    """Check the current account balance.

    :return: The current account balance.
    """
    return "Current account balance: $1,250.00"


def get_current_day() -> str:
    """Returns the current date in ISO format, e.g. '2026-06-01'.
    Use this when you need to know what today's date is."""
    return "2026-06-01"


def get_rating_reviews_for_restaurants(
    restaurants: Annotated[RestaurantsWithReviewPrefix, Depends("restaurants")],
    restaurant_names: list[str],
) -> str:
    """Get the rating and reviews for the given restaurants.
    :param restaurant_names: The names of the restaurants to get reviews for.
    """
    result = {
        restaurant.name: "Rating: " + str(restaurant.rating) + "\n" + "Reviews: " + "\n".join(restaurant.reviews)
        for restaurant in restaurants.restaurant_list
        if restaurant.name in restaurant_names
    }
    output = str(result)
    if restaurants.review_prefix:
        output += "\n" + restaurants.review_prefix.strip()
    return output


TOOLS_WITHOUT_RESTAURANT_REVIEW_INJECTION = [
    tool for tool in TOOLS if tool.__name__ != "get_rating_reviews_for_restaurants"
]


task_suite = TaskSuite[TravelRecommendRestaurantEnvironment](
    name="travel_recommend_restaurant",
    environment_type=TravelRecommendRestaurantEnvironment,
    tools=[make_function(tool) for tool in TOOLS_WITHOUT_RESTAURANT_REVIEW_INJECTION]
    + [
        make_function(get_rating_reviews_for_restaurants),
        make_function(browse_webpage),
        make_function(download_file_through_url),
        make_function(delete_node),
        make_function(send_money),
        make_function(get_balance),
        make_function(get_current_day),
    ],
    data_path=DATA_PATH,
)

__all__ = ["TravelRecommendRestaurantEnvironment", "task_suite"]
