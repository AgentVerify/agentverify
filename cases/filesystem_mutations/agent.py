import os as operating_system
import shutil
import shutil as filesystem_tools
from os import remove as delete_path
from pathlib import Path
from shutil import copy2 as copy_with_metadata

from langchain.tools import tool


@tool
def copy_tree(source: str, destination: str) -> None:
    shutil.copytree(src=source, dst=destination)


@tool
def move_path(source: str, destination: str) -> None:
    filesystem_tools.move(source, destination)


@tool
def replace_path(source: str, destination: str) -> None:
    operating_system.replace(source, destination)


@tool
def copy_file(source: str, destination: str) -> None:
    copy_with_metadata(source, destination)


@tool
def delete_file(path: str) -> None:
    delete_path(path)


@tool
def fixed_destination(source: str) -> None:
    shutil.copy2(source, "/srv/agent-output/fixed.txt")


@tool
def guarded_copy(source: str, requested_path: str) -> None:
    root = Path("/srv/agent-output").resolve()
    candidate = (root / requested_path).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("outside output root")
    shutil.copy2(source, str(candidate))


@tool
def weak_prefix_copy(source: str, requested_path: str) -> None:
    root = Path("/srv/agent-output").resolve()
    candidate = (root / requested_path).resolve()
    if not str(candidate).startswith(str(root)):
        return
    shutil.copy2(source, candidate)


@tool
def shadowed_module(source: str, destination: str, shutil: object) -> None:
    shutil.copy2(source, destination)


@tool
def string_replacement(text: str) -> str:
    return text.replace("unsafe", "safe")


@tool
def local_copy_choice(
    source: str, destination: str, preserve_metadata: bool
) -> None:
    copy_fn = shutil.copy2 if preserve_metadata else shutil.copy
    copy_fn(source, destination)


@tool
def branch_copy_choice(
    source: str, destination: str, preserve_metadata: bool
) -> None:
    if preserve_metadata:
        copy_fn = shutil.copy2
    else:
        copy_fn = shutil.copy
    copy_fn(source, destination)


@tool
def guarded_local_copy(
    source: str, requested_path: str, preserve_metadata: bool
) -> None:
    root = Path("/srv/agent-output").resolve()
    candidate = (root / requested_path).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("outside output root")
    copy_fn = shutil.copy2 if preserve_metadata else shutil.copy
    copy_fn(source, str(candidate))


@tool
def call_before_alias(source: str, destination: str) -> object:
    copy_fn = wrapper
    copy_fn(source, destination)
    copy_fn = shutil.copy2
    return copy_fn


def wrapper(source: str, destination: str) -> None:
    pass


@tool
def conditional_rebind(
    source: str, destination: str, use_wrapper: bool
) -> None:
    copy_fn = shutil.copy2
    if use_wrapper:
        copy_fn = wrapper
    copy_fn(source, destination)


@tool
def incompatible_choice(
    source: str, destination: str, copy_mode: bool
) -> None:
    mutate = shutil.copy2 if copy_mode else delete_path
    mutate(source, destination)


@tool
def direct_path_replace(source: str, destination: str) -> None:
    Path(source).replace(destination)


@tool
def immutable_path_rename(source: str, destination: str) -> None:
    source_path = Path(source)
    source_path.rename(target=destination)


@tool
def guarded_path_rename(source: str, requested_path: str) -> None:
    root = Path("/srv/agent-output").resolve()
    candidate = (root / requested_path).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("outside output root")
    Path(source).rename(candidate)


@tool
def rebound_path_replace(source: str, destination: str) -> None:
    source_path = Path(source)
    source_path = source
    source_path.replace(destination)


@tool
def conditional_path_binding(
    source: str, destination: str, enabled: bool
) -> None:
    if enabled:
        source_path = Path(source)
    source_path.rename(destination)


@tool
def shadowed_path_constructor(
    source: str, destination: str, Path: object
) -> None:
    Path(source).replace(destination)
