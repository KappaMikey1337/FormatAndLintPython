This program prepares a branch for merging
by formatting, linting, and statically analyzing Python code.

# Prerequisites
The config is expected to exist in `<repoRoot>/formatAndLintChanges/config/`.\
When cloning this repo, please move the both the `formatAndLintChanges` file and `presubmit` script to your repo's root directory.

### Upgrade Pip
Ensure you have a version of Pip capable of using the required versions of the tools used:\
`python3 -m pip install -U pip`

### Requirements
All the required packages are stored within `requirements.txt`. You can install them using:\
`python3 -m pip install -r requirements.txt`

# Usage
Calling this file with no arguments will prepare every file
that has been altered within your working branch since diverging
from main.

Args:
```
--since <base>: Sets the starting point the script uses to determine
                which files have changed. This can be a commit hash,
                branch name, HEAD~3, etc. By default, this is set
                to "main".
```
```
--file <file>:  Only run the script on the specified file, even if
                the file is normally ignored by the script.
```
Mutually Exclusive Args:
```
--format: Only run formatting.
```
```
--lint:   Only run formatting and linting.
```

## Tools used:
### Formatting:
1. Remove double newlines (`\n\n`)
2. isort (sort imports)
3. black (format file)

### Linting:
1. Flake8
2. Pylint

### Verification:
1. mypy
