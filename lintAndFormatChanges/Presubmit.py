import argparse
import shutil
import sys
from enum import Enum, auto
from pathlib import Path
from tempfile import gettempdir
from typing import List

from lintAndFormatChanges.Tools import fmt, lint, verify
from lintAndFormatChanges.Utils import create_tmp_dir, get_files_to_format, get_tracked_formattable_paths


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
    VERIFY = auto()


class PathNotFoundError(Exception):
    """
    This class defines a custom error,
    which is presented when a file cannot be found.
    """

    def __init__(self, path: Path) -> None:
        """
        Args:
            path: The Path object representing the file
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


def get_arguments():
    """
    Calling this file with no arguments will prepare every file
    that has been altered within your working branch since diverging
    from main.

    file_args:
        --since <base>: Sets the starting point the script uses to determine
                        which files have changed. This can be a commit hash,
                        branch name, HEAD~3, etc. By default, this is set
                        to "main".

        --file <file>:  Only run the script on the specified file, even if
                        the file is normally ignored by the script.

        --all-files:    Run on all the Python files that are tracked by the repo.

    tooling_args:
        --format: Run formatting.

        --lint:   Run formatting and linting.

        --verify  Run static analysis.

        Passing no tooling arguments will run all tools.

    Tools in use:
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
    parser = argparse.ArgumentParser(prog="Presubmit.py", description="Prepares file(s) for merging")

    # Arguments that affect the files checked
    file_args = parser.add_mutually_exclusive_group()
    file_args.add_argument(
        "--since",
        default="main",
        help="only run on the files changed since this point. \
              Must be a valid identifier in git \
              (commit hash, branch name, HEAD~3, etc).",
        metavar="<base>",
    )
    file_args.add_argument(
        "--file",
        action="store",
        help="only run on the specified file.",
        metavar="<file>",
        type=Path,
    )

    file_args.add_argument(
        "--all-files",
        action="store_true",
        help="run on all tracked Python files.",
    )

    # Arguments that affect to the tooling used
    tooling_args = parser.add_mutually_exclusive_group()
    tooling_args.add_argument(
        "--format",
        action="store_true",
        help="run formatting.",
    )
    tooling_args.add_argument(
        "--lint",
        action="store_true",
        help="run linting.",
    )
    tooling_args.add_argument(
        "--verify",
        action="store_true",
        help="run static analyzer.",
    )
    return parser.parse_args()


def determine_file_list(args: argparse.Namespace) -> List[Path]:
    """
    This function determines what files the script will run on
    based on the arguments passed.

    Args:
        args: The arguments parsed by the script.

    Returns:
        The list of files to run the script on.

    Raises:
        PathNotFoundError:  The path passed to the script does not exist.

        DuplicatePathError: There exists 2 or more files with the same name.
    """
    # Determine what file(s) to use
    if args.all_files is True:
        files_to_pass = list(get_tracked_formattable_paths())
    elif args.file is not None:
        if not args.file.exists():
            raise PathNotFoundError(args.file)
        files_to_pass = [args.file]
    else:
        files_to_pass = list(get_files_to_format(args.since))

        # ensure no duplicate filenames
        filenames = [path.name for path in files_to_pass]
        for filename in set(filenames):
            if filenames.count(filename) > 1:
                raise DuplicatePathError(filename)
    return files_to_pass


def main() -> int:
    """
    This program prepares a branch for merging
    by formatting, linting, and statically analyzing Python code.
    """

    args = get_arguments()

    if args.format:
        mode = Mode.FORMAT
    elif args.lint:
        mode = Mode.LINT
    elif args.verify:
        mode = Mode.VERIFY
    else:
        mode = Mode.ALL

    tmp_path = Path(gettempdir(), "presubmit")
    try:
        revision_dir = create_tmp_dir(tmp_path)
    except ValueError as tmp_dir_error:
        print(tmp_dir_error, file=sys.stderr)
        return 1

    files_to_pass = determine_file_list(args)

    for file_to_pass in files_to_pass:
        tmp_file_location = revision_dir / file_to_pass.name

        print(f"Checking {file_to_pass}...")
        with file_to_pass.open("r", encoding="utf-8") as working_file:
            code = working_file.read()

        # run formatting tool and overwrite the file
        if mode in (Mode.ALL, Mode.FORMAT):
            result = fmt(code)
            if result.return_code != 0:
                print(result.data, file=sys.stderr)
                return result.return_code

            code = result.data
            shutil.copyfile(file_to_pass, tmp_file_location)
            with file_to_pass.open("w", encoding="utf-8") as working_file:
                working_file.write(code)
            print(
                f"Successfully formatted {file_to_pass}!\n"
                f"The original file can be found at: {tmp_file_location.resolve()}"
            )

        if mode in (Mode.ALL, Mode.LINT):
            result = lint(code)
            if result.return_code != 0:
                print(result.data, file=sys.stderr)
                print(f"Failed to lint {file_to_pass}.")
                return result.return_code

            print(f"Linted {file_to_pass} successfully.")

        if mode in (Mode.ALL, Mode.VERIFY):
            result = verify(code)
            if result.return_code != 0:
                print(result.data, file=sys.stderr)
                print(f"Failed to verify {file_to_pass}.")
                return result.return_code

            print(f"Validated {file_to_pass} successfully.")

        print("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
