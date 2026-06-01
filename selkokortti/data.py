"""Locate (and, by default, refresh) the selkouutiset-scrape-cleaned dataset.

When installed as a tool (``uv tool install``) there is no git submodule on disk,
so the dataset is cloned into the user cache directory and refreshed on each run.
A local checkout (e.g. the dev submodule) can be used via ``--data-dir``.
"""

import logging
import shutil
import subprocess
from pathlib import Path

from platformdirs import user_cache_dir

logger = logging.getLogger("selkokortti")

DATA_REPO_URL = "https://github.com/hiAndrewQuinn/selkouutiset-scrape-cleaned.git"
DATA_REPO_BRANCH = "master"
DATA_DIR_NAME = "selkouutiset-scrape-cleaned"


def _run_git(args, cwd=None):
    if shutil.which("git") is None:
        raise RuntimeError(
            "`git` was not found on PATH. selkokortti needs git to fetch the "
            "Selkouutiset dataset. Install git, or pass --data-dir pointing at a "
            "local checkout of selkouutiset-scrape-cleaned."
        )
    logger.debug("git %s (cwd=%s)", " ".join(args), cwd)
    # Keep git's own chatter ("remote: ...", "HEAD is now at ...") out of the
    # way unless the user asked for verbose logging; on failure we surface the
    # captured stderr so the error is still legible.
    verbose = logger.isEnabledFor(logging.DEBUG)
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=not verbose,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or "").strip() if not verbose else ""
        suffix = f"\n{detail}" if detail else ""
        raise RuntimeError(f"`git {' '.join(args)}` failed.{suffix}")


def default_cache_dir() -> Path:
    return Path(user_cache_dir("selkokortti")) / DATA_DIR_NAME


def resolve_data_dir(data_dir=None, no_update: bool = False) -> Path:
    """Return a directory containing the YYYY/MM/DD dataset tree.

    - If ``data_dir`` is given, it is used verbatim (no clone/pull).
    - Otherwise the dataset is cloned into the user cache dir on first use and
      refreshed (``git fetch`` + ``git reset --hard``) on subsequent runs unless
      ``no_update`` is set.
    """
    if data_dir is not None:
        path = Path(data_dir).expanduser()
        if not path.exists():
            raise RuntimeError(f"--data-dir does not exist: {path}")
        return path

    path = default_cache_dir()
    if not (path / ".git").exists():
        logger.info("Cloning Selkouutiset dataset into %s ...", path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            shutil.rmtree(path)
        try:
            _run_git(
                [
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    DATA_REPO_BRANCH,
                    DATA_REPO_URL,
                    str(path),
                ]
            )
        except RuntimeError as exc:
            raise RuntimeError(
                "Failed to download the Selkouutiset dataset. Check your network "
                "connection, or pass --data-dir pointing at a local checkout of "
                f"selkouutiset-scrape-cleaned.\n{exc}"
            ) from exc
    elif not no_update:
        logger.info("Refreshing Selkouutiset dataset in %s ...", path)
        _run_git(["fetch", "--depth", "1", "origin", DATA_REPO_BRANCH], cwd=path)
        _run_git(["reset", "--hard", f"origin/{DATA_REPO_BRANCH}"], cwd=path)
    else:
        logger.info("Using cached Selkouutiset dataset in %s (--no-update)", path)

    return path
