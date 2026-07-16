from pathlib import Path

from agentdojo.default_suites.v1.banking.task_suite import TOOLS, BankingEnvironment
from agentdojo.functions_runtime import make_function
from agentdojo.task_suite.task_suite import TaskSuite

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "suites" / "banking_bridge_resistance"


def get_current_date() -> str:
    """Returns the current date in ISO format, e.g. '2023-12-20'.
    Use this when you need to know what today's date is."""
    return "2023-12-15"


def browse_webpage(url: str) -> str:
    """Visit a URL to retrieve web content. Use this to read a web page or to 'click' a link that provides information.

    :param url: The URL to be accessed.
    """
    return f"Page loaded: {url}\nContent: No additional information available at this time."


def delete_file(file_id: str) -> str:
    """Delete a file by its file ID or file path.

    :param file_id: The file ID or path to delete.
    """
    return f"Deleted file: {file_id}."


def send_email(recipients: list[str], subject: str, body: str) -> str:
    """Send an email.

    :param recipients: Email addresses that should receive the email.
    :param subject: The email subject.
    :param body: The email body.
    """
    return f"Email sent to {', '.join(recipients)} with subject: {subject}."


def download_file_through_url(url: str, save_dir: str = "/downloads") -> str:
    """Download a file from a URL.

    :param url: The URL of the file to download.
    :param save_dir: The directory to save the downloaded file.
    """
    return f"Downloaded file from {url} to {save_dir}."


task_suite = TaskSuite[BankingEnvironment](
    name="banking_bridge_resistance",
    environment_type=BankingEnvironment,
    tools=[make_function(tool) for tool in TOOLS]
    + [
        make_function(get_current_date),
        make_function(browse_webpage),
        make_function(delete_file),
        make_function(send_email),
        make_function(download_file_through_url),
    ],
    data_path=DATA_PATH,
)

__all__ = ["BankingEnvironment", "task_suite"]
