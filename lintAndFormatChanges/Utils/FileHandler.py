import getpass
import subprocess
import sys
from glob import glob
from pathlib import Path
from typing import List, Set

ALLOWLISTPATH = Path(__file__).parent / "../config/allowlist.txt"
DENYLISTPATH = Path(__file__).parent / "../config/denylist.txt"


def create_tmp_dir(base_dir: Path) -> Path:
    """
    This function creates a numbered directory
    based on the current user's username. The
    directory is created before being returned
    to the user.

    Args:
        base_dir: The base directory to work inside of.

    Returns:
        The directory to to store files into.

    Raises:
        ValueError: If a non-numbered directory exists where the numbered directory
                    will be created.
    """
    user_tmp_dir = base_dir / getpass.getuser()
    user_tmp_dir.mkdir(parents=True, exist_ok=True)
    subdirs = []
    for subdir in user_tmp_dir.iterdir():
        try:
            subdirs.append(int(subdir.name))
        except ValueError:
            errorMessage = (
                f"Error: unexpected sub-directory '{subdir}'\n"
                f"{user_tmp_dir.resolve()} should only contain numbered directories."
            )
            raise ValueError(errorMessage)

    revision = max(subdirs) + 1 if subdirs else 0
    revision_dir = user_tmp_dir / str(revision)
    revision_dir.mkdir()

    return revision_dir


def get_merge_base(start: str, end: str = "HEAD") -> str:
    """
    This function gets the merge base of two commits.

    Args:
        start: The first reference point (valid git identifier).
        end:   The second reference point (valid git identifier).

    Returns:
        The merge base of the two reference points.

    Raises:
        subprocess.CalledProcessError: If there is an error when using subprocess
                                       to get the merge-base.
    """
    try:
        return subprocess.check_output(["git", "merge-base", start, end]).strip().decode()
    except subprocess.CalledProcessError as subprocess_exception:
        print("Error occurred while getting merge base of commits.", file=sys.stderr)
        raise subprocess_exception


def get_changed_files(from_commit: str, to_commit: str = "HEAD") -> List[Path]:
    """
    This function gets the list of files
    that have changed between two commits.

    Args:
        from_commit: The starting commit.
        to_commit:   The ending commit.

    Returns:
        The list of all the files that have changed.
    """
    try:
        path_strings = (
            subprocess.check_output(["git", "diff", "--name-only", from_commit, to_commit]).strip().decode().split("\n")
        )
    except subprocess.CalledProcessError as subprocess_exception:
        print("Error occurred while getting changed files.", file=sys.stderr)
        raise subprocess_exception

    changed = [Path(path_string) for path_string in path_strings]
    changed = [path for path in changed if path.exists()]

    return changed


def get_all_tracked_files() -> List[Path]:
    """
    This function gets the list of all files
    that are currently being tracked by Git.

    Returns:
        The list of all the files that are tracked by Git.

    Raises:
        subprocess.CalledProcessError: If there is an error when using subprocess
                                       to get the list of tracked files.
    """
    try:
        path_strings = (
            subprocess.check_output(["git", "ls-tree", "-r", "--full-tree", "--name-only", "HEAD"])
            .strip()
            .decode()
            .split("\n")
        )
    except subprocess.CalledProcessError as e:
        print("Error occurred while getting tracked files.", file=sys.stderr)
        raise e

    tracked = [Path(path_string) for path_string in path_strings]

    return tracked


def get_globs_from_file(globlist_file: Path) -> Set[Path]:
    """
    This function resolves a list of glob patterns from a file.

    Args:
        globlist_file: The file that contains the glob patterns
                      to resolve.

    Returns:
        The set of all unique paths that result from the glob.
    """
    glob_strings = globlist_file.read_text().split("\n")
    path_set: Set[Path] = set()
    for glob_string in glob_strings:
        path_strings = glob(glob_string, recursive=True)
        path_set.update(Path(path_string) for path_string in path_strings)

    assert all(path.exists() for path in path_set)

    return path_set


def get_formattable_paths() -> Set[Path]:
    """
    This function gets the set of all files that can be seen by presubmit.
    It will resolve all allowlisted globs and all denylisted globs,
    and return allowlisted Paths that don't also appear in the glob of
    denylisted Paths.

    Returns:
        The set of valid Paths to be used.
    """
    allowlist_paths = get_globs_from_file(ALLOWLISTPATH)
    denylist_paths = get_globs_from_file(DENYLISTPATH)

    return allowlist_paths - denylist_paths


def get_files_to_format(changed_since: str) -> Set[Path]:
    """
    This function gets the set of files that will be formatted by presubmit.

    Args:
        changed_since: The starting commit to compare against
                      when getting the set of files changed.

    Returns:
        The set of files to be formatted.
    """
    merge_base = get_merge_base(changed_since)
    changed_files = get_changed_files(merge_base)
    formattable_paths = get_formattable_paths()

    return set(changed_files) & formattable_paths


def get_tracked_formattable_paths() -> Set[Path]:
    """
    This function gets the set of files that can be formatted by presubmit
    and are tracked by Git.

    Returns:
        The set of files that are tracked and can be formatted.
    """
    tracked_files = get_all_tracked_files()
    formattable_paths = get_formattable_paths()

    return set(tracked_files) & formattable_paths
