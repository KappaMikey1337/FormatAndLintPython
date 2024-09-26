import argparse
import shutil
import sys
from collections.abc import Mapping
from enum import Enum, auto
from pathlib import Path
from tempfile import gettempdir

from git import Repo
from lintAndFormatChanges.tools import fmt, lint, verify
from lintAndFormatChanges.utils import create_tmp_dir, get_files_to_format, get_tracked_formattable_paths


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
    CHECK = auto()


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

    behaviour_args:
        --check   Run formatter. Exit if formatter makes changes.

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
    tooling_args = parser.add_argument_group()
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

    # Arguments that affect the behaviour of the script
    behaviour_args = parser.add_argument_group()
    behaviour_args.add_argument(
        "--check",
        action="store_true",
        help="run formatting. Exit if formatters make changes.",
    )

    return parser.parse_args()


def determine_file_list(args: argparse.Namespace) -> list[Path]:
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

    return files_to_pass


def check_handler(check: bool, old_code: str, new_code: str, file_to_write: Path, copy_location: Path) -> bool:
    """
    This function handles the check argument.
    Args:
        check:          Whether --check was passed.
        old_code:       The code before formatting.
        new_code:       The code after formatting.
        file_to_write:  The original file to write the new code to.
        copy_location:  The location to copy the original file to.

    Returns:
        True if no issues are found, False if an issue is found.
    """
    if check is False:
        shutil.copyfile(file_to_write, copy_location)
        with file_to_write.open("w", encoding="utf-8") as working_file:
            working_file.write(new_code)
    else:
        if hash(old_code) != hash(new_code):
            return False

    return True


def presubmit_handler(
    files_to_pass: list[Path], repo_name: str, revision_dir: Path, config: Mapping[Mode, bool]
) -> int:
    """
    Runs the presubmit checks on the collected files.
    Args:
        files_to_pass:  The list of files to run the script on.
        repo_name:      The name of the repository.
        revision_dir:   The temporary directory to store the files.
        config:         The configuration of the script.

    Returns:
        0 if the script runs successfully, 1 if an error occurs.
    """
    for file_to_pass in files_to_pass:
        # Convert each file's path to repo_root/location/to/file
        file_to_pass_full = file_to_pass.resolve()
        index = file_to_pass_full.parts.index(repo_name)
        tmp_file = Path(*file_to_pass_full.parts[index:])

        tmp_file_location = revision_dir / tmp_file
        tmp_file_location.parent.mkdir(parents=True, exist_ok=True)

        print(f"Checking {file_to_pass}...", end="\r")
        with file_to_pass.open("r", encoding="utf-8") as working_file:
            code = working_file.read()

        # run formatting tool and overwrite the file
        if True in (config.get(Mode.ALL), config.get(Mode.FORMAT)):
            result = fmt(code)
            if result.return_code != 0:
                print(result.data, file=sys.stderr)
                return result.return_code

            if check_handler(config[Mode.CHECK], code, result.data, file_to_pass, tmp_file_location) is False:
                print(f"Failed check on {file_to_pass}. Formatter made changes.", file=sys.stderr)
                return 1

            code = result.data

        if True in (config.get(Mode.ALL), config.get(Mode.LINT)):
            result = lint(file_to_pass)
            if result.return_code != 0:
                print(result.data, file=sys.stderr)
                print(f"Failed to lint {file_to_pass}.")
                return result.return_code

        if True in (config.get(Mode.ALL), config.get(Mode.VERIFY)):
            result = verify(file_to_pass)
            if result.return_code != 0:
                print(result.data, file=sys.stderr)
                print(f"Failed to verify {file_to_pass}.")
                return result.return_code

        print(f"Success: {file_to_pass}")
    print("Success!")
    return 0


def main() -> int:
    """
    This program prepares a branch for merging
    by formatting, linting, and statically analyzing Python code.
    """
    args = get_arguments()  # type: ignore[no-untyped-call]

    config = {Mode.CHECK: args.check}
    if (args.format, args.lint, args.verify) == (False, False, False):
        config[Mode.ALL] = True
    else:
        config.update({Mode.FORMAT: args.format, Mode.LINT: args.lint, Mode.VERIFY: args.verify})

    repo_name_str = Repo(".", search_parent_directories=True).working_tree_dir
    if repo_name_str is None:
        print("Error: Unable to locate repo root.", file=sys.stderr)
        return 1

    repo_name = Path(repo_name_str).name
    tmp_path = Path(gettempdir(), "presubmit")
    try:
        revision_dir = create_tmp_dir(tmp_path)
    except ValueError as tmp_dir_error:
        print(tmp_dir_error, file=sys.stderr)
        return 1

    files_to_pass = determine_file_list(args)
    print(f"Temporary directory in use: {revision_dir}")
    return presubmit_handler(files_to_pass, repo_name, revision_dir, config)


if __name__ == "__main__":
    sys.exit(main())
