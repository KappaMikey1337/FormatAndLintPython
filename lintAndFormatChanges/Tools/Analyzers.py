from pathlib import Path
import os
import subprocess

from .ToolOutput import ToolOutput


def _flake(code: str) -> ToolOutput:
    flake_cmd = [
        "python3",
        "-m",
        "flake8",
        "--config",
        "lintAndFormatChanges/config/flake.toml",
        "-",
    ]
    flake_process = subprocess.run(
        flake_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        input=code,
        text=True,
        check=False,
    )

    return ToolOutput(flake_process.returncode, flake_cmd[:-1], flake_process.stdout)


def _pylint(code: str) -> ToolOutput:
    # This is needed for pylint to recognize our relative imports
    os.environ["PYTHONPATH"] = Path("master").resolve().as_posix()

    pylint_cmd = [
        "python3",
        "-m",
        "pylint",
        "--rcfile",
        "lintAndFormatChanges/config/config.pylintrc",
        "--from-stdin",
        "True",
    ]
    pylint_process = subprocess.run(
        pylint_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        input=code,
        text=True,
        check=False,
    )
    del os.environ["PYTHONPATH"]

    return ToolOutput(pylint_process.returncode, pylint_cmd[:-1], pylint_process.stdout)


def _mypy(code: str) -> ToolOutput:
    # mypy expects the code to be part of the command
    mypy_cmd = ["python3", "-m", "mypy", "--command", code]
    mypy_process = subprocess.run(mypy_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)

    return ToolOutput(mypy_process.returncode, mypy_cmd[:-1], mypy_process.stdout.decode())


def lint(code: str) -> ToolOutput:
    """
    This function runs code against linters.
    Specifically, against both flake8 and pylint.

    Args:
        code: The code to lint.

    Returns:
        If any tool fails:
            Return the exit code of the last command run,
            the command itself, and the code string.
        Otherwise:
            Return an exit code of 0, a blank command,
            and the updated code string.
    """
    result = _flake(code)
    if result.return_code != 0:
        return result

    result = _pylint(code)
    if result.return_code != 0:
        return result

    return ToolOutput(0, [], code)


def verify(code: str) -> ToolOutput:
    """
    This function runs the static analyzer (mypy)
    on the provided code string.

    Args:
        code: The code to analyze.

    Returns:
        If any tool fails:
            Return the exit code of the last command run,
            the command itself, and the code.
        Otherwise:
            Return an exit code of 0, a blank command,
            and the updated code string.
    """
    result = _mypy(code)
    if result.return_code != 0:
        return result

    return ToolOutput(0, [], code)
