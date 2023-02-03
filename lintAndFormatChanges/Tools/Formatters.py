import subprocess

from .ToolOutput import ToolOutput


def _remove_newlines_from_file(code: str) -> str:
    """
    This function removes any double newlines from the given code,
    as the formatters do not remove extra newlines.

    Args:
        code: The code that will be stripped of double newlines.
    """
    lines = code.split("\n")

    if len(lines) == 0:
        return ""

    stack = [lines[0]]
    for line in lines[1:]:
        if stack[-1] == "" and line == "":
            continue
        stack.append(line)

    return "\n".join(stack)


def _isort(code: str) -> ToolOutput:
    isort_cmd = [
        "python3",
        "-m",
        "isort",
        "-sp",
        "lintAndFormatChanges/config/isort.toml",
        "-",
    ]
    isort_process = subprocess.run(
        isort_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        input=code,
        text=True,
        check=False,
    )

    return ToolOutput(isort_process.returncode, isort_cmd[:-1], isort_process.stdout)


def _black(code: str) -> ToolOutput:
    black_cmd = [
        "python3",
        "-m",
        "black",
        "--config",
        "lintAndFormatChanges/config/black.toml",
        "-",
    ]
    black_process = subprocess.run(
        black_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        input=code,
        text=True,
        check=False,
    )

    return ToolOutput(black_process.returncode, black_cmd[:-1], black_process.stdout)


def fmt(code: str) -> ToolOutput:
    """
    This function runs code against formatters.
    Specifically, it removes any double newlines (\n\n)
    from the code, reformats the imports with isort,
    and reformats the rest of the code with black.

    Args:
        code: The code to format.

    Returns:
        If any tool fails:
            Return the exit code of the last command run,
            the command itself, and the output of the tool
            that failed.
        Otherwise:
            Return an exit code of 0, a blank command,
            and the updated code string.
    """
    code = _remove_newlines_from_file(code)

    result = _isort(code)
    if result.return_code != 0:
        return result

    result = _black(code)

    return result
