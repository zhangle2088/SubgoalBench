from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, EmailStr

from agentdojo.default_suites.v1.tools.cloud_drive_client import CloudDrive
from agentdojo.default_suites.v1.tools.types import CloudDriveFileID, SharingPermission
from agentdojo.default_suites.v1.workspace.task_suite import TOOLS, WorkspaceEnvironment
from agentdojo.functions_runtime import Depends, make_function
from agentdojo.task_suite.task_suite import TaskSuite

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "suites" / "workspace_suggest_activities"


class CloudDriveFileMetadata(BaseModel):
    id_: CloudDriveFileID
    filename: str
    owner: EmailStr
    shared_with: dict[EmailStr, SharingPermission] = {}
    size: int = 0


def search_files_by_filename(
    cloud_drive: Annotated[CloudDrive, Depends("cloud_drive")],
    filename: str,
) -> list[CloudDriveFileMetadata]:
    """Search cloud drive files by filename and return metadata only.

    Use get_file_by_id to read a file's full content after selecting the file.

    :param filename: The filename or filename fragment to search for.
    """
    return [
        CloudDriveFileMetadata(
            id_=file.id_,
            filename=file.filename,
            owner=file.owner,
            shared_with=file.shared_with,
            size=file.size,
        )
        for file in cloud_drive.search_files_by_filename(filename)
    ]


TOOLS_WITH_METADATA_SEARCH = [tool for tool in TOOLS if tool.__name__ != "search_files_by_filename"]


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


task_suite = TaskSuite[WorkspaceEnvironment](
    name="workspace_suggest_activities",
    environment_type=WorkspaceEnvironment,
    tools=[make_function(tool) for tool in TOOLS_WITH_METADATA_SEARCH]
    + [
        make_function(search_files_by_filename),
        make_function(browse_webpage),
        make_function(send_money),
    ],
    data_path=DATA_PATH,
)

__all__ = ["WorkspaceEnvironment", "task_suite"]
