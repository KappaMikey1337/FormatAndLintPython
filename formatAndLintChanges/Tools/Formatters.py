import subprocess

from .ToolOutput import ToolOutput


def _removeNewLinesFromFile(code: str) -> str:
    """
    This function removes any double newlines from the given code,
    as the formatters do not remove extra newlines.

    Args:
        code (str): The code that will be stripped of double newlines.
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
    isortCmd = [
        "python3",
        "-m",
        "isort",
        "-sp",
        "lintAndFormatChanges/config/config.toml",
        "-",
    ]
    isortProcess = subprocess.run(
        isortCmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        input=code,
        text=True,
        check=False,
    )

    return ToolOutput(isortProcess.returncode, isortCmd[:-1], isortProcess.stdout)


def _black(code: str) -> ToolOutput:
    blackCmd = [
        "python3",
        "-m",
        "black",
        "--config",
        "lintAndFormatChanges/config/config.toml",
        "-",
    ]
    blackProcess = subprocess.run(
        blackCmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        input=code,
        text=True,
        check=False,
    )

    return ToolOutput(blackProcess.returncode, blackCmd[:-1], blackProcess.stdout)


def fmt(code: str) -> ToolOutput:
    """
    This function runs code against formatters.
    Specifically, it removes any double newlines (\n\n)
    from the code, reformats the imports with isort,
    and reformats the rest of the code with black.

    Args:
        code (str): The code to format.

    Returns:
        ToolOutput: If any tool fails:
                        Return the exit code of the last command run,
                        the command itself, and the output of the tool
                        that failed.
                    Otherwise:
                        Return an exit code of 0, a blank command,
                        and the updated code string.
    """
    code = _removeNewLinesFromFile(code)

    result = _isort(code)
    if result.returnCode != 0:
        return result

    result = _black(code)

    return result
