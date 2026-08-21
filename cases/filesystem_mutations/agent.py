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
