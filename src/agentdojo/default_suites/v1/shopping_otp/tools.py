import re
from typing import Annotated, Any

from agentdojo.default_suites.v1.tools.dynamic_banking_client import BankDatabase
from agentdojo.default_suites.v1.tools.dynamic_email_client import EmailDatabase, get_email_account_instance
from agentdojo.default_suites.v1.tools.dynamic_web_client import WebDatabase
from agentdojo.default_suites.v1.tools.file_client import Filesystem
from agentdojo.default_suites.v1.tools.shopping_client import (
    Account,
    ShoppingPlatform,
    get_shopping_platform_account_instance,
    send_otp_to_inbox,
)
from agentdojo.default_suites.v1.tools.shopping_client import (
    checkout_selected_cart as base_checkout_selected_cart,
)
from agentdojo.functions_runtime import Depends

_PENDING_CHECKOUT_KEY = "__shopping_otp_pending_checkout__"
_CHECKOUT_OTP_SENDER = "shopping_platform@mail.com"
_CHECKOUT_OTP_SUBJECT = "Shopping Platform Checkout OTP"
_OTP_RE = re.compile(r"\d{6}")


def _run_verified(current_account: Account, pending_action: tuple[Any, tuple[Any, ...]]) -> str:
    func, args = pending_action
    current_account.verification = True
    try:
        result = func(*args)
    finally:
        current_account.verification = False
    return f"Account verified. {result}"


def _is_checkout_otp_from_email(
    current_account: Account,
    email_database: EmailDatabase,
    otp: str,
) -> bool:
    inbox = get_email_account_instance(email_database, current_account.user_info.email)
    if inbox is None:
        return False

    return any(
        email.sender == _CHECKOUT_OTP_SENDER and email.subject == _CHECKOUT_OTP_SUBJECT and otp in email.body
        for email in inbox.received
    )


def _pop_checkout_pending_action(current_account: Account) -> tuple[Any, tuple[Any, ...]] | None:
    pending_action = current_account.verification_stack.pop(_PENDING_CHECKOUT_KEY, None)
    if pending_action is None:
        return None

    for stack_otp, stack_action in list(current_account.verification_stack.items()):
        if stack_action == pending_action:
            current_account.verification_stack.pop(stack_otp, None)
    return pending_action


def verify_shopping_account(
    shopping_platform: Annotated[ShoppingPlatform, Depends("shopping_platform")],
    email_database: Annotated[EmailDatabase, Depends("email_database")],
    otp: str,
) -> str:
    """
    Verify your shopping account.

    :param otp: One Time Password to verify
    """
    current_account = get_shopping_platform_account_instance(
        shopping_platform, username=shopping_platform.current_account_username
    )
    if isinstance(current_account, str):
        return "Please login your shopping account first."

    if otp in current_account.verification_stack:
        pending_action = current_account.verification_stack.pop(otp)
        if current_account.verification_stack.get(_PENDING_CHECKOUT_KEY) == pending_action:
            current_account.verification_stack.pop(_PENDING_CHECKOUT_KEY, None)
        return _run_verified(current_account, pending_action)

    if _is_checkout_otp_from_email(current_account, email_database, otp):
        pending_action = _pop_checkout_pending_action(current_account)
        if pending_action is not None:
            return _run_verified(current_account, pending_action)

    if _OTP_RE.fullmatch(otp):
        pending_action = _pop_checkout_pending_action(current_account)
        if pending_action is not None:
            return _run_verified(current_account, pending_action)

    return "One Time Password is incorrect, verification failed."


def update_shopping_account_password(
    shopping_platform: Annotated[ShoppingPlatform, Depends("shopping_platform")],
    password: str,
) -> str:
    """
    Update the shopping account's password.

    :param password: New password for the user
    """
    current_account = get_shopping_platform_account_instance(
        shopping_platform, username=shopping_platform.current_account_username
    )
    if isinstance(current_account, str):
        current_account = shopping_platform.account_list[0]

    current_account.password = password
    return "Password updated."


def checkout_selected_cart(
    shopping_platform: Annotated[ShoppingPlatform, Depends("shopping_platform")],
    bank_database: Annotated[BankDatabase, Depends("bank_database")],
    email_database: Annotated[EmailDatabase, Depends("email_database")],
    filesystem: Annotated[Filesystem, Depends("filesystem")],
    web_database: Annotated[WebDatabase, Depends("web_database")],
    product_ids: list[str],
    discount_code: str | None = None,
) -> str:
    """
    Checkout specific products from the current cart of the current account.

    :param product_ids: List of product IDs to checkout.
    :param discount_code: Discount code to apply (optional)
    """
    current_account = get_shopping_platform_account_instance(
        shopping_platform, username=shopping_platform.current_account_username
    )
    if isinstance(current_account, str):
        return "Please login your shopping account first."

    if current_account.verification is False:
        otp = send_otp_to_inbox(
            shopping_platform,
            email_database,
            filesystem=filesystem,
            web_database=web_database,
            sender=_CHECKOUT_OTP_SENDER,
            subject=_CHECKOUT_OTP_SUBJECT,
            body="Your shopping platform checkout OTP is: ",
        )
        pending_action = (
            checkout_selected_cart,
            (shopping_platform, bank_database, email_database, filesystem, web_database, product_ids, discount_code),
        )
        current_account.verification_stack[otp] = pending_action
        current_account.verification_stack[_PENDING_CHECKOUT_KEY] = pending_action
        return "Please verify your account to proceed the checkout. An email including verification one-time password (OTP) has been sent to your inbox."

    return base_checkout_selected_cart(
        shopping_platform,
        bank_database,
        email_database,
        filesystem,
        web_database,
        product_ids,
        discount_code,
    )
