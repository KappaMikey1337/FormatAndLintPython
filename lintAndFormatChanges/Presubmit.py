import argparse
import shutil
import sys
from enum import Enum, auto
from pathlib import Path

from .Tools import ToolOutput, fmt, lint, verify
from .Utils import getFilesToFormat


class Mode(Enum):
    """
    This enum represents the different modes
    the script will run in. This script can
    either run all tools, just formatting,
    or just formatting and linting.
    """

    ALL = auto()
    FORMAT = auto()
    LINT = auto()


class PathNotFoundError(Exception):
    """
    This class defines a custom error,
    which is presented when a file cannot be found.
    """

    def __init__(self, path: Path) -> None:
        """
        Args:
            path (Path): The Path object representing the file
                         that does not exist.
        """
        self.path = path.resolve()
        self.message = f"Error: file {self.path} does not exist."


class DuplicatePathError(Exception):
     """
     This class defines a custom error,
     which is presented when files have the same name.
     """

     def __init__(self, name: str) -> None:
         """
         Args:
             name: The name that exists across multiple files.
         """
         self.name = name
         self.message = f"Error: Duplicate file names: {self.name}"


def main() -> int:
    """
    This program prepares a branch for merging
    by formatting, linting, and statically analyzing Python code.

    Calling this file with no arguments will prepare every file
    that has been altered within your working branch since diverging
    from main.

    Args:
        --since <base>: Sets the starting point the script uses to determine
                        which files have changed. This can be a commit hash,
                        branch name, HEAD~3, etc. By default, this is set
                        to "main".

        --file <file>:  Only run the script on the specified file, even if
                        the file is normally ignored by the script.

    Mutually Exclusive Args:
        --format: Only run formatting.

        --lint:   Only run formatting and linting.

    Tools used:
        Formatting:
            1. Remove double newlines (\n\n)
            2. Sort imports (isort)
            3. Format file (black)

        Linting:
            1. Flake8
            2. Pylint

        Verification:
            1. mypy
    """
    parser = argparse.ArgumentParser(
        prog="Presubmit.py", description="Prepares file(s) for merging"
    )
    parser.add_argument(
        "--since",
        default="main",
        help="only run on the files changed since this point. \
              Must be a valid identifier in git \
              (commit hash, branch name, HEAD~3, etc).",
        metavar="<base>",
    )
    parser.add_argument(
        "--file",
        action="store",
        help="only run on the specified file.",
        metavar="<file>",
        type=Path,
    )

    # mutually exclusive arguments
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--format",
        action="store_true",
        help="only run formatting.",
    )
    group.add_argument(
        "--lint",
        action="store_true",
        help="only run formatting and linting.",
    )

    args = parser.parse_args()

    if args.format:
        mode = Mode.FORMAT
    elif args.lint:
        mode = Mode.LINT
    else:
        mode = Mode.ALL

    # Determine what file(s) to use
    if args.file is not None:
        if not args.file.exists():
            raise PathNotFoundError(args.file)
        filesToPass = [args.file]
    else:
        filesToPass = list(getFilesToFormat(args.since))

        filenames = [path.name for path in filesToPass]
         for filename in filenames:
             if filenames.count(filename) > 1:
                 raise DuplicatePathError(filename)

     for fileToPass in filesToPass:
        fullPath = str(fileToPass.parent.resolve()).split("/")
        tmpFileLocation = Path(f"/tmp/presubmit.{fullPath[2]}.{fileToPass.name}")

        print(f"Checking {fileToPass}...")
        with open(fileToPass, "r", encoding="utf8") as workingFile:
            code = workingFile.read()

        # run formatting tool and overwrite the file
        toolOutput = fmt(code)
        if toolOutput.returnCode != 0:
            print(toolOutput.data, file=sys.stderr)
            return toolOutput.returnCode

        shutil.copyfile(fileToPass, tmpFileLocation)
        with open(fileToPass, "w", encoding="utf8") as workingFile:
            workingFile.write(toolOutput.data)
        print(
            f"Successfully formatted {fileToPass.name}.\n"
            f"The original file can be found at: {tmpFileLocation}"
        )

        if mode in (Mode.ALL, Mode.LINT):
            toolOutput = runAnalyzers(toolOutput.data, mode)
            if toolOutput.returnCode != 0:
                print(toolOutput.data, file=sys.stderr)
                print(f"Failed to validate {fileToPass}.")
                return toolOutput.returnCode

            print(f"Validated {fileToPass} successfully.")

    return 0


def runAnalyzers(code: str, mode: Mode) -> ToolOutput:
    """
    This function is responsible for determining which tools to run
    and running them on the provided code.

    Args:
        code: The code that the tools will be run against.

        mode: Specifies which tools to run.

    Returns:
        ToolOutput: If any tool fails:
                        Return the exit code of the last command run,
                        the command itself, and the output of the tool
                        that failed.
                    Otherwise:
                        Return an exit code of 0, a blank command,
                        and the updated code string.
    """
    if mode not in (mode.ALL, mode.LINT):
        raise ValueError(f"Error: Encountered an unexpected mode: {mode}")

    result = lint(code)
    if result.returnCode != 0:
        return result

    if mode == Mode.ALL:
        result = verify(code)
        if result.returnCode != 0:
            return result

    return ToolOutput(0, [], code)


if __name__ == "__main__":
    sys.exit(main())
