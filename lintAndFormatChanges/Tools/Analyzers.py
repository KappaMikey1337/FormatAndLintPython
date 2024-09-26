import subprocess
from pathlib import Path

from lintAndFormatChanges.tools.globals import PYTHON_COMMAND
from lintAndFormatChanges.tools.ToolOutput import ToolOutput


def _flake(file: Path) -> ToolOutput:
    flake_cmd = [
        PYTHON_COMMAND,
        "-m",
        "flake8",
        "--config",
        "lintAndFormatChanges/config/flake.toml",
        file.resolve().as_posix(),
    ]
    flake_process = subprocess.run(
        flake_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    return ToolOutput(flake_process.returncode, flake_cmd[:-1], flake_process.stdout.decode())


def _pylint(file: Path) -> ToolOutput:
    pylint_cmd = [
        PYTHON_COMMAND,
        "-m",
        "pylint",
        "--rcfile",
        "lintAndFormatChanges/config/config.pylintrc",
        file.resolve().as_posix(),
    ]
    pylint_process = subprocess.run(
        pylint_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    return ToolOutput(pylint_process.returncode, pylint_cmd[:-1], pylint_process.stdout.decode())


def _mypy(file: Path) -> ToolOutput:
    # mypy expects the code to be part of the command
    mypy_cmd = [
        PYTHON_COMMAND,
        "-m",
        "mypy",
        "--config-file",
        "lintAndFormatChanges/config/mypy.ini",
        file.resolve().as_posix(),
    ]
    mypy_process = subprocess.run(mypy_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)

    return ToolOutput(mypy_process.returncode, mypy_cmd[:-1], mypy_process.stdout.decode())


def lint(file: Path) -> ToolOutput:
    """
    This function runs code against linters.
    Specifically, against both flake8 and pylint.

    Args:
        file: The file to lint.

    Returns:
        If any tool fails:
            Return the exit code of the last command run,
            the command itself, and the code string.
        Otherwise:
            Return an exit code of 0, a blank command,
            and the updated code string.
    """
    result = _flake(file)
    if result.return_code != 0:
        return result

    result = _pylint(file)
    if result.return_code != 0:
        return result

    return ToolOutput(0, [], file.as_posix())


def verify(file: Path) -> ToolOutput:
    """
    This function runs the static analyzer (mypy)
    on the provided code string.

    Args:
        file: The file to analyze.

    Returns:
        If any tool fails:
            Return the exit code of the last command run,
            the command itself, and the code.
        Otherwise:
            Return an exit code of 0, a blank command,
            and the updated code string.
    """
    result = _mypy(file)
    if result.return_code != 0:
        return result

    return ToolOutput(0, [], result.data)
