import os


SHELL_AUTO_APPROVE = os.environ.get("SHELL_AUTO_APPROVE") == "1"


def approve_shell() -> bool:
    if SHELL_AUTO_APPROVE:
        return True
    return False


def safe_status_flag() -> bool:
    if os.getenv("AUTO_APPROVED_WARNING") == "1":
        return True
    return False


def conditional_approval(is_safe: bool) -> bool:
    if os.getenv("AUTO_APPROVE_TOOLS") == "1":
        if is_safe:
            return True
    return False


def configure_local_flag() -> bool:
    local_auto_approve = os.getenv("LOCAL_AUTO_APPROVE") == "1"
    return local_auto_approve


def unrelated_parameter(local_auto_approve: bool) -> bool:
    if local_auto_approve:
        return True
    return False
