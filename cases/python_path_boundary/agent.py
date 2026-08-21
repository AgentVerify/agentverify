from pathlib import Path

from langchain.tools import tool


@tool
def rejecting_guard(requested_path: str) -> None:
    root = Path("/srv/agent-workspace").resolve()
    candidate = (root / requested_path).resolve()
    if not candidate.is_relative_to(root) or candidate == root:
        raise ValueError("outside workspace")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    with open(candidate, "w", encoding="utf-8") as handle:
        handle.write("safe")


@tool
def positive_branch(requested_path: str) -> None:
    root = Path("/srv/agent-workspace").resolve()
    candidate = (root / requested_path).resolve()
    if candidate.is_relative_to(root):
        candidate.write_text("safe", encoding="utf-8")
    candidate.write_bytes(b"branch proof must not escape")


@tool
def prefix_check(requested_path: str) -> None:
    root = Path("/srv/agent-workspace").resolve()
    candidate = (root / requested_path).resolve()
    if not str(candidate).startswith(str(root)):
        return
    candidate.write_text("unsafe sibling-prefix check", encoding="utf-8")


@tool
def reassigned_candidate(requested_path: str) -> None:
    root = Path("/srv/agent-workspace").resolve()
    candidate = (root / requested_path).resolve()
    if not candidate.is_relative_to(root):
        return
    candidate = Path(requested_path).resolve()
    candidate.write_text("guarded value was replaced", encoding="utf-8")


@tool
def configured_root(requested_path: str, root_path: str) -> None:
    root = Path(root_path).resolve()
    candidate = (root / requested_path).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("outside configured root")
    candidate.write_text("control exists but root policy is unresolved", encoding="utf-8")


@tool
def unresolved_candidate(requested_path: str) -> None:
    root = Path("/srv/agent-workspace").resolve()
    candidate = root / requested_path
    if candidate.is_relative_to(root):
        candidate.write_text("candidate was not resolved", encoding="utf-8")


@tool
def reassigned_root(requested_path: str) -> None:
    root = Path("/srv/agent-workspace").resolve()
    candidate = (root / requested_path).resolve()
    if not candidate.is_relative_to(root):
        return
    root = Path("/tmp/other-root").resolve()
    candidate.write_text("root proof was replaced", encoding="utf-8")


@tool
def conditionally_reassigned_candidate(requested_path: str, replace: bool) -> None:
    root = Path("/srv/agent-workspace").resolve()
    candidate = (root / requested_path).resolve()
    if not candidate.is_relative_to(root):
        return
    if replace:
        candidate = Path(requested_path).resolve()
    candidate.write_text("guarded value may have been replaced", encoding="utf-8")


@tool
def parent_without_strict_descendant(requested_path: str) -> None:
    root = Path("/srv/agent-workspace").resolve()
    candidate = (root / requested_path).resolve()
    if not candidate.is_relative_to(root):
        return
    candidate.parent.mkdir(parents=True, exist_ok=True)
