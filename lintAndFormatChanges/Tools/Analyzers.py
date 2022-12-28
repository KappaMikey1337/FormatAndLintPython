from pathlib import Path
import os
import subprocess

from .ToolOutput import ToolOutput


def _flake(code: str) -> ToolOutput:
    flakeCmd = [
        "python3",
        "-m",
        "flake8",
        "--config",
        "lintAndFormatChanges/config/flake.toml",
        "-",
    ]
    flakeProcess = subprocess.run(
        flakeCmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        input=code,
        text=True,
        check=False,
    )

    return ToolOutput(flakeProcess.returncode, flakeCmd[:-1], flakeProcess.stdout)


def _pylint(code: str) -> ToolOutput:
    # This is needed for pylint to recognize our relative imports
    os.environ["PYTHONPATH"] = str(Path("master/").resolve())

    pylintCmd = [
        "python3",
        "-m",
        "pylint",
        "--rcfile",
        "lintAndFormatChanges/config/config.pylintrc",
        "--from-stdin",
        "True",
    ]
    pylintProcess = subprocess.run(
        pylintCmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        input=code,
        text=True,
        check=False,
    )
    del os.environ["PYTHONPATH"]

    return ToolOutput(pylintProcess.returncode, pylintCmd[:-1], pylintProcess.stdout)


def _mypy(code: str) -> ToolOutput:
    # mypy expects the code to be part of the command
    mypyCmd = ["python3", "-m", "mypy", "--command", code]
    mypyProcess = subprocess.run(
        mypyCmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
    )

    return ToolOutput(mypyProcess.returncode, mypyCmd[:-1], mypyProcess.stdout.decode())


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
    if result.returnCode != 0:
        return result

    result = _pylint(code)
    if result.returnCode != 0:
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
    if result.returnCode != 0:
        return result

    return ToolOutput(0, [], code)
