from pathlib import Path

from agentdojo.default_suites.v1.workspace.task_suite import TOOLS, WorkspaceEnvironment
from agentdojo.functions_runtime import make_function
from agentdojo.task_suite.task_suite import TaskSuite

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "suites" / "workspace_schedule_lunch"


def browse_webpage(url: str) -> str:
    """Visit a URL to retrieve web content.

    :param url: The URL to be accessed.
    """
    return f"Page loaded: {url}\nContent: No additional information available at this time."


def send_money(recipient: str, amount: float, subject: str, date: str) -> str:
    """Send money to a recipient.

    :param recipient: The recipient account or IBAN.
    :param amount: The amount of money to send.
    :param subject: The payment subject.
    :param date: The payment date.
    """
    return f"Sent ${amount} to {recipient} on {date} with subject: {subject}."


def download_file_through_url(url: str, save_dir: str = "/downloads") -> str:
    """Download a file from a URL.

    :param url: The URL of the file to download.
    :param save_dir: The directory to save the downloaded file.
    """
    return f"Downloaded file from {url}\nFile: document.pdf"


task_suite = TaskSuite[WorkspaceEnvironment](
    name="workspace_schedule_lunch",
    environment_type=WorkspaceEnvironment,
    tools=[make_function(tool) for tool in TOOLS]
    + [
        make_function(browse_webpage),
        make_function(send_money),
        make_function(download_file_through_url),
    ],
    data_path=DATA_PATH,
)

__all__ = ["WorkspaceEnvironment", "task_suite"]
